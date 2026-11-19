import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import zipfile

import pytest

HERE = Path(__file__).resolve().parents[1]
PRODUCT = HERE.parents[1]


def module():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    spec = importlib.util.spec_from_file_location("private_theme_update_fixture", HERE / "theme_update.py")
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def artifacts():
    return ((PRODUCT / "dist/mayortech-keycloak-theme-2026-11-17.jar").read_bytes(),
            (PRODUCT / "dist/mayortech-keycloak-theme-2026-11-18-filename-v1.jar").read_bytes())


def repair_artifact():
    return (PRODUCT / "dist/mayortech-keycloak-theme-2026-11-18.jar").read_bytes()


def cache_artifact():
    return artifacts()[1]


def test_cache_versioned_source_styles_are_a_new_url_without_a_css_change():
    properties = (PRODUCT / "deploy/keycloak/theme/mayortech/login/theme.properties").read_bytes()
    assert properties.splitlines().count(b"styles=css/styles.css css/mayortech-20261118-1.css") == 1
    css18 = repair_artifact()
    with zipfile.ZipFile(io.BytesIO(css18)) as archive:
        assert (PRODUCT / "deploy/keycloak/theme/mayortech/login/resources/css/mayortech.css").read_bytes() == archive.read("theme/mayortech/login/resources/css/mayortech.css")


def test_cache_properties_patch_is_reviewed_from_the_original_baseline(monkeypatch):
    m = module()
    old, _ = artifacts()
    css18 = repair_artifact()
    new = cache_artifact()
    monkeypatch.setattr(m, "NEW_SHA256", m.A.digest(new))
    m.verify_patch(old, new)
    with zipfile.ZipFile(io.BytesIO(css18)) as before, zipfile.ZipFile(io.BytesIO(new)) as after:
        assert [name.replace("/mayortech.css", "/mayortech-20261118-1.css") for name in before.namelist()] == after.namelist()
        assert before.read(m.CSS_ENTRY) == after.read(m.NEW_CSS_ENTRY)
        assert [name for name in before.namelist() if name != m.CSS_ENTRY and before.read(name) != after.read(name)] == ["theme/mayortech/login/theme.properties"]


@pytest.mark.parametrize("variant", ["baseline17", "css18", "cache18"])
def test_known_deployed_artifacts_require_matching_recorded_hash(monkeypatch, variant):
    m = module()
    baseline, _ = artifacts()
    css18 = repair_artifact()
    cache18 = cache_artifact()
    monkeypatch.setattr(m, "NEW_SHA256", m.A.digest(cache18))
    content = {"baseline17": baseline, "css18": css18, "cache18": cache18}[variant]
    status = {"theme_release": {"sha256": m.A.digest(content)}}
    m.validate_deployed_theme(content, status)
    with pytest.raises(m.ThemeError, match="deployed_theme_drift"):
        m.validate_deployed_theme(content, {"theme_release": {"sha256": "0" * 64}})
    with pytest.raises(m.ThemeError, match="deployed_theme_drift"):
        m.validate_deployed_theme(content + b"foreign", status)


def test_the_reviewed_jar_contains_only_the_exact_css_repair_and_versioned_filename():
    m = module()
    old, new = artifacts()
    assert m.A.digest(new) == m.NEW_SHA256
    m.verify_patch(old, new)
    with pytest.raises(m.ThemeError, match="theme_artifact_not_reviewed"):
        m.verify_patch(old, new + b"unreviewed")


@pytest.mark.parametrize("mutation", ["new-entry", "font-change", "another-css-property", "locale-change", "remove-version", "wrong-version"])
def test_even_a_newly_approved_hash_cannot_broaden_this_css_only_maintenance(monkeypatch, mutation):
    m = module()
    old, new = artifacts()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(new)) as source, zipfile.ZipFile(output, "w") as target:
        for name in source.namelist():
            data = source.read(name)
            if mutation == "font-change" and name.endswith("OFL.txt"):
                data += b"unreviewed-font-license-change"
            if mutation == "another-css-property" and name == m.NEW_CSS_ENTRY:
                data += b"\nbody { display:none; }\n"
            if name == m.PROPERTIES_ENTRY:
                if mutation == "locale-change":
                    data = data.replace(b"locales=fr,en", b"locales=fr,en,de")
                if mutation == "remove-version":
                    data = data.replace(b"mayortech-20261118-1.css", b"mayortech.css")
                if mutation == "wrong-version":
                    data = data.replace(b"mayortech-20261118-1.css", b"mayortech-20261118-2.css")
            target.writestr(name, data)
        if mutation == "new-entry":
            target.writestr("theme/mayortech/login/unreviewed.ftl", "new template")
    changed = output.getvalue()
    monkeypatch.setattr(m, "NEW_SHA256", m.A.digest(changed))
    with pytest.raises(m.ThemeError, match="theme_entries_changed|non_css_theme_change|theme_css_change_not_exact|theme_styles_change_not_exact"):
        m.verify_patch(old, changed)


