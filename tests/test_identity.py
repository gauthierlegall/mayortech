"""Individual identity, real JOSE signatures and durable revocation; no live IdP."""
import importlib

import pytest

from travaux.auth import SessionStore
from travaux.domain import DomainError
from travaux.repository import Repository


def identity():
    try:
        return importlib.import_module("travaux.identity")
    except ModuleNotFoundError as error:
        if error.name == "travaux.identity":
            pytest.fail("Individual OIDC membership must be implemented before enabling professional access")
        raise


def test_individual_principal_uses_issuer_subject_and_explicit_role(tmp_path):
    repo = Repository(tmp_path / "identity.sqlite3")
    store = identity().IdentityStore(repo, "town-a", SessionStore(tmp_path / "identity.sqlite3"))
    try:
        first = store.provision("https://identity.example/realm/town", "subject-a", "Agent A", "editor")
        other = store.provision("https://identity.example/realm/town", "subject-b", "Agent A", "reader")
        assert first["actor_id"] != other["actor_id"]
        assert first["role"] == "editor" and first["active"] is True
        assert store.authenticate("https://identity.example/realm/town", {"sub": "subject-a", "email": "admin@example.invalid", "role": "admin"})["role"] == "editor"
        with pytest.raises(DomainError):
            store.authenticate("https://other.example", {"sub": "subject-a"})
    finally:
        repo.close()


def test_unknown_identity_requests_access_without_getting_permissions(tmp_path):
    repo = Repository(tmp_path / "identity.sqlite3")
    store = identity().IdentityStore(repo, "town-a", SessionStore(tmp_path / "identity.sqlite3"))
    try:
        with pytest.raises(DomainError) as failure:
            store.authenticate("https://identity.example", {"sub": "unknown", "name": "Future agent"})
        assert failure.value.code == "identity_pending"
        pending = store.list_members(include_inactive=True)
        assert len(pending) == 1 and pending[0]["active"] is False
        assert store.get_active(pending[0]["actor_id"]) is None
    finally:
        repo.close()


def test_disable_member_revokes_every_session_and_requires_fresh_revision(tmp_path):
    path = tmp_path / "identity.sqlite3"
    repo, sessions = Repository(path), SessionStore(path)
    store = identity().IdentityStore(repo, "town-a", sessions)
    try:
        member = store.provision("https://identity.example", "a", "Agent A", "editor")
        token1 = sessions.issue(member["actor_id"], "town-a")
        token2 = sessions.issue(member["actor_id"], "town-a")
        changed = store.update(member["actor_id"], role="reader", active=False, expected_revision=member["revision"], updated_by="admin-a")
        assert changed["revision"] == member["revision"] + 1
        assert sessions.resolve(token1) is None and sessions.resolve(token2) is None
        assert store.get_active(member["actor_id"]) is None
        with pytest.raises(DomainError) as failure:
            store.update(member["actor_id"], role="admin", active=True, expected_revision=member["revision"], updated_by="admin-a")
        assert failure.value.code == "stale_revision"
    finally:
        repo.close()


def test_last_administrator_cannot_be_disabled_or_demoted(tmp_path):
    repo = Repository(tmp_path / "identity.sqlite3")
    store = identity().IdentityStore(repo, "town-a", SessionStore(tmp_path / "identity.sqlite3"))
    try:
        admin = store.provision("https://identity.example", "admin", "Administrator", "admin")
        for role, active in [("reader", True), ("admin", False)]:
            with pytest.raises(DomainError) as failure:
                store.update(admin["actor_id"], role=role, active=active, expected_revision=admin["revision"], updated_by=admin["actor_id"])
            assert failure.value.code == "last_administrator"
    finally:
        repo.close()


def test_oidc_settings_do_not_allow_shared_password_fallback(tmp_path):
    from travaux.config import Settings
    configured = Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "private.sqlite3", tenant_id="town-a", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
    assert configured.auth_required and configured.auth_mode == "oidc"
    with pytest.raises(ValueError):
        Settings(mode="public_demo", auth_mode="oidc", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
