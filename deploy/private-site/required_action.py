"""Repair only MayorTech's native deferred-password action; no email is sent."""

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from urllib.parse import quote, urlencode
import urllib.request
from uuid import UUID, uuid4

BASE = Path("/opt/apps/mayortech-private")
REALM = "mayortech"
PREFIX = "/admin/realms/mayortech/authentication"
ACTION_PATH = PREFIX + "/required-actions/UPDATE_PASSWORD"
DESIRED = {
    "alias": "UPDATE_PASSWORD",
    "providerId": "UPDATE_PASSWORD",
    "name": "Définir le mot de passe",
    "enabled": True,
    "defaultAction": False,
    "priority": 15,
    "config": {},
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("native_admin_redirect_forbidden")


class WriteOutcomeUnknown(RuntimeError):
    """A mutating HTTP request failed; inspect a fresh plan before resuming."""


def target(snapshot):
    entries = [entry for entry in snapshot["actions"] if entry.get("alias") == "UPDATE_PASSWORD"]
    if len(entries) > 1:
        raise ValueError("duplicate_native_action")
    return entries[0] if entries else None


def desired(snapshot):
    current = target(snapshot)
    if current is not None and current.get("providerId") != "UPDATE_PASSWORD":
        raise ValueError("unexpected_native_provider")
    return {**DESIRED, "config": deepcopy((current or {}).get("config") or {})}


def without_target(snapshot):
    value = deepcopy(snapshot)
    value["actions"] = [entry for entry in value["actions"] if entry.get("alias") != "UPDATE_PASSWORD"]
    return value


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def plan(snapshot):
    realm = snapshot["realm"]
    if (
        realm.get("realm") != REALM
        or realm.get("verifyEmail") is not True
        or realm.get("resetPasswordAllowed") is not True
        or realm.get("browserFlow") != "travaux-password-and-otp"
    ):
        raise ValueError("unexpected_realm_contract")
    client = snapshot["client"]
    if (
        client.get("clientId") != "mayortech-space"
        or client.get("protocol") != "openid-connect"
        or client.get("publicClient") is not False
        or client.get("redirectUris") != ["https://espace.kerforge.com/api/v1/auth/callback"]
    ):
        raise ValueError("unexpected_identity_client")
    if not any(scope.get("name") == "basic" for scope in snapshot["default_client_scopes"]):
        raise ValueError("native_basic_scope_missing")
    actions = snapshot["actions"]
    aliases = [entry["alias"] for entry in actions]
    if len(aliases) != len(set(aliases)):
        raise ValueError("duplicate_action_alias")
    for alias in ("VERIFY_EMAIL", "CONFIGURE_TOTP"):
        matches = [entry for entry in actions if entry.get("alias") == alias]
        if len(matches) != 1 or any(matches[0].get(key) is not True for key in ("enabled", "defaultAction")):
            raise ValueError("mandatory_email_or_mfa_action_missing")
    executions = snapshot["flows"].get(realm.get("registrationFlow", "registration"), [])
    passwords = [entry for entry in executions if entry.get("providerId") == "registration-password-action"]
    if len(passwords) != 1 or passwords[0].get("requirement") != "REQUIRED":
        raise ValueError("native_registration_password_not_required")
    if any(
        config.get("always_set_password_on_register_form") == "true"
        for config in snapshot["flow_configs"].values()
    ):
        raise ValueError("deprecated_early_password_override")
    browser = snapshot["flows"].get(realm["browserFlow"], [])
    if any(
        not any(
            entry.get("providerId") == provider and entry.get("requirement") == "REQUIRED"
            for entry in browser
        )
        for provider in ("auth-username-password-form", "auth-otp-form")
    ):
        raise ValueError("mandatory_native_password_and_otp_missing")
    action = desired(snapshot)
    return {
        "realm": REALM,
        "action": "UPDATE_PASSWORD",
        "fingerprint": fingerprint(snapshot),
        "needs_registration": target(snapshot) is None,
        "needs_change": target(snapshot) != action,
        "desired": {key: value for key, value in DESIRED.items() if key != "config"},
        "existing_action_config_preserved": True,
        "secret_values_included": False,
        "test_message_sent": False,
    }


def apply_reviewed(review, expected, read, write, backup):
    before = read()
    fresh = plan(before)
    new_action = desired(before)
    if expected != fresh["fingerprint"] or review != fresh:
        raise ValueError("reviewed_identity_context_changed")
    receipt = {
        "changed": False,
        "update_password_enabled": True,
        "other_settings_preserved": True,
        "secret_values_included": False,
        "test_message_sent": False,
    }
    if not fresh["needs_change"]:
        return receipt
    backup(before)
    # CAS again after writing the backup and before the first mutation.
    if fingerprint(read()) != fresh["fingerprint"]:
        raise ValueError("identity_context_changed_before_write")
    last_written = None
    try:
        if fresh["needs_registration"]:
            # Official native endpoint first registers enabled/default=false;
            # the subsequent action-only PUT sets the reviewed priority.
            write(
                PREFIX + "/register-required-action",
                "POST",
                {"providerId": "UPDATE_PASSWORD", "name": DESIRED["name"]},
            )
            registered = read()
            entry = target(registered)
            if (
                entry is None
                or any(
                    entry.get(key) != value
                    for key, value in DESIRED.items()
                    if key not in {"priority", "config"}
                )
                or not isinstance(entry.get("priority"), int)
                or entry.get("config") not in ({}, None)
            ):
                raise ValueError("unexpected_native_registration")
            last_written = deepcopy(entry)
            if without_target(registered) != without_target(before):
                raise ValueError("identity_context_changed_during_registration")
            if fingerprint(read()) != fingerprint(registered):
                raise ValueError("identity_context_changed_before_priority_write")
        write(ACTION_PATH, "PUT", new_action)
        last_written = deepcopy(new_action)
        after = read()
        if target(after) != new_action or without_target(after) != without_target(before):
            raise ValueError("unexpected_identity_delta")
        return {**receipt, "changed": True}
    except Exception:
        # Compensate only a confirmed write still equal to OUR exact action.
        # Preserve concurrent updates to every other flow/realm/action, and
        # never overwrite a concurrent administrator's edit of this action.
        current = read()
        if last_written is not None and target(current) == last_written:
            original = target(before)
            if original is None:
                write(ACTION_PATH, "DELETE")
            else:
                write(ACTION_PATH, "PUT", original)
        raise


def server_main(payload):
    import fcntl

    os.umask(0o077)
    os.environ.pop("SSLKEYLOGFILE", None)
    os.environ.pop("QUICLOGDIR", None)
    expected_uid = int(os.environ.get("SUDO_UID", os.getuid()))
    if (
        BASE.resolve() != BASE
        or BASE.is_symlink()
        or stat.S_IMODE(BASE.stat().st_mode) != 0o700
        or BASE.stat().st_uid != expected_uid
        or (BASE / ".mayortech-private-owner").read_text() != "mayortech-private-v1\n"
    ):
        raise ValueError("unowned_application")
    private = BASE / "private"
    if (
        private.resolve() != private
        or private.is_symlink()
        or stat.S_IMODE(private.stat().st_mode) != 0o700
        or private.stat().st_uid != expected_uid
    ):
        raise ValueError("private_directory_permissions")
    material = private / "bootstrap-material.json"
    with os.fdopen(os.open(material, os.O_RDONLY | os.O_NOFOLLOW), "r") as stream:
        metadata = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
            or metadata.st_uid != expected_uid
        ):
            raise ValueError("private_material_permissions")
        secret = json.load(stream)

    parent = BASE / "backups"
    if parent.exists() and (
        parent.resolve() != parent
        or parent.is_symlink()
        or stat.S_IMODE(parent.stat().st_mode) != 0o700
        or parent.stat().st_uid != os.getuid()
    ):
        raise ValueError("private_backup_directory_permissions")
    lock = os.open(BASE / ".operator.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    info = os.fstat(lock)
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or info.st_uid != os.getuid()
    ):
        os.close(lock)
        raise ValueError("operator_lock_permissions")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return server_locked(payload, secret)
    finally:
        os.close(lock)


