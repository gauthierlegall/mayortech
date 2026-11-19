"""Narrow operator for the dedicated fictional private site. No raw command logs."""
import base64
from datetime import datetime, timezone
try:
    import fcntl
except ImportError:  # Allows pure boundary tests on Windows; apply is Linux only.
    fcntl = None
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import stat
import subprocess
import time

import candidate as C

FILES = {"compose.yaml", "keycloak-healthcheck.sh", "worker-healthcheck.py", "identity-nginx.conf", "routes.caddy", "theme.jar", "realm-template.json"}
ROUTE = Path("/opt/caddy/conf.d/mayortech-private.caddy")


class OperationError(RuntimeError):
    pass


def run(args, *, data=None, timeout=120, required=True):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    if required and result.returncode:
        raise OperationError("operator_command_failed")
    return result


def write_new(path, content, uid=None):
    path = Path(path)
    if path.resolve() != path.absolute() or path.is_symlink():
        raise OperationError("indirect_path")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
    if uid is not None:
        os.chown(path, uid, uid)


def verify_base(base=C.BASE, expected_uid=None):
    base = Path(base)
    marker = base / ".mayortech-private-owner"
    if base.resolve() != base.absolute() or base.is_symlink() or not marker.is_file() or marker.is_symlink():
        raise OperationError("unowned_application_directory")
    if marker.read_text() != C.MARKER:
        raise OperationError("foreign_application_marker")
    if expected_uid is not None and base.stat().st_uid != expected_uid:
        raise OperationError("application_owner_mismatch")
    if os.name != "nt" and (stat.S_IMODE(base.stat().st_mode) != 0o700 or stat.S_IMODE(marker.stat().st_mode) != 0o600):
        raise OperationError("application_permissions")


def validate_bundle(bundle):
    if not isinstance(bundle, dict) or set(bundle.get("files", {})) != FILES:
        raise OperationError("invalid_candidate_members")
    files = {name: base64.b64decode(value, validate=True) for name, value in bundle["files"].items()}
    if any(len(value) > 300_000 for value in files.values()):
        raise OperationError("candidate_size")
    digest = hashlib.sha256(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())}, sort_keys=True).encode()).hexdigest()
    if digest != bundle.get("sha256"):
        raise OperationError("candidate_integrity")
    return files, digest


def inspect(kind, name):
    result = run(["docker", kind, "inspect", name], required=False, timeout=15)
    return json.loads(result.stdout)[0] if result.returncode == 0 else None


def service(name):
    value = run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project="+C.PROJECT, "--filter", "label=com.docker.compose.service="+name], timeout=15).stdout.split()
    if len(value) != 1:
        raise OperationError("owned_service_not_unique")
    ident = value[0].decode()
    item = inspect("container", ident)
    if item["Config"]["Labels"].get("io.kerforge.application") != C.PROJECT:
        raise OperationError("service_ownership")
    return ident, item


def caddy():
    ids = run(["docker", "ps", "--filter", "name=caddy", "--format", "{{.ID}}"], timeout=15).stdout.split()
    if len(ids) != 1:
        raise OperationError("caddy_not_unique")
    ident = ids[0].decode()
    item = inspect("container", ident)
    if not any(m.get("Source") == str(ROUTE.parent) and m.get("Destination") == "/etc/caddy/conf.d" for m in item["Mounts"]):
        raise OperationError("caddy_route_mount")
    address = item["NetworkSettings"]["Networks"]["caddy_net"]["IPAddress"]
    ipaddress.ip_address(address)
    return ident, address


def peers_digest():
    files = [Path("/opt/caddy/Caddyfile"), *sorted(ROUTE.parent.glob("*.caddy"))]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p != ROUTE}


def logging_is_safe(value):
    return value is None or (isinstance(value, dict) and all(str(item.get("level", "INFO")).upper() != "DEBUG" for item in value.get("logs", {}).values()))


