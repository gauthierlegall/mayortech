import hashlib
import json
import threading
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from travaux.config import Settings
from travaux.connection_hub import ConnectionHub, IntegrationPolicy
from travaux.domain import DomainError
from travaux.mail_oauth import OAuthMailService
from travaux.repository import Repository

ADMIN = {"actor_id": "agent-a", "tenant_id": "commune", "permissions": {"organization": {"write": True}}}
HOSTS = ("accounts.google.com", "oauth2.googleapis.com", "gmail.googleapis.com", "login.microsoftonline.com", "graph.microsoft.com")


class Governance:
    allowed = True

    def require_authorized(self, actor, resource, action):
        if not self.allowed or actor["actor_id"] != "agent-a" or actor["tenant_id"] != "commune":
            raise DomainError("forbidden", "Accès retiré.")

    def permissions(self, actor):
        return {"organization": {"write": self.allowed}}


def configured(monkeypatch):
    monkeypatch.setenv("TRAVAUX_GOOGLE_OAUTH_CLIENT_ID", "municipal-test.apps.googleusercontent.com")
    monkeypatch.setenv("TRAVAUX_GOOGLE_OAUTH_CLIENT_SECRET", "test-google-secret")
    monkeypatch.setenv("TRAVAUX_GOOGLE_OAUTH_ALLOWED_DOMAINS", "commune.example")
    monkeypatch.setenv("TRAVAUX_MICROSOFT_OAUTH_CLIENT_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("TRAVAUX_MICROSOFT_OAUTH_CLIENT_SECRET", "test-microsoft-secret")
    monkeypatch.setenv("TRAVAUX_MICROSOFT_OAUTH_TENANT_ID", "22222222-2222-2222-2222-222222222222")
    monkeypatch.setenv("TRAVAUX_MICROSOFT_OAUTH_ALLOWED_DOMAINS", "commune.example")


def setup(tmp_path, monkeypatch, handler=None, clock=None):
    configured(monkeypatch)
    monkeypatch.delenv("SSLKEYLOGFILE", raising=False)
    monkeypatch.delenv("QUICLOGDIR", raising=False)
    cfg = Settings(mode="staging", db_path=tmp_path / "oauth.sqlite3", tenant_id="commune", password_hash="scrypt$x$x", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
    repo = Repository(cfg.db_path)
    from travaux.governance import GovernanceService
    GovernanceService(repo, "commune", cfg)
    hub = ConnectionHub(repo, cfg, policy=IntegrationPolicy(True, HOSTS))
    requests = []

    def default(request):
        requests.append(request)
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "access-test-token", "refresh_token": "refresh-test-token", "token_type": "Bearer", "expires_in": 3600, "scope": "https://www.googleapis.com/auth/gmail.readonly" if request.url.host == "oauth2.googleapis.com" else "Mail.Read User.Read offline_access"})
        if request.url.path.endswith("/profile"):
            return httpx.Response(200, json={"emailAddress": "travaux@commune.example", "historyId": "100"})
        if request.url.path == "/v1.0/me":
            return httpx.Response(200, json={"id": "subject1", "mail": "travaux@commune.example"})
        if request.url.path.endswith("/revoke"):
            return httpx.Response(200, json={})
        return httpx.Response(500)

    service = OAuthMailService(repo, cfg, hub=hub, governance=Governance(), http_client=httpx.Client(transport=httpx.MockTransport(handler or default)), resolve_dns=False, clock=clock)
    return service, hub, repo, requests


def begin(service, provider="google"):
    value = service.start(ADMIN, provider, label="Service travaux", browser_binding="browser-binding-test")
    assert value.get("expires_in") == 600
    return value, parse_qs(urlsplit(value["authorization_url"]).query)["state"][0]


def connect(service, provider="google"):
    _, state = begin(service, provider)
    return service.complete(provider, state=state, code="code-test", browser_binding="browser-binding-test")


