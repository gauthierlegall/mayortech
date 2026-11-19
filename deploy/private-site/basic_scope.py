"""Restore Keycloak's native basic scope on exactly the MayorTech client."""

import argparse
import base64
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
from urllib.parse import urlencode
import urllib.request
from uuid import UUID

BASE = Path("/opt/apps/mayortech-private")
CLIENT_ID = "mayortech-space"
REALM = "mayortech"
REDIRECT = "https://espace.kerforge.com/api/v1/auth/callback"


def uid(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("invalid_native_uid")
    return value


def scope_ids(scopes):
    values = [uid(scope["id"]) for scope in scopes]
    if len(values) != len(set(values)):
        raise ValueError("duplicate_native_scope")
    return set(values)


def scope_backup_entries(scopes):
    return [{key: scope[key] for key in ("id", "name", "protocol") if key in scope} for scope in scopes]


def plan(client, basic, before, mappers):
    if (
        client.get("clientId") != CLIENT_ID
        or client.get("protocol") != "openid-connect"
        or client.get("publicClient") is not False
        or client.get("redirectUris") != [REDIRECT]
    ):
        raise ValueError("unexpected_client_contract")
    if basic.get("name") != "basic" or basic.get("protocol") != "openid-connect":
        raise ValueError("unexpected_basic_scope")
    native = any(
        mapper.get("protocolMapper") == "oidc-usersessionmodel-note-mapper"
        and all(
            mapper.get("config", {}).get(k) == v
            for k, v in {
                "user.session.note": "AUTH_TIME",
                "claim.name": "auth_time",
                "id.token.claim": "true",
                "jsonType.label": "long",
            }.items()
        )
        for mapper in mappers
    )
    if not native:
        raise ValueError("native_auth_time_mapper_missing")
    client_uid, basic_uid = uid(client["id"]), uid(basic["id"])
    before_ids = sorted(scope_ids(before))
    contract = {
        "realm": REALM,
        "client_id": CLIENT_ID,
        "client_uid": client_uid,
        "basic_uid": basic_uid,
        "before_ids": before_ids,
    }
    fingerprint = hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        **contract,
        "fingerprint": fingerprint,
        "needs_basic": basic_uid not in before_ids,
        "native_auth_time_mapper": True,
        "before_scope_fields": {
            key: all(key in scope for scope in before) for key in ("id", "name", "protocol")
        },
        "secret_values_included": False,
    }


def apply_reviewed(review, expected, before, call, backup):
    if expected != review["fingerprint"] or sorted(scope_ids(before)) != review["before_ids"]:
        raise ValueError("reviewed_scope_set_changed")
    endpoint = "/admin/realms/" + REALM + "/clients/" + uid(review["client_uid"]) + "/default-client-scopes"
    basic_uid = uid(review["basic_uid"])
    if not review["needs_basic"]:
        return {
            "changed": False,
            "basic_assigned": True,
            "client_id": CLIENT_ID,
            "secret_values_included": False,
        }
    backup(before)
    changed = False
    try:
        call(endpoint + "/" + basic_uid, "PUT")
        changed = True
        after = call(endpoint)
        if scope_ids(after) != scope_ids(before) | {basic_uid}:
            raise ValueError("unexpected_scope_delta")
        return {
            "changed": True,
            "basic_assigned": True,
            "existing_scopes_preserved": True,
            "client_id": CLIENT_ID,
            "secret_values_included": False,
        }
    except Exception:
        if changed:
            # Compensate only our newly added native link; never replace a
            # client, realm, mapper or another administrator's scope list.
            call(endpoint + "/" + basic_uid, "DELETE")
        raise


