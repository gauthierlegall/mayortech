"""Restore one native action without changing MFA, email, recovery or flows."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "deploy/private-site/required_action.py"


def module():
    spec = importlib.util.spec_from_file_location("native_required_action_test", PATH)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def snapshot():
    return {
        "realm": {
            "realm": "mayortech",
            "verifyEmail": True,
            "resetPasswordAllowed": True,
            "browserFlow": "travaux-password-and-otp",
            "smtpServer": {"port": "2465", "ssl": "true"},
        },
        "actions": [
            {
                "alias": "VERIFY_EMAIL",
                "providerId": "VERIFY_EMAIL",
                "enabled": True,
                "defaultAction": True,
                "name": "Email",
                "priority": 10,
                "config": {},
            },
            {
                "alias": "CONFIGURE_TOTP",
                "providerId": "CONFIGURE_TOTP",
                "enabled": True,
                "defaultAction": True,
                "name": "OTP",
                "priority": 20,
                "config": {},
            },
        ],
        "flows": {
            "registration": [{"providerId": "registration-password-action", "requirement": "REQUIRED"}],
            "travaux-password-and-otp": [
                {"providerId": "auth-username-password-form", "requirement": "REQUIRED"},
                {"providerId": "auth-otp-form", "requirement": "REQUIRED"},
            ],
            "reset credentials": [{"providerId": "reset-password", "requirement": "REQUIRED"}],
        },
        "flow_configs": {},
        "client": {
            "clientId": "mayortech-space",
            "protocol": "openid-connect",
            "publicClient": False,
            "redirectUris": ["https://espace.kerforge.com/api/v1/auth/callback"],
        },
        "default_client_scopes": [{"name": "basic"}, {"name": "profile"}, {"name": "email"}],
        "roles": [{"name": "default-roles-mayortech"}],
        "default_role_composites": [{"name": "offline_access"}],
    }


class Native:
    def __init__(self, state):
        self.state = deepcopy(state)
        self.writes = []
        self.saved = []
        self.fail_put = False
        self.concurrent = False

    def read(self):
        return deepcopy(self.state)

    def write(self, path, method, data=None):
        self.writes.append((path, method, deepcopy(data)))
        if method == "POST":
            assert path.endswith("/authentication/register-required-action")
            self.state["actions"].append(
                {
                    "alias": "UPDATE_PASSWORD",
                    "providerId": "UPDATE_PASSWORD",
                    "enabled": True,
                    "defaultAction": False,
                    "priority": 21,
                    "name": data["name"],
                    "config": {},
                }
            )
        elif method == "PUT":
            assert path.endswith("/required-actions/UPDATE_PASSWORD")
            if self.fail_put:
                raise RuntimeError("synthetic write failure")
            self.state["actions"] = [
                entry for entry in self.state["actions"] if entry["alias"] != "UPDATE_PASSWORD"
            ] + [deepcopy(data)]
            if self.concurrent:
                self.state["flows"]["reset credentials"][0]["requirement"] = "DISABLED"
        elif method == "DELETE":
            assert path.endswith("/required-actions/UPDATE_PASSWORD")
            self.state["actions"] = [
                entry for entry in self.state["actions"] if entry["alias"] != "UPDATE_PASSWORD"
            ]
        else:
            raise AssertionError("Unexpected mutation")


def test_template_keeps_password_creation_between_verified_email_and_otp():
    template = json.loads((ROOT / "deploy/keycloak/realm-test.example.json").read_text(encoding="utf-8"))
    actions = {entry["alias"]: entry for entry in template["requiredActions"]}
    assert "UPDATE_PASSWORD" in actions, "Native deferred password action missing"
    assert actions["UPDATE_PASSWORD"] == {
        "alias": "UPDATE_PASSWORD",
        "providerId": "UPDATE_PASSWORD",
        "enabled": True,
        "defaultAction": False,
        "name": "Définir le mot de passe",
        "priority": 15,
    }
    assert template["verifyEmail"] and template["resetPasswordAllowed"]
    assert actions["VERIFY_EMAIL"]["defaultAction"] and actions["CONFIGURE_TOTP"]["defaultAction"]


def test_absent_action_registers_native_then_sets_only_exact_action():
    m = module()
    before = snapshot()
    provider = Native(before)
    review = m.plan(before)
    result = m.apply_reviewed(
        review, review["fingerprint"], provider.read, provider.write, provider.saved.append
    )
    assert result["changed"] and result["update_password_enabled"] and result["other_settings_preserved"]
    assert provider.saved == [before]
    assert [entry[1] for entry in provider.writes] == ["POST", "PUT"]
    assert provider.state["realm"] == before["realm"]
    assert provider.state["flows"] == before["flows"]
    assert provider.state["actions"][:-1] == before["actions"]
    assert provider.state["actions"][-1] == m.DESIRED


def test_disabled_action_changes_without_registration_and_preserves_config():
    m = module()
    before = snapshot()
    before["actions"].append({**m.DESIRED, "enabled": False, "config": {"max_auth_age": "300"}})
    provider = Native(before)
    review = m.plan(before)
    m.apply_reviewed(review, review["fingerprint"], provider.read, provider.write, provider.saved.append)
    assert [entry[1] for entry in provider.writes] == ["PUT"]
    assert provider.state["actions"][-1] == {**m.DESIRED, "config": {"max_auth_age": "300"}}


def test_exact_action_is_idempotent_without_backup_or_mutation():
    m = module()
    before = snapshot()
    before["actions"].append(deepcopy(m.DESIRED))
    provider = Native(before)
    review = m.plan(before)
    result = m.apply_reviewed(
        review, review["fingerprint"], provider.read, provider.write, provider.saved.append
    )
    assert not result["changed"] and not provider.writes and not provider.saved


@pytest.mark.parametrize(
    "area", ["realm", "flows", "actions", "default_client_scopes", "roles", "default_role_composites"]
)
def test_stale_review_rejects_concurrent_changes_without_mutation(area):
    m = module()
    provider = Native(snapshot())
    review = m.plan(provider.read())
    if area == "realm":
        provider.state[area]["resetPasswordAllowed"] = False
    elif area == "flows":
        provider.state[area]["reset credentials"][0]["priority"] = 4
    elif area == "actions":
        provider.state[area][0]["priority"] = 11
    else:
        provider.state[area].append({"name": "concurrent-change"})
    with pytest.raises(ValueError):
        m.apply_reviewed(review, review["fingerprint"], provider.read, provider.write, provider.saved.append)
    assert not provider.writes and not provider.saved


def test_failed_second_write_removes_only_our_new_registration():
    m = module()
    before = snapshot()
    provider = Native(before)
    provider.fail_put = True
    review = m.plan(before)
    with pytest.raises(RuntimeError):
        m.apply_reviewed(review, review["fingerprint"], provider.read, provider.write, provider.saved.append)
    assert provider.state == before
    assert [entry[1] for entry in provider.writes] == ["POST", "PUT", "DELETE"]


def test_concurrent_other_flow_is_never_rolled_back():
    m = module()
    before = snapshot()
    provider = Native(before)
    provider.concurrent = True
    review = m.plan(before)
    with pytest.raises(ValueError):
        m.apply_reviewed(review, review["fingerprint"], provider.read, provider.write, provider.saved.append)
    assert provider.state["flows"]["reset credentials"][0]["requirement"] == "DISABLED"
    assert provider.state["actions"] == before["actions"]


@pytest.mark.parametrize(
    "change", ["foreign_realm", "email_disabled", "password_execution_disabled", "legacy_override"]
)
def test_rejects_unreviewed_or_weakened_context(change):
    m = module()
    before = snapshot()
    if change == "foreign_realm":
        before["realm"]["realm"] = "registrar"
    elif change == "email_disabled":
        before["realm"]["verifyEmail"] = False
    elif change == "password_execution_disabled":
        before["flows"]["registration"][0]["requirement"] = "DISABLED"
    else:
        before["flow_configs"]["registration"] = {"always_set_password_on_register_form": "true"}
    with pytest.raises(ValueError):
        m.plan(before)


def test_missing_native_basic_is_rejected_before_any_write():
    m = module()
    before = snapshot()
    before["default_client_scopes"] = [{"name": "email"}]
    with pytest.raises(ValueError, match="basic"):
        m.plan(before)


def test_admin_redirect_handler_never_forwards_authorization():
    m = module()
    with pytest.raises(ValueError, match="redirect_forbidden"):
        m.NoRedirect().redirect_request(None, None, 302, "synthetic", {}, "https://foreign.invalid")


def test_public_plan_never_includes_existing_private_action_config():
    m = module()
    before = snapshot()
    before["actions"].append(
        {**m.DESIRED, "enabled": False, "config": {"opaque": "synthetic-sensitive-value"}}
    )
    assert "synthetic-sensitive-value" not in json.dumps(m.plan(before))


def test_lost_response_after_committed_put_does_not_delete_or_undo_unknown_write():
    m = module()
    before = snapshot()
    provider = Native(before)
    review = m.plan(before)

    def lost_response(path, method, data=None):
        provider.write(path, method, data)
        if method == "PUT":
            raise m.WriteOutcomeUnknown("synthetic response lost")

    with pytest.raises(m.WriteOutcomeUnknown):
        m.apply_reviewed(review, review["fingerprint"], provider.read, lost_response, provider.saved.append)
    assert provider.state["actions"][-1] == m.DESIRED
    assert [entry[1] for entry in provider.writes] == ["POST", "PUT"]


def test_concurrent_target_edit_after_put_is_never_rolled_back():
    m = module()
    before = snapshot()
    provider = Native(before)
    review = m.plan(before)

    def edit_action(path, method, data=None):
        provider.write(path, method, data)
        if method == "PUT":
            provider.state["actions"][-1]["name"] = "concurrent action name"

    with pytest.raises(ValueError):
        m.apply_reviewed(review, review["fingerprint"], provider.read, edit_action, provider.saved.append)
    assert provider.state["actions"][-1]["name"] == "concurrent action name"
    assert [entry[1] for entry in provider.writes] == ["POST", "PUT"]


def test_backup_failure_never_mutates_identity():
    m = module()
    provider = Native(snapshot())
    review = m.plan(provider.read())

    def failed_backup(value):
        raise OSError("synthetic backup failure")

    with pytest.raises(OSError):
        m.apply_reviewed(review, review["fingerprint"], provider.read, provider.write, failed_backup)
    assert not provider.writes
