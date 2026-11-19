from fastapi.testclient import TestClient
import base64
import hashlib

from travaux.api import create_app
from travaux.config import Settings
from travaux.auth import hash_password


HEADERS = {"X-Requested-With": "Travaux"}


def test_full_memory_review_note_summary_and_exact_approval(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / "app.sqlite3"))) as client:
        assert client.get("/api/v1/session").json()["demo"]
        projects = client.get("/api/v1/projects").json()
        project = next(p for p in projects if p["reference"] == "TRV-2026-014")
        reviews = client.get("/api/v1/reviews").json()
        update = next(r for r in reviews if r["project_id"] == project["id"] and r["field"] == "progress")
        assert update["conflict_with"]
        assert client.post(f"/api/v1/reviews/{update['id']}/decision", json={"decision":"accept"}, headers=HEADERS).status_code == 409
        assert client.post(f"/api/v1/reviews/{update['id']}/decision", json={"decision":"replace"}, headers=HEADERS).status_code == 200
        client.post(f"/api/v1/projects/{project['id']}/notes", json={"body":"Maintenir un passage pour les poussettes."}, headers=HEADERS).raise_for_status()
        summary = client.post(f"/api/v1/projects/{project['id']}/summaries", json={}, headers=HEADERS).json()
        assert "Maintenir un passage" in summary["content"]
        assert "Terrassement terminé" in summary["content"]
        payload = {"expected_content_hash":"wrong", "expected_snapshot_hash":summary["snapshot_hash"], "expected_project_revision":summary["project_revision"]}
        assert client.post(f"/api/v1/summaries/{summary['id']}/approve", json=payload, headers=HEADERS).status_code == 409
        payload["expected_content_hash"] = summary["content_hash"]
        assert client.post(f"/api/v1/summaries/{summary['id']}/approve", json=payload, headers=HEADERS).status_code == 200
        exported = client.get(f"/api/v1/summaries/{summary['id']}/export?format=md")
        assert exported.status_code == 200
        assert "Terrassement terminé" in exported.text
        assert client.get("/api/v1/projects/not-this-tenant").status_code == 404


def test_cross_site_writes_and_oversized_body_are_rejected(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / "app.sqlite3"))) as client:
        assert client.post("/api/v1/demo/next-mail", json={}).status_code == 403
        assert client.post("/api/v1/demo/next-mail", json={}, headers={**HEADERS,"Origin":"https://attacker.example"}).status_code == 403
        assert client.post("/api/v1/imports/eml", content=b"x" * 3_100_000, headers=HEADERS).status_code == 413
        assert client.get("/", headers={"host":"attacker.example"}).status_code == 400


def test_pilot_requires_session_and_accepts_public_origin_behind_tls_proxy(tmp_path):
    settings = Settings(mode="pilot", db_path=tmp_path / "pilot.sqlite3", tenant_id="institution", password_hash=hash_password("une phrase de passe institutionnelle"), public_origin="https://travaux.example", allowed_hosts=("travaux.example",), llm="mistral", mistral_url="https://authorized.example/v1/chat/completions", mistral_model="approved", egress_approved=True)
    with TestClient(create_app(settings), base_url="https://travaux.example") as client:
        assert client.get("/api/v1/projects").status_code == 401
        assert client.post("/api/v1/session", json={"password":"incorrect"}, headers=HEADERS).status_code == 401
        # The actual upstream may be HTTP while the configured browser origin is HTTPS.
        upstream = client.post("http://travaux.example/api/v1/session", json={"password":"une phrase de passe institutionnelle"}, headers={**HEADERS, "Origin":"https://travaux.example"})
        assert upstream.status_code == 200
        assert "Secure" in upstream.headers["set-cookie"]
        assert "HttpOnly" in upstream.headers["set-cookie"]
        assert client.get("/api/v1/projects").json() == []
        client.delete("/api/v1/session", headers=HEADERS).raise_for_status()
        assert client.get("/api/v1/projects").status_code == 401


def test_binary_eml_import_preserves_original_bytes_and_decodes_declared_charset(tmp_path):
    raw = b'Subject: [TRV-2026-014] Test fictif\r\nMessage-ID: <binary@fictif.invalid>\r\nContent-Type: text/plain; charset=iso-8859-1\r\nContent-Transfer-Encoding: 8bit\r\n\r\nAvancement : Caf\xe9 accessible\r\n'
    with TestClient(create_app(Settings(db_path=tmp_path / "binary.sqlite3"))) as client:
        result = client.post("/api/v1/imports/eml", json={"filename":"fictif.eml", "content_base64":base64.b64encode(raw).decode()}, headers=HEADERS)
        result.raise_for_status()
        source = result.json()["source"]
        assert source["metadata"]["raw_sha256"] == hashlib.sha256(raw).hexdigest()
        assert "Café accessible" in source["body"]


def test_request_validation_does_not_echo_invalid_sensitive_payload(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / "validation.sqlite3"))) as client:
        result = client.post("/api/v1/session", json={"password":"fictif", "unexpected":"DO_NOT_ECHO_FAKE_SECRET"}, headers=HEADERS)
        assert result.status_code == 422
        assert "DO_NOT_ECHO_FAKE_SECRET" not in result.text
