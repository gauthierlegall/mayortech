"""The internet demo is anonymous, synthetic and isolated from protected pilots."""
import base64
import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.auth import SessionStore, hash_password
from travaux.config import Settings
from travaux.repository import Repository

ORIGIN = "https://travaux.example"
HEADERS = {"X-Requested-With": "Travaux", "Origin": ORIGIN}


@pytest.fixture(autouse=True)
def no_external_connector_environment(monkeypatch):
    import os
    for name in list(os.environ):
        if name.startswith(("TRAVAUX_MISTRAL_", "TRAVAUX_EWS_", "TRAVAUX_EXCHANGE_", "TRAVAUX_APPFLOWY_")):
            monkeypatch.delenv(name)


def public_settings(tmp_path, **changes):
    values = {"mode": "public_demo", "db_path": tmp_path / "public-demo.sqlite3", "tenant_id": "public-fiction", "public_origin": ORIGIN, "allowed_hosts": ("travaux.example",)}
    return Settings(**(values | changes))


def test_public_demo_on_https_opens_without_password_authentication_cookie_or_login(tmp_path):
    settings = public_settings(tmp_path)
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        session = client.get("/api/v1/session")
        assert session.status_code == 200
        assert session.json() == {"authenticated": True, "demo": True, "public_demo": True, "auth_required": False, "actor": {"actor_id": "responsable-demo", "tenant_id": "public-fiction"}}
        cookie = session.headers.get("set-cookie", "")
        assert cookie.startswith("travaux_chat_session=")
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
        assert "Path=/api/v1" in cookie
        assert len(client.get("/api/v1/projects").json()) == 6
        assert set(client.cookies) == {"travaux_chat_session"}
        access = client.get("/api/v1/bootstrap").json()["access"]
        assert access == {"auth_required": False, "shared_demo": True, "mail_import": False, "signature_workflow": False}
        assert client.post("/api/v1/session", headers=HEADERS).json()["authenticated"]
        assert set(client.cookies) == {"travaux_chat_session"}
        assert client.delete("/api/v1/session", headers=HEADERS).json()["authenticated"]
        assert client.get("/api/v1/projects").status_code == 200


def test_public_demo_keeps_human_edits_reviews_pages_and_summaries_interactive(tmp_path):
    with TestClient(create_app(public_settings(tmp_path)), base_url=ORIGIN) as client:
        project = next(p for p in client.get("/api/v1/projects").json() if p["reference"] == "TRV-2026-014")
        action = next(r for r in client.get("/api/v1/reviews", params={"project_id": project["id"]}).json() if r["field"].startswith("action."))
        reviewed = client.post(f"/api/v1/reviews/{action['id']}/decision", headers=HEADERS, json={"decision": "accept"})
        assert reviewed.status_code == 200 and reviewed.json()["reviewed_by"] == "responsable-demo"
        note = client.post(f"/api/v1/projects/{project['id']}/notes", headers=HEADERS, json={"body": "Constat entièrement fictif : accès maintenu."})
        assert note.status_code == 201
        page = client.post(f"/api/v1/projects/{project['id']}/page", headers=HEADERS, json={}).json()
        saved = client.put(f"/api/v1/pages/{page['id']}/state", headers=HEADERS, json={"state_base64": base64.b64encode(b"synthetic-api-state").decode(), "expected_revision_hash": None, "text": "Note de page entièrement fictive", "editor_version": "blocksuite-0.22.4"})
        assert saved.status_code == 200
        summary = client.post(f"/api/v1/projects/{project['id']}/summaries", headers=HEADERS, json={})
        assert summary.status_code == 201 and "Note de page entièrement fictive" in summary.json()["content"]