def test_theme_cas_never_replaces_a_foreign_or_drifted_jar(tmp_path):
    m = module()
    path = tmp_path / "theme.jar"
    path.write_bytes(b"foreign")
    with pytest.raises(m.ThemeError, match="concurrent_theme_change"):
        m.replace_theme(path, "0" * 64, b"next", None)
    assert path.read_bytes() == b"foreign"
    assert not list(tmp_path.glob("*.pending-*"))
    m.replace_theme(path, m.A.digest(b"foreign"), b"next", None)
    assert path.read_bytes() == b"next"


@pytest.mark.skipif(os.name == "nt", reason="POSIX file mode semantics require the Linux operator")
def test_public_jar_mode_survives_the_operators_restrictive_umask(tmp_path):
    m = module()
    path = tmp_path / "theme.jar"
    path.write_bytes(b"old")
    previous = os.umask(0o077)
    try:
        m.replace_theme(path, m.A.digest(b"old"), b"new", None)
    finally:
        os.umask(previous)
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_unknown_theme_commands_are_refused_before_any_transport():
    m = module()
    with pytest.raises(m.ThemeError, match="invalid_theme_operator_command"):
        m.execute("stop-everything", {})


def test_maintenance_cannot_downgrade_or_change_a_manually_drifted_native_image():
    m = module()
    current = {"keycloak": "expected-idp", "identity_guard": "expected-guard"}
    runtime = SimpleNamespace(C=SimpleNamespace(KEYCLOAK_IMAGE="reviewed-idp-ref"),
                              inspect=lambda kind, ref: {"Id": "expected-idp" if ref == "reviewed-idp-ref" else "expected-guard"},
                              service=lambda name: (name, {"Image": current[name]}))
    assert m.reviewed_native_images(runtime) == current
    current["keycloak"] = "different-security-release"
    with pytest.raises(m.ThemeError, match="native_image_drift_before_maintenance"):
        m.reviewed_native_images(runtime)


@pytest.fixture(params=["baseline17", "css18"])
def theme_run(tmp_path, monkeypatch, request):
    m = module()
    old, new = artifacts()
    if request.param == "css18":
        old = repair_artifact()
    state = {"uid": None, "old": old, "old_hash": m.A.digest(old), "new": new,
             "status": {"source_digest": "initial", "app_release": {"image": "unchanged-app-image"},
                        "theme_release": {"sha256": m.A.digest(old)}},
             "review_id": "source-review", "native_images": {"keycloak": "same-idp-image", "identity_guard": "same-nginx-image"},
             "app_image": "same-app-image", "frozen": {"all_other_files": "unchanged"}}
    state["status_bytes"] = json.dumps(state["status"]).encode()
    (tmp_path / "theme.jar").write_bytes(old)
    (tmp_path / "status.json").write_bytes(state["status_bytes"])
    events = []
    mutable = {"config_fails": False, "new_fails": False, "old_fails": False}
    class Lock:
        LOCK_EX = 1
        LOCK_NB = 2
        @staticmethod
        def flock(*args):
            events.append("lock")
    def compose(*args):
        events.append(("compose", args))
        if args[0] == "config" and mutable["config_fails"]:
            raise RuntimeError("Private command output must be withheld")
    def write_new(path, data, uid):
        with path.open("xb") as stream:
            stream.write(data)
        events.append(("backup" if path.name == "previous-theme.jar" else "receipt", path.name))
    def recreate(runtime, current):
        phase = "new" if (tmp_path / "theme.jar").read_bytes() == new else "old"
        events.append(("recreate", phase))
        if mutable["new_fails"] and phase == "new" or mutable["old_fails"] and phase == "old":
            raise m.ThemeError("Synthetic identity health failure")
        return {"production_oidc_httpx_https": True}
    runtime = SimpleNamespace(C=SimpleNamespace(BASE=tmp_path), fcntl=Lock,
                              verify_base=lambda **kwargs: None, compose=compose, write_new=write_new)
    monkeypatch.setattr(m, "inspect_state", lambda payload, runtime: state)
    monkeypatch.setattr(m, "assert_frozen", lambda runtime, current: None)
    monkeypatch.setattr(m, "recreate_identity", recreate)
    monkeypatch.setattr(m.A, "confirm_application", lambda *args: events.append("unchanged-existing-health-confirmed"))
    payload = {"expected_theme_sha256": state["old_hash"], "expected_status_sha256": m.A.digest(state["status_bytes"])}
    return SimpleNamespace(m=m, runtime=runtime, payload=payload, state=state, folder=tmp_path,
                           events=events, mutable=mutable)


