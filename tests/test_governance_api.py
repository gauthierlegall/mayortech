"""The same Casbin permissions guard HTTP routes, not just an organisation screen."""
import base64

from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.auth import SessionStore, hash_password
from travaux.config import Settings

ORIGIN = "https://travaux.example"
HEADERS = {"X-Requested-With": "Travaux", "Origin": ORIGIN}


def protected(tmp_path):
    return Settings(mode="staging", db_path=tmp_path / "protected.sqlite3", tenant_id="town-a",
                    password_hash=hash_password("une phrase de passe fictive"), public_origin=ORIGIN,
                    allowed_hosts=("travaux.example",))


def login_as(client, app, settings, actor_id, role):
    app.state.governance.bind_role(actor_id, role)
    token = SessionStore(settings.db_path).issue(actor_id, settings.tenant_id)
    client.cookies.set("travaux_session", token)


def test_governance_is_registered_in_the_real_app_and_public_bootstrap_exposes_effective_rights(tmp_path):
    settings = Settings(mode="public_demo", db_path=tmp_path / "public.sqlite3", tenant_id="public-fictitious",
                        public_origin=ORIGIN, allowed_hosts=("travaux.example",))
    with TestClient(create_app(settings), base_url=ORIGIN) as client:
        assert client.get("/api/v1/organization").status_code == 200
        bootstrap = client.get("/api/v1/bootstrap").json()
        assert bootstrap["role"] == "visitor"
        assert bootstrap["permissions"]["workspace"]["write"]
        assert bootstrap["permissions"]["mail"]["flags"]
        assert not bootstrap["permissions"]["mail"]["write"]
        assert not bootstrap["permissions"]["organization"]["write"]
        assert client.get("/api/v1/organization/members").json()["items"][0]["display_name"] == "Visiteur"


def test_reader_can_open_native_page_factory_but_cannot_change_content_or_profile(tmp_path):
    settings = protected(tmp_path)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        login_as(client, app, settings, "reader-test", "reader")
        project = client.get("/api/v1/projects").json()[0]
        assert client.get(f"/api/v1/projects/{project['id']}").status_code == 200
        factory = client.post(f"/api/v1/projects/{project['id']}/page", json={}, headers=HEADERS)
        assert factory.status_code == 200
        page_id = factory.json()["id"]
        state = {"state_base64": base64.b64encode(b"fictitious-state").decode(), "expected_revision_hash": None, "text": "Must not be saved"}
        assert client.put(f"/api/v1/pages/{page_id}/state", json=state, headers=HEADERS).status_code == 403
        assert client.post(f"/api/v1/projects/{project['id']}/notes", json={"body": "Must not be saved"}, headers=HEADERS).status_code == 403
        assert client.get("/api/v1/organization").status_code == 200
        assert client.patch("/api/v1/organization", json={"name": "Forbidden", "service": "Forbidden", "expected_revision": 0}, headers=HEADERS).status_code == 403
        assert client.get("/api/v1/organization/audit").status_code == 403
        assert "Must not be saved" not in str(client.get(f"/api/v1/projects/{project['id']}").json())


def test_editor_changes_workspace_and_reads_audit_but_cannot_manage_organisation(tmp_path):
    settings = protected(tmp_path)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        login_as(client, app, settings, "editor-test", "editor")
        project = client.get("/api/v1/projects").json()[0]
        assert client.post(f"/api/v1/projects/{project['id']}/notes", json={"body": "Constat entièrement fictif de test"}, headers=HEADERS).status_code == 201
        assert client.get("/api/v1/organization/audit").status_code == 200
        assert client.get("/api/v1/organization/members").status_code == 200
        assert client.patch("/api/v1/organization", json={"name": "Forbidden", "service": "Forbidden", "expected_revision": 0}, headers=HEADERS).status_code == 403


def test_literal_admin_identity_or_role_header_cannot_obtain_privileges(tmp_path):
    settings = protected(tmp_path)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        token = SessionStore(settings.db_path).issue("admin", settings.tenant_id)
        client.cookies.set("travaux_session", token)
        assert client.get("/api/v1/projects", headers={"X-Role": "admin"}).status_code == 403
        assert client.get("/api/v1/organization", headers={"X-Role": "admin"}).status_code == 403
        assert client.get("/api/v1/bootstrap").status_code == 403


def test_administrator_profile_update_is_guarded_and_in_real_journal(tmp_path):
    settings = protected(tmp_path)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/api/v1/organization").status_code == 401
        client.post("/api/v1/session", json={"password": "une phrase de passe fictive"}, headers=HEADERS).raise_for_status()
        profile = client.get("/api/v1/organization").json()
        response = client.patch("/api/v1/organization", json={"name": "Collectivité fictive", "service": "Travaux", "expected_revision": profile["revision"]}, headers=HEADERS)
        assert response.status_code == 200
        assert any(row["action"] == "organization.updated" for row in client.get("/api/v1/organization/audit").json()["items"])


