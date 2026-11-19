"""Closed release format and narrowly scoped Caddy changes; no credentials."""

from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import secrets
import tarfile
from contextlib import contextmanager

APP = "travaux-mairie"
DOMAIN = "demo-travaux.kerforge.com"
RUNTIME_DOMAIN = "travaux.kerforge.com"
BASE = Path("/opt/apps/travaux-mairie")
ROUTE = Path("/opt/caddy/conf.d/travaux-mairie-demo-origin.caddy")
NETWORK = "caddy_net"
VOLUME = "travaux-mairie-data"
ALIAS = "travaux-mairie-app"
VERSION = "0.8.1"
PUBLIC_DEMO_CADDY = r"""demo-travaux.kerforge.com {
    encode zstd gzip
    header X-Robots-Tag "noindex, nofollow, noarchive"
    log {
      output discard
    }
    route {
      request_header -X-MayorTech-Workspace
      request_header -X-MayorTech-Workspace-Token
      @mayortechForeignDemoOrigin {
        header Origin *
        not header Origin https://demo-travaux.kerforge.com
      }
      respond @mayortechForeignDemoOrigin "Origine non autorisée" 403
      @mayortechDemoChatCookie header_regexp mayortechDemoChat Cookie "(^|;[ ]*)travaux_chat_session=([A-Za-z0-9_-]{43})(;|$)"
      handle @mayortechDemoChatCookie {
        route {
          request_header Cookie "travaux_chat_session={re.mayortechDemoChat.2}"
          reverse_proxy travaux-mairie-app:8765 {
            header_up Host travaux.kerforge.com
            header_up X-Forwarded-Host travaux.kerforge.com
            header_up X-Forwarded-Proto https
            header_up X-Forwarded-Port 443
            header_up Origin "^https://demo-travaux[.]kerforge[.]com$" "https://travaux.kerforge.com"
            header_up -X-MayorTech-Workspace
            header_up -X-MayorTech-Workspace-Token
          }
        }
      }
      handle {
        route {
          request_header -Cookie
          reverse_proxy travaux-mairie-app:8765 {
            header_up Host travaux.kerforge.com
            header_up X-Forwarded-Host travaux.kerforge.com
            header_up X-Forwarded-Proto https
            header_up X-Forwarded-Port 443
            header_up Origin "^https://demo-travaux[.]kerforge[.]com$" "https://travaux.kerforge.com"
            header_up -X-MayorTech-Workspace
            header_up -X-MayorTech-Workspace-Token
          }
        }
      }
    }
    handle_errors {
      respond "Démonstration temporairement indisponible" 503
    }
}
"""


def render_public_demo_route() -> str:
    """Canonical active public alias; the protected Travaux route has another owner."""
    return PUBLIC_DEMO_CADDY


PUBLIC_RUNTIME = {
    "mode": "public_demo",
    "db_path": "/data/public-demo.sqlite3",
    "tenant_id": "public-demo-travaux",
}
LEGACY_RUNTIME = {
    "mode": "staging",
    "db_path": "/data/travaux.sqlite3",
    "tenant_id": "staging-travaux-fictif",
}
RUNTIME_RESOURCES = {
    "web/vendor/nodemailer-addressparser.js",
    "web/vendor/NODEMAILER-LICENSE.txt",
    "web/vendor/NODEMAILER-NOTICE.md",
    "web/vendor/NODEMAILER-UPSTREAM.json",
    "src/travaux/vendor/casbin_domains/rbac_with_domains_model.conf",
    "src/travaux/vendor/casbin_domains/LICENSE",
    "src/travaux/vendor/casbin_domains/UPSTREAM.json",
}
STORYLINE_PREFIX = "fixtures/storylines/lovable-v1/"
STORYLINE_MANIFEST_SHA256 = "bbeb8eb65fba682e7bc239bbb70c71dd656da99eff7039332ad77751f04351e9"
STORYLINE_RESOURCES = {
    STORYLINE_PREFIX + "README.md",
    STORYLINE_PREFIX + "storyline.json",
    STORYLINE_PREFIX + "documents/devis-portail-v1.pdf",
    STORYLINE_PREFIX + "documents/devis-portail-v2.pdf",
} | {STORYLINE_PREFIX + f"mail/m{number}.eml" for number in range(1, 11)}
REQUIRED = (
    {
        "Dockerfile",
        "pyproject.toml",
        "uv.lock",
        "src/travaux/api.py",
        "web/index.html",
        "web/app.js",
        "native-editor/dist/editor.js",
        "deploy/hetzner/common.py",
        "deploy/hetzner/remote.py",
        "deploy/hetzner/compose.yaml",
    }
    | RUNTIME_RESOURCES
    | STORYLINE_RESOURCES
)
DOCKERIGNORE = """.env\n.env.*\n**/.env*\n.git\n.venv\n**/node_modules\n**/__pycache__\n**/*.pyc\n**/*.map\n**/*.sqlite*\n**/*.log\nowner.json\nsecrets\ncredentials*\ndata\n"""