def test_start_pkce_single_use_bound_state_no_cleartext(tmp_path, monkeypatch):
    service, hub, repo, requests = setup(tmp_path, monkeypatch)
    result, state = begin(service)
    query = parse_qs(urlsplit(result["authorization_url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["code_challenge"][0]) == 43
    assert query["redirect_uri"] == ["https://travaux.example/api/v1/integrations/oauth/google/callback"]
    assert query["scope"] == ["https://www.googleapis.com/auth/gmail.readonly"]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert result["expires_in"] == 600 and requests == []
    dbrow = dict(repo._db.execute("SELECT * FROM mail_oauth_flows").fetchone())
    assert dbrow["state_hash"] == hashlib.sha256(state.encode()).hexdigest()
    assert state not in json.dumps(dbrow) and "browser-binding-test" not in json.dumps(dbrow)
    connected = service.complete("google", state=state, code="code-test", browser_binding="browser-binding-test")
    assert connected["provider"] == "google" and connected["mailbox"] == "travaux@commune.example"
    assert connected["status"] == "not_tested"
    assert "token" not in json.dumps(connected)
    assert "access-test-token" not in repo._db.execute("SELECT secret_ciphertext FROM connector_connections").fetchone()[0]
    with pytest.raises(DomainError):
        service.complete("google", state=state, code="code-test", browser_binding="browser-binding-test")
    assert len(requests) == 2
    assert hub.status(ADMIN)["providers"][2]["available"]


@pytest.mark.parametrize("change", ["browser", "provider", "expired", "permission"])
def test_callback_rejects_before_code_exchange(tmp_path, monkeypatch, change):
    now = [1000.0]
    service, _, _, requests = setup(tmp_path, monkeypatch, clock=lambda: now[0])
    _, state = begin(service)
    if change == "expired":
        now[0] += 601
    if change == "permission":
        service.governance.allowed = False
    with pytest.raises(DomainError):
        service.complete("microsoft365" if change == "provider" else "google", state=state, code="code-test", browser_binding="wrong" if change == "browser" else "browser-binding-test")
    assert requests == []


def test_public_demo_and_unconfigured_provider_are_unavailable(tmp_path, monkeypatch):
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    monkeypatch.delenv("TRAVAUX_GOOGLE_OAUTH_CLIENT_SECRET")
    assert service.provider_status("google")["available"] is False
    with pytest.raises(DomainError):
        begin(service)
    cfg = Settings(db_path=tmp_path / "demo.sqlite3")
    demo = OAuthMailService(Repository(cfg.db_path), cfg, hub=ConnectionHub(Repository(tmp_path / "other.sqlite3"), cfg), governance=Governance())
    assert not demo.provider_status("google")["available"]
    with pytest.raises(DomainError):
        begin(demo)


def test_mailbox_domain_restriction_prevents_connection(tmp_path, monkeypatch):
    def handler(request):
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "private", "refresh_token": "refresh", "token_type": "Bearer", "expires_in": 3600})
        return httpx.Response(200, json={"emailAddress": "personal@outside.example"})
    service, _, repo, _ = setup(tmp_path, monkeypatch, handler=handler)
    with pytest.raises(DomainError):
        connect(service)
    assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 0


def test_microsoft_tenant_and_scopes_are_exact(tmp_path, monkeypatch):
    service, _, _, _ = setup(tmp_path, monkeypatch)
    result, _ = begin(service, "microsoft365")
    assert urlsplit(result["authorization_url"]).path.startswith("/22222222-2222-2222-2222-222222222222/")
    assert set(parse_qs(urlsplit(result["authorization_url"]).query)["scope"][0].split()) == {"User.Read", "Mail.Read", "offline_access"}
    assert parse_qs(urlsplit(result["authorization_url"]).query)["prompt"] == ["select_account"]
    value = connect(service, "microsoft365")
    assert value["provider"] == "microsoft365"


def test_refresh_preserves_rotated_token_and_disconnect_race(tmp_path, monkeypatch):
    now = [1000.0]
    service, hub, repo, _ = setup(tmp_path, monkeypatch, clock=lambda: now[0])
    connection = connect(service)
    now[0] += 3601
    assert service.access_token(connection["id"]) == "access-test-token"
    row = hub._row("commune", connection["id"])
    assert hub.vault.decrypt(row["secret_ciphertext"])["refresh_token"] == "refresh-test-token"
    hub.disconnect(ADMIN, connection["id"], expected_revision=row["revision"])
    with pytest.raises(DomainError):
        service.access_token(connection["id"])


def test_refresh_response_cannot_reintroduce_disconnected_secret(tmp_path, monkeypatch):
    now = [1000.0]
    service, hub, repo, _ = setup(tmp_path, monkeypatch, clock=lambda: now[0])
    connection = connect(service)
    now[0] += 3601
    def handler(request):
        if request.url.path.endswith("/revoke"):
            return httpx.Response(200, json={})
        with repo._transaction() as db:
            db.execute("UPDATE connector_connections SET status='disconnected',secret_ciphertext='' WHERE id=?", (connection["id"],))
        return httpx.Response(200, json={"access_token": "new-private-token", "refresh_token": "new-refresh", "token_type": "Bearer", "expires_in": 3600})
    service.http_client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(DomainError):
        service.access_token(connection["id"])
    assert repo._db.execute("SELECT secret_ciphertext FROM connector_connections").fetchone()[0] == ""


def test_concurrent_refresh_uses_durable_lease(tmp_path, monkeypatch):
    now = [1000.0]
    service, hub, repo, _ = setup(tmp_path, monkeypatch, clock=lambda: now[0])
    connection = connect(service)
    competing, _, competing_repo, _ = setup(tmp_path, monkeypatch, clock=lambda: now[0])
    now[0] += 3601
    entered, release = threading.Event(), threading.Event()
    def handler(request):
        entered.set()
        assert release.wait(5)
        return httpx.Response(200, json={"access_token": "rotated", "refresh_token": "refresh-rotated", "token_type": "Bearer", "expires_in": 3600})
    service.http_client = httpx.Client(transport=httpx.MockTransport(handler))
    results = []
    thread = threading.Thread(target=lambda: results.append(service.access_token(connection["id"])))
    thread.start()
    assert entered.wait(5)
    try:
        with pytest.raises(DomainError) as error:
            competing.access_token(connection["id"])
        assert error.value.code == "integration_busy"
    finally:
        release.set()
        thread.join(5)
        competing_repo.close()
    assert results == ["rotated"]


@pytest.mark.parametrize("provider", ["google", "microsoft365"])
def test_http_routes_cookie_binding_and_fixed_redirect_without_tokens(tmp_path, monkeypatch, provider):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from travaux.mail_oauth import register_mail_oauth_routes
    from travaux.auth import SessionStore
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    app = FastAPI()
    routes = register_mail_oauth_routes(app, repo, "commune", lambda: ADMIN, service.settings, hub=hub, governance=service.governance)
    routes.http_client, routes.resolve_dns = service.http_client, False
    with TestClient(app, base_url="https://travaux.example") as client:
        client.cookies.set("travaux_session", SessionStore(service.settings.db_path).issue("agent-a", "commune"))
        start = client.post(f"/api/v1/integrations/oauth/{provider}/start", json={"label": "Service travaux"})
        assert start.status_code == 200
        cookie = start.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        assert "Path=/api/v1/integrations/oauth/" in cookie
        state = parse_qs(urlsplit(start.json()["authorization_url"]).query)["state"][0]
        result = client.get(f"/api/v1/integrations/oauth/{provider}/callback", params={"state": state, "code": "provider-code", "connection": "untrusted-id", "redirect": "https://foreign.invalid"}, follow_redirects=False)
        connection = repo._db.execute("SELECT id FROM connector_connections").fetchone()["id"]
        assert result.status_code == 303 and result.headers["location"] == "/espace.html#/connexions?oauth=connected&connection=" + connection
        assert "token" not in result.headers["location"] and "state=" not in result.headers["location"]
        assert all(value not in result.headers["location"] for value in ("provider-code", "foreign.invalid", "untrusted-id", "test-google-secret", "test-microsoft-secret", "access-test-token", "refresh-test-token", "travaux@commune.example"))
        assert result.headers["cache-control"] == "no-store"
        assert result.headers["referrer-policy"] == "no-referrer"
        assert "Max-Age=0" in result.headers["set-cookie"]
        assert "HttpOnly" in result.headers["set-cookie"] and "Path=/api/v1/integrations/oauth/" in result.headers["set-cookie"]
        replay = client.get(f"/api/v1/integrations/oauth/{provider}/callback", params={"state": state, "code": "provider-code", "connection": connection}, follow_redirects=False)
        assert replay.status_code == 303 and replay.headers["location"] == "/espace.html#/connexions?oauth=failed"
        assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 1
        another = client.post(f"/api/v1/integrations/oauth/{provider}/start", json={})
        next_state = parse_qs(urlsplit(another.json()["authorization_url"]).query)["state"][0]
        cancelled = client.get(f"/api/v1/integrations/oauth/{provider}/callback", params={"state": next_state, "error": "access_denied", "error_description": "private-error-description", "connection": connection}, follow_redirects=False)
        assert cancelled.status_code == 303 and cancelled.headers["location"] == "/espace.html#/connexions?oauth=cancelled"
        assert "Max-Age=0" in cancelled.headers["set-cookie"]
        assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 1


def test_callback_after_permission_change_during_profile_does_not_create_account(tmp_path, monkeypatch):
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    def handler(request):
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "private", "refresh_token": "refresh", "token_type": "Bearer", "expires_in": 3600})
        service.governance.allowed = False
        return httpx.Response(200, json={"emailAddress": "travaux@commune.example"})
    service.http_client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(DomainError):
        connect(service)
    assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 0


