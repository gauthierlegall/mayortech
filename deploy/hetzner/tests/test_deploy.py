import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import deploy
import remote


def project(tmp_path):
    for name in [
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
        *common.RUNTIME_RESOURCES,
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test", encoding="utf-8")
    source_root = Path(__file__).resolve().parents[3]
    for name in common.STORYLINE_RESOURCES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((source_root / name).read_bytes())
    for name in [
        ".env",
        "owner.json",
        ".venv/secrets.py",
        "web/tests/private.js",
        "src/travaux/__pycache__/api.pyc",
        "native-editor/node_modules/private.js",
        "native-editor/dist/editor.js.map",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("NEVER_SHIP", encoding="utf-8")
    return tmp_path


def test_inventory_is_closed_and_excludes_secrets_and_tooling(tmp_path):
    inventory = deploy.inventory(project(tmp_path))
    assert "src/travaux/api.py" in inventory and "native-editor/dist/editor.js" in inventory
    assert all("NEVER_SHIP" not in (tmp_path / name).read_text() for name in inventory)
    assert ".env" not in inventory and not any("node_modules" in n or n.endswith(".map") for n in inventory)


def test_inventory_preserves_runtime_styles_and_upstream_licences(tmp_path):
    root = project(tmp_path)
    resources = [
        "src/travaux/vendor/docs_export.css",
        "src/travaux/vendor/DOCS-LICENSE.txt",
        "src/travaux/vendor/OPENGATE-LICENSE.txt",
        "src/travaux/vendor/UPSTREAM.json",
        "native-editor/dist/vendor-source/theme-1.1.23/LICENSE",
        "native-editor/dist/vendor-source/theme-1.1.23/theme.ts",
    ]
    for name in resources:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("required upstream resource", encoding="utf-8")
    assert set(resources).issubset(deploy.inventory(root))


@pytest.mark.parametrize(
    "name",
    [
        "../owner.json",
        "/etc/passwd",
        "web/../../.env",
        "web/tests/private.js",
        "native-editor/dist/.env",
        "src/travaux/private.key",
        "web/app.js\\..\\owner.json",
    ],
)
def test_untrusted_archive_names_are_rejected(name):
    assert not common.allowed_name(name)


def test_recipe_gate_is_bound_to_current_files(tmp_path):
    root = project(tmp_path)
    items = deploy.inventory(root)
    gate = deploy.make_gate(items, python=True, frontend=True, native=True)
    deploy.validate_gate(gate, items)
    (root / "web/app.js").write_text("changed", encoding="utf-8")
    with pytest.raises(common.DeploymentError):
        deploy.validate_gate(gate, deploy.inventory(root))
    with pytest.raises(common.DeploymentError):
        deploy.make_gate(items, python=True, frontend=False, native=True)


def test_package_contains_only_verified_manifest_and_source(tmp_path):
    root = project(tmp_path / "project")
    items = deploy.inventory(root)
    out = tmp_path / "release.tar.gz"
    gate = deploy.make_gate(items, python=True, frontend=True, native=True)
    deploy.package(root, out, "20261114T180000Z-ab12cd", gate)
    manifest = common.verify_archive(out)
    assert manifest["release"] == "20261114T180000Z-ab12cd"
    with tarfile.open(out) as archive:
        assert set(archive.getnames()) == set(items) | {"release-manifest.json", ".dockerignore"}


def test_extractor_rejects_link_before_writing_any_member(tmp_path):
    archive = tmp_path / "attack.tar"
    with tarfile.open(archive, "w") as out:
        link = tarfile.TarInfo("web/app.js")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        out.addfile(link)
    with pytest.raises(common.DeploymentError):
        common.extract_verified(archive, tmp_path / "target")
    assert not (tmp_path / "target").exists()


def test_archive_tamper_and_duplicate_are_rejected(tmp_path):
    root = project(tmp_path / "project")
    items = deploy.inventory(root)
    archive = tmp_path / "ok.tar.gz"
    deploy.package(
        root,
        archive,
        "20261114T180000Z-ab12cd",
        deploy.make_gate(items, python=True, frontend=True, native=True),
    )
    changed = tmp_path / "changed.tar"
    with tarfile.open(archive) as src, tarfile.open(changed, "w") as out:
        for item in src:
            data = src.extractfile(item).read()
            if item.name == "web/app.js":
                data = b"tampered"
                item.size = len(data)
            out.addfile(item, io.BytesIO(data))
    with pytest.raises(common.DeploymentError):
        common.verify_archive(changed)


def test_dns_is_create_only_even_for_other_record_types():
    assert deploy.dns_plan([])["action"] == "create"
    for kind in ["A", "AAAA", "CNAME", "TXT"]:
        with pytest.raises(common.DeploymentError):
            deploy.dns_plan([{"type": kind, "name": common.DOMAIN}])


def test_failed_caddy_validation_restores_ours_without_touching_others(tmp_path):
    route = tmp_path / "travaux-mairie.caddy"
    route.write_text("old")
    other = tmp_path / "other.caddy"
    other.write_text("unchanged")
    calls = []
    with pytest.raises(common.DeploymentError):
        common.activate_route(
            route,
            "new",
            lambda: False,
            lambda: calls.append("reload"),
            expected_previous_hash=common.sha256(b"old"),
        )
    assert route.read_text() == "old" and other.read_text() == "unchanged" and calls == []


def test_first_invalid_route_is_removed_but_existing_route_never_adopted(tmp_path):
    route = tmp_path / "travaux-mairie.caddy"
    with pytest.raises(common.DeploymentError):
        common.activate_route(route, "new", lambda: False, lambda: True)
    assert not route.exists()
    route.write_text("someone else")
    with pytest.raises(common.DeploymentError):
        common.activate_route(route, "new", lambda: True, lambda: True)
    assert route.read_text() == "someone else"


def test_caddy_failure_does_not_overwrite_a_concurrent_change(tmp_path):
    route = tmp_path / "travaux-mairie.caddy"

    def concurrently_changed():
        route.write_text("external change")
        return False

    with pytest.raises(common.DeploymentError):
        common.activate_route(route, "new", concurrently_changed, lambda: True)
    assert route.read_text() == "external change"


def test_generated_password_hash_matches_application_algorithm():
    password, encoded = deploy.password_material()
    algorithm, salt, digest = encoded.split("$")
    assert len(password) >= 32 and algorithm == "scrypt"
    assert hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex() == digest


def test_route_removal_validation_failure_restores_the_owned_route(tmp_path, monkeypatch):
    route = tmp_path / "travaux-mairie.caddy"
    route.write_text("ours")
    monkeypatch.setattr(remote, "ROUTE", route)
    monkeypatch.setattr(remote, "caddy_valid", lambda container: False)
    monkeypatch.setattr(remote, "caddy_reload", lambda container: True)
    with pytest.raises(common.DeploymentError):
        remote.restore_route(None, common.sha256(b"ours"), "caddy")
    assert route.read_text() == "ours"


def test_failed_route_rollback_keeps_first_application_running(tmp_path, monkeypatch):
    route = tmp_path / "travaux-mairie.caddy"
    route.write_text("ours")
    monkeypatch.setattr(remote, "ROUTE", route)
    monkeypatch.setattr(
        remote,
        "current_state",
        lambda: {
            "release": "20261114T180000Z-ab12cd",
            "route_hash": common.sha256(b"ours"),
            "previous": None,
            "previous_route": None,
        },
    )
    calls = []
    monkeypatch.setattr(remote, "compose", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(remote, "caddy_id", lambda: "caddy")

    def failed(*a, **k):
        raise common.DeploymentError("validation_failed")

    monkeypatch.setattr(remote, "restore_route", failed)
    with pytest.raises(common.DeploymentError):
        remote.rollback_locked()
    assert calls == []


def test_mutation_lock_refuses_a_second_release_and_can_be_reacquired(tmp_path):
    assert callable(getattr(common, "mutation_lock", None))
    with common.mutation_lock(tmp_path):
        with pytest.raises(common.DeploymentError):
            with common.mutation_lock(tmp_path):
                pass
    with common.mutation_lock(tmp_path):
        pass


def test_rollback_uses_the_version_recorded_by_the_previous_release(tmp_path, monkeypatch):
    release = "20261114T180000Z-ab12cd"
    folder = tmp_path / "releases" / release
    folder.mkdir(parents=True)
    (folder / "release-manifest.json").write_text(json.dumps({"version": "0.2.0"}))
    monkeypatch.setattr(remote, "BASE", tmp_path)
    monkeypatch.setattr(common, "VERSION", "0.3.0")
    assert remote.image(release) == "travaux-mairie:0.2.0-" + release


def test_health_gate_requires_both_app_and_worker(monkeypatch):
    calls = []
    checks = []
    monkeypatch.setattr(
        remote,
        "compose",
        lambda release, *args: (calls.append(args), SimpleNamespace(stdout=args[-1] + "-container"))[1],
    )
    monkeypatch.setattr(
        remote,
        "command",
        lambda args, **kwargs: (checks.append(args[-1]), SimpleNamespace(stdout="healthy"))[1],
    )
    remote.wait_healthy("20261114T180000Z-ab12cd")
    assert calls == [("ps", "-q", "app"), ("ps", "-q", "worker")]
    assert checks == ["app-container", "worker-container"]


def test_unhealthy_worker_prevents_publication(monkeypatch):
    monkeypatch.setattr(remote, "compose", lambda release, *args: SimpleNamespace(stdout=args[-1]))
    monkeypatch.setattr(
        remote,
        "command",
        lambda args, **kwargs: SimpleNamespace(stdout="healthy" if args[-1] == "app" else "unhealthy"),
    )
    monkeypatch.setattr(
        remote.time, "sleep", lambda value: pytest.fail("Unhealthy worker must fail immediately")
    )
    with pytest.raises(common.DeploymentError, match="worker_health_check_failed"):
        remote.wait_healthy("20261114T180000Z-ab12cd")


def test_first_rollback_stops_both_services_after_route_removal(tmp_path, monkeypatch):
    route = tmp_path / "travaux-mairie.caddy"
    route.write_text("ours")
    (tmp_path / "current.json").write_text("{}")
    monkeypatch.setattr(remote, "BASE", tmp_path)
    monkeypatch.setattr(remote, "ROUTE", route)
    release = "20261114T180000Z-ab12cd"
    monkeypatch.setattr(
        remote,
        "current_state",
        lambda: {
            "release": release,
            "route_hash": common.sha256(b"ours"),
            "previous": None,
            "previous_route": None,
        },
    )
    events = []
    monkeypatch.setattr(remote, "compose", lambda *args, **kwargs: events.append(args))
    monkeypatch.setattr(remote, "restore_route", lambda *args: events.append("route_removed"))
    monkeypatch.setattr(remote, "caddy_id", lambda: "caddy")
    remote.rollback_locked()
    assert events == ["route_removed", (release, "stop", "app", "worker")]


def test_update_rollback_restores_both_services_before_route(tmp_path, monkeypatch):
    route = tmp_path / "travaux-mairie.caddy"
    route.write_text("ours")
    monkeypatch.setattr(remote, "BASE", tmp_path)
    monkeypatch.setattr(remote, "ROUTE", route)
    previous = {"release": "20261114T180000Z-ab12cd", "route_hash": common.sha256(remote.render_route().encode())}
    monkeypatch.setattr(
        remote,
        "current_state",
        lambda: {
            "release": "20261114T190000Z-ab12ce",
            "route_hash": common.sha256(b"ours"),
            "previous": previous,
            "previous_route": remote.render_route(),
        },
    )
    events = []
    monkeypatch.setattr(remote, "compose", lambda *args, **kwargs: events.append(args))
    monkeypatch.setattr(remote, "wait_healthy", lambda release: events.append("both_healthy"))
    monkeypatch.setattr(remote, "auth_probe", lambda release: events.append("auth_ok"))
    monkeypatch.setattr(remote, "restore_route", lambda *args: events.append("route_restored"))
    monkeypatch.setattr(remote, "caddy_id", lambda: "caddy")
    remote.rollback_locked()
    assert events == [
        (previous["release"], "up", "-d", "--no-deps", "--pull", "never", "app", "worker"),
        "both_healthy",
        "auth_ok",
        "route_restored",
    ]


def test_worker_configuration_is_private_bounded_and_shares_runtime():
    compose = (Path(__file__).resolve().parents[1] / "compose.yaml").read_text()
    assert "  worker:\n" in compose
    worker = compose.split("  worker:\n", 1)[1].split("\nvolumes:", 1)[0]
    assert "<<: *runtime" in worker and "<<: *runtime" in compose.split("  app:\n", 1)[1]
    assert "mem_limit: 256m" in worker and 'cpus: "0.25"' in worker
    assert "network_mode: none" in worker
    assert "aliases:" not in worker and "ports:" not in worker and "expose:" not in worker
    assert '["python", "-m", "travaux", "worker"]' in worker


@pytest.mark.parametrize("worker_present", [True, False])
def test_worker_healthcheck_checks_actual_process_not_its_own_probe(tmp_path, worker_present):
    compose = (Path(__file__).resolve().parents[1] / "compose.yaml").read_text()
    assert "  worker:\n" in compose
    worker = compose.split("  worker:\n", 1)[1].split("\nvolumes:", 1)[0]
    arguments = json.loads(
        next(
            line.strip().removeprefix("test: ")
            for line in worker.splitlines()
            if line.strip().startswith("test: ")
        )
    )
    assert arguments[:3] == ["CMD", "python", "-c"]
    # Relocate /proc only; run the exact production predicate on real fixture files.
    code = arguments[3].replace("Path('/proc')", f"Path({str(tmp_path)!r})")
    import os

    own = tmp_path / str(os.getpid())
    own.mkdir()
    (own / "cmdline").write_bytes(b"python\0-m\0travaux\0worker\0")
    if worker_present:
        process = tmp_path / str(os.getpid() + 1)
        process.mkdir()
        (process / "cmdline").write_bytes(b"python\0-m\0travaux\0worker\0")
    with pytest.raises(SystemExit) as result:
        exec(code, {})
    assert result.value.code == (0 if worker_present else 1)


def test_caddy_route_compresses_only_our_application():
    route = remote.render_route()
    assert "encode zstd gzip" in route
    assert f"reverse_proxy {common.ALIAS}:8765" in route
    assert "worker" not in route


@pytest.mark.parametrize("worker_healthy", [True, False])
def test_apply_manages_both_services_and_never_publishes_failed_health(tmp_path, monkeypatch, worker_healthy):
    monkeypatch.setattr(remote, "BASE", tmp_path)
    monkeypatch.setattr(remote, "ROUTE", tmp_path / "route.caddy")
    monkeypatch.setattr(remote, "current_state", lambda: None)
    monkeypatch.setattr(remote, "prepare_base", lambda: None)
    monkeypatch.setattr(common, "extract_verified", lambda *args: None)
    monkeypatch.setattr(remote, "caddy_id", lambda: "caddy")
    monkeypatch.setattr(remote, "other_caddy_fingerprint", lambda: "unchanged")
    monkeypatch.setattr(
        remote,
        "command",
        lambda args, **kwargs: SimpleNamespace(
            returncode=1 if args[:3] == ["docker", "image", "inspect"] else 0
        ),
    )
    events = []
    monkeypatch.setattr(remote, "compose", lambda *args, **kwargs: events.append(args))

    def health(release):
        events.append("health_checked")
        if not worker_healthy:
            raise common.DeploymentError("worker_health_check_failed")

    monkeypatch.setattr(remote, "wait_healthy", health)
    monkeypatch.setattr(remote, "auth_probe", lambda release: events.append("auth_checked"))
    monkeypatch.setattr(common, "activate_route", lambda *args, **kwargs: events.append("route_published"))
    release = "20261114T190000Z-ab12ce"
    if worker_healthy:
        remote.apply_locked(
            tmp_path / "release.tar.gz", {"files": {}, "runtime": common.PUBLIC_RUNTIME}, release
        )
        assert events == [
            (release, "config", "--quiet"),
            (release, "up", "-d", "--no-deps", "--pull", "never", "app", "worker"),
            "health_checked",
            "auth_checked",
            "route_published",
        ]
    else:
        with pytest.raises(common.DeploymentError):
            remote.apply_locked(
                tmp_path / "release.tar.gz", {"files": {}, "runtime": common.PUBLIC_RUNTIME}, release
            )
        assert "route_published" not in events
        assert events[-1] == (release, "stop", "app", "worker")
