from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.auth import hash_password
from travaux.config import Settings
from travaux.connection_hub import IntegrationPolicy


def test_public_api_rejects_connection_secrets_and_private_calendar_upload(tmp_path):
    settings = Settings(
        mode="public_demo",
        db_path=tmp_path / "public.sqlite3",
        tenant_id="public-town",
        public_origin="https://travaux.example.org",
        allowed_hosts=("travaux.example.org",),
    )
    with TestClient(create_app(settings), base_url="https://travaux.example.org") as client:
        assert client.get("/api/v1/integrations").status_code == 200
        assert client.get("/api/v1/onboarding").json()["persist_in_browser"] is True
        headers = {"X-Requested-With": "Travaux", "Origin": "https://travaux.example.org"}
        rejected = client.post(
            "/api/v1/integrations/connections",
            headers=headers,
            json={
                "provider": "caldav",
                "label": "secret-name",
                "endpoint": "https://cal.example.org",
                "username": "secret-user",
                "password": "secret-password",
            },
        )
        assert (
            rejected.status_code == 403
            and "secret-password" not in rejected.text
            and "secret-user" not in rejected.text
        )
        assert (
            client.post(
                "/api/v1/calendars/import-ics",
                headers=headers,
                json={"name": "Agenda privé", "content": "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR"},
            ).status_code
            == 403
        )
        assert (
            client.patch(
                "/api/v1/onboarding",
                headers=headers,
                json={"completed_steps": ["welcome"], "expected_revision": 0},
            ).status_code
            == 403
        )
        assert client.get("/api/v1/calendars/events").json()["items"] == []
        assert not (tmp_path / ".connector-vault.key").exists()


def test_real_api_auth_csrf_profile_probe_calendar_sync_and_explicit_assignment(tmp_path):
    settings = Settings(
        mode="staging",
        db_path=tmp_path / "private.sqlite3",
        tenant_id="private-town",
        password_hash=hash_password("mot de passe fictif"),
        public_origin="https://travaux.example.org",
        allowed_hosts=("travaux.example.org",),
    )
    app = create_app(settings)
    app.state.connections.policy = IntegrationPolicy(True, ("cal.example.org",))

    class Reader:
        def __init__(self, profile, secrets, policy):
            assert secrets["password"] == "secret-password"

        def probe(self):
            return {"calendars": [{"id": "cal-a", "name": "Agenda travaux"}], "mail_folders": []}

        def calendar_events(self, selected, start, end):
            return {
                "cal-a": [
                    {
                        "remote_uid": "rv-1",
                        "recurrence_id": "",
                        "title": "Visite",
                        "start": "2026-11-20T09:00:00+01:00",
                        "end": "2026-11-20T10:00:00+01:00",
                        "timezone": "Europe/Paris",
                        "all_day": False,
                        "status": "tentative",
                        "description": "À confirmer",
                        "source_url": "",
                    }
                ]
            }

        def close(self):
            pass

    app.state.connections.reader_factory = Reader
    with TestClient(app, base_url="https://travaux.example.org") as client:
        assert client.get("/api/v1/integrations").status_code == 401
        headers = {"X-Requested-With": "Travaux", "Origin": "https://travaux.example.org"}
        assert (
            client.post(
                "/api/v1/session", headers=headers, json={"password": "mot de passe fictif"}
            ).status_code
            == 200
        )
        values = {
            "provider": "caldav",
            "label": "Travaux",
            "endpoint": "https://cal.example.org/dav",
            "username": "agent",
            "password": "secret-password",
        }
        assert client.post("/api/v1/integrations/connections", json=values).status_code == 403
        response = client.post("/api/v1/integrations/connections", headers=headers, json=values)
        assert response.status_code == 201, response.text
        created = response.json()
        assert "secret-password" not in response.text
        base = "/api/v1/integrations/connections/" + created["id"]
        probe = client.post(base + "/probe", headers=headers, json={"expected_revision": created["revision"]})
        assert probe.status_code == 200, probe.text
        selection = client.put(
            base + "/selection",
            headers=headers,
            json={"calendar_ids": ["cal-a"], "folder_ids": [], "expected_revision": probe.json()["revision"]},
        )
        assert selection.status_code == 200, selection.text
        synced = client.post(
            base + "/sync",
            headers=headers,
            json={
                "expected_revision": selection.json()["revision"],
                "start": "2026-11-01",
                "end": "2026-12-01",
            },
        )
        assert synced.status_code == 200, synced.text
        assert synced.json()["connection"]["last_mail_sync_at"] is None
        event = client.get("/api/v1/calendars/events?start=2026-11-01&end=2026-12-01").json()["items"][0]
        assert event["project_id"] is None
        project = client.get("/api/v1/projects").json()[0]
        assigned = client.patch(
            "/api/v1/calendars/events/" + event["id"] + "/assignment",
            headers=headers,
            json={"project_id": project["id"], "expected_revision": event["revision"]},
        )
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["project_id"] == project["id"]
        assert (
            client.patch(
                "/api/v1/calendars/events/" + event["id"] + "/assignment",
                headers=headers,
                json={"project_id": None, "expected_revision": event["revision"]},
            ).status_code
            == 409
        )
        invalid = client.post(
            "/api/v1/integrations/connections",
            headers=headers,
            json={**values, "password": "sensitive-password", "unapproved": "field"},
        )
        assert invalid.status_code == 422 and "sensitive-password" not in invalid.text
        assert client.get("/api/v1/calendars/export.ics?start=2026-11-01&end=2026-12-01").content.startswith(
            b"BEGIN:VCALENDAR"
        )
