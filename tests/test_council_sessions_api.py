"""Tests API endpoints pour le module Séances du Conseil Municipal."""

import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.commissions import COMMISSION_1_ID
from travaux.config import Settings


@pytest.fixture
def council_api(tmp_path):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        db_path=tmp_path / "council_api.sqlite3",
        tenant_id="town-plougastel",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def headers():
    return {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def sign_in(app, client, subject="maire-dominique", role="admin"):
    member = app.state.identities.provision("https://identity.example", subject, subject, role)
    token = app.state.sessions.issue(member["actor_id"], "town-plougastel")
    client.cookies.set("travaux_session", token)
    app.state.commissions.set_member_commission_role(
        "town-plougastel", COMMISSION_1_ID, member["actor_id"], "admin", updated_by=member["actor_id"]
    )
    return member


def test_api_list_council_sessions(council_api):
    app, client = council_api
    sign_in(app, client)

    res = client.get("/api/v1/council-sessions", headers=headers())
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    session = data["items"][0]
    assert session["id"] == "CS-2026-11-26"
    assert "J-5" in session["convocation"]["alert_message"]
    assert session["quorum_stats"]["quorum_reached"] is True


def test_api_get_council_session_detail(council_api):
    app, client = council_api
    sign_in(app, client)

    res = client.get("/api/v1/council-sessions/CS-2026-11-26", headers=headers())
    assert res.status_code == 200
    data = res.json()
    assert len(data["agenda_items"]) == 4
    assert len(data["attendances"]) == 33
    assert data["convocation"]["clear_days_required"] == 5


def test_api_record_vote(council_api):
    app, client = council_api
    sign_in(app, client)

    res = client.post(
        "/api/v1/council-sessions/CS-2026-11-26/items/DELIB-2026-033/vote",
        json={
            "votes_pour": 26,
            "votes_contre": 1,
            "votes_abstention": 2,
            "votes_nppv": 0,
        },
        headers=headers(),
    )
    assert res.status_code == 200
    data = res.json()
    item3 = next(it for it in data["agenda_items"] if it["deliberation_ref"] == "DELIB-2026-033")
    assert item3["vote_result"] == "adopte"
    assert item3["votes_pour"] == 26


def test_api_transmit_megalis(council_api):
    app, client = council_api
    sign_in(app, client)

    res = client.post("/api/v1/council-sessions/CS-2026-11-26/items/DELIB-2026-033/transmit-megalis", headers=headers())
    assert res.status_code == 200
    data = res.json()
    item3 = next(it for it in data["agenda_items"] if it["deliberation_ref"] == "DELIB-2026-033")
    assert item3["transmission_megalis_status"] == "transmis"


def test_api_download_dossier_pdf(council_api):
    app, client = council_api
    sign_in(app, client)

    res = client.get("/api/v1/council-sessions/CS-2026-11-26/dossier-elus.pdf", headers=headers())
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert b"%PDF-1.4" in res.content


def test_api_deliberations_summary(council_api):
    app, client = council_api
    sign_in(app, client)

    res = client.get("/api/v1/council-sessions/CS-2026-11-26/deliberations-summary", headers=headers())
    assert res.status_code == 200
    data = res.json()
    assert data["commune"] == "Ville de Plougastel-Daoulas"
    assert len(data["deliberations"]) == 4


def test_api_proxy_limit_exceeded(council_api):
    app, client = council_api
    sign_in(app, client)

    attendances = [
        {"seat_number": 1, "member_name": "Dominique CAP", "group_name": "Majorité", "status": "present", "proxy_to": ""},
        {"seat_number": 2, "member_name": "Jean-Luc LE GALL", "group_name": "Majorité", "status": "present", "proxy_to": ""},
        {"seat_number": 25, "member_name": "Rozenn LE BOT", "group_name": "Majorité", "status": "pouvoir", "proxy_to": "Dominique CAP"},
        {"seat_number": 26, "member_name": "Michel TANGUY", "group_name": "Majorité", "status": "pouvoir", "proxy_to": "Dominique CAP"},
    ]
    res = client.post(
        "/api/v1/council-sessions/CS-2026-11-26/attendances",
        json={"attendances": attendances},
        headers=headers(),
    )
    assert res.status_code == 400
    assert "proxy_limit_exceeded" in res.text
