"""Build a standard Keycloak theme-only JAR without Java or a vendor-code copy."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

THEME_FILES = (
    "login/theme.properties", "login/resources/css/mayortech.css",
    "login/resources/img/mayortech-mark.svg", "FONT_LICENSE.md", "ASSETS.md",
    "login/resources/fonts/dm-sans-latin-wght-normal.woff2",
    "login/resources/fonts/dm-sans-latin-ext-wght-normal.woff2",
    "login/resources/fonts/OFL.txt",
)
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "deploy/keycloak/theme/mayortech"


def package_theme(output: Path, *, theme_root: Path = DEFAULT_ROOT):
    root = Path(theme_root).absolute()
    if root.resolve() != root or root.is_symlink() or not root.is_dir():
        raise ValueError("Le thème doit être un répertoire direct, sans lien ni jonction")
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n\n")
        archive.writestr("META-INF/keycloak-themes.json", json.dumps({"themes": [{"name": "mayortech", "types": ["login"]}]}))
        for name in THEME_FILES:
            target = root / name
            if target.resolve() != target or target.is_symlink() or not target.is_file() or target.stat().st_size > 256_000:
                raise ValueError("Ressource du thème absente, indirecte ou trop volumineuse")
            # A distinct filename also invalidates Keycloak's persistent gzip
            # cache, which ignores query versions on the former resource path.
            resource = "login/resources/css/mayortech-20261118-1.css" if name == "login/resources/css/mayortech.css" else name
            archive.writestr("theme/mayortech/" + resource, target.read_bytes())
    payload = data.getvalue()
    output = Path(output).absolute()
    if output.resolve() != output or output.is_symlink():
        raise ValueError("L’archive exige un chemin direct, sans lien ni jonction")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
    return {"archive": str(output), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "theme": "mayortech", "deployed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package_theme(args.output), ensure_ascii=False))


if __name__ == "__main__":
    main()
