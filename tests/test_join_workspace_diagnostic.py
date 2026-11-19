"""Exercise the frontend's actual private bootstrap dependencies after self-join."""
from fastapi.testclient import TestClient

from test_account_onboarding_http import headers, private


def test_new_test_organization_member_can_load_every_workspace_dependency(tmp_path):
    app, _, token = private(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("travaux_session", token)
        assert client.post("/api/v1/account/organizations/town-a/join", json={"code":"MAIRIE-TEST"}, headers=headers()).status_code == 200
        session = client.get("/api/v1/session")
        assert session.status_code == 200 and not session.json()["organization_required"]
        paths = [
            "/api/v1/bootstrap",
            "/api/v1/projects",
            "/api/v1/mailbox/messages?folder=all&limit=200&offset=0",
            "/api/v1/summaries",
            "/api/v1/organization",
            "/api/v1/organization/members",
            "/api/v1/organization/audit",
        ]
        projects = client.get("/api/v1/projects").json()
        paths += [path for project in projects for path in (
            "/api/v1/projects/" + project["id"],
            "/api/v1/projects/" + project["id"] + "/documents",
        )]
        statuses = {path: client.get(path).status_code for path in paths}
        assert all(status == 200 for status in statuses.values()), statuses
