"""Reviewed application-only maintenance; never updates identity, secrets or DB data.

plan prints hashes for a later compare-and-swap apply. No command runs at import.
The target must already be the current reviewed public release and exist locally.
"""

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import subprocess
import sys
import time

PUBLIC_BASE = Path("/opt/apps/travaux-mairie")
PUBLIC_RUNTIME = {
    "mode": "public_demo", "db_path": "/data/public-demo.sqlite3",
    "tenant_id": "public-demo-travaux",
}
PROTECTED = {
    "src/travaux/" + name for name in
    ("repository.py", "workspace.py", "auth.py", "jobs.py", "governance.py")
} | {"Dockerfile", "pyproject.toml", "uv.lock"}
TAG = re.compile(r"travaux-mairie:0\.8\.1-(20\d{6}T\d{6}Z-[a-f0-9]{6,12})")


class UpdateError(RuntimeError):
    """Only fixed operator error codes, never command output or credentials."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory_digest(files):
    return digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def image_release(value):
    match = TAG.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise UpdateError("invalid_application_image")
    return match.group(1)


def safe_read(path):
    path = Path(path)
    if path.resolve() != path.absolute() or path.is_symlink() or not path.is_file():
        raise UpdateError("indirect_or_missing_owned_file")
    if path.stat().st_nlink != 1:
        raise UpdateError("hardlinked_owned_file")
    return path.read_bytes()


def json_read(path):
    try:
        return json.loads(safe_read(path))
    except (ValueError, TypeError):
        raise UpdateError("invalid_owned_state") from None


def verify_manifests(old, new):
    for value in (old, new):
        if (not isinstance(value, dict) or value.get("app") != "travaux-mairie"
                or value.get("version") != "0.8.1" or value.get("runtime") != PUBLIC_RUNTIME):
            raise UpdateError("public_manifest_contract")
        image_release("travaux-mairie:0.8.1-" + value.get("release", ""))
        files = value.get("files")
        if (not isinstance(files, dict) or not PROTECTED.issubset(files)
                or any(not isinstance(x, str) or not re.fullmatch(r"[a-f0-9]{64}", x) for x in files.values())):
            raise UpdateError("invalid_public_inventory")
        gate = value.get("gate", {})
        if (gate.get("checks") != {"python": True, "frontend": True, "native": True}
                or any(type(x) is not bool for x in gate.get("checks", {}).values())
                or gate.get("source_digest") != inventory_digest(files)):
            raise UpdateError("public_verification_gate")
    if any(old["files"][name] != new["files"][name] for name in PROTECTED):
        raise UpdateError("protected_schema_or_dependency_changed")
    return inventory_digest(new["files"])


def updated_compose(current, template, old_image, new_image):
    image_release(old_image)
    image_release(new_image)
    old, new = old_image.encode(), new_image.encode()
    tags = re.findall(rb"travaux-mairie:0\.8\.1-20\d{6}T\d{6}Z-[a-f0-9]{6,12}", template)
    if len(tags) != 1 or current.count(old) != 1:
        raise UpdateError("compose_application_anchor_not_unique")
    if current.replace(old, b"APPLICATION_IMAGE") != template.replace(tags[0], b"APPLICATION_IMAGE"):
        raise UpdateError("compose_contract_changed")
    return current.replace(old, new)


def atomic_cas(path, expected, content, uid):
    """Retained operator lock serializes cooperating writers; hash fences drift."""
    path = Path(path)
    if digest(safe_read(path)) != expected:
        raise UpdateError("concurrent_file_change")
    temporary = path.with_name(path.name + ".pending-" + secrets.token_hex(8))
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if uid is not None and os.name != "nt":
            os.chown(temporary, uid, uid)
        if digest(safe_read(path)) != expected:
            raise UpdateError("concurrent_file_change")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def immutable_state(runtime):
    base = runtime.C.BASE
    names = ("keycloak-healthcheck.sh", "worker-healthcheck.py", "theme.jar", "identity-nginx.rendered.conf")
    paths = [base / name for name in names] + list((base / "private").iterdir()) + [runtime.ROUTE]
    files = {str(path): (digest(safe_read(path)), stat.S_IMODE(path.stat().st_mode), path.stat().st_uid) for path in paths}
    services = {}
    for name in ("postgres", "keycloak", "identity_guard"):
        ident, item = runtime.service(name)
        services[name] = (ident, item["Image"])
    caddy_id, _ = runtime.caddy()
    logging = json.loads(runtime.run([
        "docker", "exec", caddy_id, "wget", "-q", "-O", "-", "http://127.0.0.1:2019/config/logging",
    ], timeout=15).stdout)
    if not runtime.logging_is_safe(logging):
        raise UpdateError("caddy_debug_logging_refused")
    live = runtime.run([
        "docker", "exec", caddy_id, "wget", "-q", "-O", "-", "http://127.0.0.1:2019/config/",
    ], timeout=15).stdout
    return {"files": files, "services": services, "peers": runtime.peers_digest(), "caddy_id": caddy_id, "caddy_runtime": digest(live)}


def validate_secret_metadata(info, uid):
    if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_uid != uid or info.st_nlink != 1):
        raise UpdateError("private_file_permissions")


def validate_private_metadata(runtime, uid):
    private = runtime.C.BASE / "private"
    if (private.resolve() != private.absolute() or private.is_symlink() or not private.is_dir()
            or stat.S_IMODE(private.stat().st_mode) != 0o700 or private.stat().st_uid != uid):
        raise UpdateError("private_directory_permissions")
    owners = {"connector-vault.keys": 10001, "mayortech-realm.json": 1000}
    for path in private.iterdir():
        if path.resolve() != path.absolute() or path.is_symlink():
            raise UpdateError("indirect_or_missing_owned_file")
        validate_secret_metadata(path.stat(), owners.get(path.name, uid))


def validate_environment(runtime, material=None):
    raw = safe_read(runtime.C.BASE / "private/app.env").decode()
    lines = [line for line in raw.splitlines() if line]
    if any("=" not in line for line in lines):
        raise UpdateError("private_environment_contract")
    env = dict(line.split("=", 1) for line in lines)
    if len(env) != len(lines):
        raise UpdateError("duplicate_private_environment")
    _, address = runtime.caddy()
    expected = {
        "TRAVAUX_MODE": "staging", "TRAVAUX_AUTH_MODE": "oidc",
        "TRAVAUX_TEST_ORGANIZATION_SELF_JOIN": "true", "TRAVAUX_PASSWORD_HASH": "",
        "TRAVAUX_DB": "/data/mayortech-test.sqlite3", "TRAVAUX_TENANT": "mayortech-test",
        "TRAVAUX_PUBLIC_ORIGIN": "https://espace.kerforge.com", "TRAVAUX_ALLOWED_HOSTS": "espace.kerforge.com",
        "TRAVAUX_TRUSTED_PROXY_IPS": address,
        "TRAVAUX_CONNECTOR_KEY_FILE": "/run/secrets/connector-vault.keys",
        "TRAVAUX_CONNECTOR_SECRET_KEYS": "", "TRAVAUX_CONNECTOR_SECRET_KEY": "",
        "TRAVAUX_LLM": "demo", "TRAVAUX_LLM_EGRESS_APPROVED": "false",
        "TRAVAUX_OIDC_ISSUER": "https://identite.kerforge.com/realms/mayortech",
        "TRAVAUX_OIDC_CLIENT_ID": "mayortech-space", "TRAVAUX_OIDC_REQUIRED_AMR": "pwd,otp",
        "TRAVAUX_OIDC_REQUIRED_ACR": "", "TRAVAUX_OIDC_EGRESS_APPROVED": "true",
        "TRAVAUX_OIDC_ALLOWED_HOSTS": "identite.kerforge.com", "TRAVAUX_OIDC_PRIVATE_HOSTS": "",
        "TRAVAUX_OIDC_SIGNUP_URL": "https://identite.kerforge.com/realms/mayortech/protocol/openid-connect/registrations",
        "TRAVAUX_OIDC_RESET_URL": "https://identite.kerforge.com/realms/mayortech/protocol/openid-connect/forgot-credentials",
        "SSLKEYLOGFILE": "", "QUICLOGDIR": "",
    }
    if any(env.get(name, "") != value for name, value in expected.items()):
        raise UpdateError("private_environment_contract")
    material = material if material is not None else json_read(runtime.C.BASE / "private/bootstrap-material.json")
    client_secret = material.get("client_secret")
    if (not isinstance(client_secret, str) or len(client_secret) < 16
            or env.get("TRAVAUX_OIDC_CLIENT_SECRET") != client_secret):
        raise UpdateError("private_environment_contract")
    # This maintenance path is exclusively for the existing fictional tenant.
    # Provider activation and any change to the trust boundary need another review.
    external = ("TRAVAUX_MISTRAL_", "TRAVAUX_GOOGLE_", "TRAVAUX_MICROSOFT_", "TRAVAUX_EWS_",
                "TRAVAUX_EXCHANGE_", "TRAVAUX_CALDAV_", "TRAVAUX_TELEGRAM_", "TRAVAUX_APPFLOWY_")
    if any(value and (name.startswith(external)
                     or name.startswith(("TRAVAUX_CONNECTOR_", "TRAVAUX_OIDC_"))
                     and name not in {*expected, "TRAVAUX_OIDC_CLIENT_SECRET"})
           for name, value in env.items()):
        raise UpdateError("private_environment_contract")


def verified_image(runtime, image, manifest):
    item = runtime.inspect("image", image)
    if item is None:
        raise UpdateError("application_image_not_local")
    labels = item.get("Config", {}).get("Labels") or {}
    if (labels.get("io.kerforge.application") != "travaux-mairie"
            or labels.get("io.kerforge.source-digest") != inventory_digest(manifest["files"])):
        raise UpdateError("application_image_provenance")
    return item["Id"]


def inspect_state(payload, runtime):
    uid = int(os.environ.get("SUDO_UID", os.getuid() if hasattr(os, "getuid") else 0))
    runtime.verify_base(expected_uid=uid)
    validate_private_metadata(runtime, uid)
    image = payload["image"]
    release = image_release(image)
    review = payload.get("review_id")
    if not isinstance(review, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", review):
        raise UpdateError("review_identifier_required")
    base = runtime.C.BASE
    status_bytes, compose = safe_read(base / "status.json"), safe_read(base / "compose.yaml")
    state = json.loads(status_bytes)
    material = json_read(base / "private/bootstrap-material.json")
    if not state.get("source_digest") or state["source_digest"] != material.get("source_digest"):
        raise UpdateError("initial_site_provenance_changed")
    tags = re.findall(rb"travaux-mairie:0\.8\.1-20\d{6}T\d{6}Z-[a-f0-9]{6,12}", compose)
    if len(tags) != 1:
        raise UpdateError("compose_application_anchor_not_unique")
    old_image = tags[0].decode()
    old_release = image_release(old_image)
    expected_old = state.get("app_release", {}).get("image", runtime.C.APP_IMAGE)
    if old_image != expected_old:
        raise UpdateError("private_application_release_drift")
    owner = json_read(PUBLIC_BASE / "ownership.json")
    if owner != {"application": "travaux-mairie", "uid": PUBLIC_BASE.stat().st_uid}:
        raise UpdateError("public_application_not_owned")
    public = json_read(PUBLIC_BASE / "current.json")
    if public.get("release") != release or public.get("image") != image:
        raise UpdateError("target_is_not_current_public_release")
    old = json_read(PUBLIC_BASE / "releases" / old_release / "release-manifest.json")
    new = json_read(PUBLIC_BASE / "releases" / release / "release-manifest.json")
    if old.get("release") != old_release or new.get("release") != release:
        raise UpdateError("manifest_release_mismatch")
    source = verify_manifests(old, new)
    old_id, new_id = verified_image(runtime, old_image, old), verified_image(runtime, image, new)
    # A tagged image alone is insufficient: the public app must run that image.
    ids = runtime.run(["docker", "ps", "-q", "--filter", "label=com.docker.compose.project=travaux-mairie", "--filter", "label=com.docker.compose.service=app"], timeout=15).stdout.split()
    if len(ids) != 1:
        raise UpdateError("public_application_not_unique")
    public_app = runtime.inspect("container", ids[0].decode())
    if not public_app or public_app.get("Image") != new_id:
        raise UpdateError("public_application_image_mismatch")
    for name in ("app", "worker"):
        _, item = runtime.service(name)
        if item.get("Image") != old_id:
            raise UpdateError("private_running_image_drift")
    template = base64.b64decode(payload["compose_template"], validate=True)
    new_compose = updated_compose(compose, template, old_image, image)
    validate_environment(runtime, material)
    protected = immutable_state(runtime)
    if not all(runtime.health().values()):
        raise UpdateError("existing_service_unhealthy")
    return {"uid": uid, "status": state, "status_bytes": status_bytes, "compose": compose,
            "new_compose": new_compose, "protected": protected, "source_digest": source,
            "old_image": old_image, "old_image_id": old_id, "image": image, "image_id": new_id,
            "release": release, "review_id": review}


def plan(payload, runtime):
    state = inspect_state(payload, runtime)
    return {"read_only": True, "image": state["image"], "previous_image": state["old_image"],
            "expected_compose_sha256": digest(state["compose"]),
            "expected_status_sha256": digest(state["status_bytes"]),
            "review_id": state["review_id"], "source_digest": state["source_digest"],
            "services": ["app", "worker"], "secret_values_included": False}


def ensure_private_backup(path):
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise UpdateError("sqlite_backup_permissions")


def sqlite_backup(runtime, folder, uid):
    app, _ = runtime.service("app")
    code = "import sqlite3,sys;s=sqlite3.connect('file:/data/mayortech-test.sqlite3?mode=ro',uri=True);d=sqlite3.connect(':memory:');s.backup(d);assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok';sys.stdout.buffer.write(d.serialize());d.close();s.close()"
    data = runtime.run(["docker", "exec", app, "python", "-c", code], timeout=90).stdout
    if not data.startswith(b"SQLite format 3\x00") or len(data) > 256 * 1024**2:
        raise UpdateError("sqlite_backup_invalid")
    path = folder / "workspace.sqlite3"
    runtime.write_new(path, data, uid)
    ensure_private_backup(path)
    # A native backup of a live WAL database retains its WAL header. Reopening
    # those bytes in :memory: cannot resolve the journal. Canonicalize only this
    # owned backup file into a standalone SQLite file; never change the source.
    database = sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True)
    try:
        if database.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
            raise UpdateError("sqlite_backup_journal")
        if database.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise UpdateError("sqlite_backup_integrity")
    finally:
        database.close()
    ensure_private_backup(path)
    final_data = safe_read(path)
    if (final_data[18:20] != b"\x01\x01"
            or any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal"))):
        raise UpdateError("sqlite_backup_not_standalone")
    return {"path": str(path), "sha256": digest(final_data), "integrity_checked": True,
            "journal_mode": "delete", "restored": False}


def assert_immutable(runtime, state):
    if immutable_state(runtime) != state["protected"]:
        raise UpdateError("identity_caddy_or_private_configuration_changed")


def confirm_application(runtime, image_id, failure_code):
    """A successful compose command is not evidence that the expected code runs."""
    for _ in range(36):
        if all(runtime.health().values()):
            break
        time.sleep(5)
    else:
        raise UpdateError(failure_code)
    for name in ("app", "worker"):
        _, item = runtime.service(name)
        if item.get("Image") != image_id:
            raise UpdateError(failure_code)


def apply(payload, runtime):
    if runtime.fcntl is None:
        raise UpdateError("linux_operator_required")
    base = runtime.C.BASE
    runtime.verify_base()
    lockpath = base / ".operator.lock"
    if lockpath.is_symlink() or lockpath.resolve() != lockpath.absolute():
        raise UpdateError("indirect_operator_lock")
    descriptor = os.open(lockpath, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    changed = False
    up_started = False
    state = None
    receipt_path = None
    receipt_bytes = None
    stage = "operator_lock"
    try:
        runtime.fcntl.flock(descriptor, runtime.fcntl.LOCK_EX | runtime.fcntl.LOCK_NB)
        stage = "inspect_state"
        state = inspect_state(payload, runtime)
        if (payload.get("expected_compose_sha256") != digest(state["compose"])
                or payload.get("expected_status_sha256") != digest(state["status_bytes"])):
            raise UpdateError("stale_maintenance_plan")
        if state["image"] == state["old_image"]:
            return {"idempotent": True, "image": state["image"], "secret_values_included": False}
        stage = "backup_directory"
        updates = base / "app-updates"
        if updates.exists() and (updates.is_symlink() or updates.resolve() != updates.absolute() or stat.S_IMODE(updates.stat().st_mode) != 0o700):
            raise UpdateError("update_directory_collision")
        updates.mkdir(mode=0o700, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)
        folder = updates / stamp
        folder.mkdir(mode=0o700)
        stage = "sqlite_backup"
        backup = sqlite_backup(runtime, folder, state["uid"])
        stage = "immutable_configuration"
        assert_immutable(runtime, state)
        stage = "prepared_receipt"
        receipt = {"status": "prepared", "review_id": state["review_id"], "image": state["image"],
                   "previous_image": state["old_image"], "source_digest": state["source_digest"],
                   "backup": backup, "services": ["app", "worker"], "db_rewritten": False}
        receipt_path = folder / "receipt.json"
        runtime.write_new(folder / "previous-compose.yaml", state["compose"], state["uid"])
        receipt_bytes = json.dumps(receipt).encode()
        runtime.write_new(receipt_path, receipt_bytes, state["uid"])
        stage = "compose_compare_and_swap"
        if digest(safe_read(base / "status.json")) != digest(state["status_bytes"]):
            raise UpdateError("concurrent_file_change")
        atomic_cas(base / "compose.yaml", digest(state["compose"]), state["new_compose"], state["uid"])
        changed = True
        runtime.compose("config", "--quiet")
        up_started = True
        runtime.compose("up", "-d", "--no-deps", "--pull", "never", "app", "worker")
        confirm_application(runtime, state["image_id"], "updated_application_not_healthy_at_expected_image")
        checks = runtime.probes()
        if not checks or not all(checks.values()):
            raise UpdateError("updated_application_https_probe_failed")
        assert_immutable(runtime, state)
        if digest(safe_read(base / "compose.yaml")) != digest(state["new_compose"]):
            raise UpdateError("concurrent_file_change")
        new_status = {**state["status"], "app_release": {
            "release": state["release"], "image": state["image"], "review_id": state["review_id"],
            "source_digest": state["source_digest"], "previous_image": state["old_image"],
            "receipt": str(receipt_path), "updated_at": stamp,
        }}
        receipt.update(status="applied", checks=checks, immutable_configuration_verified=True)
        applied_receipt = json.dumps(receipt).encode()
        atomic_cas(receipt_path, digest(receipt_bytes), applied_receipt, state["uid"])
        receipt_bytes = applied_receipt
        atomic_cas(base / "status.json", digest(state["status_bytes"]), json.dumps(new_status).encode(), state["uid"])
        return {"applied": True, "image": state["image"], "receipt": str(receipt_path),
                "backup": backup, "checks": checks, "secret_values_included": False}
    except Exception as error:
        rolled_back = False
        if changed:
            try:
                atomic_cas(base / "compose.yaml", digest(state["new_compose"]), state["compose"], state["uid"])
                if up_started:
                    runtime.compose("up", "-d", "--no-deps", "--pull", "never", "app", "worker")
                confirm_application(runtime, state["old_image_id"], "previous_application_not_healthy_at_expected_image")
                if digest(safe_read(base / "status.json")) != digest(state["status_bytes"]):
                    raise UpdateError("concurrent_file_change")
                assert_immutable(runtime, state)
                rolled_back = True
            except Exception:
                pass
        if receipt_path is not None:
            try:
                receipt.update(status="failed", compose_rolled_back=rolled_back)
                atomic_cas(receipt_path, digest(receipt_bytes), json.dumps(receipt).encode(), state["uid"])
            except Exception:
                pass
        if changed:
            raise UpdateError("application_update_failed_rolled_back" if rolled_back else "application_update_failed_manual_recovery_required") from None
        if isinstance(error, UpdateError):
            raise
        raise UpdateError("application_update_refused_at_" + stage) from None
    finally:
        os.close(descriptor)


def execute(command, payload):
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    transport_path = root / "deploy/hetzner/deploy.py"
    sys.path.insert(0, str(transport_path.parent))
    spec = importlib.util.spec_from_file_location("private_update_transport", transport_path)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    modules = {name: base64.b64encode(path.read_bytes()).decode() for name, path in (
        ("candidate", here / "candidate.py"), ("private_site_remote", here / "remote.py"),
        ("private_app_update", here / "app_update.py"),
    )}
    bootstrap = "import base64,json,sys,types,os\nos.umask(0o077)\n"
    for name, code in modules.items():
        bootstrap += f"m=types.ModuleType({name!r});sys.modules[{name!r}]=m;exec(base64.b64decode({code!r}),m.__dict__)\n"
    bootstrap += f"p=json.loads(base64.b64decode({base64.b64encode(json.dumps(payload).encode()).decode()!r}))\n"
    bootstrap += f"\ntry:\n result=sys.modules['private_app_update'].{command}(p,sys.modules['private_site_remote']);print(json.dumps(result))\nexcept Exception as error:\n print(json.dumps({{'error':str(error) if isinstance(error,sys.modules['private_app_update'].UpdateError) else 'maintenance_failed','secret_values_included':False}}));sys.exit(1)\n"
    owner = transport.owner_config(transport.OWNER)
    result = subprocess.run(transport.ssh_args(owner) + ["sudo", "-n", "python3", "-"], input=bootstrap,
                            text=True, capture_output=True, timeout=600)
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError()
    except ValueError:
        return {"error": "maintenance_transport_failed", "secret_values_included": False}, 1
    return value, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("--image", required=True)
    parser.add_argument("--review-id", required=True)
    parser.add_argument("--expected-compose-sha256")
    parser.add_argument("--expected-status-sha256")
    parser.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    if args.command == "apply" and (not args.reviewed or not args.expected_compose_sha256 or not args.expected_status_sha256):
        parser.error("apply needs --reviewed and both hashes from a fresh plan")
    image_release(args.image)
    payload = vars(args)
    payload["compose_template"] = base64.b64encode((Path(__file__).resolve().parent / "compose.yaml").read_bytes()).decode()
    value, code = execute(args.command, payload)
    print(json.dumps(value))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
