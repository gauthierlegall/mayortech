"""Protected HTTP boundary for individual sessions and dossier authorization."""
import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings


@pytest.fixture
def private(tmp_path):
    settings = Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "private.sqlite3", tenant_id="town-a", public_origin="https://testserver", allowed_hosts=("testserver",))
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def sign_in(app, client, subject="agent-a", role="reader"):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    token = app.state.sessions.issue(member["actor_id"], "town-a")
    client.cookies.set("travaux_session", token)
    return member


def test_oidc_session_has_no_shared_password_fallback(private):
    _, client = private
    session = client.get("/api/v1/session").json()
    assert session["auth"]["method"] == "oidc" and session["authenticated"] is False
    response = client.post("/api/v1/session", json={"password": "a fake password must never be accepted"}, headers=headers())
    assert response.status_code == 403
    assert "travaux_session" not in response.cookies


def test_individual_member_and_revocation_are_rechecked_every_request(private):
    app, client = private
    member = sign_in(app, client, role="editor")
    assert client.get("/api/v1/bootstrap").status_code == 200
    assert client.get("/api/v1/session").json()["actor"]["actor_id"] == member["actor_id"]
    app.state.identities.update(member["actor_id"], role="reader", active=False, expected_revision=0, updated_by="operator")
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/session").json()["authenticated"] is False


def test_project_listing_and_direct_page_access_follow_grants(private):
    app, client = private
    member = sign_in(app, client, role="editor")
    assert client.get("/api/v1/projects").json() == []
    all_projects = app.state.repo.list_projects("town-a")
    first, other = all_projects[:2]
    with app.state.repo._transaction() as db:
        db.execute("INSERT INTO project_grants VALUES(?,?,?,?,?)", ("town-a", member["actor_id"], first["id"], "operator", "2026-11-17"))
    assert [row["id"] for row in client.get("/api/v1/projects").json()] == [first["id"]]
    assert client.get("/api/v1/projects/"+other["id"]).status_code == 404
    foreign_page = app.state.pages.ensure_main("town-a", other["id"])
    assert client.get("/api/v1/pages/"+foreign_page["id"]+"/state").status_code == 404
    assert client.post("/api/v1/projects/"+other["id"]+"/page", json={}, headers=headers()).status_code == 404


def test_admin_can_manage_a_member_but_editor_cannot(private):
    app, client = private
    admin = sign_in(app, client, "admin-a", "admin")
    member = app.state.identities.provision("https://identity.example", "reader-a", "Reader A", "reader")
    response = client.patch("/api/v1/organization/members/"+member["actor_id"], json={"role": "editor", "active": True, "expected_revision": 0}, headers=headers())
    assert response.status_code == 200 and response.json()["role"] == "editor"
    sign_in(app, client, "editor-b", "editor")
    assert client.patch("/api/v1/organization/members/"+member["actor_id"], json={"role": "admin", "active": True, "expected_revision": 1}, headers=headers()).status_code == 403
    assert app.state.identities.get_active(admin["actor_id"])["role"] == "admin"


def test_project_access_change_is_explicit_audited_and_version_checked(private):
    app, client = private
    sign_in(app, client, "admin-a", "admin")
    member = app.state.identities.provision("https://identity.example", "reader-a", "Reader A", "reader")
    project = app.state.repo.list_projects("town-a")[0]
    path = "/api/v1/projects/"+project["id"]+"/access"
    baseline = client.get(path).json()
    changed = client.put(path+"/"+member["actor_id"], json={"allowed": True, "expected_revision": baseline["revision"]}, headers=headers())
    assert changed.status_code == 200 and any(item["id"] == member["actor_id"] for item in changed.json()["items"])
    assert client.put(path+"/"+member["actor_id"], json={"allowed": False, "expected_revision": baseline["revision"]}, headers=headers()).status_code == 409
    assert app.state.repo._db.execute("SELECT count(*) FROM identity_audit WHERE action='project.access.changed'").fetchone()[0] == 1
