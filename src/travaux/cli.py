import argparse
import asyncio
import json
from getpass import getpass
from pathlib import Path
import sqlite3
import sys
import time

from .auth import hash_password
from .config import Settings, ensure_public_demo_database


def backup(source: Path, target: Path):
    if not source.is_file():
        raise ValueError("Base source absente")
    if target.exists():
        raise ValueError("Le fichier de sauvegarde existe déjà")
    target.parent.mkdir(parents=True, exist_ok=True)
    origin = sqlite3.connect(source)
    destination = sqlite3.connect(target)
    try:
        origin.backup(destination)
        if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Sauvegarde invalide")
    finally:
        origin.close()
        destination.close()


def _main():
    parser = argparse.ArgumentParser(description="Travaux — pilote municipal")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="Démarrer le service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    sub.add_parser("worker", help="Traiter la file durable, un processus par hôte")
    sub.add_parser("password", help="Hacher une phrase de passe sans l'afficher")
    member = sub.add_parser("identity-member", help="Autoriser une identité institutionnelle vérifiée ; commande opérateur")
    member.add_argument("--subject", required=True)
    member.add_argument("--name", required=True)
    member.add_argument("--role", required=True, choices=("admin", "editor", "reader"))
    rotate = sub.add_parser("vault-rotate", help="Ré-encrypter les secrets avec la première clé du trousseau")
    rotate.add_argument("--confirm-writers-paused", action="store_true")
    sub.add_parser("native-check", help="Vérifier les contrats MCP de l'installation AppFlowy")
    sub.add_parser("native-sync-notes", help="Importer les notes natives explicitement mappées")
    collect = sub.add_parser("collect-exchange", help="Lire les changements Exchange et persister avant checkpoint")
    collect.add_argument("--config", required=True, type=Path)
    save = sub.add_parser("backup")
    save.add_argument("target", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("source", type=Path)
    args = parser.parse_args()
    if args.command == "password":
        first = getpass("Phrase de passe (16 caractères minimum) : ")
        if first != getpass("Confirmation : "):
            parser.error("Les phrases diffèrent")
        print(hash_password(first))
        return
    settings = Settings.from_env()
    if args.command in {"identity-member", "vault-rotate"}:
        if not settings.auth_required or settings.auth_mode != "oidc":
            parser.error("Cette opération exige un espace privé avec identité institutionnelle.")
        ensure_public_demo_database(settings)
        from .repository import Repository
        repo = Repository(settings.db_path)
        try:
            if args.command == "identity-member":
                import os
                from .identity import IdentityStore
                from .auth import SessionStore
                issuer = os.getenv("TRAVAUX_OIDC_ISSUER", "")
                store = IdentityStore(repo, settings.tenant_id, SessionStore(settings.db_path))
                saved = store.provision(issuer, args.subject, args.name, args.role)
                if not saved["active"] or saved["role"] != args.role:
                    saved = store.update(saved["actor_id"], role=args.role, active=True, expected_revision=saved["revision"], updated_by="server-operator")
                print(json.dumps({"id": saved["actor_id"], "role": saved["role"], "active": saved["active"]}))
            else:
                from .maintenance import rotate_connector_secrets
                print(json.dumps(rotate_connector_secrets(repo, settings, workers_paused=args.confirm_writers_paused)))
        finally:
            repo.close()
        return
    if settings.mode == "public_demo" and args.command in {"collect-exchange", "native-check", "native-sync-notes"}:
        parser.error("Le mode public_demo est limité au corpus fictif ; les collecteurs et connexions externes sont désactivés.")
    if args.command in {"serve", "worker", "collect-exchange", "native-check", "native-sync-notes"}:
        ensure_public_demo_database(settings)
    if args.command == "collect-exchange":
        from .collector import collect_exchange
        print(json.dumps(collect_exchange(settings, args.config), ensure_ascii=False))
        return
    if args.command in {"native-check", "native-sync-notes"}:
        from .native import check_native, sync_notes
        from .repository import Repository
        repo = Repository(settings.db_path)
        try:
            result = asyncio.run(check_native(settings) if args.command == "native-check" else sync_notes(settings, repo))
            print(json.dumps(result, ensure_ascii=False))
        finally:
            repo.close()
        return
    if args.command == "serve":
        if settings.mode == "demo" and args.host not in {"127.0.0.1", "localhost", "::1"}:
            parser.error("Le mode démo sans authentification doit rester sur la boucle locale")
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(settings), host=args.host, port=args.port, access_log=False,
                    proxy_headers=bool(settings.trusted_proxy_ips),
                    forwarded_allow_ips=list(settings.trusted_proxy_ips))
    elif args.command == "worker":
        from .jobs import JobQueue
        from .llm import make_extractor
        from .pipeline import process_one
        from .repository import Repository
        extractor = make_extractor(settings)
        repo, queue = Repository(settings.db_path), JobQueue(settings.db_path)
        try:
            while True:
                if not process_one(queue, repo, extractor):
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            repo.close()
    elif args.command == "backup":
        backup(settings.db_path, args.target)
        print(f"Sauvegarde vérifiée : {args.target}")
    elif args.command == "restore":
        # Never replace a running or existing database. Explicit target is TRAVAUX_DB.
        backup(args.source, settings.db_path)
        print("Base restaurée dans une nouvelle cible. Vérifier avant de remettre en service.")


def main():
    try:
        _main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as error:
        # Do not print provider envelopes, schemas with note instances, or credentials.
        print(f"Échec contrôlé ({type(error).__name__}). Vérifier la configuration, l'état des traitements et le guide d'exploitation.", file=sys.stderr)
        raise SystemExit(1) from None