def test_public_demo_blocks_mail_upload_and_remote_publication_before_payload_validation(tmp_path):
    with TestClient(create_app(public_settings(tmp_path)), base_url=ORIGIN) as client:
        before = client.get("/api/v1/imports").json()
        upload = client.post("/api/v1/imports/eml", headers=HEADERS, json={"content": "PRIVATE_FAKE_TEST_PAYLOAD"})
        assert upload.status_code == 403
        assert "fictif" in upload.json()["error"]["message"].lower()
        assert "PRIVATE_FAKE_TEST_PAYLOAD" not in upload.text
        assert client.post("/api/v1/summaries/anything/publish", headers=HEADERS, json={}).status_code == 403
        assert client.get("/api/v1/imports").json() == before
        assert client.post("/api/v1/demo/next-mail", headers=HEADERS, json={}).status_code == 200
        mails = client.get("/api/v1/mail").json()["items"]
        assert all(item["metadata"].get("fictitious") is True for item in mails)


def test_public_demo_still_rejects_cross_origin_and_unmarked_writes_behind_https_proxy(tmp_path):
    with TestClient(create_app(public_settings(tmp_path)), base_url=ORIGIN) as client:
        pid = client.get("/api/v1/projects").json()[0]["id"]
        path = f"/api/v1/projects/{pid}/notes"
        assert client.post(path, json={"body": "Fictif"}).status_code == 403
        assert client.post(path, headers={**HEADERS, "Origin": "https://other.example"}, json={"body": "Fictif"}).status_code == 403
        assert client.post(path, headers={**HEADERS, "sec-fetch-site": "cross-site"}, json={"body": "Fictif"}).status_code == 403
        # Caddy's upstream may use HTTP: browser Origin stays the declared HTTPS origin.
        assert client.post("http://travaux.example" + path, headers=HEADERS, json={"body": "Fictif derrière proxy"}).status_code == 201
        assert client.get("/api/v1/projects", headers={"host": "intruder.example"}).status_code == 400


@pytest.mark.parametrize("changes", [
    {"public_origin": "http://travaux.example"}, {"public_origin": ""},
    {"public_origin": "https://:FAKE_SECRET_MUST_NOT_ECHO@travaux.example"},
    {"allowed_hosts": ("*",)}, {"allowed_hosts": ("other.example",)},
    {"llm": "mistral", "egress_approved": True, "mistral_url": "https://llm.example/v1", "mistral_model": "test"},
    {"egress_approved": True}, {"mistral_url": "https://llm.example/v1"},
    {"mistral_model": "test"}, {"mistral_key": "FAKE_SECRET_MUST_NOT_ECHO"},
    {"appflowy_url": "https://workspace.example"},
])
def test_public_demo_rejects_insecure_or_real_connector_configuration(tmp_path, changes):
    with pytest.raises(ValueError) as error:
        public_settings(tmp_path, **changes)
    assert "FAKE_SECRET_MUST_NOT_ECHO" not in str(error.value)


@pytest.mark.parametrize("name", ["TRAVAUX_APPFLOWY_TOKEN", "TRAVAUX_APPFLOWY_CONFIG", "TRAVAUX_EWS_USERNAME", "TRAVAUX_EWS_PASSWORD", "TRAVAUX_EXCHANGE_CONFIG", "TRAVAUX_MISTRAL_KEY"])
def test_public_demo_rejects_connector_secrets_in_environment_even_for_direct_settings(tmp_path, monkeypatch, name):
    monkeypatch.setenv(name, "FAKE_SECRET_MUST_NOT_ECHO")
    with pytest.raises(ValueError) as error:
        public_settings(tmp_path)
    assert "FAKE_SECRET_MUST_NOT_ECHO" not in str(error.value)


def test_public_demo_requires_a_new_database_and_never_relabels_existing_private_data(tmp_path):
    path = tmp_path / "existing-pilot.sqlite3"
    repo = Repository(path)
    repo.create_project("institution", "PRIVATE-FAKE", "Fake private project must stay protected")
    repo.close()
    before = path.read_bytes()
    with pytest.raises(ValueError, match="séparée"):
        create_app(public_settings(tmp_path, db_path=path))
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='public_demo_metadata'").fetchone()