def preflight():
    uid = int(os.environ.get("SUDO_UID", os.getuid()))
    verify_base(expected_uid=uid)
    memory = {line.split(":")[0]: int(line.split()[1])*1024 for line in Path("/proc/meminfo").read_text().splitlines()}
    disk = shutil.disk_usage("/opt/apps").free
    checks = {"disk_headroom": disk > 3*1024**3, "memory_headroom": memory["MemAvailable"] > 2.5*1024**3}
    for label, image in (("app_image_local", C.APP_IMAGE), ("keycloak_image_local", C.KEYCLOAK_IMAGE), ("postgres_image_local", C.POSTGRES_IMAGE), ("nginx_image_local", "nginx:alpine@sha256:df221db836e1754089190208cee7eeda94f233197056426eda74a43ab1abeac2")):
        checks[label] = inspect("image", image) is not None
    checks["caddy_network"] = inspect("network", "caddy_net") is not None
    owned_containers = True
    ids = run(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project="+C.PROJECT], timeout=15).stdout.split()
    for ident in ids:
        item = inspect("container", ident.decode())
        owned_containers = owned_containers and (item["Config"].get("Labels") or {}).get("io.kerforge.application") == C.PROJECT
    checks["containers_owned"] = owned_containers
    aliases_safe = True
    network = inspect("network", "caddy_net")
    for ident in (network or {}).get("Containers", {}):
        item = inspect("container", ident)
        aliases = item["NetworkSettings"]["Networks"]["caddy_net"].get("Aliases") or []
        if {"mayortech-identity-guard", "mayortech-private-app"}.intersection(aliases):
            aliases_safe = aliases_safe and (item["Config"].get("Labels") or {}).get("io.kerforge.application") == C.PROJECT
    checks["aliases_owned"] = aliases_safe
    for domain in (C.APP_DOMAIN, C.IDP_DOMAIN):
        checks["dns_"+domain] = all(ipaddress.ip_address(x[4][0]).is_global for x in socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM))
    for volume in ("mayortech-private-data", "mayortech-private-postgres", "mayortech-private-identity"):
        item = inspect("volume", volume)
        checks["owned_"+volume] = item is None or (item.get("Labels") or {}).get("io.kerforge.application") == C.PROJECT
    for name in ("mayortech-private-database", "mayortech-private-identity-front"):
        item = inspect("network", name)
        checks["owned_"+name] = item is None or (item.get("Labels") or {}).get("io.kerforge.application") == C.PROJECT
    smtp = C.BASE / "private/resend-smtp-key"
    checks["smtp_private_file"] = smtp.is_file() and not smtp.is_symlink() and stat.S_IMODE(smtp.stat().st_mode) == 0o600 and smtp.stat().st_uid == uid
    ident, _ = caddy()
    # Inspect only the active logger configuration through the local admin API;
    # never print a configuration, route, cookie or request URL.
    logging = run(["docker", "exec", ident, "wget", "-q", "-O", "-", "http://127.0.0.1:2019/config/logging"], timeout=15)
    checks["caddy_runtime_logging_no_debug"] = logging_is_safe(json.loads(logging.stdout))
    return {"project": C.PROJECT, "read_only": True, "checks": checks, "passed": all(checks.values()), "secret_values_included": False}


def compose(*args, required=True):
    return run(["docker", "compose", "--project-name", C.PROJECT, "--project-directory", str(C.BASE), "-f", str(C.BASE/"compose.yaml"), *args], required=required, timeout=180)


