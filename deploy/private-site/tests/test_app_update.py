import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location("private_app_update", HERE / "app_update.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def manifest(release="20261117T221755Z-6082cd"):
    m = module()
    files = {name: "a" * 64 for name in m.PROTECTED}
    files["src/travaux/oidc.py"] = "b" * 64
    digest = m.inventory_digest(files)
    return {
        "app": "travaux-mairie", "version": "0.8.1", "release": release,
        "runtime": m.PUBLIC_RUNTIME, "files": files,
        "gate": {"source_digest": digest, "checks": dict.fromkeys(("python", "frontend", "native"), True)},
    }


def test_only_the_app_anchor_image_can_change():
    m = module()
    old = "travaux-mairie:0.8.1-20261117T221755Z-6082cd"
    new = "travaux-mairie:0.8.1-20261118T010001Z-abcdef"
    template = (HERE / "compose.yaml").read_bytes()
    result = m.updated_compose(template, template, old, new)
    assert result.replace(new.encode(), old.encode()) == template
    for bad in (b"\n# foreign", b"\nservices: {}"):
        with pytest.raises(m.UpdateError, match="compose_contract_changed"):
            m.updated_compose(template + bad, template, old, new)
    with pytest.raises(m.UpdateError):
        m.updated_compose(template, template, old, "nginx:latest")


@pytest.mark.parametrize("name", [
    "src/travaux/repository.py", "src/travaux/workspace.py", "src/travaux/auth.py",
    "src/travaux/jobs.py", "src/travaux/governance.py", "Dockerfile", "pyproject.toml", "uv.lock",
])
def test_protected_schema_or_dependency_change_is_refused(name):
    m = module()
    old, new = manifest(), manifest("20261118T010001Z-abcdef")
    new["files"][name] = "c" * 64
    new["gate"]["source_digest"] = m.inventory_digest(new["files"])
    with pytest.raises(m.UpdateError, match="protected_schema_or_dependency_changed"):
        m.verify_manifests(old, new)


def test_unprotected_oidc_fix_requires_exact_manifest_gate():
    m = module()
    old, new = manifest(), manifest("20261118T010001Z-abcdef")
    new["files"]["src/travaux/oidc.py"] = "c" * 64
    with pytest.raises(m.UpdateError, match="public_verification_gate"):
        m.verify_manifests(old, new)
    new["gate"]["source_digest"] = m.inventory_digest(new["files"])
    assert m.verify_manifests(old, new) == new["gate"]["source_digest"]
    new["runtime"]["mode"] = "staging"
    with pytest.raises(m.UpdateError, match="public_manifest_contract"):
        m.verify_manifests(old, new)


def test_cas_refuses_foreign_or_symlink_without_overwrite(tmp_path):
    m = module()
    path = tmp_path / "compose.yaml"
    path.write_bytes(b"foreign")
    with pytest.raises(m.UpdateError, match="concurrent_file_change"):
        m.atomic_cas(path, "a" * 64, b"new", uid=None)
    assert path.read_bytes() == b"foreign"
    assert not list(tmp_path.glob("*.pending-*"))
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    m.atomic_cas(path, expected, b"next", uid=None)
    assert path.read_bytes() == b"next"


def test_invalid_tags_and_review_identifiers_never_execute_commands():
    m = module()
    for tag in ("latest", "travaux-mairie:0.8.2-20261118T010001Z-abcdef", "x;docker stop app"):
        with pytest.raises(m.UpdateError):
            m.image_release(tag)
    assert m.image_release("travaux-mairie:0.8.1-20261118T010001Z-abcdef") == "20261118T010001Z-abcdef"
    assert json.loads(json.dumps(manifest()))["gate"]["checks"]["python"]


@pytest.fixture
def update_run(tmp_path, monkeypatch):
    """Drive the real CAS/update procedure; only Docker and the backup boundary are simulated."""
    m = module()
    old_image = "travaux-mairie:0.8.1-20261117T221755Z-6082cd"
    new_image = "travaux-mairie:0.8.1-20261118T010001Z-abcdef"
    current = (HERE / "compose.yaml").read_bytes()
    replacement = m.updated_compose(current, current, old_image, new_image)
    status = {"source_digest": "initial-identity-candidate"}
    status_bytes = json.dumps(status).encode()
    (tmp_path / "compose.yaml").write_bytes(current)
    (tmp_path / "status.json").write_bytes(status_bytes)
    events = []
    protected = {"idp": "unchanged", "caddy": "unchanged", "secrets": "unchanged"}
    mutable = {"phase": "old", "old_healthy": True, "new_healthy": True, "config_fails": False}
    state = {"uid": None, "status": status, "status_bytes": status_bytes,
             "compose": current, "new_compose": replacement, "protected": dict(protected),
             "source_digest": "new-public-release", "old_image": old_image, "image": new_image,
             "old_image_id": "old-binary", "image_id": "new-binary", "release": m.image_release(new_image),
             "review_id": "local-source-review"}
    class Lock:
        LOCK_EX = 1
        LOCK_NB = 2
        @staticmethod
        def flock(*args):
            events.append("lock")

    def compose(*args, **kwargs):
        events.append(("compose", args))
        if args[0] == "config" and mutable["config_fails"]:
            raise RuntimeError("private command output must not be reflected")
        if args[0] == "up":
            actual = (tmp_path / "compose.yaml").read_bytes()
            mutable["phase"] = "new" if actual == replacement else "old"

    def health():
        events.append(("health", mutable["phase"]))
        good = mutable["new_healthy"] if mutable["phase"] == "new" else mutable["old_healthy"]
        return dict.fromkeys(("postgres", "keycloak", "identity_guard", "app", "worker"), good)

    def service(name):
        assert name in {"app", "worker"}
        return name, {"Image": "new-binary" if mutable["phase"] == "new" else "old-binary"}

    def write_new(path, data, uid=None):
        with path.open("xb") as stream:
            stream.write(data)

    def backup(runtime, folder, uid):
        events.append("backup")
        return {"path": str(folder / "workspace.sqlite3"), "integrity_checked": True, "restored": False}

    runtime = SimpleNamespace(C=SimpleNamespace(BASE=tmp_path), fcntl=Lock,
                              verify_base=lambda **kw: events.append("verify-base"),
                              compose=compose, health=health, service=service,
                              probes=lambda: {"real_oidc_client": True}, write_new=write_new)
    monkeypatch.setattr(m, "inspect_state", lambda payload, runtime: state)
    monkeypatch.setattr(m, "immutable_state", lambda runtime: dict(protected))
    monkeypatch.setattr(m, "sqlite_backup", backup)
    monkeypatch.setattr(m.time, "sleep", lambda seconds: None)
    payload = {"expected_compose_sha256": m.digest(current), "expected_status_sha256": m.digest(status_bytes)}
    return SimpleNamespace(m=m, runtime=runtime, payload=payload, state=state, events=events,
                           mutable=mutable, protected=protected, folder=tmp_path)


def test_application_update_backs_up_then_changes_only_two_services(update_run):
    qa = update_run
    receipt = qa.m.apply(qa.payload, qa.runtime)
    assert receipt["applied"] is True
    commands = [event[1] for event in qa.events if isinstance(event, tuple) and event[0] == "compose"]
    assert commands == [("config", "--quiet"), ("up", "-d", "--no-deps", "--pull", "never", "app", "worker")]
    assert qa.events.index("backup") < qa.events.index(("compose", commands[0]))
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["new_compose"]
    status = json.loads((qa.folder / "status.json").read_bytes())
    assert status["source_digest"] == "initial-identity-candidate"
    assert status["app_release"]["image"] == qa.state["image"]
    assert qa.protected == {"idp": "unchanged", "caddy": "unchanged", "secrets": "unchanged"}


def test_stale_plan_never_backs_up_or_runs_compose(update_run):
    qa = update_run
    qa.payload["expected_status_sha256"] = "0" * 64
    with pytest.raises(qa.m.UpdateError, match="stale_maintenance_plan"):
        qa.m.apply(qa.payload, qa.runtime)
    assert not any(event == "backup" or isinstance(event, tuple) for event in qa.events)
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]


