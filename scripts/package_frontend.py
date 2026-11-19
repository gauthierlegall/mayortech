"""Publish the reviewed static Lovable frontend into the existing backend bundle."""

from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "frontend-lovable/dist"
target = (ROOT / "web/product").resolve()
if not source.joinpath("index.html").is_file():
    raise SystemExit("Build the frontend before packaging it.")
if not target.is_relative_to((ROOT / "web").resolve()) or target.name != "product":
    raise SystemExit("Unexpected frontend destination.")
if target.exists():
    shutil.rmtree(target)
shutil.copytree(source, target, ignore=shutil.ignore_patterns("index.html"))
shutil.copyfile(source / "index.html", ROOT / "web/index.html")
for entry in ("connexion.html", "inscription.html", "mot-de-passe-oublie.html", "mentions-legales.html", "confidentialite.html"):
    shutil.copyfile(source / entry, ROOT / "web" / entry)
lock = json.loads((ROOT / "frontend-lovable/package-lock.json").read_text(encoding="utf-8"))
notices = ["Third-party packages of the static Lovable frontend. Original licenses retained below.\n"]
inventory = []
for name, entry in lock["packages"].items():
    if not name.startswith("node_modules/"):
        continue
    package = ROOT / "frontend-lovable" / name
    metadata = (
        json.loads((package / "package.json").read_text(encoding="utf-8"))
        if (package / "package.json").is_file()
        else {}
    )
    inventory.append(
        {
            "name": metadata.get("name", name),
            "version": entry["version"],
            "license": metadata.get("license"),
            "dev": entry.get("dev", False),
            "integrity": entry.get("integrity"),
        }
    )
    notices.append(f"\n===== {metadata.get('name', name)} {entry['version']} =====\n")
    for file in package.glob("*"):
        if file.is_file() and file.name.lower().split(".")[0] in {"license", "licence", "notice", "copying"}:
            notices.append(file.read_text(encoding="utf-8", errors="replace"))
(target / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(notices), encoding="utf-8")
(target / "THIRD-PARTY-PACKAGES.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
files = {
    file.relative_to(ROOT).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
    for file in target.rglob("*")
    if file.is_file()
}
(ROOT / "docs/frontend-build.json").write_text(
    json.dumps(
        {
            "files": files,
            "source": "frontend-lovable",
            "user_archive_provenance": "lovable-source.json",
            "remote_fonts": False,
            "supabase_in_runtime": False,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(
    json.dumps({"static_files": len(files), "licenses": len(inventory), "entry_published": "web/index.html"})
)
