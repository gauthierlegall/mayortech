"""Exercise release packaging against the actual compiled Lovable artifacts.

This builds a temporary test archive, never an operator attestation or deployment.
"""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import deploy
from test_deploy import project


ROOT = Path(__file__).resolve().parents[3]
RELEASE = "20261115T230000Z-abc654"
NOTICES = {"web/product/THIRD-PARTY-NOTICES.txt", "web/product/THIRD-PARTY-PACKAGES.json"}


class AssetReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.local = []
        self.remote = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        value = (
            attributes.get("src") if tag == "script" else attributes.get("href") if tag == "link" else None
        )
        if value:
            (self.local if value.startswith("/") and not value.startswith("//") else self.remote).append(
                value
            )


@pytest.fixture(scope="module")
def packaged_client(tmp_path_factory):
    """Package actual sources into a disposable archive, without a remote action."""
    folder = tmp_path_factory.mktemp("actual-product-release")
    archive = folder / "test-release.tgz"
    items = deploy.inventory(ROOT)
    manifest = deploy.package(
        ROOT, archive, RELEASE, deploy.make_gate(items, python=True, frontend=True, native=True)
    )
    with tarfile.open(archive) as source:
        files = {item.name: source.extractfile(item).read() for item in source if item.isfile()}
    return manifest, files


def test_actual_archive_contains_built_client_fonts_notices_and_all_seven_vendor_resources(packaged_client):
    manifest, files = packaged_client
    assert NOTICES.issubset(files)
    assert common.RUNTIME_RESOURCES.issubset(files)
    assert len(common.RUNTIME_RESOURCES) == 7
    product = {name for name in files if name.startswith("web/product/assets/")}
    assert any(name.endswith(".js") for name in product)
    assert any(name.endswith(".css") for name in product)
    assert any(name.endswith(".woff2") for name in product)
    for name in product | NOTICES | common.RUNTIME_RESOURCES:
        assert name in manifest["files"]
        assert files[name] == (ROOT / name).read_bytes()
        assert common.sha256(files[name]) == manifest["files"][name]


def test_root_index_references_only_shipped_local_assets(packaged_client):
    _, files = packaged_client
    parser = AssetReferences()
    parser.feed(files["web/index.html"].decode("utf-8"))
    assert not parser.remote, "The served index must not depend on a font CDN or external script"
    assert any(value.startswith("/web/product/assets/") and value.endswith(".js") for value in parser.local)
    assert any(value.startswith("/web/product/assets/") and value.endswith(".css") for value in parser.local)
    for reference in parser.local:
        path = reference.split("?", 1)[0]
        member = (
            "native-editor/dist/" + path.removeprefix("/native/")
            if path.startswith("/native/")
            else path.lstrip("/")
        )
        assert member in files, f"Index references an asset missing from the archive: {reference}"


def test_compiled_css_and_javascript_local_assets_and_font_licence_are_shipped(packaged_client):
    _, files = packaged_client
    references = set()
    for name, body in files.items():
        if name.startswith("web/product/assets/") and name.endswith((".js", ".css")):
            references.update(re.findall(r"/web/product/assets/[A-Za-z0-9_.-]+", body.decode("utf-8")))
    assert any(path.endswith(".woff2") for path in references)
    for reference in references:
        assert reference.lstrip("/") in files, (
            f"Bundle references an asset missing from the archive: {reference}"
        )
    packages = json.loads(files["web/product/THIRD-PARTY-PACKAGES.json"])
    font = next(item for item in packages if item["name"] == "@fontsource-variable/dm-sans")
    assert font["license"] == "OFL-1.1"
    assert font["version"] == "5.2.8"
    notices = files["web/product/THIRD-PARTY-NOTICES.txt"].decode("utf-8")
    assert "@fontsource-variable/dm-sans 5.2.8" in notices
    assert "SIL OPEN FONT LICENSE Version 1.1" in notices
    css = "\n".join(
        body.decode("utf-8")
        for name, body in files.items()
        if name.startswith("web/product/assets/") and name.endswith(".css")
    )
    variable_faces = [
        face for face in re.findall(r"@font-face\{[^}]+\}", css) if "font-family:DM Sans Variable" in face
    ]
    assert variable_faces, "Verify the font actually used by the CSS, not an unused package notice"
    assert all("font-weight:100 1000" in face and "woff2-variations" in face for face in variable_faces)


def test_actual_archive_excludes_lovable_secrets_supabase_runtime_and_sourcemaps(packaged_client):
    _, files = packaged_client
    for name in files:
        assert not any(part.startswith(".env") for part in Path(name).parts)
        assert not name.endswith(".map")
        assert not name.startswith("frontend-lovable/")
        assert "supabase/" not in name.lower()
    for name, body in files.items():
        if name.startswith("web/product/assets/") and name.endswith((".js", ".css")):
            text = body.decode("utf-8")
            assert "sourceMappingURL=" not in text
            assert not any(
                token in text
                for token in ("supabase.co", "@supabase/supabase-js", "VITE_SUPABASE", "LOVABLE_API_KEY")
            )


def test_product_inventory_rejects_accidental_env_supabase_config_maps_and_credentials(tmp_path):
    root = project(tmp_path)
    names = [
        "web/product/.env",
        "web/product/.env.production",
        "web/product/supabase/config.toml",
        "web/product/assets/index.js.map",
        "web/product/credentials.json",
    ]
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SUPABASE_SECRET_MUST_NEVER_SHIP", encoding="utf-8")
    items = deploy.inventory(root)
    assert not set(names).intersection(items)
