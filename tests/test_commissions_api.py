"""HTTP API integration tests for permanent commissions, permissions and project scoping."""
import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.commissions import (
    COMMISSION_1_ID,
    COMMISSION_4_ID,
)
from travaux.config import Settings


@pytest.fixture
def comm_api(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "comm_api.sqlite3",
        tenant_id="town-a",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def sign_in(app, client, subject="agent-a", role="editor"):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    token = app.state.sessions.issue(member["actor_id"], "town-a")
    client.cookies.set("travaux_session", token)
    return member


def test_bootstrap_returns_commissions_with_capabilities(comm_api):
    app, client = comm_api
    sign_in(app, client, subject="admin-user", role="admin")
    resp = client.get("/api/v1/bootstrap")
    assert resp.status_code == 200
    data = resp.json()
    assert "commissions" in data
    assert len(data["commissions"]) == 4
    comm_codes = [c["code"] for c in data["commissions"]]
    assert comm_codes == ["finances", "enfance-jeunesse", "urbanisme-travaux", "culture-vie-associative"]


def test_commission_member_role_assignment(comm_api):
    app, client = comm_api
    sign_in(app, client, subject="admin-user", role="admin")
    agent = app.state.identities.provision("https://identity.example", "agent-culture", "Agent Culture", "editor")

    # Set role in Culture commission
    put_resp = client.put(
        f"/api/v1/commissions/{COMMISSION_4_ID}/members/{agent['actor_id']}",
        json={"role": "editor"},
        headers=headers(),
    )
    assert put_resp.status_code == 200
    res = put_resp.json()
    assert res["role"] == "editor"
    assert res["commission_id"] == COMMISSION_4_ID

    # List members
    list_resp = client.get(f"/api/v1/commissions/{COMMISSION_4_ID}/members")
    assert list_resp.status_code == 200
    members = list_resp.json()["items"]
    assert any(m["id"] == agent["actor_id"] and m["role"] == "editor" for m in members)

    # Remove role
    del_resp = client.delete(
        f"/api/v1/commissions/{COMMISSION_4_ID}/members/{agent['actor_id']}",
        headers=headers(),
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["removed"] is True


def test_project_commission_scoping_and_capabilities(comm_api):
    app, client = comm_api
    admin = sign_in(app, client, subject="admin-user", role="admin")

    # Create dossiers in Culture and Finances
    p_culture = app.state.repo.create_project(
        "town-a", "CLT-100", "Festival de la Fraise", commission_id=COMMISSION_4_ID
    )
    p_finances = app.state.repo.create_project(
        "town-a", "FIN-100", "Audit financier", commission_id=COMMISSION_1_ID
    )

    # Agent Alice is editor in Culture and reader in Finances
    alice = sign_in(app, client, subject="alice", role="editor")
    app.state.commissions.set_member_commission_role(
        "town-a", COMMISSION_4_ID, alice["actor_id"], "editor", updated_by=admin["actor_id"]
    )
    app.state.commissions.set_member_commission_role(
        "town-a", COMMISSION_1_ID, alice["actor_id"], "reader", updated_by=admin["actor_id"]
    )

    # Filter by Culture commission
    culture_resp = client.get(f"/api/v1/projects?commission_id={COMMISSION_4_ID}")
    assert culture_resp.status_code == 200
    culture_projects = culture_resp.json()
    assert len(culture_projects) == 1
    assert culture_projects[0]["id"] == p_culture["id"]
    assert culture_projects[0]["can_edit"] is True
    assert culture_projects[0]["can_submit_for_review"] is True

    # Filter by Finances commission
    fin_resp = client.get(f"/api/v1/projects?commission_id={COMMISSION_1_ID}")
    assert fin_resp.status_code == 200
    fin_projects = fin_resp.json()
    assert len(fin_projects) == 1
    assert fin_projects[0]["id"] == p_finances["id"]
    assert fin_projects[0]["can_edit"] is False
    assert fin_projects[0]["can_submit_for_review"] is False

    # Alice can create project in Culture
    post_culture = client.post(
        "/api/v1/projects",
        json={
            "reference": "CLT-200",
            "name": "Concert d'été",
            "commission_id": COMMISSION_4_ID,
            "specialization": "culture",
        },
        headers=headers(),
    )
    assert post_culture.status_code == 201

    # Alice cannot create project in Finances
    post_fin = client.post(
        "/api/v1/projects",
        json={
            "reference": "FIN-200",
            "name": "Budget d'investissement",
            "commission_id": COMMISSION_1_ID,
            "specialization": "finances",
        },
        headers=headers(),
    )
    assert post_fin.status_code == 403
