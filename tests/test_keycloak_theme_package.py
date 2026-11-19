"""Consume the produced JAR and verify the file/credential boundary."""
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


def packager():
    location = Path(__file__).resolve().parents[1] / "scripts/package_keycloak_theme.py"
    assert location.is_file(), "The theme packager is missing"
    spec = importlib.util.spec_from_file_location("keycloak_theme_packager", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_standard_theme_jar_is_consumable_without_overriding_native_forms(tmp_path):
    module = packager()
    target = tmp_path / "mayortech.jar"
    result = module.package_theme(target)
    assert result["bytes"] > 0 and len(result["sha256"]) == 64
    with zipfile.ZipFile(target) as archive:
        metadata = json.loads(archive.read("META-INF/keycloak-themes.json"))
        assert metadata == {"themes": [{"name": "mayortech", "types": ["login"]}]}
        assert "parent=keycloak.v2" in archive.read("theme/mayortech/login/theme.properties").decode()
        assert archive.read("theme/mayortech/login/resources/img/mayortech-mark.svg").startswith(b"<svg")
        assert not any(name.endswith((".ftl", ".js", ".class")) for name in archive.namelist())
        assert archive.read("theme/mayortech/login/resources/fonts/OFL.txt").startswith(b"Copyright")


def test_packager_never_overwrites_an_existing_artifact(tmp_path):
    module = packager()
    target = tmp_path / "mayortech.jar"
    target.write_bytes(b"preserved")
    with pytest.raises(FileExistsError):
        module.package_theme(target)
    assert target.read_bytes() == b"preserved"


def test_css_resource_filename_versions_native_gzip_and_cdn_cache_without_duplicate_asset(tmp_path):
    module = packager()
    target = tmp_path / "cache-versioned.jar"
    module.package_theme(target)
    with zipfile.ZipFile(target) as archive:
        css = "theme/mayortech/login/resources/css/mayortech-20261118-1.css"
        assert css in archive.namelist()
        assert "theme/mayortech/login/resources/css/mayortech.css" not in archive.namelist()
        assert len(archive.namelist()) == 10
        assert archive.read(css) == (module.DEFAULT_ROOT / "login/resources/css/mayortech.css").read_bytes()
        assert b"styles=css/styles.css css/mayortech-20261118-1.css\n" in archive.read("theme/mayortech/login/theme.properties")


def test_packager_refuses_indirect_theme_file_and_does_not_create_output(tmp_path):
    module = packager()
    source = tmp_path / "mayortech"
    for relative in module.THEME_FILES:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"owned fixture")
    outside = tmp_path / "not-for-theme.txt"
    outside.write_bytes(b"fictitious private material")
    linked = source / "login/theme.properties"
    linked.unlink()
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("The Windows account cannot create a test symlink")
    target = tmp_path / "mayortech.jar"
    with pytest.raises(ValueError):
        module.package_theme(target, theme_root=source)
    assert not target.exists()
