"""API tests for Culture -> Finances cross-commission endpoints."""
import pytest
from fastapi.testclient import TestClient
from travaux.api import create_app
from travaux.commissions import COMMISSION_1_ID, COMMISSION_4_ID
from travaux.config import Settings


@pytest.fixture
def cf_api(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "cf_api.sqlite3",
        tenant_id="town-plougastel",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    repo = app.state.repo
    # Pre-create test project in Culture commission
    repo.create_project(
        "town-plougastel",
        "EVT-2027-01",
        "Fête du Port du Tinduff",
        project_id="prj-fete-tinduff",
        commission_id=COMMISSION_4_ID,
    )
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def sign_in(app, client, subject="admin-user", role="admin"):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    token = app.state.sessions.issue(member["actor_id"], "town-plougastel")
    client.cookies.set("travaux_session", token)
    app.state.commissions.set_member_commission_role(
        "town-plougastel", COMMISSION_4_ID, member["actor_id"], "admin", updated_by=member["actor_id"]
    )
    app.state.commissions.set_member_commission_role(
        "town-plougastel", COMMISSION_1_ID, member["actor_id"], "admin", updated_by=member["actor_id"]
    )
    return member


def test_api_rooms_and_reservations(cf_api):
    app, client = cf_api
    sign_in(app, client, subject="admin-user", role="admin")

    # 1. List rooms
    res = client.get("/api/v1/culture/rooms")
    if res.status_code != 200:
        print("ERROR RESPONSE:", res.status_code, res.text)
    assert res.status_code == 200
    rooms = res.json()["items"]
    assert any(r["id"] == "salle-avel-vor" for r in rooms)

    # 2. Book Avel Vor
    res_book = client.post(
        "/api/v1/projects/prj-fete-tinduff/reservations",
        headers=headers(),
        json={
            "resource_id": "salle-avel-vor",
            "resource_name": "Espace Avel Vor",
            "start_time": "2027-06-20T10:00:00+02:00",
            "end_time": "2027-06-20T18:00:00+02:00",
            "status": "confirmed",
        },
    )
    if res_book.status_code != 200:
        print("RES_BOOK ERROR:", res_book.status_code, res_book.text)
    assert res_book.status_code == 200
    booking = res_book.json()
    assert booking["status"] == "confirmed"

    # 3. List project reservations
    res_list = client.get("/api/v1/projects/prj-fete-tinduff/reservations")
    assert res_list.status_code == 200
    assert len(res_list.json()["items"]) == 1

    # 4. Overlapping booking returns conflict error
    res_conflict = client.post(
        "/api/v1/projects/prj-fete-tinduff/reservations",
        headers=headers(),
        json={
            "resource_id": "salle-avel-vor",
            "resource_name": "Espace Avel Vor",
            "start_time": "2027-06-20T12:00:00+02:00",
            "end_time": "2027-06-20T14:00:00+02:00",
            "status": "confirmed",
        },
    )
    assert res_conflict.status_code == 409
    assert "Conflit de réservation" in res_conflict.json()["error"]["message"]


def test_api_event_details_and_budget_lifecycle(cf_api):
    app, client = cf_api
    sign_in(app, client, subject="admin-user", role="admin")

    # 1. Update event details
    res_evt = client.put(
        "/api/v1/projects/prj-fete-tinduff/event-details",
        headers=headers(),
        json={
            "association_name": "SNSM Plougastel",
            "association_ref": "W291008899",
            "expected_attendance": 800,
            "location_name": "Port du Tinduff",
            "checklist": [{"id": "chk-1", "label": "Autorisation DDTM", "done": True}],
        },
    )
    assert res_evt.status_code == 200
    data = res_evt.json()
    assert data["association_name"] == "SNSM Plougastel"
    assert len(data["checklist"]) == 1

    # 2. Save budget sheet
    res_budget = client.post(
        "/api/v1/projects/prj-fete-tinduff/budget",
        headers=headers(),
        json={
            "title": "Budget Prévisionnel Tinduff 2027",
            "exercise": 2027,
            "status": "draft",
            "variants": [
                {
                    "id": "var-1",
                    "label": "Scénario A (Autofinancement)",
                    "tax_basis": "ttc",
                    "amount_cents": 1200000,
                    "subsidies_cents": 300000,
                    "hypothesis": "Budget standard",
                }
            ],
        },
    )
    assert res_budget.status_code == 200
    sheet = res_budget.json()["sheet"]
    assert sheet["variants"][0]["remaining_cents"] == 900000

    # 3. Export CSV
    res_csv = client.get("/api/v1/projects/prj-fete-tinduff/budget/export.csv")
    assert res_csv.status_code == 200
    assert "9000.00" in res_csv.text

    # 4. Transmit for finance arbitration
    res_trans = client.post(
        "/api/v1/projects/prj-fete-tinduff/transmissions/finance",
        headers=headers(),
        json={
            "motive": "Demande de subvention exceptionnelle pour matériel de secours",
            "attached_document_ids": ["devis-portail-v1"],
            "source_commission_id": COMMISSION_4_ID,
            "destination_commission_id": COMMISSION_1_ID,
        },
    )
    assert res_trans.status_code == 200
    trans = res_trans.json()["transmission"]
    assert trans["status"] == "transmis"
    trans_id = trans["id"]

    # 5. List finance transmissions
    res_list_trans = client.get("/api/v1/finance/transmissions")
    assert res_list_trans.status_code == 200
    assert len(res_list_trans.json()["items"]) >= 1

    # 6. Render favorable decision
    res_dec = client.post(
        f"/api/v1/finance/transmissions/{trans_id}/decision",
        headers=headers(),
        json={
            "opinion": "favorable",
            "motivation": "Subvention de 3 000 € approuvée par la commission finances.",
            "decision_ref": "DELIB-2027-TINDUFF",
            "expected_version": 1,
        },
    )
    assert res_dec.status_code == 200
    dec = res_dec.json()["transmission"]
    assert dec["status"] == "avis_rendu"
    assert dec["decision_ref"] == "DELIB-2027-TINDUFF"