def private_material(files, digest, uid, proxy_cidr, caddy_ip):
    private = C.BASE / "private"
    if private.resolve() != private or stat.S_IMODE(private.stat().st_mode) != 0o700 or private.stat().st_uid != uid:
        raise OperationError("private_directory_permissions")
    path = C.BASE / "private/bootstrap-material.json"
    if path.exists():
        if path.is_symlink() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise OperationError("material_permissions")
        value = json.loads(path.read_text())
        if value["source_digest"] != digest:
            raise OperationError("existing_private_candidate_changed_requires_review")
    else:
        value = {"source_digest": digest, "postgres_password": secrets.token_urlsafe(48), "client_secret": secrets.token_urlsafe(48),
                 "vault_key": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(), "admin_client_id": "mayortech-bootstrap-operator", "admin_client_secret": secrets.token_urlsafe(48)}
        write_new(path, json.dumps(value).encode(), uid)
    def keep(name, content, owner=uid):
        target = private/name
        if target.exists():
            if target.is_symlink() or stat.S_IMODE(target.stat().st_mode) != 0o600 or target.stat().st_uid != owner or target.read_bytes() != content:
                raise OperationError("existing_private_material_changed_requires_review")
        else:
            write_new(target, content, owner)
    # Only our dedicated Resend credential is read; it never leaves this process.
    smtp = (private / "resend-smtp-key").read_text().strip()
    if not smtp or len(smtp) > 1000 or "\n" in smtp:
        raise OperationError("smtp_material_invalid")
    keep("mayortech-realm.json", json.dumps(C.realm(json.loads(files["realm-template.json"]), value["client_secret"], smtp), ensure_ascii=False).encode(), 1000)
    app = C.app_environment(value["client_secret"], caddy_ip)
    keep("app.env", ("\n".join(k+"="+v for k,v in app.items())+"\n").encode())
    keep("connector-vault.keys", value["vault_key"].encode(), 10001)
    keep("postgres.env", ("POSTGRES_DB=keycloak\nPOSTGRES_USER=keycloak\nPOSTGRES_PASSWORD="+value["postgres_password"]+"\n").encode())
    idp = {"KC_DB": "postgres", "KC_DB_URL": "jdbc:postgresql://postgres/keycloak", "KC_DB_USERNAME": "keycloak", "KC_DB_PASSWORD": value["postgres_password"],
           "KC_HOSTNAME": "https://"+C.IDP_DOMAIN, "KC_HTTP_ENABLED": "true", "KC_PROXY_HEADERS": "xforwarded", "KC_PROXY_TRUSTED_ADDRESSES": proxy_cidr,
           "KC_HEALTH_ENABLED": "true", "KC_METRICS_ENABLED": "false", "KC_CACHE": "local", "KC_DB_POOL_INITIAL_SIZE": "1", "KC_DB_POOL_MIN_SIZE": "1", "KC_DB_POOL_MAX_SIZE": "8",
           "JAVA_OPTS_KC_HEAP": "-XX:MaxRAMPercentage=60 -XX:InitialRAMPercentage=25", "KC_TLS_HOSTNAME_VERIFIER": "DEFAULT",
           "KC_BOOTSTRAP_ADMIN_CLIENT_ID": value["admin_client_id"], "KC_BOOTSTRAP_ADMIN_CLIENT_SECRET": value["admin_client_secret"]}
    keep("keycloak.env", ("\n".join(k+"="+v for k,v in idp.items())+"\n").encode())


def health():
    result = {}
    for name in ("postgres", "keycloak", "identity_guard", "app", "worker"):
        try:
            _, item = service(name)
            result[name] = item["State"].get("Health", {}).get("Status") == "healthy"
        except OperationError:
            result[name] = False
    return result


def probes():
    # First-party API probes use loopback. auth/start still performs real HTTPS
    # discovery through the unchanged production OIDC client, without UA changes.
    app, _ = service("app")
    script = """import json,urllib.request,urllib.error,urllib.parse
origin='https://espace.kerforge.com'
def read(path,data=None):
 request=urllib.request.Request('http://127.0.0.1:8765'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-Requested-With':'Travaux','Origin':origin,'Host':'espace.kerforge.com'})
 return json.load(urllib.request.urlopen(request,timeout=20))
s=read('/api/v1/session');o=read('/api/v1/auth/options');a=read('/api/v1/auth/start',{});u=urllib.parse.urlsplit(a['authorization_url']);q=urllib.parse.parse_qs(u.query)
try:read('/api/v1/projects');denied=False
except urllib.error.HTTPError as error:denied=error.code==401
from travaux.config import Settings
from travaux.repository import Repository
from travaux.oidc import OIDCService
repo=Repository(Settings.from_env().db_path);identity=OIDCService(repo,Settings.from_env(),None,None)
d=identity.metadata();identity.close();repo.close()
print(json.dumps({'sso_available':s['auth']['sso_available'],'signup_available':s['auth']['signup_available'],'recovery_available':o.get('recovery_available',False),'anonymous_projects_denied':denied,'discovery':d['issuer']=='https://identite.kerforge.com/realms/mayortech','pkce_authorize':u.scheme=='https' and u.hostname=='identite.kerforge.com' and q.get('code_challenge_method')==['S256']}))
"""
    return json.loads(run(["docker", "exec", "-i", app, "python", "-"], data=script.encode(), timeout=100).stdout)


