"""Portable source selection; never builds the real delivery archive."""
import importlib.util
import json
import os
from pathlib import Path

import pytest


def packager():
    source = Path(__file__).resolve().parents[1] / "scripts/package_release.py"
    spec = importlib.util.spec_from_file_location("release_packager_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report(project, filename, **values):
    folder = project / "docs"
    folder.mkdir(exist_ok=True)
    path = folder / filename
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_latest_production_report_keeps_its_unfinished_status(tmp_path):
    m = packager()
    report(tmp_path, "verification-production-2026-11-17.json", date="2026-11-17", status="passed")
    latest = report(tmp_path, "verification-production-2026-11-18.json", date="2026-11-18", status="in_progress")
    report(tmp_path, "verification-professionnelle-2026-11-19.json", date="2026-11-19", status="passed")
    path, content = m.load_verification(tmp_path)
    assert path == latest
    assert content["status"] == "in_progress"
    assert not list(tmp_path.glob("*.zip"))


def test_verification_falls_back_only_when_a_production_report_is_absent(tmp_path):
    m = packager()
    native = report(tmp_path, "verification-native.json", status="historical")
    assert m.load_verification(tmp_path)[0] == native
    professional = report(tmp_path, "verification-professionnelle-2026-11-17.json", date="2026-11-17", status="historical")
    assert m.load_verification(tmp_path)[0] == professional
    invalid = report(tmp_path, "verification-production-2026-11-18.json", date="2026-11-17")
    with pytest.raises(ValueError, match="verification_date_mismatch"):
        m.load_verification(tmp_path)
    assert invalid.exists()


def test_portable_sources_exclude_nested_live_secrets_and_local_artifacts(tmp_path):
    m = packager()
    keep = ["README.md", ".env.example", "deploy/private-site/app_update.py", "docs/public-review.json", "frontend-lovable/src/app.tsx"]
    omit = [
        "private/bootstrap-material.json", "deploy/private/app.env", ".local/public-copy.json",
        "local/operator-state.json", "secrets/secret.txt", ".secrets/provider.json",
        "test-results/screenshot.png", "diagnostics/callback.txt", ".ssh/id_ed25519",
        "frontend-lovable/node_modules/pkg/index.js", "frontend-lovable/dist/index.html",
        "dist/candidate.json", "data/records.txt", "safe/owner.json", "safe/CREDENTIALS.JSON",
        "safe/.env.production", "safe/app.env", "safe/connector-vault.keys", "safe/key.PEM",
        "safe/archive.PFX", "safe/workspace.SQLITE3-wal", "safe/id_rsa", "safe/cache.pyc",
    ]
    for relative in keep + omit:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture only", encoding="utf-8")
    selected = {path.relative_to(tmp_path).as_posix() for path in m.source_files(tmp_path)}
    assert selected == set(keep)


def test_indirect_source_never_copies_an_external_file(tmp_path):
    m = packager()
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "external.txt"
    outside.write_text("synthetic private fixture", encoding="utf-8")
    alias = project / "apparently-public.txt"
    try:
        alias.symlink_to(outside)
    except OSError:
        pytest.skip("This Windows account cannot create symbolic links")
    assert list(m.source_files(project)) == []


def test_hardlinked_source_never_copies_an_external_file(tmp_path):
    m = packager()
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "external.txt"
    outside.write_text("synthetic private fixture", encoding="utf-8")
    try:
        os.link(outside, project / "apparently-public.txt")
    except OSError:
        pytest.skip("This filesystem cannot create hard links")
    assert list(m.source_files(project)) == []
