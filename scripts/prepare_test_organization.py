"""Prepare persistent fictional fixtures; no server, account or secret is created.

Run with the project's installed Python environment. Runtime OIDC configuration
is an independent operator step; this preparation never uses existing secrets.
"""
import argparse
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser(description="Préparer une organisation test persistante, isolée et sans compte implicite")
    parser.add_argument("--database", required=True, type=Path, help="Nouvelle base ou base test déjà marquée ; jamais une base réelle")
    parser.add_argument("--tenant", default="organization-test", help="Identifiant stable de 3 à 64 caractères ASCII")
    parser.add_argument("--public-origin", required=True, help="Origine HTTPS exacte qui sera utilisée pour cette instance test")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", args.tenant):
        parser.error("Identifiant d’organisation invalide")
    target = args.database.absolute()
    if target.resolve() != target or target.is_symlink():
        parser.error("Choisissez un chemin direct, sans lien ni jonction, pour la base test")
    # Do not load owner.env or any existing external connector/IdP credentials.
    for name in list(os.environ):
        if name.startswith("TRAVAUX_") or name in {"SSLKEYLOGFILE", "QUICLOGDIR"}:
            del os.environ[name]
    from travaux.api import create_app
    from travaux.config import Settings
    settings = Settings(mode="staging", auth_mode="oidc", llm="demo", egress_approved=False,
                        test_organization_self_join=True, db_path=target, tenant_id=args.tenant,
                        public_origin=args.public_origin, allowed_hosts=(urlsplit(args.public_origin).hostname or "",))
    app = create_app(settings)  # The same markerDB guard and fixture setup as serve.
    try:
        assert not app.state.identity_login.available
        repo = app.state.repo
        with repo._lock:
            assert repo._db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            profile = repo._db.execute("SELECT name FROM organization_profiles WHERE tenant_id=?", (args.tenant,)).fetchone()
            count = repo._db.execute("SELECT count(*) FROM projects WHERE tenant_id=?", (args.tenant,)).fetchone()[0]
        print(json.dumps({"database": str(target), "tenant": args.tenant, "organization": profile["name"],
                          "projects": count, "accounts_created": 0, "server_started": False,
                          "identity_configured": False, "fictional_only": True}, ensure_ascii=False))
    finally:
        app.state.identity_login.close()
        app.state.repo.close()


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None
