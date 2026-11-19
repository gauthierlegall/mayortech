"""API tests for Urbanisme, Travaux et Ports endpoints."""
import pytest
from fastapi.testclient import TestClient
from travaux.api import create_app
from travaux.commissions import COMMISSION_3_ID
from travaux.config import Settings


@pytest.fixture
def up_api(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "up_api.sqlite3",
        tenant_id="town-plougastel",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    repo = app.state.repo
    # Pre-create test project in Urbanisme commission
    repo.create_project(
        "town-plougastel",
        "TRV-2026-042",
        "Réfection Ponton Tinduff",
        project_id="prj-tinduff",
        commission_id=COMMISSION_3_ID,
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
        "town-plougastel", COMMISSION_3_ID, member["actor_id"], "admin", updated_by=member["actor_id"]
    )
    return member


def test_api_geo_features(up_api):
    app, client = up_api
    sign_in(app, client, subject="admin-user", role="admin")

    # 1. Create a geo feature for the project
    res = client.post(
        "/api/v1/projects/prj-tinduff/geo",
        headers=headers(),
        json={
            "feature_type": "port_ouvrage",
            "name": "Port du Tinduff — Ponton de pêche",
            "longitude": -4.3820,
            "latitude": 48.3370,
            "properties": {"ouvrage": "ponton"},
        },
    )
    assert res.status_code == 200, res.text
    created = res.json()
    assert created["feature_type"] == "port_ouvrage"

    # 2. Get project geo features
    res = client.get("/api/v1/projects/prj-tinduff/geo")
    assert res.status_code == 200
    p_geo = res.json()
    assert p_geo["type"] == "FeatureCollection"
    assert len(p_geo["features"]) == 1
    assert p_geo["features"][0]["properties"]["name"] == "Port du Tinduff — Ponton de pêche"

    # 3. Get global geo features
    res = client.get("/api/v1/geo/features")
    assert res.status_code == 200
    all_geo = res.json()
    assert len(all_geo["features"]) == 1


def test_api_urbanisme_dossier(up_api):
    app, client = up_api
    sign_in(app, client, subject="admin-user", role="admin")

    # 1. Save urbanisme dossier
    res = client.put(
        "/api/v1/projects/prj-tinduff/urbanisme",
        headers=headers(),
        json={
            "parcel_ref": "Parcelle Exemple A-12",
            "request_type": "permis_construire",
            "regulation_source": "PLU Plougastel Zone Ub",
            "checklist": [
                {"id": "pcmi1", "label": "Plan de situation", "checked": True},
                {"id": "pcmi2", "label": "Plan de masse", "checked": True},
            ],
            "advice_status": "favorable",
            "follow_up_date": "2027-04-15",
        },
    )
    assert res.status_code == 200, res.text
    saved = res.json()
    assert saved["parcel_ref"] == "Parcelle Exemple A-12"
    assert saved["advice_status"] == "favorable"

    # 2. Get urbanisme dossier
    res = client.get("/api/v1/projects/prj-tinduff/urbanisme")
    assert res.status_code == 200
    dossier = res.json()["dossier"]
    assert dossier is not None
    assert dossier["parcel_ref"] == "Parcelle Exemple A-12"
    assert len(dossier["checklist"]) == 2


def test_api_port_inspections(up_api):
    app, client = up_api
    sign_in(app, client, subject="admin-user", role="admin")

    # 1. Create inspection
    res = client.post(
        "/api/v1/projects/prj-tinduff/port-inspections",
        headers=headers(),
        json={
            "port_name": "Port du Tinduff",
            "ouvrage_type": "Ponton plaisance",
            "inspector": "Gilles Le Gall",
            "inspection_date": "2026-11-18",
            "condition_rating": "moyen",
            "observations": "Usure normale des caténaires d'amarrage.",
            "linked_action_id": "",
        },
    )
    assert res.status_code == 200, res.text
    insp = res.json()
    assert insp["port_name"] == "Port du Tinduff"
    assert insp["condition_rating"] == "moyen"

    # 2. List inspections
    res = client.get("/api/v1/projects/prj-tinduff/port-inspections")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["inspector"] == "Gilles Le Gall"
