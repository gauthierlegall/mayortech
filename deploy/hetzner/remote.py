"""Run only via deploy.py SSH bootstrap. Mutates this application's resources only."""

from pathlib import Path
import json
import os
import re
import subprocess
import sys
import time

import common

BASE, APP, ROUTE = common.BASE, common.APP, common.ROUTE
SERVICES = ("app", "worker")


def command(args, *, environment=None, timeout=60, required=True, stdin_text=None):
    try:
        result = subprocess.run(
            args,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, **(environment or {})},
        )
    except Exception:
        raise common.DeploymentError("server_command_failed_no_sensitive_output") from None
    if required and result.returncode:
        raise common.DeploymentError("server_command_failed_no_sensitive_output")
    return result


def read_json(path):
    common.no_symlinks(path)
    try:
        return json.loads(path.read_text())
    except Exception:
        raise common.DeploymentError("private_server_state_invalid") from None


def owned():
    common.no_symlinks(BASE)
    if not BASE.exists():
        return False
    marker = read_json(BASE / "ownership.json")
    if marker != {"application": APP, "uid": os.getuid()}:
        raise common.DeploymentError("application_directory_collision")
    return True


def current_state():
    if not owned() or not (BASE / "current.json").exists():
        return None
    state = read_json(BASE / "current.json")
    common.release_id(state["release"])
    return state


def compose(release, *arguments, required=True, timeout=120, stdin_text=None):
    common.release_id(release)
    config = BASE / "releases" / release / "deploy/hetzner/compose.yaml"
    common.no_symlinks(config)
    return command(
        [
            "docker",
            "compose",
            "--project-name",
            APP,
            "--env-file",
            str(BASE / "secrets/runtime.env"),
            "--file",
            str(config),
            *arguments,
        ],
        environment={"TRAVAUX_IMAGE": image(release)},
        required=required,
        timeout=timeout,
        stdin_text=stdin_text,
    )


def image(release):
    common.release_id(release)
    manifest = BASE / "releases" / release / "release-manifest.json"
    version = read_json(manifest).get("version") if manifest.exists() else common.VERSION
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise common.DeploymentError("stored_release_version_invalid")
    return f"{APP}:{version}-{release}"


def release_runtime(release):
    """A public release can never relabel the historical protected database."""
    common.release_id(release)
    manifest = read_json(BASE / "releases" / release / "release-manifest.json")
    runtime = manifest.get("runtime")
    if runtime is None and manifest.get("version") in {"0.2.0", "0.3.0"}:
        return dict(common.LEGACY_RUNTIME)
    if runtime not in (common.PUBLIC_RUNTIME, common.LEGACY_RUNTIME):
        raise common.DeploymentError("stored_runtime_contract_invalid")
    return dict(runtime)


def separate_public_database_transition(previous, current):
    return previous == common.LEGACY_RUNTIME and current == common.PUBLIC_RUNTIME


def caddy_id():
    found = command(["docker", "ps", "--filter", "name=caddy", "--format", "{{.ID}}"]).stdout.split()
    if len(found) != 1:
        raise common.DeploymentError("caddy_container_not_unique")
    return found[0]


def caddy_valid(container):
    return (
        command(
            [
                "docker",
                "exec",
                container,
                "caddy",
                "validate",
                "--config",
                "/etc/caddy/Caddyfile",
                "--adapter",
                "caddyfile",
            ],
            required=False,
        ).returncode
        == 0
    )


def caddy_reload(container):
    return (
        command(
            [
                "docker",
                "exec",
                container,
                "caddy",
                "reload",
                "--config",
                "/etc/caddy/Caddyfile",
                "--adapter",
                "caddyfile",
            ],
            required=False,
        ).returncode
        == 0
    )


def other_caddy_fingerprint():
    common.no_symlinks(ROUTE.parent)
    files = {
        str(p): common.sha256(p.read_bytes())
        for p in ROUTE.parent.glob("*.caddy")
        if p != ROUTE and p.is_file()
    }
    main = Path("/opt/caddy/Caddyfile")
    files[str(main)] = common.sha256(main.read_bytes())
    return common.inventory_digest(files)


def render_route():
    return common.render_public_demo_route()