def test_invalid_compose_restores_file_without_restarting_the_old_services(update_run):
    qa = update_run
    qa.mutable["config_fails"] = True
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_rolled_back"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]
    commands = [event[1] for event in qa.events if isinstance(event, tuple) and event[0] == "compose"]
    assert commands == [("config", "--quiet")]
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_failed_new_health_checks_roll_back_and_confirm_the_old_binary(update_run):
    qa = update_run
    qa.mutable["new_healthy"] = False
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_rolled_back"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]
    assert ("health", "old") in qa.events
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_failed_rollback_health_never_claims_a_successful_rollback(update_run):
    qa = update_run
    qa.mutable["new_healthy"] = qa.mutable["old_healthy"] = False
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_manual_recovery_required"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_concurrent_receipt_change_is_preserved_and_never_relabelled_applied(update_run):
    qa = update_run
    def drift():
        path = next((qa.folder / "app-updates").glob("*/receipt.json"))
        path.write_bytes(b'{"foreign":"preserve this operator note"}')
        return {"real_oidc_client": True}
    qa.runtime.probes = drift
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_rolled_back"):
        qa.m.apply(qa.payload, qa.runtime)
    path = next((qa.folder / "app-updates").glob("*/receipt.json"))
    assert path.read_bytes() == b'{"foreign":"preserve this operator note"}'
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_concurrent_compose_change_is_never_overwritten_or_executed(update_run):
    qa = update_run
    def drift():
        (qa.folder / "compose.yaml").write_bytes(b"name: unrelated-operator-change")
        return {"real_oidc_client": True}
    qa.runtime.probes = drift
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_manual_recovery_required"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "compose.yaml").read_bytes() == b"name: unrelated-operator-change"
    ups = [event for event in qa.events if isinstance(event, tuple) and event[0] == "compose" and event[1][0] == "up"]
    assert len(ups) == 1  # No rollback invokes the unreviewed replacement file.
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_concurrent_status_change_is_preserved_and_requires_manual_reconciliation(update_run):
    qa = update_run
    def drift():
        (qa.folder / "status.json").write_bytes(b'{"foreign":"preserve this status"}')
        return {"real_oidc_client": True}
    qa.runtime.probes = drift
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_manual_recovery_required"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]
    assert (qa.folder / "status.json").read_bytes() == b'{"foreign":"preserve this status"}'


