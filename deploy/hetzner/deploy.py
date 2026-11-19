"""Operator CLI. No credentials are printed; no action is implicit."""

from pathlib import Path
import argparse
import base64
import io
import json
import os
import re
import secrets
import shlex
import subprocess
import tarfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
import common

ROOT = Path(__file__).resolve().parents[2]
OWNER = Path.home() / ".saas-factory" / "owner.json"
password_material = common.password_material


def inventory(root: Path) -> dict:
    root = root.resolve()
    candidates = [
        root / name
        for name in [
            "Dockerfile",
            "pyproject.toml",
            "uv.lock",
            "deploy/hetzner/common.py",
            "deploy/hetzner/remote.py",
            "deploy/hetzner/compose.yaml",
        ]
    ]
    candidates += list((root / "src/travaux").rglob("*"))
    candidates += list((root / "web").rglob("*"))
    candidates += list((root / "native-editor/dist").rglob("*"))
    candidates += list((root / "fixtures/storylines/lovable-v1").rglob("*"))
    result = {}
    for path in candidates:
        name = path.relative_to(root).as_posix()
        if not common.allowed_name(name):
            continue
        common.no_symlinks(path)
        if path.is_file():
            result[name] = common.sha256(path.read_bytes())
    if not common.REQUIRED.issubset(result):
        raise common.DeploymentError("required_release_file_missing")
    common.verify_storyline_contents(
        {name: (root / name).read_bytes() for name in common.STORYLINE_RESOURCES}
    )
    return dict(sorted(result.items()))


