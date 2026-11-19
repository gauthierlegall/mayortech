from pathlib import Path

import pytest

from travaux.config import Settings, ensure_public_demo_database
from travaux.document_review import DocumentReviewService
from travaux.documents import DocumentRepository
from travaux.domain import DomainError
from travaux.jobs import JobQueue
from travaux.repository import Repository
from travaux.storyline import seed_storyline

TENANT = "demo-review"
FIXTURES = Path(__file__).parents[1] / "fixtures/storylines/lovable-v1"


def actor(tenant=TENANT, *, write=True):
    return {
        "tenant_id": tenant,
        "actor_id": "responsable-demo",
        "permissions": {"workspace": {"read": True, "write": write}},
    }


@pytest.fixture
def scenario(tmp_path):
    path = tmp_path / "public-demo.sqlite3"
    ensure_public_demo_database(
        Settings(
            mode="public_demo",
            db_path=path,
            tenant_id=TENANT,
            public_origin="https://demo.invalid",
            allowed_hosts=("demo.invalid",),
        )
    )
    repo = Repository(path)
    manifest = seed_storyline(repo, JobQueue(path), TENANT, FIXTURES)
    service = DocumentReviewService(repo)
    yield repo, manifest, service
    repo.close()


def test_fixture_catalogue_is_a_proven_baseline_not_a_human_review(scenario):
    repo, fixture, service = scenario
    data = service.list_project(TENANT, fixture["projects"]["portail"], actor=actor())
    rows = {row["document_id"]: row for row in data["items"]}
    first, second = [rows[item["document_id"]] for item in fixture["document_catalog"]]
    assert first["status"] == "approved" and second["status"] == "under_review"
    assert first["origin"] == "fixture_catalogue" and first["reviewer"] is None
    assert first["source_id"] == fixture["mail_sources"]["m2"]
    for row in rows.values():
        for evidence in row["evidence"].values():
            source = repo.get_source(TENANT, evidence["source_id"])
            assert source["body"][evidence["start"] : evidence["end"]] == evidence["quote"]
            assert source["body_hash"] == evidence["source_hash"]


def test_human_approval_creates_exact_note_and_preserves_originals_facts_and_v1(scenario):
    repo, fixture, service = scenario
    project = fixture["projects"]["portail"]
    before = repo.get_memory(TENANT, project)
    second = fixture["document_catalog"][1]
    original = DocumentRepository(repo).download(TENANT, second["document_id"])[1]
    decision = service.decide(
        TENANT,
        second["document_id"],
        decision="approve",
        expected_project_revision=before["project"]["revision"],
        reason="Montant et périmètre relus dans le scénario fictif.",
        actor=actor(),
    )
    assert decision["status"] == "approved" and decision["status_label"] == "Validé"
    assert decision["origin"] == "human_decision" and decision["reviewer"] == "responsable-demo"
    assert decision["document_source_id"] == second["source_id"]
    assert decision["sha256"] == second["sha256"]
    assert decision["source_id"] != second["source_id"]
    note_source = repo.get_source(TENANT, decision["source_id"])
    assert second["filename"] in note_source["body"] and "Validé" in note_source["body"]
    assert "Montant et périmètre relus" in note_source["body"]
    after = repo.get_memory(TENANT, project)
    assert len(after["notes"]) == len(before["notes"]) + 1
    assert after["project"]["revision"] == before["project"]["revision"] + 1
    assert after["facts"] == before["facts"] and after["pending"] == before["pending"]
    assert DocumentRepository(repo).download(TENANT, second["document_id"])[1] == original
    first = next(
        row
        for row in service.list_project(TENANT, project, actor=actor())["items"]
        if row["document_id"] == fixture["document_catalog"][0]["document_id"]
    )
    assert first["status"] == "approved" and first["origin"] == "fixture_catalogue"
    assert repo.get_summary(TENANT, fixture["summary_ids"]["portail_current"])["stale"]


def test_stale_revision_does_not_create_a_note_or_decision(scenario):
    repo, fixture, service = scenario
    project = fixture["projects"]["portail"]
    before = repo.get_memory(TENANT, project)
    with pytest.raises(DomainError) as rejected:
        service.decide(
            TENANT,
            fixture["document_catalog"][1]["document_id"],
            decision="approve",
            expected_project_revision=before["project"]["revision"] - 1,
            actor=actor(),
        )
    assert rejected.value.code == "stale_revision"
    assert repo.get_memory(TENANT, project) == before


def test_review_is_durable_and_return_to_under_review_keeps_history(scenario):
    repo, fixture, service = scenario
    project = fixture["projects"]["portail"]
    document = fixture["document_catalog"][1]["document_id"]
    first = service.decide(
        TENANT,
        document,
        decision="approve",
        expected_project_revision=repo.get_project(TENANT, project)["revision"],
        actor=actor(),
    )
    second = service.decide(
        TENANT,
        document,
        decision="under_review",
        expected_project_revision=first["project_revision"],
        reason="Relecture à compléter",
        actor=actor(),
    )
    reopened = DocumentReviewService(repo).list_project(TENANT, project, actor=actor())
    current = next(row for row in reopened["items"] if row["document_id"] == document)
    assert current["status"] == "under_review" and current["source_id"] == second["source_id"]
    assert first["source_id"] != second["source_id"]
    assert "Validé" in repo.get_source(TENANT, first["source_id"])["body"]