def wait_for_tls():
    # ACME can finish after container health becomes ready. Only anonymous GET
    # requests are retried, with strict certificate validation and a deadline.
    app, _ = service("app")
    script = """import time
from travaux.config import Settings
from travaux.repository import Repository
from travaux.oidc import OIDCService
settings=Settings.from_env();repo=Repository(settings.db_path);identity=OIDCService(repo,settings,None,None)
deadline=time.monotonic()+80
while True:
 try:
  d=identity.metadata()
  assert d['issuer']=='https://identite.kerforge.com/realms/mayortech'
  identity.close();repo.close();print('ready');break
 except Exception:
  if time.monotonic()>=deadline:raise SystemExit(1)
  time.sleep(3)
"""
    run(["docker", "exec", "-i", app, "python", "-"], data=script.encode(), timeout=105)


def backup():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = C.BASE / "backups" / stamp
    folder.mkdir(parents=True, mode=0o700)
    pg, _ = service("postgres")
    dump = run(["docker", "exec", pg, "pg_dump", "-Fc", "-U", "keycloak", "keycloak"], timeout=120).stdout
    run(["docker", "exec", "-i", pg, "pg_restore", "--list"], data=dump, timeout=30)
    write_new(folder/"identity.dump", dump)
    app, _ = service("app")
    code = "import sqlite3,sys; s=sqlite3.connect('file:/data/mayortech-test.sqlite3?mode=ro',uri=True); d=sqlite3.connect(':memory:'); s.backup(d); assert d.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; sys.stdout.buffer.write(d.serialize()); d.close();s.close()"
    write_new(folder/"workspace.sqlite3", run(["docker", "exec", app, "python", "-c", code], timeout=60).stdout)
    return {"path": str(folder), "postgres_dump_validated": True, "sqlite_integrity_checked": True, "encrypted": False, "offsite": False}


