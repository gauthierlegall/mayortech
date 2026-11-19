from travaux.documents import extract_document
import io

import hashlib
from email.message import EmailMessage

import pytest

from travaux import documents as document_module
from travaux.domain import DomainError
from travaux.importing import import_mail
from travaux.jobs import JobQueue
from travaux.repository import Repository


def test_html_mail_never_fetches_remote_content_and_discards_scripts():
    result = extract_document("message.html", b'<p>Acces chantier ferme</p><script>sendSecret()</script><img src="https://tracker.example/x">')
    assert "Acces chantier ferme" in result["text"]
    assert "sendSecret" not in result["text"]
    assert result["status"] == "extracted"


def test_unknown_and_oversized_attachments_are_explicit_partial_coverage():
    assert extract_document("plan.dwg", b"opaque")["status"] == "unsupported"
    assert extract_document("large.txt", b"a" * 5_000_001)["status"] == "too_large"


def test_docx_is_extracted_in_isolated_process_and_scanned_pdf_requires_ocr():
    from docx import Document
    from pypdf import PdfWriter
    document = Document()
    document.add_paragraph("Note de chantier entièrement fictive.")
    data = io.BytesIO()
    document.save(data)
    result = extract_document("note-fictive.docx", data.getvalue())
    assert result["status"] == "extracted"
    assert "Note de chantier entièrement fictive." in result["text"]
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    pdf = io.BytesIO()
    writer.write(pdf)
    assert extract_document("scan-fictif.pdf", pdf.getvalue())["status"] == "ocr_required"


@pytest.fixture
def document_env(tmp_path):
    repo = Repository(tmp_path / "documents.sqlite3")
    queue = JobQueue(tmp_path / "jobs.sqlite3")
    project = repo.create_project("municipality-a", "DOC-2026-01", "Chantier entièrement fictif")
    assert hasattr(document_module, "DocumentRepository"), "Les vrais octets doivent avoir un dépôt durable"
    documents = document_module.DocumentRepository(repo)
    yield repo, queue, documents, project
    repo.close()


def test_original_document_repository_is_available():
    assert hasattr(document_module, "DocumentRepository"), "Le texte extrait ne doit pas remplacer les octets originaux"


def fictional_mail(*attachments, message_id="documents@fictif.invalid"):
    mail = EmailMessage()
    mail["From"] = "entreprise@fictif.invalid"
    mail["To"] = "travaux@fictif.invalid"
    mail["Subject"] = "[DOC-2026-01] Documents de chantier fictifs"
    mail["Message-ID"] = f"<{message_id}>"
    mail["Date"] = "Sat, 14 Nov 2026 10:00:00 +0100"
    mail.set_content("Documents fictifs. Avancement : accès maintenu.")
    for filename, content, media_type in attachments:
        main, sub = media_type.split("/", 1)
        mail.add_attachment(content, maintype=main, subtype=sub, filename=filename)
    return mail.as_bytes()


def test_original_mail_and_attachment_bytes_survive_reopen_and_source_links(document_env):
    repo, queue, documents, project = document_env
    content = b"devis fictif\x00\xff\r\n12345 EUR HT\n"
    raw = fictional_mail(("devis-fictif.txt", content, "text/plain"))
    imported = import_mail(repo, queue, "municipality-a", raw, metadata={"filename": "courrier-fictif.eml"})
    inventory = documents.list_project("municipality-a", project["id"])
    assert len(inventory) == 2
    email, attachment = next(d for d in inventory if d["kind"] == "email"), next(d for d in inventory if d["kind"] == "attachment")
    assert email["source_id"] == imported["source"]["id"]
    assert attachment["source_id"] == imported["related_sources"][0]["id"]
    assert attachment["parent_source_id"] == email["source_id"]
    assert attachment["sha256"] == hashlib.sha256(content).hexdigest()
    assert attachment["size"] == len(content)
    assert documents.download("municipality-a", email["id"])[1] == raw
    assert documents.download("municipality-a", attachment["id"])[1] == content
    path = repo.path
    repo.close()
    reopened = Repository(path)
    try:
        assert document_module.DocumentRepository(reopened).download("municipality-a", attachment["id"])[1] == content
    finally:
        reopened.close()


def test_replayed_import_keeps_same_documents_jobs_and_source_ids(document_env):
    repo, queue, documents, project = document_env
    raw = fictional_mail(("note.txt", b"Note fictive", "text/plain"))
    first = import_mail(repo, queue, "municipality-a", raw)
    before = documents.list_project("municipality-a", project["id"])
    second = import_mail(repo, queue, "municipality-a", raw)
    assert first["source"]["id"] == second["source"]["id"]
    assert first["job_ids"] == second["job_ids"]
    assert documents.list_project("municipality-a", project["id"]) == before


