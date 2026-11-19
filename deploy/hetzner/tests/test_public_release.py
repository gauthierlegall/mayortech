"""Closed artifacts and anonymous public release contract, without a remote deployment."""
import io
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace
import urllib.error
import urllib.parse
import urllib.request

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import deploy
import remote
from test_deploy import project


RESOURCES = {
    "web/vendor/nodemailer-addressparser.js",
    "web/vendor/NODEMAILER-LICENSE.txt",
    "web/vendor/NODEMAILER-NOTICE.md",
    "web/vendor/NODEMAILER-UPSTREAM.json",
    "src/travaux/vendor/casbin_domains/rbac_with_domains_model.conf",
    "src/travaux/vendor/casbin_domains/LICENSE",
    "src/travaux/vendor/casbin_domains/UPSTREAM.json",
}
PUBLIC = {"mode": "public_demo", "db_path": "/data/public-demo.sqlite3", "tenant_id": "public-demo-travaux"}
LEGACY = {"mode": "staging", "db_path": "/data/travaux.sqlite3", "tenant_id": "staging-travaux-fictif"}
RELEASE = "20261115T110000Z-ab12ce"


def test_public_compose_has_separate_database_and_no_password_requirement():
    compose = (Path(__file__).resolve().parents[1] / "compose.yaml").read_text()
    assert "TRAVAUX_MODE: public_demo" in compose
    assert "TRAVAUX_DB: /data/public-demo.sqlite3" in compose
    assert "TRAVAUX_TENANT: public-demo-travaux" in compose
    assert 'TRAVAUX_PASSWORD_HASH: ""' in compose
    assert "TRAVAUX_PASSWORD_HASH:?" not in compose
    assert "<<: *runtime" in compose.split("  worker:\n", 1)[1]


def test_nested_runtime_reuse_is_complete_but_not_a_vendor_wildcard(tmp_path):
    root = project(tmp_path)
    for name in RESOURCES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("required resource")
    for name in ["web/vendor/private.js", "web/vendor/credentials.json", "src/travaux/vendor/casbin_domains/policies.csv"]:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("NEVER_SHIP")
    items = deploy.inventory(root)
    assert RESOURCES.issubset(items)
    assert RESOURCES.issubset(common.REQUIRED)
    assert all("NEVER_SHIP" not in (root / name).read_text() for name in items)


def test_package_carries_explicit_public_contract(tmp_path):
    root = project(tmp_path / "source")
    for name in RESOURCES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("resource")
    items = deploy.inventory(root)
    manifest = deploy.package(root, tmp_path / "release.tgz", RELEASE,
                              deploy.make_gate(items, python=True, frontend=True, native=True))
    assert manifest["runtime"] == PUBLIC
    assert common.verify_archive(tmp_path / "release.tgz")["runtime"] == PUBLIC


def test_runtime_contract_supports_legacy_rollback_and_rejects_relabelled_private_database(tmp_path, monkeypatch):
    release = tmp_path / "releases" / RELEASE
    release.mkdir(parents=True)
    manifest = release / "release-manifest.json"
    monkeypatch.setattr(remote, "BASE", tmp_path)
    manifest.write_text(json.dumps({"version": "0.3.0"}))
    assert remote.release_runtime(RELEASE) == LEGACY
    manifest.write_text(json.dumps({"version": "0.4.0", "runtime": PUBLIC}))
    assert remote.release_runtime(RELEASE) == PUBLIC
    manifest.write_text(json.dumps({"version": "0.4.0", "runtime": PUBLIC | {"db_path": LEGACY["db_path"]}}))
    with pytest.raises(common.DeploymentError):
        remote.release_runtime(RELEASE)


def test_only_explicit_separate_public_database_bypasses_schema_update_guard():
    assert remote.separate_public_database_transition(LEGACY, PUBLIC)
    assert not remote.separate_public_database_transition(PUBLIC, PUBLIC)
    assert not remote.separate_public_database_transition(LEGACY, LEGACY)
    assert not remote.separate_public_database_transition(LEGACY, PUBLIC | {"db_path": LEGACY["db_path"]})


def test_archive_cannot_relabel_the_private_database_as_public(tmp_path):
    root = project(tmp_path / "source")
    items = deploy.inventory(root)
    archive = tmp_path / "ok.tgz"
    deploy.package(root, archive, RELEASE,
                   deploy.make_gate(items, python=True, frontend=True, native=True))
    changed = tmp_path / "changed.tar"
    with tarfile.open(archive) as source, tarfile.open(changed, "w") as output:
        for item in source:
            data = source.extractfile(item).read()
            if item.name == "release-manifest.json":
                manifest = json.loads(data)
                manifest["runtime"]["db_path"] = LEGACY["db_path"]
                data = json.dumps(manifest).encode()
                item.size = len(data)
            output.addfile(item, io.BytesIO(data))
    with pytest.raises(common.DeploymentError):
        common.verify_archive(changed)


