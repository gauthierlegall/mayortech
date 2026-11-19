from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings


def test_field_report_http_create_filter_status_and_native_link_use_real_api_guards(tmp_path):
    app = create_app(Settings(db_path=tmp_path / "field-http.sqlite3", tenant_id="town"))
    project = app.state.repo.create_project("town", "TRV-QA-FIELD-HTTP", "Constats fictifs")
    with TestClient(app) as client:
        body = {
            "client_id": "fixture-report-http-1",
            "project_id": project["id"],
            "kind": "Réserve",
            "date": "2026-11-15",
            "title": "Réserve fictive",
            "detail": "Texte fictif préservé.",
            "author": "Service fictif",
        }
        path = "/api/v1/field-reports"
        headers = {"X-Requested-With": "Travaux"}
        assert client.post(path, json=body).status_code == 403
        created = client.post(path, headers=headers, json=body)
        assert created.status_code == 201, created.text
        report = created.json()
        ident = report["id"]
        assert client.post(path, headers=headers, json=body).json()["id"] == ident
        assert (
            client.get(path, params={"project_id": project["id"], "status": "À traiter"}).json()["total"] == 1
        )
        assert client.get(path + "/" + ident).json()["source_id"] == report["source_id"]
        invalid = client.patch(
            path + "/" + ident, headers=headers, json={"expected_revision": True, "status": "Levée"}
        )
        assert invalid.status_code == 422
        saved = client.patch(
            path + "/" + ident, headers=headers, json={"expected_revision": 0, "status": "Levée"}
        )
        assert saved.status_code == 200 and saved.json()["revision"] == 1
        assert (
            client.patch(
                path + "/" + ident, headers=headers, json={"expected_revision": 0, "status": "À traiter"}
            ).status_code
            == 409
        )
        page = client.post("/api/v1/projects/" + project["id"] + "/page", headers=headers, json={}).json()
        link = {
            "expected_revision": 1,
            "page_id": page["id"],
            "database_id": "native-database",
            "row_id": "native-row",
        }
        linked = client.post(path + "/" + ident + "/action-link", headers=headers, json=link)
        assert linked.status_code == 200, linked.text
        assert linked.json()["action_link"]["source_key"] == "field-report:" + ident
        assert (
            client.post(path + "/" + ident + "/action-link", headers=headers, json=link).json()["revision"]
            == 2
        )
        bad = client.post(
            path, headers=headers, json={**body, "client_id": "fixture-report-http-2", "secret": "never-echo"}
        )
        assert bad.status_code == 422 and "never-echo" not in bad.text
        assert client.get("/api/v1/projects/" + project["id"]).json()["facts"] == []


def test_private_field_reports_require_authentication(tmp_path):
    from travaux.auth import hash_password

    app = create_app(
        Settings(
            mode="staging",
            db_path=tmp_path / "private-field.sqlite3",
            tenant_id="town",
            password_hash=hash_password("Phrase de recette fictive"),
            public_origin="https://travaux.example.invalid",
            allowed_hosts=("travaux.example.invalid",),
        )
    )
    with TestClient(app, base_url="https://travaux.example.invalid") as client:
        assert client.get("/api/v1/field-reports").status_code == 401
        headers = {"Origin": "https://travaux.example.invalid", "X-Requested-With": "Travaux"}
        assert (
            client.post(
                "/api/v1/session", headers=headers, json={"password": "Phrase de recette fictive"}
            ).status_code
            == 200
        )
        assert client.get("/api/v1/field-reports").status_code == 200