def test_external_identity_or_secret_drift_is_not_hidden_by_application_rollback(update_run):
    qa = update_run
    def drift():
        qa.protected["secrets"] = "foreign-secret-change"
        return {"real_oidc_client": True}
    qa.runtime.probes = drift
    with pytest.raises(qa.m.UpdateError, match="application_update_failed_manual_recovery_required"):
        qa.m.apply(qa.payload, qa.runtime)
    assert qa.protected["secrets"] == "foreign-secret-change"
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]


@pytest.fixture
def private_environment(tmp_path):
    spec = importlib.util.spec_from_file_location("private_update_candidate_fixture", HERE / "candidate.py")
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    private = tmp_path / "private"
    private.mkdir()
    material = {"client_secret": "synthetic-confidential-client-secret"}
    (private / "bootstrap-material.json").write_text(json.dumps(material))
    env = candidate.app_environment(material["client_secret"], "192.0.2.10")
    runtime = SimpleNamespace(C=SimpleNamespace(BASE=tmp_path), caddy=lambda: ("fixture-caddy", "192.0.2.10"))
    def write(values):
        (private / "app.env").write_text("\n".join(name + "=" + value for name, value in values.items()) + "\n")
    write(env)
    return runtime, env, write


def test_environment_requires_the_original_client_secret(private_environment):
    runtime, env, write = private_environment
    m = module()
    m.validate_environment(runtime)
    env["TRAVAUX_OIDC_CLIENT_SECRET"] = "a-different-synthetic-secret"
    write(env)
    with pytest.raises(m.UpdateError, match="private_environment_contract"):
        m.validate_environment(runtime)


@pytest.mark.parametrize("name,value", [
    ("TRAVAUX_TEST_ORGANIZATION_SELF_JOIN", "false"),
    ("TRAVAUX_CONNECTOR_SECRET_KEYS", "unexpected-inline-key"),
    ("TRAVAUX_CONNECTOR_SECRET_KEY", "unexpected-inline-key"),
    ("TRAVAUX_OIDC_ALLOWED_HOSTS", "unreviewed.example.invalid"),
    ("TRAVAUX_OIDC_PRIVATE_HOSTS", "identite.kerforge.com"),
    ("TRAVAUX_OIDC_RESET_URL", "https://other.example.invalid/reset"),
    ("TRAVAUX_OIDC_SIGNUP_URL", "https://other.example.invalid/register"),
    ("SSLKEYLOGFILE", "/tmp/unreviewed-tls-diagnostic"),
    ("TRAVAUX_MISTRAL_KEY", "synthetic-unreviewed-provider-key"),
])
def test_drifted_security_or_real_external_provider_configuration_is_refused(private_environment, name, value):
    runtime, env, write = private_environment
    env[name] = value
    write(env)
    m = module()
    with pytest.raises(m.UpdateError, match="private_environment_contract"):
        m.validate_environment(runtime)