def server_main(payload):
    os.umask(0o077)
    if (
        BASE.resolve() != BASE
        or BASE.is_symlink()
        or stat.S_IMODE(BASE.stat().st_mode) != 0o700
        or (BASE / ".mayortech-private-owner").read_text() != "mayortech-private-v1\n"
    ):
        raise ValueError("unowned_application")
    expected_uid = int(os.environ.get("SUDO_UID", os.getuid()))
    private = BASE / "private"
    if (
        private.resolve() != private
        or private.is_symlink()
        or stat.S_IMODE(private.stat().st_mode) != 0o700
        or private.stat().st_uid != expected_uid
    ):
        raise ValueError("private_directory_permissions")
    material = private / "bootstrap-material.json"
    if material.is_symlink():
        raise ValueError("private_material_permissions")
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
        raise ValueError("owned_service_not_unique")
    item = json.loads(run(["docker", "inspect", ids[0]]))[0]
    if (
        item["Config"]["Labels"].get("io.kerforge.application") != "mayortech-private"
        or item["State"]["Health"]["Status"] != "healthy"
    ):
        raise ValueError("owned_service_not_healthy")
    address = item["NetworkSettings"]["Networks"]["mayortech-private-identity-front"]["IPAddress"]
    if not ipaddress.ip_address(address).is_private:
        raise ValueError("private_network_required")
    origin = "http://" + address + ":8080"

    def request(path, method="GET", data=None, token=None):
        headers = {"Host": "identite.kerforge.com", "Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urlencode(data).encode()
        with urllib.request.urlopen(
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
    )["access_token"]

    def call(path, method="GET"):
        return request(path, method, token=token)

    clients = call("/admin/realms/mayortech/clients?clientId=mayortech-space")
    if len(clients) != 1:
        raise ValueError("exact_client_not_unique")
    client = clients[0]
    client_uid = uid(client["id"])
    basics = [
        scope for scope in call("/admin/realms/mayortech/client-scopes") if scope.get("name") == "basic"
    ]
    if len(basics) != 1:
        raise ValueError("exact_basic_scope_not_unique")
    basic = basics[0]
    basic_uid = uid(basic["id"])
    mappers = call("/admin/realms/mayortech/client-scopes/" + basic_uid + "/protocol-mappers/models")
    endpoint = "/admin/realms/mayortech/clients/" + client_uid + "/default-client-scopes"
    before = call(endpoint)
    review = plan(client, basic, before, mappers)
    if payload.get("action") == "plan":
        return review
    if payload.get("action") != "apply":
        raise ValueError("invalid_action")
    backup_path = None

    def backup(scopes):
        nonlocal backup_path
        parent = BASE / "backups"
        if parent.resolve() != parent or parent.is_symlink():
            raise ValueError("indirect_backup_directory")
        parent.mkdir(mode=0o700, exist_ok=True)
        if stat.S_IMODE(parent.stat().st_mode) != 0o700:
            raise ValueError("private_backup_directory_permissions")
        backup_path = parent / (
            "basic-scope-before-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json"
        )
        content = {
            "realm": REALM,
            "client_id": CLIENT_ID,
            "client_uid": client_uid,
            "default_scopes": scope_backup_entries(scopes),
        }
        with os.fdopen(os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            json.dump(content, stream)

    result = apply_reviewed(review, payload.get("fingerprint"), before, call, backup)
    return {
        **result,
        "reviewed_fingerprint": review["fingerprint"],
        "backup": str(backup_path) if backup_path else None,
    }


def remote(payload):
    root = Path(__file__).resolve().parents[2]
    folder = root / "deploy/hetzner"
    sys.path.insert(0, str(folder))
    spec = importlib.util.spec_from_file_location("scope_existing_transport", folder / "deploy.py")
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    source = base64.b64encode(Path(__file__).read_bytes()).decode()
    body = base64.b64encode(json.dumps(payload).encode()).decode()
    script = f"""import base64,json,sys,types
m=types.ModuleType('private_basic_scope');exec(base64.b64decode({source!r}),m.__dict__)
try: print(json.dumps(m.server_main(json.loads(base64.b64decode({body!r})))))
except Exception as error:
 print(json.dumps({{'error':'native_basic_scope_operation_failed','exception_type':type(error).__name__,'secret_values_included':False}}));sys.exit(1)
"""
    process = subprocess.run(
        transport.ssh_args(transport.owner_config(transport.OWNER)) + ["sudo -n python3 -"],
        input=script.encode(),
        capture_output=True,
        timeout=90,
    )
    try:
        value = json.loads(process.stdout)
        if not isinstance(value, dict):
            raise ValueError()
    except Exception:
        return {"error": "scope_transport_failed", "secret_values_included": False}, 1
    return value, process.returncode or (1 if "error" in value else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("--reviewed-fingerprint")
    args = parser.parse_args()
    if args.action == "apply" and not args.reviewed_fingerprint:
        parser.error("A reviewed fingerprint is required")
    result, code = remote({"action": args.action, "fingerprint": args.reviewed_fingerprint})
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
