"""Organization codes and administrator decisions never bootstrap privileges."""

from dataclasses import replace
import json

from fastapi.testclient import TestClient
import pytest

from test_account_onboarding import account_setup
from travaux.api import create_app
from travaux.config import Settings
from travaux.domain import DomainError


def setup(tmp_path, *, test=True):
    values = account_setup(tmp_path, test=test)
    service = values[0]
    service.settings = replace(service.settings, organization_join_code="" if test else "TOWN-ACCESS")
    return values


def admin_token(service, members, sessions, *, role="admin", active=True, tenant=None):
    member = members.provision(
        "https://identity.example", "operator-" + role, "Administrateur", role, active=active
    )
    token = sessions.issue(member["actor_id"], tenant or service.tenant)
    return member, token


@pytest.mark.parametrize("code", [None, "", "OTHER-CODE", "MAIRIE TEST", "mairie-test\nX", "MAIRIE-TÉST"])
def test_wrong_or_missing_code_cannot_join_by_legacy_id(tmp_path, code):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path)
    with pytest.raises(DomainError):
        service.join(token, "town-a", code=code)
    assert members.get_active(member["actor_id"]) is None
    assert repo._db.execute("SELECT count(*) FROM account_join_requests").fetchone()[0] == 0
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"


def test_legacy_id_alone_is_never_a_new_access_grant(tmp_path):
    service, _, _, members, member, token, _ = account_setup(tmp_path)
    with pytest.raises(DomainError):
        service.join(token, "town-a")
    assert members.get_active(member["actor_id"]) is None


def test_normalized_test_code_joins_only_fictional_projects_and_is_not_audited(tmp_path):
    service, repo, sessions, members, member, token, project = account_setup(tmp_path)
    result, replacement = service.join_code(token, "  mairie-test  ")
    assert result["status"] == "joined" and replacement
    assert members.get_active(member["actor_id"])["role"] == "editor"
    assert sessions.resolve(token) is None
    assert sessions.resolve(replacement)["tenant_id"] == "town-a"
    assert (
        repo._db.execute(
            "SELECT project_id FROM project_grants WHERE actor_id=?", (member["actor_id"],)
        ).fetchone()[0]
        == project["id"]
    )
    audit = json.dumps([dict(row) for row in repo._db.execute("SELECT * FROM identity_audit")])
    assert "MAIRIE-TEST" not in audit and "mairie-test" not in audit
    assert service.organizations(sessions.resolve(replacement))["items"][0]["membership_status"] == "joined"


def test_code_rate_limit_is_bound_to_account_and_not_bypassed_by_new_session(tmp_path):
    service, _, sessions, _, member, token, _ = account_setup(tmp_path)
    for _ in range(10):
        with pytest.raises(DomainError):
            service.join_code(token, "INVALID-CODE")
    replacement = sessions.issue(member["actor_id"], "onboarding:town-a")
    with pytest.raises(DomainError) as error:
        service.join_code(replacement, "MAIRIE-TEST")
    assert error.value.code == "conversation_limit"


def test_real_code_requests_access_without_project_or_session_grant(tmp_path):
    service, repo, sessions, members, member, token, _ = setup(tmp_path, test=False)
    result, replacement = service.join_code(token, "town-access")
    assert result["status"] == "pending" and replacement is None
    assert members.get_active(member["actor_id"]) is None
    assert repo._db.execute("SELECT count(*) FROM project_grants").fetchone()[0] == 0
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"
    item = service.organizations(sessions.resolve(token))["items"][0]
    assert item["membership_status"] == "pending" and not item["can_enter"]
    assert "test_join_code" not in item


def test_active_member_can_enter_without_resubmitting_a_code(tmp_path):
    service, _, sessions, members, member, token, _ = account_setup(tmp_path)
    _, access = service.join_code(token, "MAIRIE-TEST")
    result, replacement = service.join(access, "town-a")
    assert result["status"] == "joined" and replacement
    assert sessions.resolve(access) is None
    assert members.get_active(member["actor_id"]) is not None


