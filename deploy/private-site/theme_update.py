"""Reviewed CSS repair and cache-versioned URL; no realm, credential or DB administration.

Recreating Keycloak interrupts unfinished identity flows. Run only in the reviewed
maintenance window, after the separate MFA diagnostic has finished.
"""
import argparse
import base64
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys
import zipfile

import app_update as A

OLD_SHA256 = "fd30180db6848be258c2806e017c046f9c0dbac6d048b97a8df1501a0218eadd"
CSS_REPAIR_SHA256 = "5c8846381580c89e73e98bab770977c9f2017ba1e0002f11d7e21e3d559b7069"
NEW_SHA256 = "4288841cc62f7f3ed06373c178741835e08b13a2c4fa5106e1a092861fa13afd"
CSS_ENTRY = "theme/mayortech/login/resources/css/mayortech.css"
NEW_CSS_ENTRY = "theme/mayortech/login/resources/css/mayortech-20261118-1.css"
PROPERTIES_ENTRY = "theme/mayortech/login/theme.properties"
OLD_STYLES = b"styles=css/styles.css css/mayortech.css\n"
NEW_STYLES = b"styles=css/styles.css css/mayortech-20261118-1.css\n"
OLD_RULE = b".pf-v5-c-login__container { width:min(100%,490px);max-width:490px;grid-template-columns:minmax(0,1fr);margin-inline:auto; }"
NEW_RULE = OLD_RULE.replace(b"max-width:490px;", b"max-width:490px;padding-inline:0;")
GUARD_IMAGE = "nginx:alpine@sha256:df221db836e1754089190208cee7eeda94f233197056426eda74a43ab1abeac2"


class ThemeError(RuntimeError):
    """Fixed codes only; private configuration and command output are withheld."""


def verify_patch(old, new):
    if A.digest(old) != OLD_SHA256 or A.digest(new) != NEW_SHA256:
        raise ThemeError("theme_artifact_not_reviewed")
    with zipfile.ZipFile(io.BytesIO(old)) as before, zipfile.ZipFile(io.BytesIO(new)) as after:
        names = before.namelist()
        expected_names = [NEW_CSS_ENTRY if name == CSS_ENTRY else name for name in names]
        if len(names) != len(set(names)) or expected_names != after.namelist():
            raise ThemeError("theme_entries_changed")
        if CSS_ENTRY not in names or PROPERTIES_ENTRY not in names:
            raise ThemeError("theme_css_or_properties_missing")
        for name in names:
            original = before.read(name)
            replacement = after.read(NEW_CSS_ENTRY if name == CSS_ENTRY else name)
            if name == CSS_ENTRY:
                if original.count(OLD_RULE) != 1 or replacement != original.replace(OLD_RULE, NEW_RULE):
                    raise ThemeError("theme_css_change_not_exact")
            elif name == PROPERTIES_ENTRY:
                if original.count(OLD_STYLES) != 1 or replacement != original.replace(OLD_STYLES, NEW_STYLES):
                    raise ThemeError("theme_styles_change_not_exact")
            elif original != replacement:
                raise ThemeError("non_css_theme_change")


def validate_deployed_theme(content, status):
    deployed_hash = A.digest(content)
    recorded = status.get("theme_release", {}).get("sha256", OLD_SHA256)
    if deployed_hash != recorded or deployed_hash not in {OLD_SHA256, CSS_REPAIR_SHA256, NEW_SHA256}:
        raise ThemeError("deployed_theme_drift")


def frozen_state(runtime):
    value = A.immutable_state(runtime)
    del value["files"][str(runtime.C.BASE / "theme.jar")]
    # Only the two explicitly recreated containers may obtain different IDs.
    del value["services"]["keycloak"]
    del value["services"]["identity_guard"]
    for name in ("app", "worker"):
        ident, item = runtime.service(name)
        value["services"][name] = (ident, item["Image"])
    path = runtime.C.BASE / "compose.yaml"
    value["compose"] = (A.digest(A.safe_read(path)), stat.S_IMODE(path.stat().st_mode), path.stat().st_uid)
    return value