def test_transport_rejects_tls_debug_and_redirect_without_exposing_provider_body(tmp_path, monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://evil.example/steal"}, text="private-provider-response")
    service, _, _, _ = setup(tmp_path, monkeypatch, handler=handler)
    _, state = begin(service)
    monkeypatch.setenv("SSLKEYLOGFILE", "synthetic-keylog-path")
    with pytest.raises(DomainError) as error:
        service.complete("google", state=state, code="code-test", browser_binding="browser-binding-test")
    assert calls == [] and "private" not in str(error.value)
    monkeypatch.delenv("SSLKEYLOGFILE")
    _, state = begin(service)
    with pytest.raises(DomainError) as error:
        service.complete("google", state=state, code="code-test", browser_binding="browser-binding-test")
    assert len(calls) == 1 and "private" not in str(error.value)


def test_read_only_grant_is_required(tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"access_token": "private", "refresh_token": "refresh", "token_type": "Bearer", "expires_in": 3600, "scope": "openid profile"})
    service, _, repo, _ = setup(tmp_path, monkeypatch, handler=handler)
    with pytest.raises(DomainError) as error:
        connect(service)
    assert error.value.code == "connection_authorization_required"
    assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 0


def test_token_response_body_is_bounded_without_reflecting_content(tmp_path, monkeypatch):
    def handler(request):
        return httpx.Response(200, content=b"x" * 4_000_001)
    service, _, repo, _ = setup(tmp_path, monkeypatch, handler=handler)
    with pytest.raises(DomainError) as error:
        connect(service)
    assert "xxxxx" not in str(error.value)
    assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 0