def test_admin_approves_real_member_as_reader_without_project_grants_or_session(tmp_path):
    service, repo, sessions, members, member, token, _ = setup(tmp_path, test=False)
    service.join_code(token, "TOWN-ACCESS")
    admin, admin_session = admin_token(service, members, sessions)
    items = service.join_requests(admin_session)["items"]
    request = next(item for item in items if item["actor_id"] == member["actor_id"])
    assert set(request) == {"actor_id", "display_name", "email", "status", "revision", "requested_at"}
    result = service.decide(admin_session, member["actor_id"], "approve", request["revision"])
    assert result == {"status": "joined", "member_id": member["actor_id"]}
    active = members.get_active(member["actor_id"])
    assert active["role"] == "reader" and active["revision"] == request["revision"] + 1
    assert repo._db.execute("SELECT count(*) FROM project_grants").fetchone()[0] == 0
    assert (
        repo._db.execute(
            "SELECT count(*) FROM sessions WHERE actor_id=? AND tenant_id='town-a'", (member["actor_id"],)
        ).fetchone()[0]
        == 0
    )
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"
    _, replacement = service.join(token, "town-a")
    assert sessions.resolve(replacement)["tenant_id"] == "town-a"


def test_rejected_request_remains_rejected_with_test_code_and_retains_only_onboarding(tmp_path):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path)
    # A previously revoked membership may request human review but never auto-activate.
    with repo._transaction() as db:
        db.execute("UPDATE identity_members SET revision=2 WHERE actor_id=?", (member["actor_id"],))
    service.join_code(token, "MAIRIE-TEST")
    _, admin_session = admin_token(service, members, sessions)
    request = service.join_requests(admin_session)["items"][0]
    stale_workspace_session = sessions.issue(member["actor_id"], "town-a")
    result = service.decide(admin_session, member["actor_id"], "reject", request["revision"])
    assert result["status"] == "rejected"
    assert sessions.resolve(stale_workspace_session) is None
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"
    assert service.organizations(sessions.resolve(token))["items"][0]["membership_status"] == "rejected"
    joined, replacement = service.join_code(token, "MAIRIE-TEST")
    assert joined["status"] == "rejected" and replacement is None
    assert members.get_active(member["actor_id"]) is None
    assert service.join_requests(admin_session)["items"][0]["status"] == "rejected"


def test_stale_decision_is_rejected_and_does_not_reactivate_a_refused_member(tmp_path):
    service, _, sessions, members, member, token, _ = setup(tmp_path, test=False)
    service.join_code(token, "TOWN-ACCESS")
    _, admin_session = admin_token(service, members, sessions)
    revision = service.join_requests(admin_session)["items"][0]["revision"]
    service.decide(admin_session, member["actor_id"], "reject", revision)
    with pytest.raises(DomainError) as error:
        service.decide(admin_session, member["actor_id"], "approve", revision)
    assert error.value.code == "stale_revision" and members.get_active(member["actor_id"]) is None


@pytest.mark.parametrize(
    "role,active,namespace",
    [
        ("editor", True, None),
        ("reader", True, None),
        ("admin", False, None),
        ("admin", True, "onboarding:town-a"),
        ("admin", True, "other-town"),
    ],
)
def test_admin_routes_revalidate_membership_role_tenant_and_namespace(tmp_path, role, active, namespace):
    service, _, sessions, members, member, token, _ = setup(tmp_path, test=False)
    service.join_code(token, "TOWN-ACCESS")
    _, unauthorized = admin_token(service, members, sessions, role=role, active=active, tenant=namespace)
    with pytest.raises(DomainError):
        service.join_requests(unauthorized)
    with pytest.raises(DomainError):
        service.decide(unauthorized, member["actor_id"], "approve", 0)
    assert members.get_active(member["actor_id"]) is None


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_decision_audit_failure_rolls_back_member_request_and_all_workspace_sessions(
    tmp_path, monkeypatch, decision
):
    service, repo, sessions, members, member, token, _ = setup(tmp_path, test=False)
    service.join_code(token, "TOWN-ACCESS")
    _, admin_session = admin_token(service, members, sessions)
    before = service.join_requests(admin_session)["items"][0]
    workspace_session = sessions.issue(member["actor_id"], "town-a")

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(service, "_audit", fail)
    with pytest.raises(RuntimeError):
        service.decide(admin_session, member["actor_id"], decision, before["revision"])
    assert members.get_active(member["actor_id"]) is None
    assert service.join_requests(admin_session)["items"][0] == before
    assert sessions.resolve(workspace_session)["tenant_id"] == "town-a"
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"


