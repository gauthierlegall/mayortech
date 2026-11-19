"""Real API/session boundary for the private fictional organization profile."""
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def private(tmp_path, *, test=True):
    cfg = Settings(mode="staging", auth_mode="oidc", test_organization_self_join=test, organization_join_code="" if test else "TOWN-ACCESS", db_path=tmp_path / "accounts-http.sqlite3", tenant_id="town-a", public_origin="https://testserver", allowed_hosts=("testserver",))
    app = create_app(cfg)
    member = app.state.identities.provision("https://identity.example", "new-person", "Nouvelle personne", "reader", active=False)
    token = app.state.sessions.issue(member["actor_id"], "onboarding:town-a", ttl=900)
    return app, member, token


def test_private_account_selects_test_organization_before_any_workspace_access(tmp_path):
    app, member, token = private(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("travaux_session", token)
        session = client.get("/api/v1/session").json()
        assert session["authenticated"] and session["organization_required"]
        assert session["actor"] is None and session["account"]["id"] == member["actor_id"]
        for path in ("/api/v1/bootstrap", "/api/v1/projects", "/api/v1/integrations"):
            assert client.get(path).status_code in {401, 403}
        directory = client.get("/api/v1/account/organizations")
        assert directory.status_code == 200
        assert directory.json()["items"][0]["is_test"] is True
        joined = client.post("/api/v1/account/organizations/town-a/join", json={"code":"MAIRIE-TEST"}, headers=headers())
        assert joined.status_code == 200 and joined.json()["status"] == "joined"
        assert "HttpOnly" in joined.headers["set-cookie"] and "SameSite=strict" in joined.headers["set-cookie"]
        assert app.state.sessions.resolve(token) is None
        entered = client.get("/api/v1/session").json()
        assert entered["authenticated"] and entered["organization_required"] is False
        assert entered["actor"]["tenant_id"] == "town-a"
        assert app.state.identities.get_active(member["actor_id"])["role"] == "editor"
        assert client.get("/api/v1/projects").status_code == 200
        assert len(client.get("/api/v1/projects").json()) > 0
        assert client.post("/api/v1/integrations/oauth/google/start", json={}, headers=headers()).status_code == 403
        assert client.post("/api/v1/imports/eml", content=b"fictional", headers=headers()).status_code == 403


def test_real_organization_request_does_not_unlock_bootstrap(tmp_path):
    app, member, token = private(tmp_path, test=False)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("travaux_session", token)
        result = client.post("/api/v1/account/organizations/town-a/join", json={"code":"TOWN-ACCESS"}, headers=headers())
        assert result.status_code == 200 and result.json()["status"] == "pending"
        assert "set-cookie" not in result.headers
        assert client.get("/api/v1/bootstrap").status_code in {401, 403}
        assert app.state.identities.get_active(member["actor_id"]) is None


def test_join_is_csrf_protected_and_cannot_choose_a_different_tenant(tmp_path):
    app, member, token = private(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("travaux_session", token)
        assert client.post("/api/v1/account/organizations/town-a/join", json={}).status_code == 403
        assert client.post("/api/v1/account/organizations/other-town/join", json={}, headers=headers()).status_code == 404
        assert app.state.identities.get_active(member["actor_id"]) is None