def preflight():
    state = current_state()
    container = caddy_id()
    mounts = json.loads(command(["docker", "inspect", "--format", "{{json .Mounts}}", container]).stdout)
    imported = command(["docker", "exec", container, "cat", "/etc/caddy/Caddyfile"]).stdout
    common.no_symlinks(ROUTE)
    volume = command(["docker", "volume", "inspect", common.VOLUME], required=False)
    volume_safe = volume.returncode != 0
    if not volume_safe and owned():
        labels = json.loads(volume.stdout)[0].get("Labels") or {}
        volume_safe = (
            labels.get("io.kerforge.application") == APP and labels.get("com.docker.compose.project") == APP
        )
    route_safe = (
        not ROUTE.exists()
        if not state
        else ROUTE.is_file() and common.sha256(ROUTE.read_bytes()) == state["route_hash"]
    )
    ids = command(
        ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={APP}"]
    ).stdout.split()
    containers_safe = (
        not ids
        if not owned()
        else all(
            json.loads(
                command(["docker", "inspect", "--format", "{{json .Config.Labels}}", item]).stdout
            ).get("io.kerforge.application")
            == APP
            for item in ids
        )
    )
    aliases_safe = True
    network = command(["docker", "network", "inspect", common.NETWORK], required=False)
    if network.returncode == 0:
        for identifier in json.loads(network.stdout)[0].get("Containers", {}):
            networks = json.loads(
                command(
                    ["docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", identifier]
                ).stdout
            )
            if common.ALIAS in (networks.get(common.NETWORK, {}).get("Aliases") or []):
                labels = json.loads(
                    command(["docker", "inspect", "--format", "{{json .Config.Labels}}", identifier]).stdout
                )
                aliases_safe &= (
                    owned()
                    and labels.get("io.kerforge.application") == APP
                    and labels.get("com.docker.compose.project") == APP
                )
    import shutil

    memory = {
        line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()
    }
    return {
        "docker_available": command(["docker", "info"], required=False).returncode == 0,
        "compose_available": command(["docker", "compose", "version"], required=False).returncode == 0,
        "sudo_noninteractive": command(["sudo", "-n", "true"], required=False).returncode == 0,
        "application_path_available_or_owned": not BASE.exists() or owned(),
        "caddy_conf_mount_matches": any(
            m.get("Source") == str(ROUTE.parent) and m.get("Destination") == "/etc/caddy/conf.d"
            for m in mounts
        ),
        "caddy_import_matches": "import /etc/caddy/conf.d/*.caddy" in imported,
        "caddy_configuration_valid": caddy_valid(container),
        "caddy_conf_writable": os.access(ROUTE.parent, os.W_OK),
        "caddy_host_config_readable": os.access("/opt/caddy/Caddyfile", os.R_OK),
        "network_exists": network.returncode == 0,
        "private_volume_available_or_owned": volume_safe,
        "application_containers_available_or_owned": containers_safe,
        "network_alias_available_or_owned": bool(aliases_safe),
        "route_available_or_owned": route_safe,
        "disk_headroom": shutil.disk_usage("/opt").free > 3 * 1024**3,
        "memory_headroom": memory.get("MemAvailable", 0) > 1024 * 1024,
    }


def reserve_base():
    common.no_symlinks(BASE)
    if not BASE.exists():
        # mkdir without -p fails on a concurrent collision; chown only our new dir.
        command(["sudo", "-n", "mkdir", "--mode=700", str(BASE)])
        command(["sudo", "-n", "chown", f"{os.getuid()}:{os.getgid()}", str(BASE)])
        common.atomic_write(
            BASE / "ownership.json", json.dumps({"application": APP, "uid": os.getuid()}).encode()
        )
    elif not owned():
        raise common.DeploymentError("application_path_collision")


def prepare_base():
    if not owned():
        raise common.DeploymentError("application_directory_not_reserved")
    for part in ["secrets", "releases"]:
        location = BASE / part
        common.no_symlinks(location)
        location.mkdir(mode=0o700, exist_ok=True)
    access = BASE / "secrets/access.json"
    runtime = BASE / "secrets/runtime.env"
    common.no_symlinks(access)
    common.no_symlinks(runtime)
    if access.exists() != runtime.exists():
        raise common.DeploymentError("incomplete_existing_secret_state")
    if not access.exists():
        password, encoded = common.password_material()
        # Single quotes are essential: Compose dotenv must preserve every `$`.
        common.atomic_write(runtime, f"TRAVAUX_PASSWORD_HASH='{encoded}'\n".encode())
        common.atomic_write(
            access,
            json.dumps(
                {
                    "url": f"https://{common.DOMAIN}",
                    "password": password,
                    "environment": "staging",
                    "data": "entièrement fictives",
                }
            ).encode(),
        )