def test_revoked_starting_session_blocks_callback_without_strict_cookie(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from travaux.auth import SessionStore
    from travaux.mail_oauth import register_mail_oauth_routes
    service, hub, repo, requests = setup(tmp_path, monkeypatch)
    sessions = SessionStore(service.settings.db_path)
    token = sessions.issue("agent-a", "commune")
    app = FastAPI()
    routes = register_mail_oauth_routes(app, repo, "commune", lambda: ADMIN, service.settings, hub=hub, governance=service.governance)
    routes.http_client, routes.resolve_dns = service.http_client, False
    with TestClient(app, base_url="https://travaux.example") as client:
        client.cookies.set("travaux_session", token)
        response = client.post("/api/v1/integrations/oauth/google/start", json={"label": "Travaux"})
        state = parse_qs(urlsplit(response.json()["authorization_url"]).query)["state"][0]
        sessions.revoke(token)
        client.cookies.delete("travaux_session")
        result = client.get("/api/v1/integrations/oauth/google/callback", params={"state": state, "code": "provider-code"}, follow_redirects=False)
        assert result.headers["location"] == "/espace.html#/connexions?oauth=failed"
        assert requests == []
        assert repo._db.execute("SELECT count(*) FROM connector_connections").fetchone()[0] == 0


def test_connection_and_disconnect_are_audited_without_tokens_or_mail_body(tmp_path, monkeypatch):
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    value = connect(service)
    hub.disconnect(ADMIN, value["id"], expected_revision=value["revision"])
    rows = [dict(row) for row in repo._db.execute("SELECT * FROM organization_audit ORDER BY created_at")]
    assert {row["action"] for row in rows} >= {"mail.oauth.connected", "mail.oauth.disconnected"}
    encoded = json.dumps(rows)
    assert "access-test-token" not in encoded and "refresh-test-token" not in encoded
    assert "test-google-secret" not in encoded and "browser-binding-test" not in encoded


def test_disconnect_audit_failure_rolls_back_local_erasure(tmp_path, monkeypatch):
    service, hub, _, _ = setup(tmp_path, monkeypatch)
    value = connect(service)
    before = hub._row("commune", value["id"])
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")
    monkeypatch.setattr(service, "_audit", fail)
    with pytest.raises(RuntimeError):
        hub.disconnect(ADMIN, value["id"], expected_revision=value["revision"])
    after = hub._row("commune", value["id"])
    assert after["secret_ciphertext"] == before["secret_ciphertext"]
    assert after["status"] == before["status"]


def test_non_admin_status_does_not_disclose_mailbox_credentials_metadata(tmp_path, monkeypatch):
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    value = connect(service)
    reader = {"actor_id": "agent-reader", "tenant_id": "commune", "permissions": {"organization": {"write": False}}}
    status = hub.status(reader)
    assert status["connections"] == []
    assert all(provider["available"] is False for provider in status["providers"] if provider["id"] != "ics")
    with repo._transaction() as db:
        db.execute("UPDATE connector_connections SET status='verified',selected_folders='[\"INBOX\"]' WHERE id=?", (value["id"],))
    assert hub.mail_status(reader)["connections"] == []
    assert "travaux@commune.example" not in json.dumps(hub.mail_status(reader))


@pytest.mark.parametrize("identifier", ["https://foreign.invalid/?token=private", "../../escape", "private@example.invalid", None])
def test_callback_rejects_non_uuid_connection_dto_without_redirect_or_pii_leak(tmp_path, monkeypatch, identifier):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from travaux.mail_oauth import register_mail_oauth_routes
    service, hub, repo, _ = setup(tmp_path, monkeypatch)
    app = FastAPI()
    routes = register_mail_oauth_routes(app, repo, "commune", lambda: ADMIN, service.settings, hub=hub, governance=service.governance)
    monkeypatch.setattr(routes, "complete", lambda *args, **kwargs: {"id": identifier, "mailbox": "private@example.invalid", "access_token": "private-token"})
    with TestClient(app, base_url="https://travaux.example") as client:
        result = client.get("/api/v1/integrations/oauth/microsoft365/callback", params={"state":"synthetic", "code":"synthetic"}, follow_redirects=False)
        assert result.status_code == 303
        assert result.headers["location"] == "/espace.html#/connexions?oauth=failed"
        assert result.headers["cache-control"] == "no-store" and result.headers["referrer-policy"] == "no-referrer"
