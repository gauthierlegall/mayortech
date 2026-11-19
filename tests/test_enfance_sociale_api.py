"""API tests for Action sociale, enfance et jeunesse (Lot 4)."""

import pytest
from fastapi.testclient import TestClient
from travaux.api import create_app
from travaux.commissions import COMMISSION_2_ID
from travaux.config import Settings


@pytest.fixture
def social_api(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "social_api.sqlite3",
        tenant_id="town-plougastel",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    repo = app.state.repo
    # Pre-create test project in Commission 2 (Enfance & Solidarités)
    repo.create_project(
        "town-plougastel",
        "SOC-2027-001",
        "Dispositif Rentrée Scolaire et Périscolaire",
        project_id="prj-social-rentree",
        commission_id=COMMISSION_2_ID,
    )
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def sign_in(app, client, subject="social-worker", role="admin"):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    token = app.state.sessions.issue(member["actor_id"], "town-plougastel")
    client.cookies.set("travaux_session", token)
    app.state.commissions.set_member_commission_role(
        "town-plougastel", COMMISSION_2_ID, member["actor_id"], "admin", updated_by=member["actor_id"]
    )
    return member


def test_api_quotient_calculator(social_api):
    app, client = social_api
    sign_in(app, client)

    res = client.get("/api/v1/social/quotient-calculator?quotient_familial=500", headers=headers())
    assert res.status_code == 200
    data = res.json()
    assert data["bracket"] == "T2"
    assert data["meal_rate_cents"] == 215

    res_t1 = client.get("/api/v1/social/quotient-calculator?quotient_familial=380", headers=headers())
    assert res_t1.status_code == 200
    assert res_t1.json()["bracket"] == "T1"
    assert res_t1.json()["meal_rate_cents"] == 100


def test_api_campaign_lifecycle_and_renewal(social_api):
    app, client = social_api
    sign_in(app, client)

    # 1. Create campaign
    create_payload = {
        "campaign_type": "rentree_scolaire",
        "title": "Campagne Rentrée 2026-2027",
        "school_year": "2026-2027",
        "start_date": "2026-05-01",
        "end_date": "2026-07-15",
        "config": {"ecoles": ["Alizés", "Goëland"]},
    }
    res = client.post("/api/v1/social/campaigns", headers=headers(), json=create_payload)
    assert res.status_code == 200
    camp = res.json()
    camp_id = camp["id"]
    assert camp_id.startswith("CMP-")

    # 2. Add a dossier
    dos_payload = {
        "family_ref": "FAM-29470-88",
        "beneficiary_name": "Famille Kervella",
        "child_name": "Lena Kervella",
        "school_name": "École des Alizés",
        "quotient_familial": 410,
        "details": {"cantine": True},
    }
    dos_res = client.post(f"/api/v1/social/campaigns/{camp_id}/dossiers", headers=headers(), json=dos_payload)
    assert dos_res.status_code == 200
    dos_data = dos_res.json()
    assert dos_data["rate_bracket"] == "T1"

    # List dossiers
    d_list = client.get(f"/api/v1/social/campaigns/{camp_id}/dossiers", headers=headers()).json()
    assert len(d_list["items"]) == 1

    # 3. Add a reminder
    rem_payload = {
        "campaign_id": camp_id,
        "title": "Date limite dépôt dossiers bourse communale",
        "due_date": "2026-06-30",
        "reminder_type": "inscription_deadline",
    }
    rem_res = client.post("/api/v1/social/reminders", headers=headers(), json=rem_payload)
    assert rem_res.status_code == 200
    rem_id = rem_res.json()["id"]

    # 4. Renew campaign for 2027-2028
    renew_payload = {
        "target_school_year": "2027-2028",
        "carry_over_dossiers": True,
        "carry_over_reminders": True,
    }
    renew_res = client.post(f"/api/v1/social/campaigns/{camp_id}/renew", headers=headers(), json=renew_payload)
    assert renew_res.status_code == 200
    renew_data = renew_res.json()
    assert renew_data["dossiers_renewed_count"] == 1
    assert renew_data["reminders_carried_count"] == 1
    assert renew_data["target_campaign"]["school_year"] == "2027-2028"

    # Dismiss old reminder
    dis_res = client.post(f"/api/v1/social/reminders/{rem_id}/dismiss", headers=headers())
    assert dis_res.status_code == 200
    assert dis_res.json()["dismissed"] is True


def test_api_social_aid_registry(social_api):
    app, client = social_api
    sign_in(app, client)

    # Record aid
    aid_payload = {
        "aid_type": "secours_urgence",
        "confidential_ref": "DOSSIER-CONFIDENTIEL-CCAS-09",
        "amount_cents": 15000,
        "commission_decision": "accorde",
        "deliberation_ref": "DELIB-CCAS-2027-04",
        "notes": "Aide d'urgence validée en séance CCAS",
    }
    res = client.post("/api/v1/projects/prj-social-rentree/social-aid", headers=headers(), json=aid_payload)
    assert res.status_code == 200
    aid_data = res.json()
    assert aid_data["id"].startswith("AID-")
    assert aid_data["amount_cents"] == 15000

    # List aids
    list_res = client.get("/api/v1/projects/prj-social-rentree/social-aid", headers=headers())
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["deliberation_ref"] == "DELIB-CCAS-2027-04"