def apply(bundle):
    if fcntl is None:
        raise OperationError("linux_operator_required")
    files, digest = validate_bundle(bundle)
    admission = preflight()
    if not admission["passed"]:
        raise OperationError("capacity_images_ownership_or_dns_preflight_refused")
    uid = int(os.environ.get("SUDO_UID", os.getuid()))
    lock = os.open(C.BASE/".operator.lock", os.O_CREAT | os.O_RDWR, 0o600)
    compose_started, route_created = False, False
    stage = "candidate_validation"
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status_file = C.BASE/"status.json"
        if status_file.exists():
            previous = json.loads(status_file.read_text())
            if previous.get("source_digest") != digest:
                raise OperationError("reviewed_existing_site_update_required")
            return {**previous, "idempotent": True, "health": health(), "checks": probes()}
        if ROUTE.exists():
            raise OperationError("route_collision")
        for name in ("data", "postgres", "identity"):
            if inspect("volume", "mayortech-private-"+name) is not None and not (C.BASE/"private/bootstrap-material.json").exists():
                raise OperationError("existing_volume_without_secret_state")
        caddy_id, _ = caddy()
        run(["docker", "exec", "-i", caddy_id, "caddy", "adapt", "--adapter", "caddyfile", "--config", "-"], data=files["routes.caddy"], timeout=30)
        front = inspect("network", "mayortech-private-identity-front")
        if front is None:
            run(["docker", "network", "create", "--label", "io.kerforge.application="+C.PROJECT,
                 "--label", "com.docker.compose.project="+C.PROJECT, "--label", "com.docker.compose.network=identity_front", "mayortech-private-identity-front"])
            front = inspect("network", "mayortech-private-identity-front")
        proxy_cidr = front["IPAM"]["Config"][0]["Subnet"]
        if not ipaddress.ip_network(proxy_cidr).is_private:
            raise OperationError("proxy_network_not_private")
        ident, caddy_ip = caddy()
        private_material(files, digest, uid, proxy_cidr, caddy_ip)
        prior_peers = peers_digest()
        for name, content in files.items():
            if name in {"realm-template.json", "routes.caddy", "identity-nginx.conf"}:
                continue
            target = C.BASE/name
            if target.exists():
                if target.is_symlink() or target.read_bytes() != content:
                    raise OperationError("candidate_file_collision")
            else:
                write_new(target, content, uid)
            os.chmod(target, 0o644)
        nginx = files["identity-nginx.conf"].decode().replace("__CADDY_TRUSTED_IP__", caddy_ip).replace("__KEYCLOAK_UPSTREAM__", "mayortech-keycloak:8080")
        rendered = C.BASE/"identity-nginx.rendered.conf"
        if rendered.exists() and rendered.read_text() != nginx:
            raise OperationError("guard_configuration_changed_requires_review")
        if not rendered.exists():
            write_new(rendered, nginx.encode(), uid)
        os.chmod(rendered, 0o644)
        # Static compose validation never prints its resolved secret environment.
        stage = "compose_validation"
        compose("config", "--quiet")
        compose_started = True
        stage = "compose_start"
        compose("up", "-d", "--pull", "never")
        route = files["routes.caddy"]
        write_new(ROUTE, route, uid)
        route_created = True
        if prior_peers != peers_digest():
            raise OperationError("concurrent_caddy_change")
        stage = "caddy_validation"
        run(["docker", "exec", ident, "caddy", "validate", "--config", "/etc/caddy/Caddyfile"])
        stage = "caddy_reload"
        run(["docker", "exec", ident, "caddy", "reload", "--config", "/etc/caddy/Caddyfile", "--force"])
        stage = "health_readiness"
        for _ in range(90):
            states = health()
            if all(states.values()):
                break
            time.sleep(5)
        else:
            raise OperationError("service_health_timeout")
        stage = "tls_readiness"
        wait_for_tls()
        stage = "application_probes"
        checks = probes()
        if not all(checks.values()):
            raise OperationError("public_identity_probe_failed")
        stage = "initial_backup"
        result = {"project": C.PROJECT, "runtime": "staging-fictional", "source_digest": digest,
                  "urls": {"app": "https://"+C.APP_DOMAIN, "identity": "https://"+C.IDP_DOMAIN}, "issuer": C.ISSUER,
                  "health": states, "checks": checks, "routes_applied": True, "mail_sent": False, "secret_values_included": False,
                  "probe_transport": {"application_api": "loopback-host-origin", "identity": "production_oidc_httpx_https", "user_agent_overridden": False, "public_browser_pending": True},
                  "initial_backup": backup()}
        write_new(status_file, json.dumps(result).encode(), uid)
        return result
    except Exception as error:
        if route_created and ROUTE.exists() and ROUTE.read_bytes() == files.get("routes.caddy"):
            ROUTE.unlink()
            try:
                ident, _ = caddy()
                run(["docker", "exec", ident, "caddy", "validate", "--config", "/etc/caddy/Caddyfile"])
                run(["docker", "exec", ident, "caddy", "reload", "--config", "/etc/caddy/Caddyfile", "--force"])
            except Exception:
                pass
        if compose_started:
            compose("stop", required=False)
        if isinstance(error, OperationError) and str(error) == "operator_command_failed":
            raise OperationError(stage+"_failed") from None
        raise
    finally:
        os.close(lock)