def server_locked(payload, secret):
    def run(args):
        process = subprocess.run(args, capture_output=True, timeout=20)
        if process.returncode:
            raise ValueError("owned_service_lookup_failed")
        return process.stdout

    ids = (
        run(
            [
                "docker",
                "ps",
                "-q",
                "--filter",
                "label=com.docker.compose.project=mayortech-private",
                "--filter",
                "label=com.docker.compose.service=keycloak",
            ]
        )
        .decode()
        .split()
    )
    if len(ids) != 1:
        raise ValueError("owned_identity_not_unique")
    item = json.loads(run(["docker", "inspect", ids[0]]))[0]
    if (
        item["Config"]["Labels"].get("io.kerforge.application") != "mayortech-private"
        or item["State"]["Health"]["Status"] != "healthy"
    ):
        raise ValueError("owned_identity_not_healthy")
    address = item["NetworkSettings"]["Networks"]["mayortech-private-identity-front"]["IPAddress"]
    if not ipaddress.ip_address(address).is_private:
        raise ValueError("private_identity_network_required")
    origin = "http://" + address + ":8080"

    def request(path, method="GET", data=None, token=None, form=False):
        headers = {"Host": "identite.kerforge.com", "Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            data = urlencode(data).encode() if form else json.dumps(data).encode()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(
            urllib.request.Request(origin + path, data=data, headers=headers, method=method), timeout=20
        ) as response:
            body = response.read(2_000_000)
            return json.loads(body) if body else None

    token = request(
        "/realms/master/protocol/openid-connect/token",
        "POST",
        {
            "grant_type": "client_credentials",
            "client_id": secret["admin_client_id"],
            "client_secret": secret["admin_client_secret"],
        },
        form=True,
    )["access_token"]

    def call(path, method="GET", data=None):
        try:
            return request(path, method, data, token)
        except Exception:
            if method != "GET":
                raise WriteOutcomeUnknown("native_write_requires_fresh_inspection") from None
            raise

    def read():
        realm = call("/admin/realms/mayortech")
        actions = sorted(call(PREFIX + "/required-actions"), key=lambda entry: entry["alias"])
        clients = call("/admin/realms/mayortech/clients?clientId=mayortech-space")
        if len(clients) != 1 or clients[0].get("clientId") != "mayortech-space":
            raise ValueError("identity_client_not_unique")
        client = clients[0]
        client_id = client["id"]
        if str(UUID(client_id)) != client_id:
            raise ValueError("identity_client_uid")
        default_scopes = sorted(
            call("/admin/realms/mayortech/clients/" + client_id + "/default-client-scopes"),
            key=lambda entry: entry["id"],
        )
        roles = sorted(call("/admin/realms/mayortech/roles"), key=lambda entry: entry["id"])
        role_id = realm["defaultRole"]["id"]
        if str(UUID(role_id)) != role_id:
            raise ValueError("default_role_uid")
        composites = sorted(
            call("/admin/realms/mayortech/roles-by-id/" + role_id + "/composites"),
            key=lambda entry: entry["id"],
        )
        flows = {}
        configs = {}
        for flow in sorted(call(PREFIX + "/flows"), key=lambda entry: entry["alias"]):
            alias = flow["alias"]
            if not isinstance(alias, str) or not alias or len(alias) > 200:
                raise ValueError("unexpected_native_flow")
            entries = call(PREFIX + "/flows/" + quote(alias, safe="") + "/executions")
            flows[alias] = entries
            for entry in entries:
                identifier = entry.get("authenticationConfig")
                if identifier and identifier not in configs:
                    if str(UUID(identifier)) != identifier:
                        raise ValueError("unexpected_native_config_uid")
                    configs[identifier] = call(PREFIX + "/config/" + identifier).get("config", {})
        return {
            "realm": realm,
            "actions": actions,
            "flows": flows,
            "flow_configs": configs,
            "client": client,
            "default_client_scopes": default_scopes,
            "roles": roles,
            "default_role_composites": composites,
        }

    current = read()
    review = plan(current)
    if payload.get("action") == "plan":
        return review
    if payload.get("action") != "apply":
        raise ValueError("invalid_action")
    backup_path = None

    def backup(value):
        nonlocal backup_path
        parent = BASE / "backups"
        if parent.resolve() != parent or parent.is_symlink():
            raise ValueError("indirect_backup_directory")
        parent.mkdir(mode=0o700, exist_ok=True)
        if stat.S_IMODE(parent.stat().st_mode) != 0o700 or parent.stat().st_uid != os.getuid():
            raise ValueError("private_backup_directory_permissions")
        backup_path = parent / (
            "required-action-before-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid4().hex[:8]
            + ".json"
        )
        with os.fdopen(
            os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "w"
        ) as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())

    result = apply_reviewed(review, payload.get("fingerprint"), read, call, backup)
    return {
        **result,
        "reviewed_fingerprint": review["fingerprint"],
        "backup": str(backup_path) if backup_path else None,
    }