def assert_frozen(runtime, state):
    if frozen_state(runtime) != state["frozen"]:
        raise ThemeError("identity_routing_application_or_secret_drift")
    for name, image in state["native_images"].items():
        _, item = runtime.service(name)
        if item["Image"] != image:
            raise ThemeError("native_image_changed")


def reviewed_native_images(runtime):
    images = {}
    for name, reference in (("keycloak", runtime.C.KEYCLOAK_IMAGE), ("identity_guard", GUARD_IMAGE)):
        local = runtime.inspect("image", reference)
        _, current = runtime.service(name)
        if local is None or current["Image"] != local.get("Id"):
            raise ThemeError("native_image_drift_before_maintenance")
        images[name] = current["Image"]
    return images


def inspect_state(payload, runtime):
    uid = int(os.environ.get("SUDO_UID", os.getuid() if hasattr(os, "getuid") else 0))
    runtime.verify_base(expected_uid=uid)
    A.validate_private_metadata(runtime, uid)
    A.validate_environment(runtime)
    review = payload.get("review_id")
    if not isinstance(review, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}", review):
        raise ThemeError("review_identifier_required")
    new = base64.b64decode(payload["new_theme"], validate=True)
    old_baseline = base64.b64decode(payload["baseline_theme"], validate=True)
    if max(len(new), len(old_baseline)) > 300_000:
        raise ThemeError("theme_size")
    verify_patch(old_baseline, new)
    base = runtime.C.BASE
    old, status_bytes = A.safe_read(base / "theme.jar"), A.safe_read(base / "status.json")
    info = (base / "theme.jar").stat()
    if stat.S_IMODE(info.st_mode) != 0o644 or info.st_uid != uid:
        raise ThemeError("theme_file_permissions")
    status = json.loads(status_bytes)
    material = A.json_read(base / "private/bootstrap-material.json")
    if not status.get("source_digest") or status["source_digest"] != material.get("source_digest"):
        raise ThemeError("initial_site_provenance_changed")
    old_hash = A.digest(old)
    validate_deployed_theme(old, status)
    compose = A.safe_read(base / "compose.yaml")
    tags = re.findall(rb"travaux-mairie:0\.8\.1-20\d{6}T\d{6}Z-[a-f0-9]{6,12}", compose)
    if len(tags) != 1:
        raise ThemeError("compose_contract_changed")
    template = base64.b64decode(payload["compose_template"], validate=True)
    A.updated_compose(compose, template, tags[0].decode(), tags[0].decode())
    if not all(runtime.health().values()):
        raise ThemeError("existing_service_unhealthy")
    native = reviewed_native_images(runtime)
    app_image = runtime.service("app")[1]["Image"]
    A.confirm_application(runtime, app_image, "existing_application_image_drift")
    return {"uid": uid, "old": old, "old_hash": old_hash, "new": new, "status": status,
            "status_bytes": status_bytes, "frozen": frozen_state(runtime), "review_id": review,
            "native_images": native, "app_image": app_image}


def plan(payload, runtime):
    value = inspect_state(payload, runtime)
    return {"read_only": True, "expected_theme_sha256": value["old_hash"],
            "expected_status_sha256": A.digest(value["status_bytes"]), "new_theme_sha256": NEW_SHA256,
            "review_id": value["review_id"], "restart_services": ["keycloak", "identity_guard"],
            "administrative_database_operation": False, "secret_values_included": False}