def test_code_settings_test_default_and_real_configuration_do_not_overlap(tmp_path, monkeypatch):
    service, *_ = account_setup(tmp_path)
    assert service.settings.effective_organization_join_code == "MAIRIE-TEST"
    real = replace(service.settings, test_organization_self_join=False)
    assert real.effective_organization_join_code == ""
    assert (
        replace(real, organization_join_code="  town-access  ").effective_organization_join_code
        == "TOWN-ACCESS"
    )
    monkeypatch.setenv("TRAVAUX_ORGANIZATION_JOIN_CODE", "another-code")
    cfg = Settings.from_env()
    assert cfg.organization_join_code == "ANOTHER-CODE"


@pytest.mark.parametrize("code", ["SHORT", "MAIRIE TEST", "MAIRIE-TÉST", "BAD\x00CODE", "X" * 65])
def test_invalid_configured_code_is_rejected_without_echoing_it(tmp_path, code):
    service, *_ = account_setup(tmp_path)
    with pytest.raises(ValueError) as error:
        replace(service.settings, organization_join_code=code)
    assert code not in str(error.value)


def private_app(tmp_path, *, test=True):
    settings = Settings(
        mode="staging",
        auth_mode="oidc",
        test_organization_self_join=test,
        organization_join_code="" if test else "TOWN-ACCESS",
        db_path=tmp_path / "code-http.sqlite3",
        tenant_id="town-a",
        public_origin="https://testserver",
        allowed_hosts=("testserver",),
    )
    app = create_app(settings)
    member = app.state.identities.provision(
        "https://identity.example",
        "new-user",
        "Nouvelle personne",
        "reader",
        email="fictive@example.invalid",
        active=False,
    )
    token = app.state.sessions.issue(member["actor_id"], "onboarding:town-a")
    return app, member, token


HEADERS = {"X-Requested-With": "Travaux", "Origin": "https://testserver"}


def test_http_join_requires_code_both_paths_and_csrf_then_rotates_cookie(tmp_path):
    app, member, token = private_app(tmp_path)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("travaux_session", token)
        assert (
            client.post("/api/v1/account/organizations/join", json={"code": "MAIRIE-TEST"}).status_code == 403
        )
        assert client.post("/api/v1/account/organizations/join", json={}, headers=HEADERS).status_code == 422
        assert (
            client.post("/api/v1/account/organizations/town-a/join", json={}, headers=HEADERS).status_code
            == 422
        )
        assert app.state.identities.get_active(member["actor_id"]) is None
        directory = client.get("/api/v1/account/organizations").json()
        assert directory["test_join_code"] == "MAIRIE-TEST"
        assert directory["items"][0]["test_join_code"] == "MAIRIE-TEST"
        assert directory["items"][0]["name"] == "Mairie test"
        result = client.post(
            "/api/v1/account/organizations/join", json={"code": "mairie-test"}, headers=HEADERS
        )
        assert result.status_code == 200 and result.json()["status"] == "joined"
        assert (
            "HttpOnly" in result.headers["set-cookie"] and "SameSite=strict" in result.headers["set-cookie"]
        )
        assert app.state.sessions.resolve(token) is None
        assert client.get("/api/v1/projects").status_code == 200


