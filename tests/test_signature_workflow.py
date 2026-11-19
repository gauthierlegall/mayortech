import hashlib
import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from travaux.api import create_app
from travaux.config import Settings
from travaux.domain import DomainError
from travaux.signature_workflow import advance_circuit, create_circuit, describe_circuit


PDF_SHA = hashlib.sha256(b"fictional document").hexdigest()


def test_approval_opens_signature_step_and_can_resume_from_snapshot():
    original = create_circuit(PDF_SHA)
    assert describe_circuit(original) == {"status": "review", "document_sha256": PDF_SHA}
    approved = advance_circuit(original, "approve")
    assert describe_circuit(approved) == {"status": "awaiting_signature", "document_sha256": PDF_SHA}
    assert describe_circuit(original)["status"] == "review"
    with pytest.raises(DomainError):
        advance_circuit(approved, "approve")


def test_rejection_closes_workflow_without_opening_signature():
    rejected = advance_circuit(create_circuit(PDF_SHA), "reject")
    assert describe_circuit(rejected)["status"] == "rejected"
    with pytest.raises(DomainError):
        advance_circuit(rejected, "approve")


def test_review_and_manual_confirmation_cannot_mark_document_signed():
    snapshot = advance_circuit(create_circuit(PDF_SHA), "approve")
    with pytest.raises(DomainError):
        advance_circuit(snapshot, "signed")
    assert describe_circuit(snapshot)["status"] == "awaiting_signature"


def test_circuit_in_api_enforces_identity_pdf_scope_and_revision(tmp_path, monkeypatch):
    monkeypatch.delenv("SSLKEYLOGFILE", raising=False)
    monkeypatch.delenv("QUICLOGDIR", raising=False)
    tenant, origin = "signature-test", "https://workflow.invalid"
    settings = Settings(mode="staging", auth_mode="oidc", tenant_id=tenant,
                        db_path=tmp_path / "test.sqlite3", public_origin=origin,
                        allowed_hosts=("workflow.invalid",), signature_workflow_enabled=True)
    app = create_app(settings)
    repo = app.state.repo
    project = repo.create_project(tenant, "SIG-1", "Chantier fictif")
    other = repo.create_project(tenant, "SIG-2", "Autre chantier fictif")
    source = repo.ingest_source(tenant, "test-pdf", "PDF test", "Fiche de recette", project_ref="SIG-1")
    pdf = PdfWriter()
    pdf.add_blank_page(400, 400)
    stream = io.BytesIO()
    pdf.write(stream)
    doc = app.state.documents.store(tenant, source["id"], stream.getvalue(), "recette.pdf", "application/pdf")

    def login(name, grant):
        user = app.state.identities.provision("https://identity.invalid", name, name, "editor")
        ident = user["actor_id"]
        repo._db.execute("INSERT INTO project_grants VALUES(?,?,?,?,?)", (tenant, ident, grant, "fixture", "today"))
        return app.state.sessions.issue(ident, tenant)

    submitter = login("déposant", project["id"])
    reviewer = login("relecteur", project["id"])
    other_reviewer = login("autre", other["id"])
    url = f"/api/v1/projects/{project['id']}/documents/{doc['id']}/signature-circuit"
    other_url = f"/api/v1/projects/{other['id']}/documents/{doc['id']}/signature-circuit"
    with TestClient(app, base_url=origin, headers={"X-Requested-With": "Travaux", "Origin": origin}) as client:
        assert client.get(url).status_code == 401
        client.cookies.set("travaux_session", other_reviewer)
        assert client.get(url).status_code == 404
        assert client.get(other_url).status_code == 404
        client.cookies.set("travaux_session", submitter)
        assert client.get(url).json()["status"] == "not_started"
        assert client.post(url, json={"document_sha256": PDF_SHA}).status_code == 409
        created = client.post(url, json={"document_sha256": doc["sha256"]})
        assert created.status_code == 201
        assert created.json()["status"] == "review"
        assert client.post(url, json={"document_sha256": doc["sha256"]}).json() == created.json()
        decision = {"decision": "approve", "revision": 1}
        assert client.patch(url, json=decision).status_code == 403
        client.cookies.set("travaux_session", reviewer)
        assert client.get(url).json()["can_decide"] is True
        approved = client.patch(url, json=decision)
        assert approved.status_code == 200
        assert approved.json()["status"] == "awaiting_signature"
        assert client.patch(url, json=decision).status_code == 409
        assert client.get(url).json() == approved.json()