@pytest.mark.parametrize("old_runtime", [LEGACY, PUBLIC])
def test_actual_update_guard_and_backup_preserve_the_previous_database(tmp_path, monkeypatch, old_runtime):
    previous_id = "20261114T180000Z-ab12cd"
    folder = tmp_path / "releases" / previous_id
    folder.mkdir(parents=True)
    (folder / "release-manifest.json").write_text(json.dumps({
        "version": "0.3.0" if old_runtime == LEGACY else "0.4.0",
        "runtime": old_runtime,
        "files": {"src/travaux/repository.py": "old-schema"},
    }))
    route = tmp_path / "route.caddy"
    route.write_text("our previous route")
    previous = {"release": previous_id, "route_hash": common.sha256(route.read_bytes())}
    monkeypatch.setattr(remote, "BASE", tmp_path)
    monkeypatch.setattr(remote, "ROUTE", route)
    monkeypatch.setattr(remote, "current_state", lambda: previous)
    monkeypatch.setattr(remote, "prepare_base", lambda: None)
    monkeypatch.setattr(common, "extract_verified", lambda *args: None)
    monkeypatch.setattr(remote, "caddy_id", lambda: "caddy")
    monkeypatch.setattr(remote, "other_caddy_fingerprint", lambda: "unchanged")
    monkeypatch.setattr(remote, "wait_healthy", lambda *args: None)
    monkeypatch.setattr(remote, "auth_probe", lambda *args: None)
    monkeypatch.setattr(common, "activate_route", lambda *args, **kwargs: None)
    commands, calls = [], []
    def command(args, **kwargs):
        commands.append(args)
        return SimpleNamespace(returncode=1 if args[:3] == ["docker", "image", "inspect"] else 0)
    monkeypatch.setattr(remote, "command", command)
    monkeypatch.setattr(remote, "compose", lambda *args, **kwargs: calls.append(args))
    manifest = {"files": {"src/travaux/repository.py": "new-schema"}, "runtime": PUBLIC}
    if old_runtime == PUBLIC:
        with pytest.raises(common.DeploymentError, match="schema_review_required_before_update"):
            remote.apply_locked(tmp_path / "release.tar.gz", manifest, RELEASE)
        assert commands == calls == []
    else:
        result = remote.apply_locked(tmp_path / "release.tar.gz", manifest, RELEASE)
        assert result["runtime"] == PUBLIC
        backup = calls[0]
        assert backup[:6] == (previous_id, "exec", "-T", "app", "python", "-c")
        assert "file:/data/travaux.sqlite3?mode=ro" in backup[-1]
        assert "/data/public-demo.sqlite3" not in backup[-1]


@pytest.mark.parametrize("mode", ["staging", "public_demo"])
def test_auth_probe_matches_the_stored_release_runtime(monkeypatch, mode):
    calls = []
    monkeypatch.setattr(remote, "release_runtime", lambda release: PUBLIC if mode == "public_demo" else LEGACY)
    monkeypatch.setattr(remote, "private_auth_probe", lambda release: calls.append("private"))
    monkeypatch.setattr(remote, "public_auth_probe", lambda release: calls.append("public"))
    remote.auth_probe(RELEASE)
    assert calls == ["public" if mode == "public_demo" else "private"]


def test_actual_public_probe_needs_no_password_and_checks_import_refusal(tmp_path, monkeypatch):
    from travaux.api import create_app
    from travaux.config import Settings

    calls = []
    monkeypatch.setattr(remote, "compose", lambda release, *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(remote, "read_json", lambda *args: pytest.fail("Public probe must not read private access material"))
    remote.public_auth_probe(RELEASE)
    assert len(calls) == 1 and not calls[0][1].get("stdin_text")
    code = calls[0][0][-1]
    for key in list(__import__("os").environ):
        if key.startswith(("TRAVAUX_MISTRAL_", "TRAVAUX_EWS_", "TRAVAUX_EXCHANGE_", "TRAVAUX_APPFLOWY_")):
            monkeypatch.delenv(key)
    settings = Settings(mode="public_demo", db_path=tmp_path / "public-demo.sqlite3",
                        tenant_id=PUBLIC["tenant_id"], public_origin="https://" + common.RUNTIME_DOMAIN,
                        allowed_hosts=(common.RUNTIME_DOMAIN,))
    for key, value in {"TRAVAUX_MODE": "public_demo", "TRAVAUX_DB": PUBLIC["db_path"],
                       "TRAVAUX_TENANT": PUBLIC["tenant_id"], "TRAVAUX_LLM": "demo",
                       "TRAVAUX_LLM_EGRESS_APPROVED": "false"}.items():
        monkeypatch.setenv(key, value)
    requests = []
    with TestClient(create_app(settings), base_url="https://" + common.RUNTIME_DOMAIN) as client:
        def urlopen(request, timeout=None):
            method = request.get_method() if isinstance(request, urllib.request.Request) else "GET"
            url = request.full_url if isinstance(request, urllib.request.Request) else request
            path = urllib.parse.urlsplit(url).path
            headers = dict(request.header_items()) if isinstance(request, urllib.request.Request) else {}
            content = request.data if isinstance(request, urllib.request.Request) else None
            response = client.request(method, path, headers=headers, content=content)
            requests.append((method, path, response.status_code))
            if response.status_code >= 400:
                raise urllib.error.HTTPError(url, response.status_code, "probe response", response.headers, None)
            result = io.BytesIO(response.content)
            result.headers = response.headers
            return result
        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
        exec(code, {})
    assert ("GET", "/api/v1/projects", 200) in requests
    assert ("POST", "/api/v1/imports/eml", 403) in requests
    assert not any(path == "/api/v1/session" and method == "POST" for method, path, _ in requests)
