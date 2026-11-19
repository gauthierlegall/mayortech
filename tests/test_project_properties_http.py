from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings


def test_properties_http_double_cas_strict_types_and_project_projection(tmp_path):
    app = create_app(Settings(db_path=tmp_path / "surface.sqlite3", tenant_id="commune"))
    project = app.state.repo.create_project("commune", "TRV-FICTIF-77", "Dossier fictif")
    with TestClient(app) as client:
        headers = {"X-Requested-With": "Travaux"}
        path = f"/api/v1/projects/{project['id']}/properties"
        previous = client.get(path)
        assert previous.status_code == 200, previous.text
        previous = previous.json()
        payload = {
            "expected_revision": previous["revision"],
            "expected_project_revision": previous["project_revision"],
            "changes": {"requester": "Équipe fictive", "name": "Nom fictif modifié"},
        }
        assert client.patch(path, json=payload).status_code == 403
        saved = client.patch(path, headers=headers, json=payload)
        assert saved.status_code == 200, saved.text
        assert saved.json()["values"]["requester"] == "Équipe fictive"
        assert client.get(f"/api/v1/projects/{project['id']}").json()["name"] == "Nom fictif modifié"
        assert client.patch(path, headers=headers, json=payload).status_code == 409
        latest = saved.json()
        payload.update(
            expected_revision=latest["revision"], expected_project_revision=latest["project_revision"]
        )
        payload["expected_revision"] = True
        assert client.patch(path, headers=headers, json=payload).status_code == 422
        payload["expected_revision"] = latest["revision"]
        payload["changes"] = {"actual_cost": 1.5}
        assert client.patch(path, headers=headers, json=payload).status_code == 422
        payload["changes"] = {"actual_cost": "1.5", "password": "private-value"}
        rejected = client.patch(path, headers=headers, json=payload)
        assert rejected.status_code == 422 and "private-value" not in rejected.text
        assert client.get(path).json()["values"]["actual_cost"] == ""


def test_private_properties_requires_authenticated_actor(tmp_path):
    from travaux.auth import hash_password

    app = create_app(
        Settings(
            mode="staging",
            db_path=tmp_path / "private.sqlite3",
            tenant_id="commune",
            password_hash=hash_password("mot de passe fictif long"),
            public_origin="https://travaux.example.org",
            allowed_hosts=("travaux.example.org",),
        )
    )
    project = app.state.repo.create_project("commune", "TRV-FICTIF-88", "Dossier fictif")
    with TestClient(app, base_url="https://travaux.example.org") as client:
        path = f"/api/v1/projects/{project['id']}/properties"
        assert client.get(path).status_code == 401
        headers = {"X-Requested-With": "Travaux", "Origin": "https://travaux.example.org"}
        assert (
            client.post(
                "/api/v1/session", headers=headers, json={"password": "mot de passe fictif long"}
            ).status_code
            == 200
        )
        snapshot = client.get(path)
        assert snapshot.status_code == 200
        assert snapshot.json()["values"]["name"] == "Dossier fictif"
