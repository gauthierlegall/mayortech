"""Verified IdP identities may choose an organization without app privileges."""
import json
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest

from test_oidc import oidc as _oidc_fixture, begin
from travaux.domain import DomainError

oidc = _oidc_fixture


def test_signup_intent_uses_only_the_explicit_provider_registration_url(oidc):
    service, state, _, _, _ = oidc
    signup = "https://identity.example/realm/town/registrations"
    object.__setattr__(service.configuration, "signup_url", signup)
    assert getattr(service, "signup_available", False) is True
    try:
        started = service.start(intent="signup")
    except TypeError:
        pytest.fail("The OIDC start service must accept the explicit signup intent")
    assert urlsplit(started["authorization_url"]).path == "/realm/town/registrations"
    query = parse_qs(urlsplit(started["authorization_url"]).query)
    assert query["code_challenge_method"] == ["S256"] and query["nonce"] and query["state"]


def test_signup_missing_configuration_is_not_silently_changed_to_login(oidc):
    service, _, _, _, _ = oidc
    assert not getattr(service, "signup_available", False)
    with pytest.raises(DomainError):
        service.start(intent="signup")


def test_valid_mfa_unknown_identity_gets_only_a_short_onboarding_session(oidc):
    service, state, _, repo, sessions = oidc
    response, query = begin(service, state)
    state["claims"] = {"sub": "new-person", "name": "Nouvelle personne"}
    try:
        token = service.finish(state=query["state"][0], code="fake-code", binding=response["binding"], allow_onboarding=True)
    except TypeError:
        pytest.fail("Verified pending identities need a distinct onboarding session")
    current = sessions.resolve(token)
    assert current["tenant_id"] == "onboarding:town-a"
    assert service.members.get_active(current["actor_id"]) is None
    row = repo._db.execute("SELECT role,active FROM identity_members WHERE actor_id=?", (current["actor_id"],)).fetchone()
    assert row["role"] == "reader" and row["active"] == 0
    lifetime = repo._db.execute("SELECT expires FROM sessions WHERE digest=?", (sessions.digest(token),)).fetchone()[0]
    import time
    assert 0 < lifetime - time.time() <= 900


def test_invalid_mfa_cannot_get_an_onboarding_session(oidc):
    service, state, _, repo, _ = oidc
    response, query = begin(service, state)
    state["claims"] = {"sub": "new-person", "acr": "password-only"}
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"], allow_onboarding=True)
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_signup_configuration_rejects_a_url_outside_authorized_identity_hosts(oidc):
    service, _, _, _, _ = oidc
    with pytest.raises(ValueError):
        replace(service.configuration, signup_url="https://evil.example/signup")


def account_setup(tmp_path, *, test=True):
    from travaux.auth import SessionStore
    from travaux.config import Settings
    from travaux.governance import GovernanceService
    from travaux.identity import IdentityStore
    from travaux.project_access import ProjectAccess
    from travaux.repository import Repository
    try:
        from travaux.account_onboarding import AccountOnboardingService
    except ModuleNotFoundError:
        pytest.fail("The isolated account onboarding service must be implemented")
    settings = Settings(mode="staging", auth_mode="oidc", test_organization_self_join=test, organization_join_code="" if test else "TOWN-ACCESS", db_path=tmp_path / "accounts.sqlite3", tenant_id="town-a", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
    repo = Repository(settings.db_path)
    sessions = SessionStore(settings.db_path)
    members = repo.identity_store = IdentityStore(repo, settings.tenant_id, sessions)
    repo.access = ProjectAccess(repo, settings)
    GovernanceService(repo, settings.tenant_id, settings)
    with repo._transaction() as db:
        db.execute("UPDATE organization_profiles SET name=? WHERE tenant_id=?", ("Mairie test" if test else "Collectivité", settings.tenant_id))
    project = repo.create_project("town-a", "TEST-1", "Cour fictive")
    member = members.provision("https://identity.example", "new-person", "Nouvelle personne", "reader", active=False)
    token = sessions.issue(member["actor_id"], "onboarding:town-a", ttl=900)
    service = AccountOnboardingService(repo, settings, sessions, members)
    return service, repo, sessions, members, member, token, project


def test_onboarding_session_exposes_only_directory_until_explicit_test_join(tmp_path):
    service, repo, sessions, members, member, token, project = account_setup(tmp_path)
    principal = sessions.resolve(token)
    state = service.session_state(principal)
    assert state["authenticated"] and state["organization_required"] and state["actor"] is None
    assert state["account"] == {"id": member["actor_id"], "display_name": "Nouvelle personne"}
    directory = service.organizations(principal)
    assert directory["organization_required"] is True
    item = directory["items"][0]
    assert item["id"] == "town-a" and item["name"] == "Mairie test"
    assert item["is_test"] is True and item["can_self_join"] is True and item["membership_status"] == "not_joined"
    assert members.get_active(member["actor_id"]) is None
    assert repo._db.execute("SELECT count(*) FROM project_grants").fetchone()[0] == 0
    result, replacement = service.join(token, "town-a", code="MAIRIE-TEST")
    assert result["status"] == "joined" and replacement
    assert sessions.resolve(token) is None
    entered = sessions.resolve(replacement)
    assert entered["tenant_id"] == "town-a"
    assert members.get_active(member["actor_id"])["role"] == "editor"
    assert repo._db.execute("SELECT project_id FROM project_grants WHERE actor_id=?", (member["actor_id"],)).fetchone()[0] == project["id"]
    assert service.session_state(entered)["organization_required"] is False
    assert "token" not in json.dumps(result)


def test_real_organization_join_remains_pending_without_permissions(tmp_path):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path, test=False)
    response, replacement = service.join(token, "town-a", code="TOWN-ACCESS")
    assert response["status"] == "pending" and replacement is None
    assert members.get_active(member["actor_id"]) is None
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"
    assert service.organizations(sessions.resolve(token))["items"][0]["membership_status"] == "pending"
    assert repo._db.execute("SELECT count(*) FROM project_grants").fetchone()[0] == 0