def wait_healthy(release):
    for _ in range(24):
        healthy = True
        for service in SERVICES:
            identifiers = compose(release, "ps", "-q", service).stdout.split()
            if len(identifiers) != 1:
                healthy = False
                continue
            result = command(
                ["docker", "inspect", "--format", "{{.State.Health.Status}}", identifiers[0]], required=False
            )
            status = result.stdout.strip()
            if status == "unhealthy":
                raise common.DeploymentError(f"{service}_health_check_failed")
            healthy &= status == "healthy"
        if healthy:
            return
        time.sleep(3)
    raise common.DeploymentError("application_or_worker_health_check_failed")


def private_auth_probe(release):
    code = (
        "import json,urllib.request,urllib.error; h={'Host':'"
        + common.RUNTIME_DOMAIN
        + "'}; req=urllib.request.Request('http://127.0.0.1:8765/api/v1/projects',headers=h)\ntry: urllib.request.urlopen(req);raise SystemExit(1)\nexcept urllib.error.HTTPError as e: assert e.code==401\ns=json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/api/v1/session',headers=h)));assert s['authenticated'] is False\nimport os;assert os.environ['TRAVAUX_MODE']=='staging' and os.environ['TRAVAUX_LLM']=='demo' and os.environ['TRAVAUX_LLM_EGRESS_APPROVED']=='false'"
    )
    compose(release, "exec", "-T", "app", "python", "-c", code)
    # Password crosses the local Docker exec stdin only, never argv/env/logs.
    access = read_json(BASE / "secrets/access.json")
    login_code = """import json,sys,urllib.request
data=json.load(sys.stdin)
headers={'Host':'travaux.kerforge.com','Origin':'https://travaux.kerforge.com','X-Requested-With':'Travaux','Content-Type':'application/json'}
request=urllib.request.Request('http://127.0.0.1:8765/api/v1/session',data=json.dumps({'password':data['password']}).encode(),headers=headers,method='POST')
response=urllib.request.urlopen(request,timeout=5)
assert json.load(response)['authenticated'] is True
cookie=response.headers['Set-Cookie']
assert 'Secure' in cookie and 'HttpOnly' in cookie and 'samesite=strict' in cookie.lower()
headers['Cookie']=cookie.split(';',1)[0]
urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/api/v1/session',headers=headers,method='DELETE'),timeout=5).read()
"""
    compose(
        release,
        "exec",
        "-T",
        "app",
        "python",
        "-c",
        login_code,
        stdin_text=json.dumps({"password": access["password"]}),
    )


def public_auth_probe(release):
    """Exercise the deployed public profile without reading any password material."""
    code = f"""import json,os,urllib.request,urllib.error
from http.cookies import SimpleCookie
assert os.environ['TRAVAUX_MODE']=='public_demo'
assert os.environ['TRAVAUX_DB']=='/data/public-demo.sqlite3'
assert os.environ['TRAVAUX_TENANT']=='public-demo-travaux'
assert os.environ['TRAVAUX_LLM']=='demo'
assert os.environ['TRAVAUX_LLM_EGRESS_APPROVED']=='false'
headers={{'Host':{common.RUNTIME_DOMAIN!r}}}
base='http://127.0.0.1:8765/api/v1/'
response=urllib.request.urlopen(urllib.request.Request(base+'session',headers=headers),timeout=5)
raw_cookie=response.headers.get('Set-Cookie')
if raw_cookie:
    cookies=SimpleCookie(raw_cookie)
    assert set(cookies)=={{'travaux_chat_session'}}
    visitor=cookies['travaux_chat_session']
    assert visitor['secure'] and visitor['httponly'] and visitor['samesite'].lower()=='strict' and visitor['path']=='/api/v1'
session=json.load(response)
assert session['authenticated'] is True and session['demo'] is True
assert session['public_demo'] is True and session['auth_required'] is False
assert session['actor']['tenant_id']=='public-demo-travaux'
projects=json.load(urllib.request.urlopen(urllib.request.Request(base+'projects',headers=headers),timeout=5))
assert isinstance(projects,list) and len(projects)>0
bootstrap=json.load(urllib.request.urlopen(urllib.request.Request(base+'bootstrap',headers=headers),timeout=5))
assert bootstrap['access']['mail_import'] is False
headers.update({{'Origin':'https://{common.RUNTIME_DOMAIN}','X-Requested-With':'Travaux','Content-Type':'application/json'}})
payload=json.dumps({{'filename':'probe-fictif.eml','content':'From: probe@example.invalid\\r\\nSubject: Verification fictive\\r\\n\\r\\nFictif.'}}).encode()
request=urllib.request.Request(base+'imports/eml',data=payload,headers=headers,method='POST')
try:
    urllib.request.urlopen(request,timeout=5)
except urllib.error.HTTPError as error:
    assert error.code==403
else:
    raise AssertionError('public_demo_import_must_be_refused')
"""
    compose(release, "exec", "-T", "app", "python", "-c", code)


