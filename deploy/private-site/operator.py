"""Narrow SSH entry point; only the public reviewed candidate crosses the wire."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def bundle():
    sources = {name: HERE/name for name in ("compose.yaml", "keycloak-healthcheck.sh", "worker-healthcheck.py", "identity-nginx.conf", "routes.caddy")}
    sources.update({"theme.jar": ROOT/"dist/mayortech-keycloak-theme-2026-11-17.jar", "realm-template.json": ROOT/"deploy/keycloak/realm-test.example.json"})
    data = {}
    for name, path in sources.items():
        if path.is_symlink() or path.resolve() != path.absolute() or not path.is_file():
            raise ValueError("invalid_public_candidate_path")
        data[name] = path.read_bytes()
    digest = hashlib.sha256(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in sorted(data.items())}, sort_keys=True).encode()).hexdigest()
    return {"sha256": digest, "files": {name: base64.b64encode(value).decode() for name, value in data.items()}}


def command_script(command, payload):
    if command not in {"preflight", "apply", "backup", "status"}:
        raise ValueError("invalid_operator_command")
    candidate = base64.b64encode((HERE/"candidate.py").read_bytes()).decode()
    remote = base64.b64encode((HERE/"remote.py").read_bytes()).decode()
    body = base64.b64encode(json.dumps(payload).encode()).decode()
    return f'''import base64,json,os,sys,types
os.umask(0o077)
c=types.ModuleType('candidate');sys.modules['candidate']=c
exec(base64.b64decode({candidate!r}),c.__dict__)
r=types.ModuleType('private_site_remote');sys.modules['private_site_remote']=r;exec(base64.b64decode({remote!r}),r.__dict__)
try:
 p=json.loads(base64.b64decode({body!r}))
 command={command!r}
 if command=='apply': result=r.apply(p)
 elif command=='preflight': result=r.preflight()
 elif command=='backup': r.verify_base();result=r.backup()
 else: r.verify_base();result={{'health':r.health(),'checks':r.probes(),'secret_values_included':False}}
 print(json.dumps(result))
except Exception as error:
 code=str(error) if isinstance(error,r.OperationError) else type(error).__name__
 print(json.dumps({{'error':code,'secret_values_included':False}}));sys.exit(1)
'''


def execute(command):
    # Reuse the existing approved SSH transport. Credentials are consumed only
    # by it, never included in the public result or the remote candidate.
    path = ROOT/"deploy/hetzner"
    sys.path.insert(0, str(path))
    spec = importlib.util.spec_from_file_location("existing_private_transport", path/"deploy.py")
    transport = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transport)
    owner = transport.owner_config(transport.OWNER)
    result = subprocess.run(transport.ssh_args(owner)+["sudo", "-n", "python3", "-"],
                            input=command_script(command, bundle()), text=True, capture_output=True, timeout=1200)
    try:
        value = json.loads(result.stdout)
        if not isinstance(value, dict):
            raise ValueError("invalid_result")
    except (ValueError, TypeError):
        return {"error": "operator_transport_failed", "secret_values_included": False}, 1
    return value, result.returncode or (1 if "error" in value else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "preflight", "apply", "backup", "status"])
    parser.add_argument("--reviewed", action="store_true", help="The exact candidate was independently reviewed")
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps({"source_digest": bundle()["sha256"], "files": sorted(bundle()["files"]), "mutates_server": False}))
        return 0
    if args.command == "apply" and not args.reviewed:
        parser.error("apply requires --reviewed after independent review")
    result, code = execute(args.command)
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