def test_join_refuses_foreign_tenant_and_cannot_reactivate_revoked_member(tmp_path):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path)
    with pytest.raises(DomainError):
        service.join(token, "other-town")
    with repo._transaction() as db:
        db.execute("UPDATE identity_members SET revision=2 WHERE actor_id=?", (member["actor_id"],))
    result, replacement = service.join(token, "town-a", code="MAIRIE-TEST")
    assert result["status"] == "pending" and replacement is None
    assert members.get_active(member["actor_id"]) is None
    assert not service.organizations(sessions.resolve(token))["items"][0]["can_self_join"]


def test_join_failure_rolls_back_activation_grants_and_session_revocation(tmp_path, monkeypatch):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path)
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")
    monkeypatch.setattr(service, "_audit", fail)
    with pytest.raises(RuntimeError):
        service.join(token, "town-a", code="MAIRIE-TEST")
    assert members.get_active(member["actor_id"]) is None
    assert repo._db.execute("SELECT count(*) FROM project_grants").fetchone()[0] == 0
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"


def test_join_session_creation_failure_is_atomic(tmp_path, monkeypatch):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path)
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic session insert failure")
    monkeypatch.setattr(service, "_issue_session", fail)
    with pytest.raises(RuntimeError):
        service.join(token, "town-a", code="MAIRIE-TEST")
    assert members.get_active(member["actor_id"]) is None
    assert repo._db.execute("SELECT count(*) FROM project_grants").fetchone()[0] == 0
    assert sessions.resolve(token)["tenant_id"] == "onboarding:town-a"


def test_expired_global_session_cannot_join_and_other_namespace_is_not_a_principal(tmp_path):
    service, _, sessions, _, member, _, _ = account_setup(tmp_path)
    expired = sessions.issue(member["actor_id"], "onboarding:town-a", ttl=-1)
    foreign = sessions.issue(member["actor_id"], "onboarding:other-town", ttl=900)
    for token in (expired, foreign):
        with pytest.raises(DomainError):
            service.join(token, "town-a")
    assert service.session_state(sessions.resolve(foreign))["authenticated"] is False


def test_signup_requires_verified_email_in_addition_to_mfa(oidc):
    service, state, _, repo, _ = oidc
    object.__setattr__(service.configuration, "signup_url", "https://identity.example/realm/town/registrations")
    started = service.start(intent="signup")
    query = parse_qs(urlsplit(started["authorization_url"]).query)
    state["nonce"] = query["nonce"][0]
    state["claims"] = {"sub": "new-person", "email_verified": False}
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=started["binding"], allow_onboarding=True)
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_revoked_previous_membership_can_only_record_a_new_pending_request(tmp_path):
    service, repo, sessions, members, member, token, _ = account_setup(tmp_path)
    _, active_session = service.join(token, "town-a", code="MAIRIE-TEST")
    active = members.get_active(member["actor_id"])
    members.update(active["actor_id"], role="editor", active=False, expected_revision=active["revision"], updated_by="operator")
    assert sessions.resolve(active_session) is None
    returning = sessions.issue(member["actor_id"], "onboarding:town-a", ttl=900)
    result, replacement = service.join(returning, "town-a", code="MAIRIE-TEST")
    assert result["status"] == "pending" and replacement is None
    assert repo._db.execute("SELECT status FROM account_join_requests").fetchone()[0] == "pending"
    assert members.get_active(member["actor_id"]) is None