def auth_probe(release):
    if release_runtime(release)["mode"] == "public_demo":
        public_auth_probe(release)
    else:
        private_auth_probe(release)


def restore_route(previous: bytes | None, expected_hash: str, container):
    common.no_symlinks(ROUTE)
    if not ROUTE.is_file() or common.sha256(ROUTE.read_bytes()) != expected_hash:
        raise common.DeploymentError("rollback_route_changed_refuse_overwrite")
    if previous is None:
        common.remove_route(
            ROUTE,
            lambda: caddy_valid(container),
            lambda: caddy_reload(container),
            expected_hash=expected_hash,
        )
    else:
        common.activate_route(
            ROUTE,
            previous.decode(),
            lambda: caddy_valid(container),
            lambda: caddy_reload(container),
            expected_previous_hash=expected_hash,
        )


def apply(archive_name, digest, release):
    common.release_id(release)
    archive = Path(archive_name)
    if archive != Path(f"/tmp/travaux-mairie-{release}.tar.gz"):
        raise common.DeploymentError("unexpected_upload_path")
    common.no_symlinks(archive)
    if not archive.is_file() or common.sha256(archive.read_bytes()) != digest:
        raise common.DeploymentError("uploaded_archive_hash_mismatch")
    manifest = common.verify_archive(archive)
    if manifest["release"] != release or not all(preflight().values()):
        raise common.DeploymentError("deployment_preflight_failed")
    reserve_base()
    with common.mutation_lock(BASE):
        if not all(preflight().values()):
            raise common.DeploymentError("deployment_preflight_changed")
        return apply_locked(archive, manifest, release)


