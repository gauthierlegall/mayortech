from pathlib import Path
from fastapi.testclient import TestClient
from travaux.api import create_app
from travaux.config import Settings


def test_initial_form_fields_are_saved_as_exact_human_evidence(tmp_path: Path):
    db = tmp_path / "projects.sqlite3"
    app = create_app(Settings(db_path=db))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects",
            headers={"X-Requested-With": "Travaux"},
            json={
                "reference": "FORM-042",
                "name": "Portail",
                "location": "École de Ker Avel",
                "contractor": "Armor Fermetures",
                "owner": "Marie",
                "delivery_date": "2026-11-25",
            },
        )
        assert response.status_code == 201, response.text
        detail = client.get("/api/v1/projects/" + response.json()["id"]).json()
        facts = {row["field"]: row for row in detail["facts"]}
        assert detail["status"] == "planned"
        assert facts["delivery_date"]["value"] == "2026-11-25"
        assert facts["contractor"]["origin"] == "human_assertion"
        assert facts["owner"]["reviewed_by"] == "responsable-demo"
        for row in facts.values():
            proof = row["evidence"][0]
            source = client.get("/api/v1/sources/" + proof["source_id"]).json()
            assert source["body"][proof["start"] : proof["end"]] == proof["quote"]
        assert (
            client.post(
                "/api/v1/projects",
                headers={"X-Requested-With": "Travaux"},
                json={"reference": "FORM-042", "name": "Autre", "location": "Autre lieu"},
            ).status_code
            == 409
        )


def test_invalid_calendar_date_does_not_leave_a_project(tmp_path):
    db = tmp_path / "projects.sqlite3"
    app = create_app(Settings(db_path=db))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects",
            headers={"X-Requested-With": "Travaux"},
            json={"reference": "FORM-BAD", "name": "Portail", "delivery_date": "2026-02-30"},
        )
        assert response.status_code == 422
        assert not any(item["reference"] == "FORM-BAD" for item in client.get("/api/v1/projects").json())