class DeploymentError(RuntimeError):
    """Messages deliberately avoid command output and credential contents."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def release_id(value: str) -> str:
    if not re.fullmatch(r"20\d{6}T\d{6}Z-[a-f0-9]{6,12}", value):
        raise DeploymentError("invalid_release_id")
    return value


def allowed_name(name: str) -> bool:
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or path.as_posix() != name:
        return False
    if any(part in {"..", ".", "node_modules", "__pycache__"} or part.startswith(".") for part in path.parts):
        return False
    if path.name.lower() in {"owner.json", "credentials.json", "secrets.json"}:
        return False
    if name in RUNTIME_RESOURCES or name in STORYLINE_RESOURCES:
        return True
    if name in {
        "web/GRIST-LICENSE.txt",
        "web/GRIST-NOTICE.txt",
        "src/travaux/vendor/docs_export.css",
        "src/travaux/vendor/DOCS-LICENSE.txt",
        "src/travaux/vendor/OPENGATE-LICENSE.txt",
        "src/travaux/vendor/UPSTREAM.json",
    }:
        return True
    if name in {"Dockerfile", "pyproject.toml", "uv.lock"}:
        return True
    if name in {"deploy/hetzner/common.py", "deploy/hetzner/remote.py", "deploy/hetzner/compose.yaml"}:
        return True
    if name.startswith("src/travaux/"):
        return path.suffix == ".py"
    if len(path.parts) == 2 and path.parts[0] == "web":
        return path.suffix in {".js", ".css", ".html", ".svg", ".ico"}
    if name.startswith("web/product/"):
        return path.suffix.lower() in {
            ".js",
            ".css",
            ".woff",
            ".woff2",
            ".png",
            ".jpg",
            ".svg",
            ".txt",
            ".json",
        }
    if name.startswith("native-editor/dist/"):
        if name.startswith("native-editor/dist/vendor-source/theme-1.1.23/"):
            return path.suffix.lower() in {".ts", ".json", ".txt", ".md"} or path.name == "LICENSE"
        return path.suffix.lower() in {
            ".js",
            ".css",
            ".wasm",
            ".woff",
            ".woff2",
            ".ttf",
            ".otf",
            ".png",
            ".svg",
            ".webp",
            ".jpg",
            ".jpeg",
            ".ico",
            ".json",
            ".txt",
        }
    return False


def verify_storyline_contents(contents: dict[str, bytes]):
    if not STORYLINE_RESOURCES.issubset(contents):
        raise DeploymentError("storyline_fixture_missing")
    raw = contents[STORYLINE_PREFIX + "storyline.json"]
    if sha256(raw) != STORYLINE_MANIFEST_SHA256:
        raise DeploymentError("storyline_manifest_integrity_failed")
    fixture = json.loads(raw)
    expected_assets = {
        name.removeprefix(STORYLINE_PREFIX)
        for name in STORYLINE_RESOURCES
        if not name.endswith(("storyline.json", "README.md"))
    }
    if set(fixture.get("assets", {})) != expected_assets:
        raise DeploymentError("storyline_asset_inventory_mismatch")
    for name, digest in fixture["assets"].items():
        if sha256(contents[STORYLINE_PREFIX + name]) != digest:
            raise DeploymentError("storyline_original_integrity_failed")


def inventory_digest(files: dict) -> str:
    return sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())


def reviewed_public_schema_upgrade(previous: dict, candidate: dict) -> bool:
    """One audited additive upgrade, never an operator force/skip switch.

    Baseline -> candidate -> baseline was tested against the same public DB:
    all 44 original tables/rows unchanged, only 14 new tables. The old runtime
    remains readable for rollback. Freeze every backend file AND dependencies;
    any further backend edit needs another review. Audit:
    docs/publication-hetzner/REVUE_MIGRATION_PUBLIQUE_2026-11-17.md.
    """
    if previous.get("release") != "20261116T102001Z-234aeb":
        return False
    if previous.get("runtime") != PUBLIC_RUNTIME or candidate.get("runtime") != PUBLIC_RUNTIME:
        return False

    def backend_digest(manifest):
        files = manifest.get("files")
        if not isinstance(files, dict):
            return None
        backend = {name: digest for name, digest in files.items()
                   if name.startswith("src/travaux/") or name in {"Dockerfile", "pyproject.toml", "uv.lock"}}
        return inventory_digest(backend)

    return (
        backend_digest(previous) == "63c42120f748d29602aaffdc931190d3ea4da79a9deba894297531c2a220305c"
        and backend_digest(candidate) == "503b33f8d37f60fd97c41587a8785e9703b356efdd1a7f71d39b02e2d195f378"
    )


def valid_checks(checks) -> bool:
    return (
        isinstance(checks, dict)
        and set(checks) == {"python", "frontend", "native"}
        and all(type(value) is bool and value for value in checks.values())
    )


def password_material() -> tuple[str, str]:
    password = secrets.token_urlsafe(36)
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return password, f"scrypt${salt}${digest}"


def no_symlinks(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise DeploymentError("symlink_not_allowed")


@contextmanager
def mutation_lock(base: Path):
    """Nonblocking process lock; retained inode prevents unlink/reopen races."""
    path = base / ".deployment.lock"
    no_symlinks(path)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    stream = os.fdopen(descriptor, "r+b")
    locked = False
    try:
        if os.name == "nt":
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                locked = True
            except OSError:
                raise DeploymentError("another_deployment_is_running") from None
        else:
            import fcntl

            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                raise DeploymentError("another_deployment_is_running") from None
        yield
    finally:
        if locked:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        stream.close()


def verify_archive(archive: Path) -> dict:
    try:
        with tarfile.open(archive, "r:*") as package:
            members = package.getmembers()
            names = [member.name for member in members]
            if (
                len(names) != len(set(names))
                or len(names) > 5000
                or sum(member.size for member in members) > 200 * 1024**2
            ):
                raise DeploymentError("invalid_archive_inventory")
            if any(
                not member.isfile()
                or member.size < 0
                or (
                    not allowed_name(member.name)
                    and member.name not in {"release-manifest.json", ".dockerignore"}
                )
                for member in members
            ):
                raise DeploymentError("unsafe_archive_member")
            if (
                "release-manifest.json" not in names
                or package.getmember("release-manifest.json").size > 1024**2
            ):
                raise DeploymentError("missing_release_manifest")
            manifest = json.load(package.extractfile("release-manifest.json"))
            release_id(manifest.get("release", ""))
            files = manifest.get("files", {})
            if (
                manifest.get("app") != APP
                or manifest.get("version") != VERSION
                or manifest.get("runtime") != PUBLIC_RUNTIME
                or not isinstance(files, dict)
            ):
                raise DeploymentError("invalid_release_manifest")
            if (
                not REQUIRED.issubset(files)
                or set(names) != set(files) | {"release-manifest.json", ".dockerignore"}
                or not all(allowed_name(name) for name in files)
            ):
                raise DeploymentError("archive_manifest_mismatch")
            gate = manifest.get("gate", {})
            if not valid_checks(gate.get("checks")) or gate.get("source_digest") != inventory_digest(files):
                raise DeploymentError("release_verification_gate_missing_or_stale")
            for name, digest in files.items():
                if (
                    not re.fullmatch(r"[a-f0-9]{64}", str(digest))
                    or sha256(package.extractfile(name).read()) != digest
                ):
                    raise DeploymentError("release_content_hash_mismatch")
            if package.extractfile(".dockerignore").read() != DOCKERIGNORE.encode():
                raise DeploymentError("invalid_dockerignore")
            verify_storyline_contents(
                {name: package.extractfile(name).read() for name in STORYLINE_RESOURCES}
            )
            return manifest
    except DeploymentError:
        raise
    except (OSError, tarfile.TarError, ValueError, TypeError, AttributeError, KeyError):
        raise DeploymentError("unreadable_release_archive") from None


def extract_verified(archive: Path, target: Path) -> dict:
    manifest = verify_archive(archive)
    no_symlinks(target)
    if target.exists():
        raise DeploymentError("release_directory_already_exists")
    target.mkdir(mode=0o700)
    with tarfile.open(archive, "r:*") as package:
        for member in package.getmembers():
            destination = target / member.name
            destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(package.extractfile(member).read())
            destination.chmod(0o644)
    return manifest


def atomic_write(path: Path, data: bytes, mode=0o600) -> None:
    no_symlinks(path)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_create(path: Path, data: bytes, mode=0o644) -> None:
    """Publish a complete file only if the final name remains absent."""
    no_symlinks(path)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        try:
            if os.name == "nt":
                # Windows rename fails if destination exists; unlike POSIX rename.
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        except FileExistsError:
            raise DeploymentError("target_created_concurrently_refuse_overwrite") from None
    finally:
        if temporary.exists():
            temporary.unlink()


def activate_route(path: Path, content: str, validate, reload, *, expected_previous_hash=None) -> dict:
    no_symlinks(path)
    previous = path.read_bytes() if path.exists() else None
    if previous is not None and (
        expected_previous_hash is None or sha256(previous) != expected_previous_hash
    ):
        raise DeploymentError("existing_caddy_route_not_owned_or_changed")
    if previous is None and expected_previous_hash is not None:
        raise DeploymentError("owned_caddy_route_missing")
    current = content.encode()
    if previous is None:
        atomic_create(path, current)
    else:
        atomic_write(path, current, 0o644)
    attempted_reload = False
    try:
        if not validate():
            raise DeploymentError("caddy_validation_failed")
        if sha256(path.read_bytes()) != sha256(current):
            raise DeploymentError("caddy_route_changed_concurrently")
        attempted_reload = True
        if reload() is False:
            raise DeploymentError("caddy_reload_failed")
        return {"previous": previous, "hash": sha256(current)}
    except Exception:
        if path.is_symlink() or not path.exists() or sha256(path.read_bytes()) != sha256(current):
            raise DeploymentError("caddy_route_changed_concurrently_no_restore") from None
        if previous is None:
            path.unlink()
        else:
            atomic_write(path, previous, 0o644)
        if attempted_reload and (not validate() or reload() is False):
            raise DeploymentError("caddy_reload_and_restore_failed") from None
        raise


def remove_route(path: Path, validate, reload, *, expected_hash: str) -> None:
    no_symlinks(path)
    if not path.is_file() or sha256(path.read_bytes()) != expected_hash:
        raise DeploymentError("owned_route_changed_refuse_removal")
    previous = path.read_bytes()
    path.unlink()
    attempted_reload = False
    try:
        if not validate():
            raise DeploymentError("caddy_removal_validation_failed")
        if path.exists() or path.is_symlink():
            raise DeploymentError("caddy_route_created_concurrently")
        attempted_reload = True
        if reload() is False:
            raise DeploymentError("caddy_removal_reload_failed")
    except Exception:
        if path.exists() or path.is_symlink():
            raise DeploymentError("caddy_route_changed_concurrently_no_restore") from None
        atomic_create(path, previous)
        if attempted_reload and (not validate() or reload() is False):
            raise DeploymentError("caddy_removal_and_restore_reload_failed") from None
        raise