def test_public_mailbox_allows_fictional_flags_but_no_server_draft_or_send(tmp_path):
    settings = Settings(mode="public_demo", db_path=tmp_path / "public-mail.sqlite3", tenant_id="public-fictitious",
                        public_origin=ORIGIN, allowed_hosts=("travaux.example",))
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        capabilities = client.get("/api/v1/mailbox/capabilities")
        assert capabilities.status_code == 200
        assert capabilities.json() == {"can_send": False, "server_drafts": False, "can_compose": False, "can_manage_flags": True, "provider_status": "not_connected"}
        message = client.get("/api/v1/mailbox/messages").json()["items"][0]
        original = app.state.repo.get_source(settings.tenant_id, message["id"])
        changed = client.patch(f"/api/v1/mailbox/messages/{message['id']}", headers=HEADERS, json={"folder": "archive", "starred": True, "read": True})
        assert changed.status_code == 200 and changed.json()["folder"] == "archive"
        assert app.state.repo.get_source(settings.tenant_id, message["id"]) == original
        assert client.get("/api/v1/mailbox/drafts").status_code == 403
        assert client.post("/api/v1/mailbox/drafts", headers=HEADERS, json={"subject": "Must not persist", "body": "Must not persist"}).status_code == 403
        assert client.post("/api/v1/mailbox/send", headers=HEADERS, json={}).status_code == 403


def test_reader_mail_capabilities_and_draft_routes_match_the_same_permissions(tmp_path):
    settings = protected(tmp_path)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        login_as(client, app, settings, "reader-mail", "reader")
        caps = client.get("/api/v1/mailbox/capabilities").json()
        assert not caps["server_drafts"] and not caps["can_compose"] and not caps["can_manage_flags"]
        message = client.get("/api/v1/mailbox/messages").json()["items"][0]
        assert client.patch(f"/api/v1/mailbox/messages/{message['id']}", headers=HEADERS, json={"read": True}).status_code == 403
        assert client.post("/api/v1/mailbox/drafts", headers=HEADERS, json={"subject": "Must not persist"}).status_code == 403


def test_private_drafts_are_owned_by_current_actor_and_send_never_claims_success(tmp_path):
    settings = protected(tmp_path)
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        login_as(client, app, settings, "editor-one", "editor")
        caps = client.get("/api/v1/mailbox/capabilities").json()
        assert caps["server_drafts"] and caps["can_compose"] and not caps["can_send"]
        draft = client.post("/api/v1/mailbox/drafts", headers=HEADERS, json={"to": ["fictif@example.invalid"], "subject": "Brouillon fictif", "body": "Ne pas envoyer"})
        assert draft.status_code == 201
        draft_id = draft.json()["id"]
        send = client.post("/api/v1/mailbox/send", headers=HEADERS, json={"draft_id": draft_id})
        assert send.status_code == 503 and send.json()["error"]["code"] == "mail_transport_not_configured"
        assert client.get(f"/api/v1/mailbox/drafts/{draft_id}").json()["body"] == "Ne pas envoyer"
        assert next(folder for folder in client.get("/api/v1/mailbox/folders").json()["items"] if folder["id"] == "sent")["total"] == 0
        client.cookies.clear()
        login_as(client, app, settings, "editor-two", "editor")
        assert client.get(f"/api/v1/mailbox/drafts/{draft_id}").status_code == 404


def test_public_mail_flags_require_fictitious_metadata_and_source_tenant_ownership(tmp_path):
    settings = Settings(mode="public_demo", db_path=tmp_path / "public-flags.sqlite3", tenant_id="public-fictitious",
                        public_origin=ORIGIN, allowed_hosts=("travaux.example",))
    app = create_app(settings)
    with TestClient(app, base_url=ORIGIN) as client:
        # Synthetic records deliberately lack approval markers: the boundary must still refuse them.
        unapproved = app.state.repo.ingest_source(settings.tenant_id, "fake-unapproved", "Test fictif non approuvé", "Fictif", metadata={"fictitious": False})
        foreign = app.state.repo.ingest_source("another-tenant", "fake-foreign", "Autre espace fictif", "Fictif", metadata={"fictitious": True})
        assert client.patch(f"/api/v1/mailbox/messages/{unapproved['id']}", headers=HEADERS, json={"read": True}).status_code == 403
        assert client.patch(f"/api/v1/mailbox/messages/{foreign['id']}", headers=HEADERS, json={"read": True}).status_code == 404
