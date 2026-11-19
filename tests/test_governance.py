"""Real tenant/resource/action authorization; no fictitious identity provider."""
import importlib

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from travaux.auth import hash_password
from travaux.config import Settings
from travaux.domain import DomainError
from travaux.repository import Repository


def governance_module():
    try:
        return importlib.import_module("travaux.governance")
    except ModuleNotFoundError as error:
        if error.name == "travaux.governance":
            pytest.fail("Le profil organisation doit être servi par un contrôle tenant/ressource/action réel")
        raise


def settings(tmp_path, mode="staging"):
    return Settings(mode=mode, db_path=tmp_path / "governance.sqlite3", tenant_id="town-a",
                    password_hash=hash_password("une phrase fictive de test"),
                    public_origin="https://travaux.example", allowed_hosts=("travaux.example",))


def app_client(repo, configured, current):
    app = FastAPI()
    @app.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse({"error": {"code": error.code}}, status_code={"not_found": 404, "forbidden": 403, "unauthenticated": 401, "invalid_input": 422}.get(error.code, 409))
    def actor():
        if current is None:
            raise DomainError("unauthenticated", "Session requise")
        return dict(current)
    service = governance_module().register_governance_routes(app, repo, configured.tenant_id, actor, configured)
    return TestClient(app), service


def test_private_admin_profile_update_is_durable_and_audited(tmp_path):
    repo = Repository(tmp_path / "store.sqlite3")
    configured = settings(tmp_path)
    try:
        client, _ = app_client(repo, configured, {"actor_id": "responsable", "tenant_id": "town-a"})
        with client:
            profile = client.get("/api/v1/organization").json()
            assert profile["can_manage"] and profile["capabilities"]["identity_provider"] is False
            changed = client.patch("/api/v1/organization", json={"name": "Collectivité fictive A", "service": "Bâtiments et voirie", "expected_revision": profile["revision"]})
            assert changed.status_code == 200
            assert changed.json()["name"] == "Collectivité fictive A" and changed.json()["revision"] == profile["revision"] + 1
            audit = client.get("/api/v1/organization/audit").json()["items"]
            update = next(row for row in audit if row["action"] == "organization.updated")
            assert update["actor_id"] == "responsable"
        again, _ = app_client(repo, configured, {"actor_id": "responsable", "tenant_id": "town-a"})
        with again:
            assert again.get("/api/v1/organization").json()["service"] == "Bâtiments et voirie"
    finally:
        repo.close()


def test_stale_profile_updates_and_replays_cannot_erase_other_changes(tmp_path):
    repo = Repository()
    try:
        client, _ = app_client(repo, settings(tmp_path), {"actor_id": "responsable", "tenant_id": "town-a"})
        with client:
            current = client.get("/api/v1/organization").json()
            data = {"name": "Fictif", "service": "Travaux", "expected_revision": current["revision"]}
            latest = client.patch("/api/v1/organization", json=data).json()
            assert client.patch("/api/v1/organization", json={**data, "service": "Ancien onglet"}).status_code == 409
            replay = client.patch("/api/v1/organization", json={**data, "expected_revision": latest["revision"]})
            assert replay.status_code == 200 and replay.json()["revision"] == latest["revision"]
            updates = [row for row in client.get("/api/v1/organization/audit").json()["items"] if row["action"] == "organization.updated"]
            assert len(updates) == 1
    finally:
        repo.close()


def test_public_visitor_is_real_current_shared_actor_without_invented_members(tmp_path):
    repo = Repository()
    try:
        client, service = app_client(repo, settings(tmp_path, "public_demo"), {"actor_id": "responsable-demo", "tenant_id": "town-a", "role": "admin"})
        with client:
            profile = client.get("/api/v1/organization").json()
            assert not profile["can_manage"]
            assert client.patch("/api/v1/organization", json={"name": "Interdit", "service": "Interdit", "expected_revision": profile["revision"]}).status_code == 403
            members = client.get("/api/v1/organization/members").json()
            assert members["total"] == 1
            assert members["items"][0]["display_name"] == "Visiteur"
            assert members["items"][0]["kind"] == "shared_access"
            assert members["items"][0]["is_current"]
            assert not members["capabilities"]["identity_provider"] and not members["capabilities"]["invitations"]
            assert client.get("/api/v1/organization/roles").status_code == 200
            assert client.get("/api/v1/organization/audit").status_code == 200
        # Even a mistaken extra server-side policy cannot open public imports or profile writes.
        service.bind_role("responsable-demo", "admin")
        actor = {"actor_id": "responsable-demo", "tenant_id": "town-a"}
        assert not service.authorize(actor, "organization", "write")
        assert not service.authorize(actor, "mail", "write")
        assert service.authorize(actor, "workspace", "write") and service.authorize(actor, "mail", "flags")
    finally:
        repo.close()


