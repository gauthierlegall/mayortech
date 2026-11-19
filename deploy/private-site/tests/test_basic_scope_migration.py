import importlib.util
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "basic_scope.py"
    assert path.is_file(), "Restricted native-scope migration is not implemented"
    spec = importlib.util.spec_from_file_location("private_basic_scope_migration", path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


CLIENT = {
    "clientId": "mayortech-space",
    "id": "11111111-1111-4111-8111-111111111111",
    "protocol": "openid-connect",
    "publicClient": False,
    "redirectUris": ["https://espace.kerforge.com/api/v1/auth/callback"],
}
BASIC = {"id": "22222222-2222-4222-8222-222222222222", "name": "basic", "protocol": "openid-connect"}
BEFORE = [{"id": "33333333-3333-4333-8333-333333333333", "name": "profile", "protocol": "openid-connect"}]
MAPPERS = [
    {
        "protocolMapper": "oidc-usersessionmodel-note-mapper",
        "config": {
            "user.session.note": "AUTH_TIME",
            "claim.name": "auth_time",
            "id.token.claim": "true",
            "jsonType.label": "long",
        },
    }
]


def test_plan_never_changes_the_provider_and_requires_the_native_time_mapper():
    m = module()
    plan = m.plan(CLIENT, BASIC, BEFORE, MAPPERS)
    assert plan["needs_basic"] and plan["client_id"] == "mayortech-space"
    with pytest.raises(ValueError):
        m.plan(CLIENT, BASIC, BEFORE, [])


def test_other_client_is_refused_before_any_write():
    m = module()
    with pytest.raises(ValueError):
        m.plan({**CLIENT, "clientId": "another-application"}, BASIC, BEFORE, MAPPERS)


def test_reviewed_scope_addition_uses_one_native_link_and_preserves_existing_scopes():
    m = module()
    review = m.plan(CLIENT, BASIC, BEFORE, MAPPERS)
    calls = []
    backups = []

    def call(path, method="GET"):
        calls.append((path, method))
        return BEFORE + [BASIC] if method == "GET" else None

    result = m.apply_reviewed(review, review["fingerprint"], BEFORE, call, backups.append)
    writes = [x for x in calls if x[1] != "GET"]
    assert writes == [
        ("/admin/realms/mayortech/clients/" + CLIENT["id"] + "/default-client-scopes/" + BASIC["id"], "PUT")
    ]
    assert backups == [BEFORE] and result["basic_assigned"]


def test_changed_scope_set_cannot_be_approved_with_an_old_fingerprint():
    m = module()
    review = m.plan(CLIENT, BASIC, BEFORE, MAPPERS)
    calls = []
    with pytest.raises(ValueError):
        m.apply_reviewed(
            review, "old-fingerprint", BEFORE, lambda *a, **k: calls.append(a), lambda before: None
        )
    assert calls == []


def test_failed_postcondition_removes_only_the_link_added_by_this_operation():
    m = module()
    review = m.plan(CLIENT, BASIC, BEFORE, MAPPERS)
    calls = []

    def call(path, method="GET"):
        calls.append((path, method))
        return BEFORE if method == "GET" else None

    with pytest.raises(ValueError):
        m.apply_reviewed(review, review["fingerprint"], BEFORE, call, lambda value: None)
    writes = [item for item in calls if item[1] != "GET"]
    endpoint = "/admin/realms/mayortech/clients/" + CLIENT["id"] + "/default-client-scopes/" + BASIC["id"]
    assert writes == [(endpoint, "PUT"), (endpoint, "DELETE")]


def test_already_assigned_basic_scope_is_idempotent_without_backup_or_writes():
    m = module()
    before = BEFORE + [BASIC]
    review = m.plan(CLIENT, BASIC, before, MAPPERS)

    def refuse(*args, **kwargs):
        raise AssertionError("An idempotent migration must not write")

    result = m.apply_reviewed(review, review["fingerprint"], before, refuse, refuse)
    assert result["basic_assigned"] and not result["changed"]


def test_native_scope_backup_accepts_a_brief_representation_without_protocol():
    m = module()
    value = {"id": BEFORE[0]["id"], "name": "profile", "unrelated_private_field": "synthetic"}
    assert m.scope_backup_entries([value]) == [{"id": BEFORE[0]["id"], "name": "profile"}]
