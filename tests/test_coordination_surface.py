import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app, request_permission
from travaux.auth import hash_password
from travaux.config import Settings
from travaux.connection_hub import IntegrationPolicy


@pytest.mark.parametrize(
    "method,path,permission",
    [
        ("GET", "/api/v1/projects/p/properties", ("workspace", "read")),
        ("PATCH", "/api/v1/projects/p/properties", ("workspace", "write")),
        ("GET", "/api/v1/mail-backfills", ("organization", "read")),
        ("GET", "/api/v1/mail-backfills/job", ("organization", "read")),
        ("POST", "/api/v1/mail-backfills", ("organization", "write")),
        ("POST", "/api/v1/mail-backfills/preview", ("organization", "write")),
        ("POST", "/api/v1/mail-backfills/job/run", ("organization", "write")),
        ("POST", "/api/v1/mail-backfills/job/pause", ("organization", "write")),
        ("POST", "/api/v1/mail-backfills/job/resume", ("organization", "write")),
        ("POST", "/api/v1/mail-backfills/job/cancel", ("organization", "write")),
        ("GET", "/api/v1/field-reports", ("workspace", "read")),
        ("GET", "/api/v1/field-reports/report", ("workspace", "read")),
        ("POST", "/api/v1/field-reports", ("workspace", "write")),
        ("PATCH", "/api/v1/field-reports/report", ("workspace", "write")),
        ("POST", "/api/v1/field-reports/report/action-link", ("workspace", "write")),
        ("DELETE", "/api/v1/field-reports/report", None),
        ("DELETE", "/api/v1/projects/p/properties", None),
        ("POST", "/api/v1/mail-backfills/job/unknown", None),
    ],
)
def test_property_and_historical_mail_routes_keep_explicit_permissions(method, path, permission):
    assert request_permission(method, path) == permission


def test_human_property_projection_stays_distinct_from_confirmed_facts(tmp_path):
    app = create_app(Settings(db_path=tmp_path / "properties.sqlite3"))
    with TestClient(app) as client:
        row = client.get("/api/v1/projects").json()[0]
        ident = row["id"]
        endpoint = f"/api/v1/projects/{ident}"
        profile = client.get(endpoint + "/properties")
        assert profile.status_code == 200
        profile = profile.json()
        old_facts = client.get(endpoint).json()["facts"]
        response = client.patch(endpoint + "/properties", headers={"X-Requested-With": "Travaux", "Origin": "http://testserver"}, json={
            "expected_revision": profile["revision"],
            "expected_project_revision": profile["project_revision"],
            "changes": {"location": "", "service_owner": "Équipe de démonstration", "status": "En attente"},
        })
        assert response.status_code == 200, response.text
        detail = client.get(endpoint).json()
        assert detail["properties"]["values"]["location"] == ""
        assert detail["properties"]["values"]["service_owner"] == "Équipe de démonstration"
        assert detail["status"] == "on_hold"
        assert detail["facts"] == old_facts
        projected = next(item for item in client.get("/api/v1/projects").json() if item["id"] == ident)
        assert projected["properties"]["values"]["service_owner"] == "Équipe de démonstration"


@pytest.mark.parametrize(
    "name",
    [
        "TRAVAUX_CONNECTOR_SECRET_KEY",
        "TRAVAUX_TELEGRAM_BOT_TOKEN",
        "TRAVAUX_CALDAV_PASSWORD",
        "TRAVAUX_GOOGLE_CLIENT_SECRET",
    ],
)
def test_public_profile_refuses_new_connector_environment_without_echo(monkeypatch, tmp_path, name):
    secret = "invented-secret-never-echo"
    monkeypatch.setenv(name, secret)
    with pytest.raises(ValueError) as failure:
        Settings(
            mode="public_demo",
            db_path=tmp_path / "public.sqlite3",
            public_origin="https://demo.example",
            allowed_hosts=("demo.example",),
        )
    assert secret not in str(failure.value)


def test_api_mail_account_status_tracks_actual_selected_exchange_reader_and_not_calendar_only(tmp_path):
    origin = "https://travaux.example"
    app = create_app(
        Settings(
            mode="staging",
            db_path=tmp_path / "private.sqlite3",
            password_hash=hash_password("phrase fictive pour test"),
            public_origin=origin,
            allowed_hosts=("travaux.example",),
        )
    )
    app.state.connections.policy = IntegrationPolicy(True, ("exchange.example",))

    class Reader:
        def __init__(self, profile, secrets, policy):
            assert secrets["password"] == "fake-password"

        def probe(self):
            return {
                "calendars": [{"id": "cal", "name": "Agenda"}],
                "mail_folders": [{"id": "inbox", "name": "Réception"}],
            }

        def calendar_events(self, selected, start, end):
            return {"cal": []}

        def collect_mail(self, repo, tenant, ident, *, guard):
            guard()
            return {"accepted": 0, "batches": [], "more_available": False, "remote_write_enabled": False}

        def close(self):
            pass

    app.state.connections.reader_factory = Reader
    headers = {"Origin": origin, "X-Requested-With": "Travaux"}
    with TestClient(app, base_url=origin) as client:
        assert client.post("/api/v1/session", headers=headers, json={"password": "phrase fictive pour test"}).status_code == 200
        record = client.post(
            "/api/v1/integrations/connections",
            headers=headers,
            json={
                "provider": "exchange",
                "label": "Service",
                "endpoint": "https://exchange.example/EWS/Exchange.asmx",
                "username": "fake",
                "mailbox": "fake@example.invalid",
                "password": "fake-password",
            },
        ).json()
        prefix = "/api/v1/integrations/connections/" + record["id"]
        record = client.post(
            prefix + "/probe", headers=headers, json={"expected_revision": record["revision"]}
        ).json()
        record = client.put(
            prefix + "/selection",
            headers=headers,
            json={"calendar_ids": ["cal"], "folder_ids": ["inbox"], "expected_revision": record["revision"]},
        ).json()
        assert client.get("/api/v1/mailbox/folders").json()["account"]["status"] == "ready"
        synced = client.post(
            prefix + "/sync",
            headers=headers,
            json={"expected_revision": record["revision"], "start": "2026-11-01", "end": "2026-12-01"},
        )
        assert synced.status_code == 200, synced.text
        assert client.get("/api/v1/mailbox/folders").json()["account"]["status"] == "ready"
        record = synced.json()["connection"]
        assert (
            client.post(
                prefix + "/sync-mail", headers=headers, json={"expected_revision": record["revision"]}
            ).status_code
            == 200
        )
        folders = client.get("/api/v1/mailbox/folders").json()
        assert folders["account"]["status"] == "read_only"
        assert folders["account"]["last_sync_at"]
        assert folders["capabilities"]["can_send"] is False
        assert client.get("/api/v1/settings").json()["capabilities"]["exchange"]["status"] == "read_only"


def test_only_secret_authenticated_webhook_bypasses_browser_csrf(tmp_path):
    origin = "https://travaux.example"
    app = create_app(
        Settings(
            mode="staging",
            db_path=tmp_path / "private.sqlite3",
            password_hash=hash_password("phrase fictive pour test"),
            public_origin=origin,
            allowed_hosts=("travaux.example",),
        )
    )
    with TestClient(app, base_url=origin) as client:
        response = client.post("/api/v1/integrations/telegram/webhook", json={"update_id": 1})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        response = client.post("/api/v1/conversations", json={})
        assert response.status_code == 403 and response.json()["error"]["code"] == "csrf_rejected"