def test_http_admin_decision_is_csrf_protected_and_code_is_not_returned_to_real_members(tmp_path):
    app, member, token = private_app(tmp_path, test=False)
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set("travaux_session", token)
        assert client.get("/api/v1/organization/join-requests").status_code in {401, 403}
        directory = client.get("/api/v1/account/organizations").json()
        assert "test_join_code" not in directory
        assert "test_join_code" not in directory["items"][0]
        request = client.post(
            "/api/v1/account/organizations/join", json={"code": "TOWN-ACCESS"}, headers=HEADERS
        )
        assert request.status_code == 200 and request.json()["status"] == "pending"
        assert "set-cookie" not in request.headers
        admin = app.state.identities.provision("https://identity.example", "admin", "Admin", "admin")
        admin_session = app.state.sessions.issue(admin["actor_id"], "town-a")
        client.cookies.set("travaux_session", admin_session)
        items = client.get("/api/v1/organization/join-requests").json()["items"]
        item = next(item for item in items if item["actor_id"] == member["actor_id"])
        url = "/api/v1/organization/join-requests/" + member["actor_id"] + "/decision"
        payload = {"decision": "approve", "expected_revision": item["revision"]}
        assert client.post(url, json=payload).status_code == 403
        assert client.post(url, json={**payload, "role": "admin"}, headers=HEADERS).status_code == 422
        result = client.post(url, json=payload, headers=HEADERS)
        assert result.status_code == 200 and result.json() == {
            "status": "joined",
            "member_id": member["actor_id"],
        }
        assert "set-cookie" not in result.headers
        assert app.state.identities.get_active(member["actor_id"])["role"] == "reader"
        assert client.post(url, json=payload, headers=HEADERS).status_code == 409


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_pending_record_cannot_modify_member_already_activated_by_existing_admin_ui(tmp_path, decision):
    service, _, sessions, members, member, token, _ = setup(tmp_path, test=False)
    service.join_code(token, "TOWN-ACCESS")
    _, admin_session = admin_token(service, members, sessions)
    request = service.join_requests(admin_session)["items"][0]
    active = members.update(
        member["actor_id"],
        role="admin",
        active=True,
        expected_revision=request["revision"],
        updated_by="operator",
    )
    with pytest.raises(DomainError) as error:
        service.decide(admin_session, member["actor_id"], decision, active["revision"])
    assert error.value.code == "conflict"
    assert members.get_active(member["actor_id"]) == active


def test_revoked_admin_session_between_resolution_and_transaction_cannot_decide(tmp_path, monkeypatch):
    service, _, sessions, members, member, token, _ = setup(tmp_path, test=False)
    service.join_code(token, "TOWN-ACCESS")
    _, admin_session = admin_token(service, members, sessions)
    revision = service.join_requests(admin_session)["items"][0]["revision"]
    original = service.principal

    def resolve_then_revoke(value):
        current = original(value)
        sessions.revoke(value)
        return current

    monkeypatch.setattr(service, "principal", resolve_then_revoke)
    with pytest.raises(DomainError):
        service.decide(admin_session, member["actor_id"], "approve", revision)
    assert members.get_active(member["actor_id"]) is None


def test_production_approval_does_not_restore_old_dossier_grants(tmp_path):
    service, repo, sessions, members, member, token, project = setup(tmp_path, test=False)
    with repo._transaction() as db:
        db.execute("UPDATE identity_members SET revision=2 WHERE actor_id=?", (member["actor_id"],))
        db.execute(
            "INSERT INTO project_grants VALUES(?,?,?,?,?)",
            (service.tenant, member["actor_id"], project["id"], "old-access", "2026-01-01"),
        )
    service.join_code(token, "TOWN-ACCESS")
    _, admin_session = admin_token(service, members, sessions)
    revision = service.join_requests(admin_session)["items"][0]["revision"]
    service.decide(admin_session, member["actor_id"], "approve", revision)
    assert members.get_active(member["actor_id"])["role"] == "reader"
    assert (
        repo._db.execute(
            "SELECT count(*) FROM project_grants WHERE actor_id=?", (member["actor_id"],)
        ).fetchone()[0]
        == 0
    )


def test_instance_without_real_code_never_accepts_the_test_default(tmp_path):
    service, _, _, members, member, token, _ = setup(tmp_path, test=False)
    service.settings = replace(service.settings, organization_join_code="")
    with pytest.raises(DomainError):
        service.join_code(token, "MAIRIE-TEST")
    assert members.get_active(member["actor_id"]) is None


def test_existing_member_supplied_wrong_code_is_rejected_without_rotating_session(tmp_path):
    service, _, sessions, _, _, token, _ = account_setup(tmp_path)
    _, access = service.join_code(token, "MAIRIE-TEST")
    with pytest.raises(DomainError):
        service.join_code(access, "INVALID-CODE")
    assert sessions.resolve(access)["tenant_id"] == "town-a"