def apply_locked(archive, manifest, release):
    previous = current_state()
    runtime = manifest.get("runtime")
    if runtime != common.PUBLIC_RUNTIME:
        raise common.DeploymentError("new_release_runtime_contract_invalid")
    if previous:
        old = read_json(BASE / "releases" / previous["release"] / "release-manifest.json")
        schema = ["repository.py", "workspace.py", "auth.py", "jobs.py", "governance.py"]
        schema_changed = any(
            old["files"].get("src/travaux/" + name) != manifest["files"].get("src/travaux/" + name)
            for name in schema
        )
        if (schema_changed
                and not separate_public_database_transition(release_runtime(previous["release"]), runtime)
                and not common.reviewed_public_schema_upgrade(old, manifest)):
            raise common.DeploymentError("schema_review_required_before_update")
    if command(["docker", "image", "inspect", image(release)], required=False).returncode == 0:
        raise common.DeploymentError("release_image_already_exists_refuse_overwrite")
    prepare_base()
    target = BASE / "releases" / release
    common.extract_verified(archive, target)
    container = caddy_id()
    other_config = other_caddy_fingerprint()

    def valid_without_other_changes():
        return other_caddy_fingerprint() == other_config and caddy_valid(container)

    prior_route = ROUTE.read_bytes() if ROUTE.exists() else None
    route_hash = common.sha256(render_route().encode())
    started = published = False
    try:
        if previous:
            backup = f"/data/backups/pre-{release}.sqlite3"
            previous_db = release_runtime(previous["release"])["db_path"]
            code = (
                "import sqlite3,pathlib,os;p=pathlib.Path("
                + repr(backup)
                + ");p.parent.mkdir(exist_ok=True);s=sqlite3.connect("
                + repr("file:" + previous_db + "?mode=ro")
                + ",uri=True);d=sqlite3.connect(p);s.backup(d);d.close();s.close();os.chmod(p,0o600)"
            )
            compose(previous["release"], "exec", "-T", "app", "python", "-c", code)
        command(
            [
                "docker",
                "build",
                "--tag",
                image(release),
                "--label",
                f"io.kerforge.application={APP}",
                "--label",
                f"io.kerforge.source-digest={common.inventory_digest(manifest['files'])}",
                "--file",
                str(target / "Dockerfile"),
                str(target),
            ],
            timeout=600,
        )
        compose(release, "config", "--quiet")
        started = True
        compose(release, "up", "-d", "--no-deps", "--pull", "never", *SERVICES)
        wait_healthy(release)
        auth_probe(release)
        common.activate_route(
            ROUTE,
            render_route(),
            valid_without_other_changes,
            lambda: other_caddy_fingerprint() == other_config and caddy_reload(container),
            expected_previous_hash=previous["route_hash"] if previous else None,
        )
        published = True
        state = {
            "release": release,
            "image": image(release),
            "route_hash": route_hash,
            "previous": previous,
            "previous_route": prior_route.decode() if prior_route is not None else None,
        }
        common.atomic_write(BASE / "current.json", json.dumps(state).encode())
        return {
            "deployed": True,
            "public_demo": True,
            "auth_required": False,
            "mail_import_disabled": True,
            "runtime": dict(runtime),
            "fake_llm": True,
            "route_validated_and_reloaded": True,
            "release": release,
            "public_https_probe_required": True,
            "credentials_required": False,
        }
    except Exception:
        restored_route = not published
        restored_app = not started
        if published:
            try:
                restore_route(prior_route, route_hash, container)
                restored_route = True
            except Exception:
                pass
        if started:
            try:
                if previous:
                    compose(previous["release"], "up", "-d", "--no-deps", "--pull", "never", *SERVICES)
                else:
                    compose(release, "stop", *SERVICES)
                restored_app = True
            except Exception:
                pass
        common.atomic_write(
            BASE / "last-failure.json",
            json.dumps(
                {
                    "release": release,
                    "route_restored": restored_route,
                    "app_restored": restored_app,
                    "database_restored": False,
                }
            ).encode(),
        )
        raise common.DeploymentError("release_failed_own_app_rollback_attempted_no_secret_output") from None


def rollback():
    if not owned():
        raise common.DeploymentError("no_owned_application")
    with common.mutation_lock(BASE):
        return rollback_locked()


def rollback_locked():
    state = current_state()
    if not state:
        raise common.DeploymentError("no_owned_current_release")
    common.no_symlinks(ROUTE)
    if not ROUTE.is_file() or common.sha256(ROUTE.read_bytes()) != state["route_hash"]:
        raise common.DeploymentError("rollback_route_changed_refuse_any_mutation")
    previous = state.get("previous")
    if state.get("previous_route") is not None and state["previous_route"] != render_route():
        raise common.DeploymentError("legacy_rollback_route_requires_migration")
    if previous:
        compose(previous["release"], "up", "-d", "--no-deps", "--pull", "never", *SERVICES)
        wait_healthy(previous["release"])
        auth_probe(previous["release"])
    restore_route(
        state["previous_route"].encode() if state.get("previous_route") is not None else None,
        state["route_hash"],
        caddy_id(),
    )
    if not previous:
        compose(state["release"], "stop", *SERVICES)
    if previous:
        common.atomic_write(BASE / "current.json", json.dumps(previous).encode())
    else:
        (BASE / "current.json").unlink()
    return {
        "rolled_back": True,
        "other_services_changed": False,
        "volume_preserved": True,
        "database_restored": False,
        "dns_changed": False,
    }


def main():
    action = sys.argv[1]
    if action == "preflight":
        result = preflight()
    elif action == "apply" and len(sys.argv) == 5:
        result = apply(*sys.argv[2:])
    elif action == "rollback":
        result = rollback()
    elif action == "credentials":
        if not owned():
            raise common.DeploymentError("no_owned_application")
        result = read_json(BASE / "secrets/access.json")
    else:
        raise common.DeploymentError("unsupported_deployment_action")
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print('{"error":"remote_deployment_failed_no_sensitive_output"}')
        raise SystemExit(1)