def test_foreign_tenant_reader_email_and_ambiguous_project_are_rejected(scenario):
    repo, fixture, service = scenario
    project = fixture["projects"]["portail"]
    document = fixture["document_catalog"][1]["document_id"]
    revision = repo.get_project(TENANT, project)["revision"]
    for current in (actor("foreign"), actor(write=False)):
        with pytest.raises(DomainError):
            service.decide(
                TENANT, document, decision="approve", expected_project_revision=revision, actor=current
            )
    with pytest.raises(DomainError):
        service.list_project("foreign", project, actor=actor("foreign"))
    email = next(
        row for row in DocumentRepository(repo).list_project(TENANT, project) if row["kind"] == "email"
    )
    with pytest.raises(DomainError):
        service.decide(
            TENANT, email["id"], decision="approve", expected_project_revision=revision, actor=actor()
        )
    other = fixture["projects"]["voirie"]
    with repo._transaction() as db:
        db.execute(
            "INSERT INTO source_links VALUES(?,?,?,?,?)",
            (TENANT, fixture["document_catalog"][1]["source_id"], other, "migration-test", "2026-11-15"),
        )
    with pytest.raises(DomainError):
        service.decide(
            TENANT, document, decision="approve", expected_project_revision=revision, actor=actor()
        )


def test_transaction_failure_keeps_note_event_and_review_uncommitted(scenario, monkeypatch):
    repo, fixture, service = scenario
    project = fixture["projects"]["portail"]
    before = repo.get_memory(TENANT, project)
    add_note = repo.add_note

    def fail_after_note(*args, **kwargs):
        add_note(*args, **kwargs)
        raise RuntimeError("synthetic decision failure")

    monkeypatch.setattr(repo, "add_note", fail_after_note)
    with pytest.raises(RuntimeError):
        service.decide(
            TENANT,
            fixture["document_catalog"][1]["document_id"],
            decision="approve",
            expected_project_revision=before["project"]["revision"],
            actor=actor(),
        )
    assert repo.get_memory(TENANT, project) == before
    current = service.list_project(TENANT, project, actor=actor())["items"]
    assert all(row["origin"] == "fixture_catalogue" for row in current)


def test_filename_and_latest_original_never_imply_approval(scenario):
    repo, _, service = scenario
    project = repo.create_project(TENANT, "TEST-NON-VALIDE", "Pièce sans décision")
    source = repo.ingest_source(
        TENANT,
        "undecided@example.invalid",
        "Pièce fictive",
        "Texte sans validation.",
        project_ref=project["reference"],
        metadata={"fictitious": True},
    )
    document = DocumentRepository(repo).store(
        TENANT,
        source["id"],
        b"fictional undecided original",
        "devis-valide-version-99.pdf",
        "application/pdf",
    )
    row = service.list_project(TENANT, project["id"], actor=actor())["items"][0]
    assert row["document_id"] == document["id"]
    assert row["status"] == "unknown" and row["origin"] == "none"
    assert row["source_id"] is None and row["evidence"] == {}


def test_http_contract_validation_and_note_proof(scenario):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient
    from travaux.document_review import register_document_review_routes

    repo, fixture, _ = scenario
    app = FastAPI()
    current = actor()
    register_document_review_routes(app, repo, TENANT, lambda: current)

    @app.exception_handler(DomainError)
    def failure(request, error):
        return JSONResponse(
            {"error": {"code": error.code, "message": str(error)}},
            status_code=403 if error.code == "forbidden" else 409,
        )

    client = TestClient(app)
    project = fixture["projects"]["portail"]
    document = fixture["document_catalog"][1]["document_id"]
    initial = client.get(f"/api/v1/projects/{project}/document-reviews")
    assert initial.status_code == 200 and len(initial.json()["items"]) == 2
    revision = initial.json()["project_revision"]
    for invalid in (
        {"decision": "approve", "expected_project_revision": True},
        {"decision": "replace", "expected_project_revision": revision},
        {"decision": "approve", "expected_project_revision": revision, "actor_id": "pretend-admin"},
    ):
        assert client.post(f"/api/v1/documents/{document}/decision", json=invalid).status_code == 422
    current["permissions"]["workspace"]["write"] = False
    assert (
        client.post(
            f"/api/v1/documents/{document}/decision",
            json={"decision": "approve", "expected_project_revision": revision},
        ).status_code
        == 403
    )
    current["permissions"]["workspace"]["write"] = True
    saved = client.post(
        f"/api/v1/documents/{document}/decision",
        json={"decision": "approve", "expected_project_revision": revision},
    )
    assert saved.status_code == 200
    proof = saved.json()["evidence"]["status"]
    assert proof["source_id"] == saved.json()["source_id"]
    assert proof["source_hash"] == repo.get_source(TENANT, proof["source_id"])["body_hash"]
    assert (
        client.post(
            f"/api/v1/documents/{document}/decision",
            json={"decision": "under_review", "expected_project_revision": revision},
        ).status_code
        == 409
    )