def test_unsupported_attachment_has_own_source_and_real_original_without_fake_preview(document_env):
    repo, queue, documents, project = document_env
    content = b"FICTIF-DWG\x00\xff"
    imported = import_mail(repo, queue, "municipality-a", fictional_mail(("plan.dwg", content, "application/octet-stream")))
    assert len(imported["related_sources"]) == 1
    attachment = next(d for d in documents.list_project("municipality-a", project["id"]) if d["kind"] == "attachment")
    assert attachment["available"] and not attachment["text_available"]
    assert attachment["extraction_status"] == "unsupported"
    assert attachment["preview_source_id"] is None
    assert documents.download("municipality-a", attachment["id"])[1] == content
    assert len(imported["job_ids"]) == 1  # Do not invent extraction work for opaque bytes.


def test_legacy_text_sources_never_become_reconstructed_originals(document_env):
    repo, queue, documents, project = document_env
    source = repo.ingest_source("municipality-a", "legacy", "[DOC-2026-01] Ancien mail", "Texte extrait seulement", metadata={"filename": "ancien.eml", "attachments": [{"filename": "ancien-plan.dwg", "sha256": "a" * 64, "status": "unsupported"}]})
    inventory = documents.list_project("municipality-a", project["id"])
    assert len(inventory) == 2
    assert all(not d["available"] and d["download_url"] is None and d["id"] is None for d in inventory)
    mail = next(d for d in inventory if d["kind"] == "email")
    attachment = next(d for d in inventory if d["kind"] == "attachment")
    assert mail["preview_source_id"] == source["id"]
    assert attachment["preview_source_id"] is None
    assert attachment["filename"] == "ancien-plan.dwg"


def test_legacy_inventory_keeps_opaque_sibling_even_when_other_part_has_text_source(document_env):
    repo, queue, documents, project = document_env
    parent = repo.ingest_source("municipality-a", "mixed-legacy", "[DOC-2026-01] Ancien mail mixte", "Deux pièces fictives", metadata={"attachments": [{"filename": "note.txt", "status": "extracted"}, {"filename": "plan.dwg", "status": "unsupported"}]})
    repo.ingest_source("municipality-a", "legacy-text-part", "Pièce jointe", "Note déjà extraite", project_ref="DOC-2026-01", metadata={"parent_source_id": parent["id"], "filename": "note.txt", "extraction_status": "extracted"})
    inventory = documents.list_project("municipality-a", project["id"])
    assert len(inventory) == 3
    assert len([item for item in inventory if item["filename"] == "plan.dwg" and not item["available"]]) == 1


def test_documents_are_tenant_scoped_and_project_inventory_requires_real_link(document_env):
    repo, queue, documents, project = document_env
    other = repo.create_project("municipality-b", "DOC-2026-01", "Autre collectivité fictive")
    imported = import_mail(repo, queue, "municipality-a", fictional_mail(("note.txt", b"A seulement", "text/plain")))
    item = documents.list_project("municipality-a", project["id"])[0]
    assert documents.list_project("municipality-b", other["id"]) == []
    with pytest.raises(DomainError, match="introuvable"):
        documents.download("municipality-b", item["id"])
    with pytest.raises(DomainError):
        documents.list_project("municipality-b", project["id"])
    with pytest.raises(DomainError):
        documents.store("municipality-b", imported["source"]["id"], b"X", "injection.txt", "text/plain")


def test_same_filename_different_content_is_not_a_claim_of_verified_document_versions(document_env):
    repo, queue, documents, project = document_env
    for n in [1, 2]:
        import_mail(repo, queue, "municipality-a", fictional_mail(("devis.pdf.txt", f"Devis fictif {n}".encode(), "text/plain"), message_id=f"document-{n}@fictif.invalid"))
    items = [d for d in documents.list_project("municipality-a", project["id"]) if d["kind"] == "attachment"]
    assert len(items) == 2 and len({d["sha256"] for d in items}) == 2
    assert all("version" not in d and "superseded" not in d for d in items)


def test_source_and_binary_storage_roll_back_together_if_part_cannot_be_saved(document_env, monkeypatch):
    repo, queue, documents, project = document_env
    actual = document_module.DocumentRepository.store
    def fail_attachment(self, tenant, source_id, content, filename, media_type, **kwargs):
        if filename == "note.txt":
            raise OSError("Synthetic storage failure")
        return actual(self, tenant, source_id, content, filename, media_type, **kwargs)
    monkeypatch.setattr(document_module.DocumentRepository, "store", fail_attachment)
    with pytest.raises(OSError):
        import_mail(repo, queue, "municipality-a", fictional_mail(("note.txt", b"Fictif", "text/plain")))
    assert repo.list_sources("municipality-a") == []
    assert documents.list_project("municipality-a", project["id"]) == []
    assert queue.list("municipality-a") == []