def test_theme_update_backs_up_before_recreating_and_preserves_application_status(theme_run):
    qa = theme_run
    receipt = qa.m.apply(qa.payload, qa.runtime)
    assert receipt["applied"] is True
    assert qa.events.index(("backup", "previous-theme.jar")) < qa.events.index(("recreate", "new"))
    status = json.loads((qa.folder / "status.json").read_bytes())
    assert status["app_release"] == qa.state["status"]["app_release"]
    assert status["source_digest"] == "initial"
    assert status["theme_release"]["sha256"] == qa.m.NEW_SHA256
    assert (qa.folder / "theme.jar").read_bytes() == qa.state["new"]


def test_stale_theme_plan_never_writes_a_jar_or_restarts(theme_run):
    qa = theme_run
    qa.payload["expected_status_sha256"] = "0" * 64
    with pytest.raises(qa.m.ThemeError, match="stale_theme_plan"):
        qa.m.apply(qa.payload, qa.runtime)
    assert qa.events == ["lock"]
    assert (qa.folder / "theme.jar").read_bytes() == qa.state["old"]


def test_pre_restart_validation_failure_restores_jar_without_restarting(theme_run):
    qa = theme_run
    qa.mutable["config_fails"] = True
    with pytest.raises(qa.m.ThemeError, match="theme_update_failed_rolled_back"):
        qa.m.apply(qa.payload, qa.runtime)
    assert not any(isinstance(value, tuple) and value[0] == "recreate" for value in qa.events)
    assert (qa.folder / "theme.jar").read_bytes() == qa.state["old"]
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_failed_new_theme_restores_old_jar_and_checks_old_identity(theme_run):
    qa = theme_run
    qa.mutable["new_fails"] = True
    with pytest.raises(qa.m.ThemeError, match="theme_update_failed_rolled_back"):
        qa.m.apply(qa.payload, qa.runtime)
    assert ("recreate", "old") in qa.events
    assert (qa.folder / "theme.jar").read_bytes() == qa.state["old"]


def test_failed_rollback_is_reported_as_manual_recovery(theme_run):
    qa = theme_run
    qa.mutable["new_fails"] = qa.mutable["old_fails"] = True
    with pytest.raises(qa.m.ThemeError, match="theme_update_failed_manual_recovery_required"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_concurrent_jar_replacement_is_never_overwritten_or_restarted(theme_run, monkeypatch):
    qa = theme_run
    def drift(runtime, current):
        (qa.folder / "theme.jar").write_bytes(b"foreign-operator-jar")
        raise qa.m.ThemeError("Synthetic update failure")
    monkeypatch.setattr(qa.m, "recreate_identity", drift)
    with pytest.raises(qa.m.ThemeError, match="theme_update_failed_manual_recovery_required"):
        qa.m.apply(qa.payload, qa.runtime)
    assert (qa.folder / "theme.jar").read_bytes() == b"foreign-operator-jar"
    assert (qa.folder / "status.json").read_bytes() == qa.state["status_bytes"]


def test_concurrent_receipt_change_is_preserved_during_rollback(theme_run, monkeypatch):
    qa = theme_run
    def drift(runtime, current):
        path = next((qa.folder / "theme-updates").glob("*/receipt.json"))
        path.write_bytes(b"foreign receipt")
        return {"https": True}
    monkeypatch.setattr(qa.m, "recreate_identity", drift)
    with pytest.raises(qa.m.ThemeError, match="theme_update_failed_rolled_back"):
        qa.m.apply(qa.payload, qa.runtime)
    path = next((qa.folder / "theme-updates").glob("*/receipt.json"))
    assert path.read_bytes() == b"foreign receipt"
    assert (qa.folder / "theme.jar").read_bytes() == qa.state["old"]


def test_real_recreation_commands_are_only_keycloak_then_guard_after_readiness(monkeypatch):
    m = module()
    events = []
    runtime = SimpleNamespace(compose=lambda *args: events.append(args), probes=lambda: {"https": True})
    monkeypatch.setattr(m.A, "confirm_application", lambda *args: events.append("healthy"))
    m.recreate_identity(runtime, {"app_image": "same-app-binary"})
    assert events == [("up", "-d", "--no-deps", "--pull", "never", "--force-recreate", "keycloak"), "healthy",
                      ("up", "-d", "--no-deps", "--pull", "never", "--force-recreate", "identity_guard"), "healthy"]