def remote(payload):
    root = Path(__file__).resolve().parents[2]
    folder = root / "deploy/hetzner"
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("required_action_transport", folder / "deploy.py")
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    source = base64.b64encode(Path(__file__).read_bytes()).decode()
    body = base64.b64encode(json.dumps(payload).encode()).decode()
    script = f"""import base64,json,sys,types
m=types.ModuleType('private_required_action');exec(base64.b64decode({source!r}),m.__dict__)
try: print(json.dumps(m.server_main(json.loads(base64.b64decode({body!r})))))
except Exception as error:
 print(json.dumps({{'error':'native_required_action_failed','exception_type':type(error).__name__,'mutation_state':'unknown_inspect_fresh_plan' if isinstance(error,m.WriteOutcomeUnknown) else 'not_qualified','secret_values_included':False,'test_message_sent':False}}));sys.exit(1)
"""
    process = subprocess.run(
        transport.ssh_args(transport.owner_config(transport.OWNER)) + ["sudo -n python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=150,
    )
    try:
        value = json.loads(process.stdout)
        if not isinstance(value, dict):
            raise ValueError()
    except Exception:
        return {"error": "required_action_transport_failed", "secret_values_included": False}, 1
    return value, process.returncode or (1 if "error" in value else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("--reviewed-fingerprint")
    args = parser.parse_args()
    if args.action == "apply" and not args.reviewed_fingerprint:
        parser.error("A reviewed fingerprint is required")
    value, code = remote({"action": args.action, "fingerprint": args.reviewed_fingerprint})
    print(json.dumps(value))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
