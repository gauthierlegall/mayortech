"""An exact reviewed public upgrade is allowed; a generic override never is."""

from copy import deepcopy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import remote


@pytest.fixture
def review():
    return json.loads((Path(__file__).parent / "fixtures/public-identity-upgrade-20261117.json").read_text())


def test_exact_reviewed_public_upgrade_and_dependencies_are_recognized(review):
    # This is an archived baseline/candidate pair, not a promise that a future
    # working tree has the reviewed backend. Never replace it with inventory().
    assert review["previous"]["release"] == "20261116T102001Z-234aeb"
    assert review["candidate"]["release"] == "20261117T203000Z-001122"
    assert review["previous"]["runtime"] == review["candidate"]["runtime"] == common.PUBLIC_RUNTIME
    assert common.reviewed_public_schema_upgrade(review["previous"], review["candidate"])


def test_any_unreviewed_backend_change_is_still_refused(review):
    for name in review["candidate"]["files"]:
        changed = deepcopy(review["candidate"])
        changed["files"][name] = "0" * 64
        assert not common.reviewed_public_schema_upgrade(review["previous"], changed), name
    added = deepcopy(review["candidate"])
    added["files"]["src/travaux/unknown_migration.py"] = "a" * 64
    assert not common.reviewed_public_schema_upgrade(review["previous"], added)


def test_review_cannot_be_reused_for_another_baseline_or_private_database(review):
    old, new = review["previous"], review["candidate"]
    for key, value in [("release", "20261115T102001Z-234aeb"), ("runtime", common.LEGACY_RUNTIME)]:
        changed = deepcopy(old)
        changed[key] = value
        assert not common.reviewed_public_schema_upgrade(changed, new)
    changed = deepcopy(new)
    changed["runtime"] = common.LEGACY_RUNTIME
    assert not common.reviewed_public_schema_upgrade(old, changed)
    changed = deepcopy(old)
    changed["files"]["src/travaux/auth.py"] = "f" * 64
    assert not common.reviewed_public_schema_upgrade(changed, new)


def test_ui_assets_can_change_without_extending_the_reviewed_backend_scope(review):
    candidate = deepcopy(review["candidate"])
    candidate["files"]["web/index.html"] = "b" * 64
    assert common.reviewed_public_schema_upgrade(review["previous"], candidate)


@pytest.mark.parametrize("mutation", [None, "auth", "api", "dependency", "new_backend"])
def test_apply_backs_up_before_starting_only_the_reviewed_upgrade(review, tmp_path, monkeypatch, mutation):
    events = []
    old = review["previous"]
    candidate = deepcopy(review["candidate"])
    if mutation:
        # The original protected-schema change is still present. An additional
        # future edit must not inherit that historical migration authorization.
        name = {
            "auth": "src/travaux/auth.py",
            "api": "src/travaux/api.py",
            "dependency": "uv.lock",
            "new_backend": "src/travaux/future_feature.py",
        }[mutation]
        candidate["files"][name] = "0" * 64
        candidate["release"] = "20270101T000000Z-aabbcc"
    monkeypatch.setattr(remote, "BASE", tmp_path)
    monkeypatch.setattr(remote, "ROUTE", tmp_path / "route.caddy")
    monkeypatch.setattr(remote, "current_state", lambda: {"release": old["release"], "route_hash": "a" * 64})
    monkeypatch.setattr(remote, "read_json", lambda path: old)
    monkeypatch.setattr(remote, "release_runtime", lambda release: common.PUBLIC_RUNTIME)
    monkeypatch.setattr(remote, "prepare_base", lambda: None)
    monkeypatch.setattr(common, "extract_verified", lambda *args: events.append("extract"))
    monkeypatch.setattr(remote, "caddy_id", lambda: "caddy")
    monkeypatch.setattr(remote, "other_caddy_fingerprint", lambda: "unchanged")

    def command(args, **kwargs):
        if args[:3] == ["docker", "image", "inspect"]:
            return SimpleNamespace(returncode=1)
        if args[:2] == ["docker", "build"]:
            events.append("build")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(remote, "command", command)
    monkeypatch.setattr(remote, "compose", lambda *args, **kwargs: events.append(args))
    monkeypatch.setattr(remote, "wait_healthy", lambda release: events.append("healthy"))
    monkeypatch.setattr(remote, "auth_probe", lambda release: events.append("public_probe"))
    monkeypatch.setattr(common, "activate_route", lambda *args, **kwargs: events.append("route"))
    if mutation:
        with pytest.raises(common.DeploymentError, match="schema_review_required"):
            remote.apply_locked(tmp_path / "release.tar.gz", candidate, candidate["release"])
        assert events == []
        return
    result = remote.apply_locked(tmp_path / "release.tar.gz", candidate, candidate["release"])
    assert result["deployed"] is True and result["fake_llm"] is True
    backup = events[1]
    assert backup[:6] == (old["release"], "exec", "-T", "app", "python", "-c")
    assert "file:/data/public-demo.sqlite3?mode=ro" in backup[-1]
    assert (
        events.index(backup)
        < events.index("build")
        < events.index("healthy")
        < events.index("public_probe")
        < events.index("route")
    )