def replace_theme(path, expected, data, uid):
    if A.digest(A.safe_read(path)) != expected:
        raise ThemeError("concurrent_theme_change")
    temporary = path.with_name(path.name + ".pending-" + secrets.token_hex(8))
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if uid is not None and os.name != "nt":
            os.chown(temporary, uid, uid)
        # The operator's umask is 077; public bind-mounted assets must retain
        # their reviewed 0644 metadata rather than inheriting secret-file mode.
        os.chmod(temporary, 0o644)
        if A.digest(A.safe_read(path)) != expected:
            raise ThemeError("concurrent_theme_change")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def recreate_identity(runtime, state):
    # The bind-mounted JAR needs a new inode in Keycloak. Nginx resolves the
    # Keycloak service name at startup, so it is recreated only after readiness.
    runtime.compose("up", "-d", "--no-deps", "--pull", "never", "--force-recreate", "keycloak")
    A.confirm_application(runtime, state["app_image"], "identity_restart_not_healthy")
    runtime.compose("up", "-d", "--no-deps", "--pull", "never", "--force-recreate", "identity_guard")
    A.confirm_application(runtime, state["app_image"], "identity_guard_restart_not_healthy")
    checks = runtime.probes()
    if not checks or not all(checks.values()):
        raise ThemeError("identity_https_probe_failed")
    return checks