def make_gate(files, *, python=False, frontend=False, native=False):
    if any(type(value) is not bool or not value for value in (python, frontend, native)):
        raise common.DeploymentError("all_three_verifications_required")
    return {
        "checks": {"python": True, "frontend": True, "native": True},
        "source_digest": common.inventory_digest(files),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_gate(gate, files):
    if not common.valid_checks(gate.get("checks")) or gate.get("source_digest") != common.inventory_digest(
        files
    ):
        raise common.DeploymentError("verification_gate_missing_or_stale")


def package(root, output, release, gate):
    common.release_id(release)
    files = inventory(root)
    validate_gate(gate, files)
    manifest = {
        "app": common.APP,
        "version": common.VERSION,
        "runtime": dict(common.PUBLIC_RUNTIME),
        "release": release,
        "files": files,
        "gate": gate,
    }
    if output.exists():
        raise common.DeploymentError("archive_already_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as archive:
        contents = {name: (root / name).read_bytes() for name in files}
        contents[".dockerignore"] = common.DOCKERIGNORE.encode()
        contents["release-manifest.json"] = json.dumps(manifest, sort_keys=True).encode()
        for name, data in contents.items():
            if name in files and common.sha256(data) != files[name]:
                raise common.DeploymentError("source_changed_during_packaging")
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o600
            archive.addfile(item, io.BytesIO(data))
    output.chmod(0o600)
    common.verify_archive(output)
    return manifest


def dns_plan(records):
    if records:
        raise common.DeploymentError("dns_record_exists_refuse_overwrite")
    return {
        "action": "create",
        "name": common.DOMAIN,
        "content_reference": "owner.vps.default_host",
        "type": "A_if_ipv4_otherwise_verify",
        "proxied": True,
        "ttl": 1,
        "mutation_performed": False,
    }


def owner_config(path):
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        vps = result["vps"]
        if vps["default_user"] != "deploy" or not re.fullmatch(r"[A-Za-z0-9.:-]+", vps["default_host"]):
            raise ValueError()
        if not Path(vps["identity_file"]).expanduser().is_file():
            raise ValueError()
        return result
    except Exception:
        raise common.DeploymentError("owner_ssh_configuration_invalid") from None


def ssh_args(owner):
    vps = owner["vps"]
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "ConnectTimeout=10",
        "-i",
        str(Path(vps["identity_file"]).expanduser()),
        f"deploy@{vps['default_host']}",
    ]


def remote_call(owner, action, arguments=(), *, timeout=900):
    # Code is supplied by this reviewed release, never extracted from untrusted tar.
    sources = {
        name: base64.b64encode((Path(__file__).parent / name).read_bytes()).decode()
        for name in ["common.py", "remote.py"]
    }
    bootstrap = 'import base64,sys,types\nmodule=types.ModuleType("common")\nsys.modules["common"]=module\n'
    bootstrap += f"exec(base64.b64decode({sources['common.py']!r}),module.__dict__)\n"
    bootstrap += f"sys.argv={json.dumps(['remote.py', action, *arguments])}\n"
    bootstrap += f'exec(compile(base64.b64decode({sources["remote.py"]!r}),"remote.py","exec"),{{"__name__":"__main__"}})\n'
    process = subprocess.run(
        [*ssh_args(owner), "python3 -"], input=bootstrap.encode(), capture_output=True, timeout=timeout
    )
    if process.returncode:
        # Do not relay stderr, docker output, owner fields, or exception repr.
        raise common.DeploymentError("remote_operation_failed_check_private_server_state")
    try:
        return json.loads(process.stdout)
    except Exception:
        raise common.DeploymentError("invalid_remote_result") from None


def upload(owner, archive, release):
    common.release_id(release)
    path = f"/tmp/travaux-mairie-{release}.tar.gz"
    code = (
        "import os,sys,shutil;f=os.fdopen(os.open("
        + repr(path)
        + ',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),"wb");shutil.copyfileobj(sys.stdin.buffer,f);f.close()'
    )
    command = "python3 -c " + shlex.quote(code)
    process = subprocess.run(
        [*ssh_args(owner), command], input=archive.read_bytes(), capture_output=True, timeout=180
    )
    if process.returncode:
        raise common.DeploymentError("upload_failed_or_release_upload_already_exists")
    return path


def private_output(path, data):
    path = path.resolve()
    if path.is_relative_to(ROOT):
        raise common.DeploymentError("private_report_must_be_outside_project")
    common.no_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with os.fdopen(
        os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8"
    ) as output:
        json.dump(data, output, ensure_ascii=False, indent=2)


def check_dns(owner):
    token = owner.get("cloudflare", {}).get("api_token")
    if not token:
        raise common.DeploymentError("cloudflare_credential_missing")

    def get(path):
        request = urllib.request.Request(
            "https://api.cloudflare.com/client/v4/" + path,
            headers={"Authorization": "Bearer " + token, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.load(response)
            if not result.get("success"):
                raise ValueError()
            return result["result"]
        except Exception:
            raise common.DeploymentError("cloudflare_read_check_failed") from None

    zones = get("zones?name=kerforge.com&status=active")
    if len(zones) != 1:
        raise common.DeploymentError("expected_cloudflare_zone_not_unique")
    records = get(f"zones/{zones[0]['id']}/dns_records?name={common.DOMAIN}&per_page=100")
    return dns_plan(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", type=Path, default=OWNER)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("plan")
    commands.add_parser("preflight")
    commands.add_parser("dns-plan")
    gate = commands.add_parser("gate")
    gate.add_argument("--python-passed", action="store_true")
    gate.add_argument("--frontend-passed", action="store_true")
    gate.add_argument("--native-passed", action="store_true")
    gate.add_argument("--out", required=True, type=Path)
    bundle = commands.add_parser("package")
    bundle.add_argument("--gate", required=True, type=Path)
    bundle.add_argument(
        "--release",
        default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3),
    )
    bundle.add_argument("--out", required=True, type=Path)
    apply = commands.add_parser("apply")
    apply.add_argument("--archive", required=True, type=Path)
    commands.add_parser("rollback")
    credentials = commands.add_parser("credentials")
    credentials.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "plan":
        items = inventory(ROOT)
        print(
            json.dumps(
                {
                    "files": len(items),
                    "source_digest": common.inventory_digest(items),
                    "domain": common.DOMAIN,
                    "version": common.VERSION,
                    "deploy_performed": False,
                }
            )
        )
        return
    if args.action == "gate":
        private_output(
            args.out,
            make_gate(
                inventory(ROOT),
                python=args.python_passed,
                frontend=args.frontend_passed,
                native=args.native_passed,
            ),
        )
        print('{"verification_attestation_recorded":true}')
        return
    if args.action == "package":
        if args.out.resolve().is_relative_to(ROOT):
            raise common.DeploymentError("archive_must_be_outside_project")
        manifest = package(ROOT, args.out, args.release, json.loads(args.gate.read_text(encoding="utf-8")))
        print(
            json.dumps(
                {
                    "release": manifest["release"],
                    "archive_sha256": common.sha256(args.out.read_bytes()),
                    "deploy_performed": False,
                }
            )
        )
        return
    owner = owner_config(args.owner)
    if args.action == "dns-plan":
        print(json.dumps(check_dns(owner)))
        return
    if args.action == "apply":
        manifest = common.verify_archive(args.archive)
        # Reject stale bundles, including reviewed deployment helpers, before SSH.
        if manifest["files"] != inventory(ROOT):
            raise common.DeploymentError("bundle_differs_from_current_reviewed_source")
        path = upload(owner, args.archive, manifest["release"])
        result = remote_call(
            owner, "apply", [path, common.sha256(args.archive.read_bytes()), manifest["release"]]
        )
    elif args.action == "credentials":
        result = remote_call(owner, "credentials")
        private_output(args.out, result)
        print('{"credentials_saved_outside_project":true}')
        return
    else:
        result = remote_call(owner, args.action)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except common.DeploymentError as error:
        print(json.dumps({"error": str(error)}))
        raise SystemExit(1)
    except Exception:
        print('{"error":"deployment_operation_failed_no_sensitive_output"}')
        raise SystemExit(1)
