import importlib.util
import base64
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import candidate  # noqa: E402 - This deployment directory is deliberately not an installed package.


def remote():
    path = ROOT / "remote.py"
    assert path.is_file(), "Remote ownership and secret writer are not implemented"
    spec = importlib.util.spec_from_file_location("private_site_remote", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_admission_refuses_low_disk_or_memory():
    assert not candidate.admitted(3*1024**3, 10*1024**3)
    assert not candidate.admitted(10*1024**3, int(2.5*1024**3))
    assert candidate.admitted(7*1024**3, 4*1024**3)


def test_existing_directory_without_marker_is_never_adopted(tmp_path):
    module = remote()
    (tmp_path / "unrelated").write_text("preserved")
    with pytest.raises(module.OperationError):
        module.verify_base(tmp_path, expected_uid=tmp_path.stat().st_uid)
    assert (tmp_path / "unrelated").read_text() == "preserved"


def test_exclusive_secret_write_never_replaces_existing_material(tmp_path):
    module = remote()
    target = tmp_path / "secret"
    module.write_new(target, b"fictitious-first")
    with pytest.raises(FileExistsError):
        module.write_new(target, b"fictitious-second")
    assert target.read_bytes() == b"fictitious-first"


def test_bundle_refuses_any_unlisted_member_before_writing(tmp_path):
    module = remote()
    with pytest.raises(module.OperationError):
        module.validate_bundle({"files": {"../../elsewhere": "AAAA"}, "sha256": ""})
    assert list(tmp_path.iterdir()) == []


def test_app_trusts_only_the_explicit_caddy_address():
    values = candidate.app_environment("fictitious-secret", "172.20.0.8")
    assert values["TRAVAUX_TRUSTED_PROXY_IPS"] == "172.20.0.8"
    assert values["TRAVAUX_TEST_ORGANIZATION_SELF_JOIN"] == "true"
    assert values["TRAVAUX_LLM"] == "demo"
    assert values["TRAVAUX_LLM_EGRESS_APPROVED"] == "false"
    with pytest.raises(ValueError):
        candidate.app_environment("fictitious-secret", "*")


def test_changed_candidate_refusal_never_stops_an_existing_site(tmp_path, monkeypatch):
    module = remote()
    monkeypatch.setattr(candidate, "BASE", tmp_path)
    monkeypatch.setattr(module.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(module, "preflight", lambda: {"passed": True})
    class Lock:
        LOCK_EX = 1
        LOCK_NB = 2
        @staticmethod
        def flock(*args):
            pass
    monkeypatch.setattr(module, "fcntl", Lock)
    commands = []
    monkeypatch.setattr(module, "compose", lambda *args, **kw: commands.append(args))
    files = {name: b"public-fixture" for name in module.FILES}
    digest = hashlib.sha256(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())}, sort_keys=True).encode()).hexdigest()
    (tmp_path/"status.json").write_text(json.dumps({"source_digest": "older-reviewed-site"}))
    payload = {"sha256": digest, "files": {name: base64.b64encode(value).decode() for name, value in files.items()}}
    with pytest.raises(module.OperationError, match="reviewed_existing_site_update_required"):
        module.apply(payload)
    assert commands == []
    assert json.loads((tmp_path/"status.json").read_text())["source_digest"] == "older-reviewed-site"


def test_foreign_compose_collision_never_runs_compose_stop(tmp_path, monkeypatch):
    module = remote()
    monkeypatch.setattr(candidate, "BASE", tmp_path)
    monkeypatch.setattr(module.os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(module, "preflight", lambda: {"passed": True})
    monkeypatch.setattr(module, "ROUTE", tmp_path/"uncreated-route")
    class Lock:
        LOCK_EX = 1
        LOCK_NB = 2
        @staticmethod
        def flock(*args):
            pass
    monkeypatch.setattr(module, "fcntl", Lock)
    monkeypatch.setattr(module, "inspect", lambda kind, name: {"IPAM": {"Config": [{"Subnet": "172.29.0.0/24"}]}} if kind == "network" else None)
    monkeypatch.setattr(module, "private_material", lambda *args: None)
    monkeypatch.setattr(module, "caddy", lambda: ("fictitious-caddy", "172.28.0.2"))
    monkeypatch.setattr(module, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "peers_digest", lambda: {})
    commands = []
    monkeypatch.setattr(module, "compose", lambda *args, **kw: commands.append(args))
    (tmp_path/"compose.yaml").write_text("name: unrelated-existing-application")
    files = {name: b"public-fixture" for name in module.FILES}
    for name in module.FILES-{"compose.yaml", "routes.caddy", "realm-template.json", "identity-nginx.conf"}:
        (tmp_path/name).write_bytes(b"public-fixture")
    digest = hashlib.sha256(json.dumps({name: hashlib.sha256(value).hexdigest() for name, value in sorted(files.items())}, sort_keys=True).encode()).hexdigest()
    payload = {"sha256": digest, "files": {name: base64.b64encode(value).decode() for name, value in files.items()}}
    with pytest.raises(module.OperationError, match="candidate_file_collision"):
        module.apply(payload)
    assert commands == []
    assert (tmp_path/"compose.yaml").read_text() == "name: unrelated-existing-application"


def test_debug_logging_is_refused_for_handled_authentication_errors():
    module = remote()
    assert module.logging_is_safe(None)  # Caddy's absent configuration uses INFO.
    assert module.logging_is_safe({"logs": {"default": {"level": "INFO"}}})
    assert not module.logging_is_safe({"logs": {"default": {"level": "DEBUG"}}})
    assert not module.logging_is_safe({"logs": {"extra": {"level": "debug"}}})