def test_real_domain_rbac_distinguishes_admin_editor_reader_and_unknown_actor(tmp_path):
    service = governance_module().GovernanceService(Repository(), "town-a", settings(tmp_path))
    try:
        service.bind_role("editor-test", "editor")
        service.bind_role("reader-test", "reader")
        editor = {"actor_id": "editor-test", "tenant_id": "town-a"}
        reader = {"actor_id": "reader-test", "tenant_id": "town-a"}
        assert service.authorize(editor, "workspace", "write") and service.authorize(editor, "mail", "write")
        assert not service.authorize(editor, "organization", "write")
        assert service.authorize(reader, "workspace", "read") and service.authorize(reader, "mail", "read")
        assert not service.authorize(reader, "workspace", "write") and not service.authorize(reader, "mail", "write")
        assert not service.authorize({"actor_id": "unregistered", "tenant_id": "town-a", "role": "admin"}, "organization", "write")
        assert not service.authorize({"actor_id": "admin", "tenant_id": "town-a"}, "organization", "write")
        assert not service.authorize({"actor_id": "responsable", "tenant_id": "town-b"}, "organization", "write")
        assert not service.authorize(editor, "unknown-resource", "read")
    finally:
        service.repo.close()


def test_role_matrix_is_backed_by_the_same_enforcer_and_no_assignment_endpoint_exists(tmp_path):
    repo = Repository()
    try:
        client, service = app_client(repo, settings(tmp_path), {"actor_id": "responsable", "tenant_id": "town-a"})
        with client:
            roles = client.get("/api/v1/organization/roles").json()
            assert {role["id"] for role in roles["items"]} == {"admin", "editor", "reader"}
            for role in roles["items"]:
                assert role["assignable"] is False
                for permission in role["permissions"]:
                    assert permission["allowed"] == service.enforcer.enforce(role["id"], "town-a", permission["resource"], permission["action"])
            assert roles["capabilities"]["identity_provider"] is False
            assert client.post("/api/v1/organization/members", json={"email": "nobody@fictitious.invalid"}).status_code == 405
    finally:
        repo.close()


def test_audit_uses_real_project_events_and_source_provenance_without_other_tenant_or_raw_payload(tmp_path):
    repo = Repository()
    try:
        project = repo.create_project("town-a", "FAKE-A", "Chantier fictif A")
        other = repo.create_project("town-b", "FAKE-B", "OTHER_TENANT_MUST_NOT_LEAK")
        source = repo.ingest_source("town-a", "fake-mail", "[FAKE-A] Accès", "Accès : maintenu", project_ref="FAKE-A")
        candidate = repo.add_candidate("town-a", project["id"], source["id"], "access", "maintenu", quote="Accès : maintenu")
        repo.review_candidate("town-a", candidate["id"], "accept", actor_id="responsable")
        repo.add_note("town-b", other["id"], "OTHER_PRIVATE_NOTE_MUST_NOT_LEAK", actor_id="other")
        with repo._transaction() as db:
            repo._audit(db, "town-a", project["id"], "custom.test", "responsable", source["id"], {"password": "RAW_PAYLOAD_MUST_NOT_LEAK", "access_token": "RAW_TOKEN_MUST_NOT_LEAK"})
        client, _ = app_client(repo, settings(tmp_path), {"actor_id": "responsable", "tenant_id": "town-a"})
        with client:
            response = client.get("/api/v1/organization/audit")
            assert response.status_code == 200
            accepted = next(item for item in response.json()["items"] if item["action"] == "candidate.accepted")
            assert accepted["actor_id"] == "responsable" and accepted["project_id"] == project["id"]
            assert accepted["provenance"]["source_id"] == source["id"]
            assert accepted["provenance"]["source_hash"] == source["body_hash"]
            assert next(item for item in response.json()["items"] if item["action"] == "custom.test")["object_id"] == source["id"]
            assert all(phrase not in response.text for phrase in ["OTHER_TENANT", "OTHER_PRIVATE_NOTE", "RAW_PAYLOAD", "RAW_TOKEN"])
            assert len(client.get("/api/v1/organization/audit?limit=1").json()["items"]) == 1
            assert client.get(f"/api/v1/organization/audit?project_id={other['id']}").status_code == 404
    finally:
        repo.close()


def test_governance_api_requires_actor_and_refuses_foreign_tenant_even_with_admin_claim(tmp_path):
    repo = Repository()
    try:
        configured = settings(tmp_path)
        client, _ = app_client(repo, configured, None)
        with client:
            assert client.get("/api/v1/organization").status_code == 401
        foreign, _ = app_client(repo, configured, {"actor_id": "responsable", "tenant_id": "town-b", "role": "admin"})
        with foreign:
            for path in ["organization", "organization/members", "organization/roles", "organization/audit"]:
                assert foreign.get("/api/v1/" + path).status_code == 403
    finally:
        repo.close()


def test_organization_profile_rejects_control_characters_and_unexpected_fields(tmp_path):
    repo = Repository()
    try:
        client, _ = app_client(repo, settings(tmp_path), {"actor_id": "responsable", "tenant_id": "town-a"})
        with client:
            profile = client.get("/api/v1/organization").json()
            assert client.patch("/api/v1/organization", json={"name": "A\x00B", "service": "Travaux", "expected_revision": profile["revision"]}).status_code == 422
            assert client.patch("/api/v1/organization", json={"name": "A", "service": "Travaux", "expected_revision": profile["revision"], "role": "admin"}).status_code == 422
            assert client.get("/api/v1/organization").json()["revision"] == profile["revision"]
    finally:
        repo.close()