def test_public_demo_marker_allows_restart_only_for_the_same_tenant(tmp_path):
    settings = public_settings(tmp_path)
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        projects = client.get("/api/v1/projects").json()
        client.post(f"/api/v1/projects/{projects[0]['id']}/notes", headers=HEADERS, json={"body": "Note fictive conservée au redémarrage"}).raise_for_status()
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        assert [p["id"] for p in client.get("/api/v1/projects").json()] == [p["id"] for p in projects]
        assert "Note fictive conservée" in str(client.get(f"/api/v1/projects/{projects[0]['id']}").json()["notes"])
    with pytest.raises(ValueError):
        create_app(public_settings(tmp_path, tenant_id="other-tenant"))


def test_public_database_cannot_be_reused_as_protected_pilot_then_exposed_again(tmp_path):
    settings = public_settings(tmp_path)
    with TestClient(create_app(settings), base_url=ORIGIN):
        pass
    protected = Settings(mode="staging", db_path=settings.db_path, tenant_id=settings.tenant_id,
                         password_hash=hash_password("une phrase de passe institutionnelle"),
                         public_origin=ORIGIN, allowed_hosts=("travaux.example",))
    with pytest.raises(ValueError, match="réservée"):
        create_app(protected)


def test_public_demo_environment_defaults_to_separate_database(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAVAUX_MODE", "public_demo")
    monkeypatch.setenv("TRAVAUX_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("TRAVAUX_ALLOWED_HOSTS", "travaux.example")
    monkeypatch.delenv("TRAVAUX_DB", raising=False)
    assert str(Settings.from_env().db_path).replace("\\", "/") == "data/public-demo.sqlite3"


@pytest.mark.parametrize("mode", ["staging", "pilot"])
def test_public_demo_does_not_weaken_protected_modes(tmp_path, mode):
    options = {"mode": mode, "db_path": tmp_path / (mode + ".sqlite3"), "password_hash": hash_password("une phrase de passe institutionnelle"), "public_origin": ORIGIN, "allowed_hosts": ("travaux.example",)}
    if mode == "pilot":
        options.update(llm="mistral", mistral_url="https://authorized.example/v1", mistral_model="approved", egress_approved=True)
    with TestClient(create_app(Settings(**options)), base_url=ORIGIN) as client:
        assert not client.get("/api/v1/session").json()["authenticated"]
        assert client.get("/api/v1/projects").status_code == 401
        assert client.post("/api/v1/session", headers=HEADERS, json={"password": "wrong"}).status_code == 401
        assert client.post("/api/v1/session", headers=HEADERS, json={"password": "une phrase de passe institutionnelle"}).status_code == 200
        assert client.get("/api/v1/projects").status_code == 200
        client.delete("/api/v1/session", headers=HEADERS).raise_for_status()
        assert client.get("/api/v1/projects").status_code == 401


def test_protected_session_does_not_claim_foreign_tenant_cookie_authenticated(tmp_path):
    settings = Settings(mode="staging", db_path=tmp_path / "protected.sqlite3", tenant_id="institution", password_hash=hash_password("une phrase de passe institutionnelle"), public_origin=ORIGIN, allowed_hosts=("travaux.example",))
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        foreign_cookie = SessionStore(settings.db_path).issue("another-operator", "another-institution")
        client.cookies.set("travaux_session", foreign_cookie)
        session = client.get("/api/v1/session").json()
        assert not session["authenticated"] and session["actor"] is None
        assert client.get("/api/v1/projects").status_code == 401


@pytest.mark.parametrize("command", [["collect-exchange", "--config", "unread-private-config.json"], ["native-check"], ["native-sync-notes"]])
def test_public_demo_cli_refuses_real_collectors_before_reading_config(tmp_path, monkeypatch, capsys, command):
    from travaux.cli import _main
    monkeypatch.setenv("TRAVAUX_MODE", "public_demo")
    monkeypatch.setenv("TRAVAUX_DB", str(tmp_path / "public.sqlite3"))
    monkeypatch.setenv("TRAVAUX_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("TRAVAUX_ALLOWED_HOSTS", "travaux.example")
    monkeypatch.setattr(sys, "argv", ["travaux", *command])
    with pytest.raises(SystemExit) as error:
        _main()
    assert error.value.code == 2
    assert "public_demo" in capsys.readouterr().err