def test_shared_database_mail_sources_documents_and_jobs_obey_outer_unit_of_work(tmp_path):
    path = tmp_path / "shared.sqlite3"
    repo, queue = Repository(path), JobQueue(path)
    try:
        project = repo.create_project("municipality-a", "DOC-2026-01", "Chantier fictif")
        documents = document_module.DocumentRepository(repo)
        with pytest.raises(RuntimeError, match="Synthetic outer rollback"):
            with repo._transaction():
                import_mail(repo, queue, "municipality-a", fictional_mail(("note.txt", b"Fictif", "text/plain")))
                raise RuntimeError("Synthetic outer rollback")
        assert repo.list_sources("municipality-a") == []
        assert documents.list_project("municipality-a", project["id"]) == []
        assert queue.list("municipality-a") == []
    finally:
        repo.close()


def document_client(repo, tenant, authenticated=True):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient
    app = FastAPI()
    @app.exception_handler(DomainError)
    async def error(request, exc):
        return JSONResponse({"code": exc.code}, status_code=401 if exc.code == "unauthenticated" else 404)
    def actor():
        if not authenticated:
            raise DomainError("unauthenticated", "Session requise")
        return {"actor_id": "responsable-fictif", "tenant_id": tenant}
    document_module.register_document_routes(app, repo, tenant, actor)
    return TestClient(app)


def test_document_routes_require_session_and_download_exact_bytes_as_attachment(document_env):
    repo, queue, documents, project = document_env
    raw = fictional_mail(("note.html", b'<script>mustNotExecute()</script><p>Fictif</p>', "text/html"))
    import_mail(repo, queue, "municipality-a", raw)
    item = next(d for d in documents.list_project("municipality-a", project["id"]) if d["kind"] == "attachment")
    with document_client(repo, "municipality-a", authenticated=False) as client:
        assert client.get(f"/api/v1/projects/{project['id']}/documents").status_code == 401
        assert client.get(item["download_url"]).status_code == 401
    with document_client(repo, "municipality-a") as client:
        inventory = client.get(f"/api/v1/projects/{project['id']}/documents").json()
        assert inventory["total"] == 2 and all("content" not in d and "bytes" not in d for d in inventory["items"])
        response = client.get(item["download_url"])
        assert response.status_code == 200 and response.content == b'<script>mustNotExecute()</script><p>Fictif</p>'
        assert response.headers["content-type"] == "application/octet-stream"
        assert response.headers["content-disposition"].startswith("attachment;")
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in response.headers["content-security-policy"]
    with document_client(repo, "municipality-b") as client:
        assert client.get(item["download_url"]).status_code == 404


def test_download_filename_cannot_inject_headers_or_paths(document_env):
    repo, queue, documents, project = document_env
    source = repo.ingest_source("municipality-a", "hostile-name", "[DOC-2026-01] Pièce fictive", "Contenu fictif")
    original = '..\\../../dossier/plan "fictif"\r\nX-Evil: oui.html'
    item = documents.store("municipality-a", source["id"], b"<h1>Fictif</h1>", original, "text/html")
    assert item["original_filename"] == original
    assert "/" not in item["filename"] and "\\" not in item["filename"] and "\r" not in item["filename"] and "\n" not in item["filename"]
    with document_client(repo, "municipality-a") as client:
        response = client.get(item["download_url"])
        assert response.status_code == 200 and "x-evil" not in response.headers
        assert "\r" not in response.headers["content-disposition"] and "\n" not in response.headers["content-disposition"]


def test_original_cannot_be_bound_to_source_with_different_recorded_raw_hash(document_env):
    repo, queue, documents, project = document_env
    source = repo.ingest_source("municipality-a", "hash-proof", "[DOC-2026-01] Original fictif", "Texte fictif", metadata={"raw_sha256": hashlib.sha256(b"original A").hexdigest()})
    with pytest.raises(DomainError):
        documents.store("municipality-a", source["id"], b"different B", "original.txt", "text/plain")
    assert not any(item["available"] for item in documents.list_project("municipality-a", project["id"]))


def test_download_refuses_bytes_no_longer_matching_immutable_hash(document_env):
    repo, queue, documents, project = document_env
    import_mail(repo, queue, "municipality-a", fictional_mail(("note.txt", b"Original fictif", "text/plain")))
    item = next(d for d in documents.list_project("municipality-a", project["id"]) if d["kind"] == "attachment")
    with repo._transaction() as db:
        db.execute("UPDATE original_documents SET content=? WHERE tenant_id=? AND id=?", (b"Alteration fictive", "municipality-a", item["id"]))
    with pytest.raises(DomainError):
        documents.download("municipality-a", item["id"])