def test_secret_file_metadata_rejects_world_readability_foreign_owner_and_hardlinks():
    m = module()
    safe = SimpleNamespace(st_mode=0o100600, st_uid=10001, st_nlink=1)
    m.validate_secret_metadata(safe, 10001)
    for info in (
        SimpleNamespace(st_mode=0o100644, st_uid=10001, st_nlink=1),
        SimpleNamespace(st_mode=0o100600, st_uid=1000, st_nlink=1),
        SimpleNamespace(st_mode=0o100600, st_uid=10001, st_nlink=2),
        SimpleNamespace(st_mode=0o040600, st_uid=10001, st_nlink=1),
    ):
        with pytest.raises(m.UpdateError, match="private_file_permissions"):
            m.validate_secret_metadata(info, 10001)


@pytest.mark.parametrize("journal", ["DELETE", "WAL"])
def test_native_sqlite_backup_is_a_standalone_file_even_for_a_live_wal_source(tmp_path, monkeypatch, journal):
    m = module()
    source_path = tmp_path / "synthetic-live.sqlite3"
    source = sqlite3.connect(source_path)
    assert source.execute("PRAGMA journal_mode=" + journal).fetchone()[0] == journal.lower()
    source.execute("CREATE TABLE fixture(value TEXT)")
    source.execute("INSERT INTO fixture VALUES('synthetic-regression-only')")
    source.commit()
    readonly = sqlite3.connect(source_path.absolute().as_uri() + "?mode=ro", uri=True)
    memory = sqlite3.connect(":memory:")
    readonly.backup(memory)
    data = memory.serialize()
    output = tmp_path / "owned-backup"
    output.mkdir()
    commands = []
    def run(args, **kwargs):
        commands.append(args)
        assert args[:3] == ["docker", "exec", "synthetic-app"]
        return SimpleNamespace(stdout=data)
    def write_new(path, content, uid):
        assert path.parent == output
        with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
            stream.write(content)
    runtime = SimpleNamespace(service=lambda name: ("synthetic-app", {}), run=run, write_new=write_new)
    if os.name == "nt":
        # Windows does not implement POSIX0600. Only that OS boundary is
        # substituted; real SQLite backup, journaling and file reopening run.
        monkeypatch.setattr(m, "ensure_private_backup", lambda path: None, raising=False)
    try:
        result = m.sqlite_backup(runtime, output, None)
        backup = output / "workspace.sqlite3"
        canonical = backup.read_bytes()
        assert result["sha256"] == m.digest(canonical)
        assert result["integrity_checked"] and result["restored"] is False
        assert canonical[18:20] == bytes((1, 1))
        independent = sqlite3.connect(backup.absolute().as_uri() + "?mode=ro", uri=True)
        try:
            assert independent.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
            assert independent.execute("SELECT value FROM fixture").fetchall() == [("synthetic-regression-only",)]
        finally:
            independent.close()
        assert source.execute("PRAGMA journal_mode").fetchone()[0] == journal.lower()
        assert source.execute("SELECT count(*) FROM fixture").fetchone()[0] == 1
        assert len(commands) == 1
        assert not (output / "workspace.sqlite3-wal").exists()
        assert not (output / "workspace.sqlite3-shm").exists()
    finally:
        readonly.close()
        memory.close()
        source.close()


def test_pre_mutation_snapshot_failure_reports_only_the_fixed_stage(update_run, monkeypatch):
    qa = update_run
    def refuse(*args):
        raise sqlite3.OperationalError("synthetic-private-error-details-must-not-be-printed")
    monkeypatch.setattr(qa.m, "sqlite_backup", refuse)
    with pytest.raises(qa.m.UpdateError, match="application_update_refused_at_sqlite_backup") as error:
        qa.m.apply(qa.payload, qa.runtime)
    assert "synthetic-private" not in str(error.value)
    assert not any(isinstance(event, tuple) and event[0] == "compose" for event in qa.events)
    assert (qa.folder / "compose.yaml").read_bytes() == qa.state["compose"]
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]