def apply(payload, runtime):
    if runtime.fcntl is None:
        raise ThemeError("linux_operator_required")
    base = runtime.C.BASE
    runtime.verify_base()
    lock = base / ".operator.lock"
    if lock.is_symlink() or lock.resolve() != lock.absolute():
        raise ThemeError("indirect_operator_lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    changed = restarted = False
    receipt_path = receipt_bytes = None
    state = None
    try:
        runtime.fcntl.flock(fd, runtime.fcntl.LOCK_EX | runtime.fcntl.LOCK_NB)
        state = inspect_state(payload, runtime)
        if (payload.get("expected_theme_sha256") != state["old_hash"]
                or payload.get("expected_status_sha256") != A.digest(state["status_bytes"])):
            raise ThemeError("stale_theme_plan")
        if state["old_hash"] == NEW_SHA256:
            return {"idempotent": True, "theme_sha256": NEW_SHA256, "secret_values_included": False}
        folder = base / "theme-updates"
        if folder.exists() and (folder.resolve() != folder.absolute() or folder.is_symlink()
                                or stat.S_IMODE(folder.stat().st_mode) != 0o700):
            raise ThemeError("theme_backup_directory_collision")
        folder.mkdir(mode=0o700, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4)
        folder = folder / stamp
        folder.mkdir(mode=0o700)
        runtime.write_new(folder / "previous-theme.jar", state["old"], state["uid"])
        receipt = {"status": "prepared", "review_id": state["review_id"], "previous_sha256": state["old_hash"],
                   "theme_sha256": NEW_SHA256, "restart_services": ["keycloak", "identity_guard"],
                   "administrative_database_operation": False, "backup": str(folder / "previous-theme.jar")}
        receipt_path = folder / "receipt.json"
        receipt_bytes = json.dumps(receipt).encode()
        runtime.write_new(receipt_path, receipt_bytes, state["uid"])
        assert_frozen(runtime, state)
        if A.digest(A.safe_read(base / "status.json")) != A.digest(state["status_bytes"]):
            raise ThemeError("concurrent_status_change")
        replace_theme(base / "theme.jar", state["old_hash"], state["new"], state["uid"])
        changed = True
        runtime.compose("config", "--quiet")
        restarted = True
        checks = recreate_identity(runtime, state)
        assert_frozen(runtime, state)
        if A.digest(A.safe_read(base / "theme.jar")) != NEW_SHA256:
            raise ThemeError("concurrent_theme_change")
        receipt.update(status="applied", checks=checks, immutable_configuration_verified=True)
        applied = json.dumps(receipt).encode()
        A.atomic_cas(receipt_path, A.digest(receipt_bytes), applied, state["uid"])
        receipt_bytes = applied
        status = {**state["status"], "theme_release": {"sha256": NEW_SHA256,
                  "previous_sha256": state["old_hash"], "review_id": state["review_id"],
                  "receipt": str(receipt_path), "updated_at": stamp}}
        A.atomic_cas(base / "status.json", A.digest(state["status_bytes"]), json.dumps(status).encode(), state["uid"])
        return {"applied": True, "theme_sha256": NEW_SHA256, "receipt": str(receipt_path),
                "checks": checks, "secret_values_included": False}
    except Exception as error:
        restored = False
        if changed:
            try:
                replace_theme(base / "theme.jar", NEW_SHA256, state["old"], state["uid"])
                if restarted:
                    recreate_identity(runtime, state)
                else:
                    A.confirm_application(runtime, state["app_image"], "previous_identity_not_healthy")
                assert_frozen(runtime, state)
                if A.digest(A.safe_read(base / "status.json")) != A.digest(state["status_bytes"]):
                    raise ThemeError("concurrent_status_change")
                restored = True
            except Exception:
                pass
        if receipt_path is not None:
            try:
                receipt.update(status="failed", theme_rolled_back=restored)
                A.atomic_cas(receipt_path, A.digest(receipt_bytes), json.dumps(receipt).encode(), state["uid"])
            except Exception:
                pass
        if changed:
            raise ThemeError("theme_update_failed_rolled_back" if restored else "theme_update_failed_manual_recovery_required") from None
        if isinstance(error, (ThemeError, A.UpdateError)):
            raise
        raise ThemeError("theme_update_refused") from None
    finally:
        os.close(fd)


def execute(command, payload):
    if command not in {"plan", "apply"}:
        raise ThemeError("invalid_theme_operator_command")
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    transport_path = root / "deploy/hetzner/deploy.py"
    sys.path.insert(0, str(transport_path.parent))
    spec = importlib.util.spec_from_file_location("theme_update_transport", transport_path)
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    body = "import base64,json,sys,types,os\nos.umask(0o077)\n"
    for name, filename in (("candidate", "candidate.py"), ("private_site_remote", "remote.py"),
                           ("app_update", "app_update.py"), ("private_theme_update", "theme_update.py")):
        code = base64.b64encode((here / filename).read_bytes()).decode()
        body += f"m=types.ModuleType({name!r});sys.modules[{name!r}]=m;exec(base64.b64decode({code!r}),m.__dict__)\n"
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    body += f"p=json.loads(base64.b64decode({encoded!r}))\n"
    body += f"\ntry:\n result=sys.modules['private_theme_update'].{command}(p,sys.modules['private_site_remote']);print(json.dumps(result))\nexcept Exception as error:\n print(json.dumps({{'error':str(error) if isinstance(error,(sys.modules['private_theme_update'].ThemeError,sys.modules['app_update'].UpdateError)) else 'theme_maintenance_failed','secret_values_included':False}}));sys.exit(1)\n"
    owner = transport.owner_config(transport.OWNER)
    result = subprocess.run(transport.ssh_args(owner) + ["sudo", "-n", "python3", "-"], input=body,
                            text=True, capture_output=True, timeout=900)
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError()
    except ValueError:
        return {"error": "theme_transport_failed", "secret_values_included": False}, 1
    return value, result.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "apply"))
    parser.add_argument("--jar", required=True, type=Path)
    parser.add_argument("--review-id", required=True)
    parser.add_argument("--expected-theme-sha256")
    parser.add_argument("--expected-status-sha256")
    parser.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    if args.command == "apply" and (not args.reviewed or not args.expected_theme_sha256 or not args.expected_status_sha256):
        parser.error("apply needs --reviewed and both hashes from a fresh plan")
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    if not args.jar.resolve().is_relative_to((root / "dist").resolve()):
        parser.error("only the reviewed public dist JAR is accepted")
    new = A.safe_read(args.jar.absolute())
    baseline = A.safe_read(root / "dist/mayortech-keycloak-theme-2026-11-17.jar")
    verify_patch(baseline, new)
    payload = {"review_id": args.review_id, "expected_theme_sha256": args.expected_theme_sha256,
               "expected_status_sha256": args.expected_status_sha256,
               "new_theme": base64.b64encode(new).decode(), "baseline_theme": base64.b64encode(baseline).decode(),
               "compose_template": base64.b64encode((here / "compose.yaml").read_bytes()).decode()}
    value, code = execute(args.command, payload)
    print(json.dumps(value))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
