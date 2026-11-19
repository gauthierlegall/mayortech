import base64

from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.auth import hash_password
from travaux.config import Settings

HEADERS = {"X-Requested-With": "Travaux"}


def test_page_edits_are_part_of_the_project_context_and_cannot_overwrite_a_newer_version(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / "api.sqlite3"))) as client:
        project = client.get("/api/v1/projects").json()[0]
        page = client.post(f"/api/v1/projects/{project['id']}/page", json={}, headers=HEADERS).json()
        payload = {"state_base64":base64.b64encode(b"fixture-native-state").decode(), "expected_revision_hash":None, "text":"Constat terrain fictif : passage piéton maintenu.", "editor_version":"blocksuite-0.22.4"}
        saved = client.put(f"/api/v1/pages/{page['id']}/state", json=payload, headers=HEADERS)
        saved.raise_for_status()
        summary = client.post(f"/api/v1/projects/{project['id']}/summaries", json={}, headers=HEADERS).json()
        assert "passage piéton maintenu" in summary["content"]
        payload.update(state_base64=base64.b64encode(b"different-native-state").decode(), text="Other old tab")
        assert client.put(f"/api/v1/pages/{page['id']}/state", json=payload, headers=HEADERS).status_code == 409
        assert client.get(f"/api/v1/pages/{page['id']}/state").json()["text"].startswith("Constat terrain")


def test_correspondence_search_filters_and_attachments_read_in_same_session(tmp_path):
    with TestClient(create_app(Settings(db_path=tmp_path / "mail.sqlite3"))) as client:
        response = client.get("/api/v1/mail?q=TRV-2026-014").json()
        assert response["total"] == 2
        assert all("note_id" not in item["metadata"] for item in response["items"])
        source = response["items"][0]
        message = client.get(f"/api/v1/mail/{source['id']}").json()
        assert message["body"] and message["project_id"]
        assert client.get("/api/v1/mail?q=not-in-any-fictitious-mail").json()["total"] == 0
        assert client.get("/api/v1/mail/not-authorized").status_code == 404


def test_protected_staging_seeds_only_fiction_and_does_not_bypass_auth(tmp_path):
    settings = Settings(mode="staging", db_path=tmp_path / "staging.sqlite3", password_hash=hash_password("une phrase de passe de demonstration"), public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
    with TestClient(create_app(settings), base_url="https://travaux.example") as client:
        assert not client.get("/api/v1/session").json()["authenticated"]
        assert client.get("/api/v1/projects").status_code == 401
        client.post("/api/v1/session", json={"password":"une phrase de passe de demonstration"}, headers=HEADERS).raise_for_status()
        assert client.get("/api/v1/session").json()["demo"]
        assert len(client.get("/api/v1/projects").json()) == 6
