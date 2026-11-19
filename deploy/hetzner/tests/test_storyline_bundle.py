"""The operator seed must work from the exact verified release, without a wildcard."""

import json
import io
from pathlib import Path
import shutil
import sys
import tarfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common
import deploy
from test_deploy import project

ROOT = Path(__file__).resolve().parents[3]
PREFIX = "fixtures/storylines/lovable-v1/"
RUNTIME = {
    PREFIX + "storyline.json",
    PREFIX + "documents/devis-portail-v1.pdf",
    PREFIX + "documents/devis-portail-v2.pdf",
} | {PREFIX + f"mail/m{number}.eml" for number in range(1, 11)}


def test_release_inventory_includes_all_pinned_operator_seed_inputs():
    items = deploy.inventory(ROOT)
    assert RUNTIME.issubset(items), "The deployed CLI needs the actual EML/PDF corpus and its pinned manifest"


def test_storyline_allowlist_is_literal_and_rejects_other_fixtures_secrets_and_tools():
    assert all(common.allowed_name(name) for name in RUNTIME)
    assert all(
        not common.allowed_name(name)
        for name in (
            PREFIX + ".env",
            PREFIX + "credentials.json",
            PREFIX + "operator.sqlite3",
            PREFIX + "mail/m11.eml",
            PREFIX + "documents/unreviewed.pdf",
            PREFIX + "storyline-other.json",
            "fixtures/storylines/other/private.eml",
            "fixtures/municipal-real/mail.eml",
        )
    )


def test_container_copies_only_the_selected_fixture_and_never_seeds_on_start():
    docker = (ROOT / "Dockerfile").read_text()
    runtime = docker.split("FROM base AS runtime", 1)[1]
    assert (
        "COPY --chown=10001:10001 fixtures/storylines/lovable-v1 ./fixtures/storylines/lovable-v1" in runtime
    )
    assert "python -m travaux.storyline" not in docker
    assert "COPY fixtures ./fixtures" not in docker


def test_inventory_rejects_modified_original_before_an_archive_is_created(tmp_path):
    root = project(tmp_path / "release")
    for name in RUNTIME:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (root / PREFIX / "documents/devis-portail-v2.pdf").write_bytes(b"modified original")
    with pytest.raises(common.DeploymentError, match="storyline_original_integrity"):
        deploy.inventory(root)


def test_packaged_fixture_hashes_and_code_pin_match_the_verified_archive(tmp_path):
    from travaux.storyline import MANIFEST_SHA256

    items = deploy.inventory(ROOT)
    archive = tmp_path / "storyline-release.tgz"
    deploy.package(
        ROOT,
        archive,
        "20261115T235959Z-acde42",
        deploy.make_gate(items, python=True, frontend=True, native=True),
    )
    with tarfile.open(archive) as content:
        raw = content.extractfile(PREFIX + "storyline.json").read()
        assert common.sha256(raw) == MANIFEST_SHA256
        fixture = json.loads(raw)
        for name, digest in fixture["assets"].items():
            assert common.sha256(content.extractfile(PREFIX + name).read()) == digest


@pytest.mark.parametrize(
    "member,code",
    [
        (PREFIX + "documents/devis-portail-v2.pdf", "storyline_original_integrity"),
        (PREFIX + "storyline.json", "storyline_manifest_integrity"),
    ],
)
def test_archive_refuses_altered_story_even_with_recomputed_release_hashes(tmp_path, member, code):
    root = project(tmp_path / "release")
    items = deploy.inventory(root)
    original = tmp_path / "verified.tgz"
    deploy.package(
        root,
        original,
        "20261115T235959Z-acde42",
        deploy.make_gate(items, python=True, frontend=True, native=True),
    )
    with tarfile.open(original) as archive:
        content = {item.name: archive.extractfile(item).read() for item in archive.getmembers()}
    content[member] += b" changed outside the verified story"
    manifest = json.loads(content["release-manifest.json"])
    manifest["files"][member] = common.sha256(content[member])
    manifest["gate"]["source_digest"] = common.inventory_digest(manifest["files"])
    content["release-manifest.json"] = json.dumps(manifest).encode()
    altered = tmp_path / "altered.tgz"
    with tarfile.open(altered, "w:gz") as archive:
        for name, body in content.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(body))
    with pytest.raises(common.DeploymentError, match=code):
        common.verify_archive(altered)
