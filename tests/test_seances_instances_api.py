"""API tests for Séances et Instances Spécialisées (Lot 5)."""

import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.commissions import COMMISSION_3_ID
from travaux.config import Settings


@pytest.fixture
def seances_api(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "seances_api.sqlite3",
        tenant_id="town-plougastel",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    repo = app.state.repo
    # Pre-create test project in Commission 3
    repo.create_project(
        "town-plougastel",
        "TRAV-2027-010",
        "Rénovation Énergétique École Avel Vor",
        project_id="prj-avel-vor",
        commission_id=COMMISSION_3_ID,
    )
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def sign_in(app, client, subject="maire-adjoint", role="admin"):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    token = app.state.sessions.issue(member["actor_id"], "town-plougastel")
    client.cookies.set("travaux_session", token)
    app.state.commissions.set_member_commission_role(
        "town-plougastel", COMMISSION_3_ID, member["actor_id"], "admin", updated_by=member["actor_id"]
    )
    return member


def test_api_sessions_lifecycle_and_close(seances_api):
    app, client = seances_api
    sign_in(app, client)

    # 1. Create a session
    payload = {
        "commission_id": COMMISSION_3_ID,
        "session_type": "commission",
        "title": "Séance Commission Travaux - Mars 2027",
        "session_date": "2027-03-25",
        "session_time": "18:00",
        "location": "Salle des Mariages, Mairie de Plougastel",
        "quorum_required": 2,
    }
    res = client.post("/api/v1/sessions", json=payload, headers=headers())
    assert res.status_code == 200, res.text
    session = res.json()
    session_id = session["id"]
    assert session["title"] == "Séance Commission Travaux - Mars 2027"
    assert session["status"] == "draft"

    # 2. Add agenda items
    item_payload = {
        "title": "Examen du marché Avel Vor",
        "description": "Validation du devis et des tranches conditionnelles",
        "project_id": "prj-avel-vor",
        "rapporteur": "Jean-Luc Le Gall",
    }
    res_item = client.post(f"/api/v1/sessions/{session_id}/agenda", json=item_payload, headers=headers())
    assert res_item.status_code == 200
    updated_session = res_item.json()
    assert len(updated_session["agenda_items"]) == 1
    item_id = updated_session["agenda_items"][0]["id"]
    assert updated_session["agenda_items"][0]["deliberation_ref"] == "DELIB-2027-COM3-01"

    # 3. Update attendance
    att_payload = {
        "attendances": [
            {"member_name": "Jean-Luc Le Gall", "member_role": "titulaire", "status": "present"},
            {"member_name": "Marie Le Meur", "member_role": "titulaire", "status": "present"},
        ]
    }
    res_att = client.post(f"/api/v1/sessions/{session_id}/attendance", json=att_payload, headers=headers())
    assert res_att.status_code == 200
    assert res_att.json()["quorum_present"] == 2

    # 4. Vote on item
    vote_payload = {
        "vote_result": "favorable",
        "votes_for": 2,
        "votes_against": 0,
        "votes_abstention": 0,
        "official_decision": "Avis favorable sans réserve",
    }
    res_vote = client.post(f"/api/v1/sessions/{session_id}/items/{item_id}/vote", json=vote_payload, headers=headers())
    assert res_vote.status_code == 200
    voted_item = next(it for it in res_vote.json()["agenda_items"] if it["id"] == item_id)
    assert voted_item["vote_result"] == "favorable"
    assert voted_item["votes_for"] == 2

    # 5. Close session and seal PV
    close_payload = {
        "closed_by": "Secrétaire de Séance",
        "force_quorum": False,
    }
    res_close = client.post(f"/api/v1/sessions/{session_id}/close", json=close_payload, headers=headers())
    assert res_close.status_code == 200
    closed = res_close.json()
    assert closed["status"] == "closed"
    assert len(closed["pv_hash"]) == 64  # SHA-256 seal

    # 6. Verify modification attempt on closed session fails with 409
    res_fail = client.post(
        f"/api/v1/sessions/{session_id}/agenda",
        json={"title": "Point post-clôture"},
        headers=headers(),
    )
    assert res_fail.status_code == 409
    assert res_fail.json()["error"]["code"] == "session_closed"


def test_api_specialized_instances_cao_ccspl_ccid(seances_api):
    app, client = seances_api
    sign_in(app, client)

    # 1. List specialized instances
    res = client.get("/api/v1/instances/specialized", headers=headers())
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    ids = {inst["id"] for inst in data["items"]}
    assert ids == {"cao", "ccspl", "ccid"}

    # 2. Add CAO tender record
    cao_payload = {
        "record_type": "cao_marche",
        "reference": "MEGALIS-BRETAGNE-2027-MAR-01",
        "title": "Travaux d'assainissement et réseaux Tinduff",
        "status": "en_cours",
        "details": {
            "plateforme": "Mégalis Bretagne",
            "montant_estime_eur": 450000,
            "lots": 2,
        },
    }
    res_rec = client.post("/api/v1/instances/specialized/cao/records", json=cao_payload, headers=headers())
    assert res_rec.status_code == 200
    rec = res_rec.json()
    assert rec["reference"] == "MEGALIS-BRETAGNE-2027-MAR-01"
    assert rec["details"]["montant_estime_eur"] == 450000

    # 3. List records
    res_list = client.get("/api/v1/instances/specialized/cao/records", headers=headers())
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1
