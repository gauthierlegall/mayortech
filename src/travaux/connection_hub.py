"""Server-owned connection setup. Secrets never enter a read DTO or public demo.

CalDAV/exchangelib are used by the optional readers; no protocol is simulated.
Google/Microsoft OAuth uses a separately registered server-side application.
"""

from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import socket
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from .domain import DomainError, canonical_json, require_text, utc_now


STEPS = ("welcome", "email", "calendars", "notifications", "finish")
PROVIDERS = {
    "exchange": "Exchange local / prestataire",
    "caldav": "CalDAV / Nextcloud",
    "google": "Google Agenda",
    "microsoft365": "Microsoft 365",
    "ics": "Fichier calendrier (.ics)",
}


@dataclass(frozen=True)
class IntegrationPolicy:
    egress_approved: bool = False
    allowed_hosts: tuple[str, ...] = ()
    private_hosts: tuple[str, ...] = ()
    allowed_ports: tuple[int, ...] = (443,)

    @classmethod
    def from_env(cls):
        def hosts(name):
            return tuple(item.strip().lower() for item in os.getenv(name, "").split(",") if item.strip())

        try:
            ports = tuple(
                int(item) for item in os.getenv("TRAVAUX_CONNECTOR_ALLOWED_PORTS", "443").split(",")
            )
        except ValueError:
            ports = ()
        return cls(
            os.getenv("TRAVAUX_CONNECTOR_EGRESS_APPROVED") == "true",
            hosts("TRAVAUX_CONNECTOR_ALLOWED_HOSTS"),
            hosts("TRAVAUX_CONNECTOR_PRIVATE_HOSTS"),
            ports,
        )

    def endpoint(self, value, *, resolve=False, same_host=None):
        try:
            parsed = urlsplit(value)
            hostname = (parsed.hostname or "").lower()
            port = parsed.port or 443
        except (ValueError, TypeError):
            raise DomainError("invalid_input", "Adresse du serveur invalide.") from None
        if (
            not isinstance(value, str)
            or len(value) > 2000
            or parsed.scheme != "https"
            or not hostname
            or hostname not in self.allowed_hosts
            or "*" in hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or parsed.query
            or port not in self.allowed_ports
            or (same_host and hostname != same_host)
        ):
            raise DomainError(
                "forbidden", "Ce serveur HTTPS ne figure pas dans le périmètre autorisé par l’administrateur."
            )
        if resolve:
            try:
                addresses = {
                    ipaddress.ip_address(result[4][0])
                    for result in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
                }
            except (OSError, ValueError):
                raise DomainError("integration_unavailable", "Le serveur ne peut pas être résolu.") from None
            if not addresses or any(
                address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_unspecified
                or (not address.is_global and hostname not in self.private_hosts)
                for address in addresses
            ):
                raise DomainError(
                    "forbidden", "Cette adresse réseau n’est pas autorisée pour les connecteurs."
                )
        return hostname


class SecretVault:
    """Fernet recipe from pyca/cryptography; encryption key stays outside SQLite."""

    def __init__(self, settings):
        self.settings = settings

    def _fernet(self):
        if not self.settings.auth_required or self.settings.mode == "public_demo":
            raise DomainError("forbidden", "Les secrets de connexion sont réservés à un espace protégé.")
        try:
            ring = os.getenv("TRAVAUX_CONNECTOR_SECRET_KEYS", "")
            legacy = os.getenv("TRAVAUX_CONNECTOR_SECRET_KEY", "")
            external = os.getenv("TRAVAUX_CONNECTOR_KEY_FILE", "")
            if sum(bool(value) for value in (ring, legacy, external)) > 1:
                raise ValueError("ambiguous_key_source")
            if external:
                target = Path(external).absolute()
                if target.is_symlink() or target.resolve() != target or not target.is_file() or target.stat().st_size > 8192:
                    raise ValueError("invalid_external_key_file")
                if self.settings.auth_mode == "oidc" and target.resolve().is_relative_to(Path(self.settings.db_path).parent.resolve()):
                    raise ValueError("key_must_be_separate_from_data")
                if os.name != "nt" and target.stat().st_mode & 0o077:
                    raise ValueError("key_file_permissions")
                ring = target.read_text(encoding="ascii").strip().replace("\n", ",")
            if ring:
                keys = [value.strip().encode("ascii") for value in ring.split(",")]
                if not 1 <= len(keys) <= 5 or any(not value for value in keys) or len(keys) != len(set(keys)):
                    raise ValueError("invalid_key_ring")
                return MultiFernet([Fernet(value) for value in keys])
            key = legacy.encode("ascii")
            if not key:
                if self.settings.auth_mode == "oidc":
                    raise ValueError("explicit_key_required")
                target = Path(self.settings.db_path).parent / ".connector-vault.key"
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink():
                    raise ValueError("symlink")
                try:
                    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    key = target.read_bytes()
                else:
                    key = Fernet.generate_key()
                    with os.fdopen(descriptor, "wb") as output:
                        output.write(key)
                    os.chmod(target, 0o600)
            return MultiFernet([Fernet(key)])
        except (ValueError, OSError, UnicodeError):
            raise DomainError(
                "integration_unavailable", "Le coffre de connexion doit être vérifié par l’administrateur."
            ) from None

    def encrypt(self, value):
        return (
            self._fernet()
            .encrypt(canonical_json({"tenant_id": self.settings.tenant_id, "payload": value}).encode())
            .decode("ascii")
        )

    def decrypt(self, value):
        try:
            envelope = json.loads(self._fernet().decrypt(value.encode("ascii")))
            if envelope.get("tenant_id") != self.settings.tenant_id or not isinstance(
                envelope.get("payload"), dict
            ):
                raise ValueError("vault_scope_mismatch")
            return envelope["payload"]
        except (InvalidToken, ValueError, TypeError, UnicodeError):
            raise DomainError(
                "integration_unavailable", "Le coffre de connexion doit être vérifié par l’administrateur."
            ) from None

    def rotate(self, value):
        self.decrypt(value)  # Includes tenant binding before rotation.
        try:
            return self._fernet().rotate(value.encode("ascii")).decode("ascii")
        except (InvalidToken, ValueError, UnicodeError):
            raise DomainError("integration_unavailable", "La rotation du coffre n’a pas pu être validée.") from None


class ConnectionHub:
    def __init__(self, repo, settings, *, policy=None, reader_factory=None):
        self.repo, self.settings = repo, settings
        self.policy, self.vault = policy or IntegrationPolicy.from_env(), SecretVault(settings)
        self.reader_factory = reader_factory
        self.oauth_service = None
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS connector_connections(
                id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,provider TEXT NOT NULL,label TEXT NOT NULL,
                endpoint TEXT NOT NULL,username TEXT NOT NULL,mailbox TEXT NOT NULL,secret_ciphertext TEXT NOT NULL,
                status TEXT NOT NULL,calendar_choices TEXT NOT NULL DEFAULT '[]',folder_choices TEXT NOT NULL DEFAULT '[]',
                selected_calendars TEXT NOT NULL DEFAULT '[]',selected_folders TEXT NOT NULL DEFAULT '[]',revision INTEGER NOT NULL DEFAULT 0,
                last_sync_at TEXT,last_error TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                UNIQUE(tenant_id,id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS connector_onboarding(
                tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,completed_steps TEXT NOT NULL,dismissed INTEGER NOT NULL,
                revision INTEGER NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(tenant_id,actor_id))""")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(connector_connections)")}
            for column in ("last_mail_sync_at", "last_calendar_sync_at"):
                if column not in columns:
                    db.execute(f"ALTER TABLE connector_connections ADD COLUMN {column} TEXT")

    def _actor(self, actor, *, manage=False, external=False):
        if (
            not isinstance(actor, dict)
            or actor.get("tenant_id") != self.settings.tenant_id
            or not isinstance(actor.get("actor_id"), str)
            or not actor["actor_id"]
        ):
            raise DomainError("forbidden", "Cet accès ne correspond pas à votre espace.")
        if manage and actor.get("permissions", {}).get("organization", {}).get("write") is not True:
            raise DomainError("forbidden", "La configuration des connexions exige un administrateur.")
        if external and (
            not self.settings.auth_required
            or self.settings.mode == "public_demo"
            or self.settings.test_organization_self_join
            or not self.policy.egress_approved
        ):
            raise DomainError(
                "forbidden",
                "Les connexions réelles exigent un espace protégé et une autorisation serveur de sortie réseau.",
            )

    def _row(self, tenant, ident):
        row = self.repo._db.execute(
            "SELECT * FROM connector_connections WHERE tenant_id=? AND id=?", (tenant, ident)
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Cette connexion n’existe pas dans votre espace.")
        return dict(row)

    @staticmethod
    def _dto(row):
        selected = json.loads(row["selected_calendars"])
        folders = json.loads(row["selected_folders"])
        return {
            key: row[key]
            for key in (
                "id",
                "provider",
                "label",
                "endpoint",
                "username",
                "mailbox",
                "status",
                "revision",
                "last_sync_at",
                "last_mail_sync_at",
                "last_calendar_sync_at",
                "last_error",
            )
        } | {
            "has_secret": bool(row["secret_ciphertext"]),
            "calendars": [
                {**item, "selected": item["id"] in selected} for item in json.loads(row["calendar_choices"])
            ],
            "mail_folders": [
                {**item, "selected": item["id"] in folders} for item in json.loads(row["folder_choices"])
            ],
            "selected_calendar_ids": selected,
            "selected_folder_ids": folders,
        }

    def status(self, actor):
        self._actor(actor)
        manage = (
            actor.get("permissions", {}).get("organization", {}).get("write") is True
            and self.settings.auth_required
        )
        enabled = manage and not self.settings.test_organization_self_join and self.policy.egress_approved and bool(self.policy.allowed_hosts)
        providers = []
        for ident, label in PROVIDERS.items():
            oauth = ident in {"google", "microsoft365"}
            oauth_status = self.oauth_service.provider_status(ident) if oauth and self.oauth_service else None
            available = (enabled and bool(oauth_status and oauth_status["available"])) if oauth else enabled if ident != "ics" else self.settings.mode != "public_demo"
            reason = (
                (oauth_status["reason"] if oauth_status else "Le raccordement OAuth de ce fournisseur doit être configuré sur le serveur.")
                if oauth
                else "Disponible dans un espace protégé après autorisation du serveur."
                if not available
                else ""
            )
            if not manage and ident != "ics":
                reason = "Un administrateur de l’espace peut configurer cette connexion."
            providers.append(
                {
                    "id": ident,
                    "label": label,
                    "available": available,
                    "status": "requires_administrator" if not manage and ident != "ics" else "requires_server_configuration" if not available else "available",
                    "requires_server_configuration": not available,
                    "reason": reason,
                    **({"authorization": "oauth2", "mail_only": True} if oauth else {}),
                }
            )
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT * FROM connector_connections WHERE tenant_id=? ORDER BY created_at,id",
                (self.settings.tenant_id,),
            ).fetchall()
        return {
            "providers": providers,
            "connections": [self._dto(dict(row)) for row in rows] if manage else [],
            "can_manage": manage,
            "public_demo": self.settings.mode == "public_demo",
            "test_organization": self.settings.test_organization_self_join,
            "external_connections_enabled": enabled,
            "calendar_sync_mode": "read_only",
            "mail_sync_mode": "read_only",
        }

    def mail_status(self, actor):
        self._actor(actor)
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT * FROM connector_connections WHERE tenant_id=? AND provider IN ('exchange','google','microsoft365') AND status IN (?,?) AND secret_ciphertext<>?",
                (self.settings.tenant_id, "verified", "synced", ""),
            ).fetchall()
        enabled = [dict(row) for row in rows if json.loads(row["selected_folders"])]
        last = max((row["last_mail_sync_at"] for row in enabled if row["last_mail_sync_at"]), default=None)
        manage = actor.get("permissions", {}).get("organization", {}).get("write") is True and self.settings.auth_required
        return {
            "status": "read_only" if last else "ready" if enabled else "not_connected",
            "last_successful_mail_sync_at": last,
            "can_read": bool(enabled),
            "can_send": False,
            "remote_write_enabled": False,
            "connections": [
                {
                    "id": row["id"],
                    "label": row["label"],
                    "mailbox": row["mailbox"],
                    "last_mail_sync_at": row["last_mail_sync_at"],
                }
                for row in enabled if manage
            ],
        }

    def create(self, actor, values):
        self._actor(actor, manage=True, external=True)
        allowed = {"provider", "label", "endpoint", "username", "password", "mailbox"}
        if not isinstance(values, dict) or set(values) - allowed:
            raise DomainError("invalid_input", "Paramètres de connexion inconnus.")
        provider = values.get("provider")
        if provider not in {"exchange", "caldav"}:
            raise DomainError(
                "integration_unavailable", "Ce fournisseur demande une configuration OAuth serveur préalable."
            )
        endpoint = require_text(values.get("endpoint"), "endpoint", maximum=2000).strip()
        self.policy.endpoint(endpoint)
        if provider == "exchange" and urlsplit(endpoint).path.lower() != "/ews/exchange.asmx":
            raise DomainError(
                "invalid_input", "L’adresse du service Exchange doit se terminer par /EWS/Exchange.asmx."
            )
        label = require_text(values.get("label"), "label", maximum=200).strip()
        username = require_text(values.get("username"), "username", maximum=320).strip()
        password = require_text(values.get("password"), "password", maximum=4000)
        mailbox = require_text(
            values.get("mailbox", ""), "mailbox", maximum=320, empty=provider != "exchange"
        ).strip()
        if any(not value.isprintable() for value in (label, username, mailbox) if value):
            raise DomainError("invalid_input", "Les paramètres de connexion doivent tenir sur une ligne.")
        encrypted = self.vault.encrypt({"password": password})
        ident, now = str(uuid4()), utc_now()
        with self.repo._transaction() as db:
            count = db.execute(
                "SELECT count(*) FROM connector_connections WHERE tenant_id=?", (self.settings.tenant_id,)
            ).fetchone()[0]
            if count >= 20:
                raise DomainError("invalid_input", "Vingt connexions au maximum sont autorisées par espace.")
            db.execute(
                """INSERT INTO connector_connections(id,tenant_id,provider,label,endpoint,username,mailbox,secret_ciphertext,status,created_at,updated_at)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ident,
                    self.settings.tenant_id,
                    provider,
                    label,
                    endpoint,
                    username,
                    mailbox,
                    encrypted,
                    "not_tested",
                    now,
                    now,
                ),
            )
            return self._dto(self._row(self.settings.tenant_id, ident))

    @staticmethod
    def _revision(row, expected):
        if isinstance(expected, bool) or not isinstance(expected, int) or expected != row["revision"]:
            raise DomainError(
                "stale_revision", "La connexion a changé. Rechargez ses paramètres avant de poursuivre."
            )

    def reader(self, row):
        self.policy.endpoint(row["endpoint"])
        if row["provider"] in {"google", "microsoft365"}:
            if self.oauth_service is None:
                raise DomainError("integration_unavailable", "Le service de raccordement OAuth doit être configuré.")
            return self.oauth_service.reader(row)
        factory = self.reader_factory
        if factory is None:
            from .integrations.calendar_readers import open_reader

            factory = open_reader
        return factory(row, self.vault.decrypt(row["secret_ciphertext"]), self.policy)

    def probe(self, actor, ident, *, expected_revision):
        self._actor(actor, manage=True, external=True)
        with self.repo._lock:
            row = self._row(self.settings.tenant_id, ident)
            self._revision(row, expected_revision)
        reader = None
        try:
            reader = self.reader(row)
            result = reader.probe()
            calendars = self._choices(result.get("calendars", []))
            folders = self._choices(result.get("mail_folders", []))
        except Exception:
            raise DomainError(
                "integration_unavailable",
                "La connexion n’a pas pu être vérifiée. Contrôlez le serveur, les droits et les identifiants avec votre administrateur.",
            ) from None
        finally:
            if reader is not None:
                reader.close()
        with self.repo._transaction() as db:
            current = self._row(self.settings.tenant_id, ident)
            self._revision(current, expected_revision)
            db.execute(
                "UPDATE connector_connections SET status=?,calendar_choices=?,folder_choices=?,selected_calendars=?,selected_folders=?,revision=revision+1,last_error=?,updated_at=? WHERE tenant_id=? AND id=?",
                (
                    "verified",
                    canonical_json(calendars),
                    canonical_json(folders),
                    canonical_json(
                        [
                            x
                            for x in json.loads(row["selected_calendars"])
                            if x in {c["id"] for c in calendars}
                        ]
                    ),
                    canonical_json(
                        [x for x in json.loads(row["selected_folders"]) if x in {f["id"] for f in folders}]
                    ),
                    "",
                    utc_now(),
                    self.settings.tenant_id,
                    ident,
                ),
            )
            return self._dto(self._row(self.settings.tenant_id, ident))

    @staticmethod
    def _choices(items):
        if not isinstance(items, list) or len(items) > 100:
            raise ValueError("choice_limit")
        result = []
        for item in items:
            ident = require_text(item.get("id"), "calendar_id", maximum=2000)
            name = require_text(item.get("name") or ident, "calendar_name", maximum=500)
            if ident in {x["id"] for x in result}:
                raise ValueError("duplicate_choice")
            result.append({"id": ident, "name": name})
        return result

    def select(self, actor, ident, *, calendar_ids, folder_ids, expected_revision):
        self._actor(actor, manage=True, external=True)
        with self.repo._transaction() as db:
            row = self._row(self.settings.tenant_id, ident)
            self._revision(row, expected_revision)
            if row["status"] not in {"verified", "synced"}:
                raise DomainError("invalid_state", "Vérifiez la connexion avant de choisir son périmètre.")
            for selected, known in [
                (calendar_ids, json.loads(row["calendar_choices"])),
                (folder_ids, json.loads(row["folder_choices"])),
            ]:
                if (
                    not isinstance(selected, list)
                    or len(selected) > 100
                    or any(not isinstance(x, str) for x in selected)
                    or len(selected) != len(set(selected))
                    or any(x not in {item["id"] for item in known} for x in selected)
                ):
                    raise DomainError(
                        "invalid_input",
                        "Choisissez uniquement les agendas et dossiers vérifiés de cette connexion.",
                    )
            db.execute(
                "UPDATE connector_connections SET selected_calendars=?,selected_folders=?,revision=revision+1,updated_at=? WHERE tenant_id=? AND id=?",
                (
                    canonical_json(calendar_ids),
                    canonical_json(folder_ids),
                    utc_now(),
                    self.settings.tenant_id,
                    ident,
                ),
            )
            return self._dto(self._row(self.settings.tenant_id, ident))

    def disconnect(self, actor, ident, *, expected_revision):
        self._actor(actor, manage=True)
        with self.repo._transaction() as db:
            row = self._row(self.settings.tenant_id, ident)
            self._revision(row, expected_revision)
            if row["provider"] in {"google", "microsoft365"} and self.oauth_service:
                self.oauth_service.audit_disconnect(db, row, actor["actor_id"])
            db.execute(
                "UPDATE connector_connections SET secret_ciphertext=?,status=?,selected_calendars=?,selected_folders=?,revision=revision+1,updated_at=? WHERE tenant_id=? AND id=?",
                ("", "disconnected", "[]", "[]", utc_now(), self.settings.tenant_id, ident),
            )
            result = self._dto(self._row(self.settings.tenant_id, ident))
        if row["provider"] in {"google", "microsoft365"} and self.oauth_service:
            result["remote_authorization"] = self.oauth_service.revoke_after_disconnect(row)
        return result

    def sync_mail(self, actor, ident, *, expected_revision):
        self._actor(actor, manage=True, external=True)
        with self.repo._lock:
            row = self._row(self.settings.tenant_id, ident)
            self._revision(row, expected_revision)
            if (
                row["provider"] not in {"exchange", "google", "microsoft365"}
                or row["status"] not in {"verified", "synced"}
                or not json.loads(row["selected_folders"])
            ):
                raise DomainError(
                    "invalid_state",
                    "Choisissez un dossier de messagerie vérifié avant de synchroniser les courriels.",
                )
        reader = None
        try:
            reader = self.reader(row)

            def guard():
                with self.repo._lock:
                    self._revision(self._row(self.settings.tenant_id, ident), expected_revision)

            report = reader.collect_mail(self.repo, self.settings.tenant_id, ident, guard=guard)
        except DomainError:
            raise
        except Exception:
            raise DomainError(
                "integration_unavailable",
                "La collecte des courriels n’a pas pu être achevée. Les messages déjà enregistrés et leurs checkpoints durables sont conservés.",
            ) from None
        finally:
            if reader is not None:
                reader.close()
        with self.repo._transaction() as db:
            guard()
            db.execute(
                "UPDATE connector_connections SET status=?,revision=revision+1,last_sync_at=?,last_mail_sync_at=?,updated_at=? WHERE tenant_id=? AND id=?",
                ("synced", utc_now(), utc_now(), utc_now(), self.settings.tenant_id, ident),
            )
            return {**report, "connection": self._dto(self._row(self.settings.tenant_id, ident))}

    def onboarding(self, actor):
        self._actor(actor)
        browser = self.settings.mode == "public_demo"
        with self.repo._lock:
            row = (
                self.repo._db.execute(
                    "SELECT * FROM connector_onboarding WHERE tenant_id=? AND actor_id=?",
                    (self.settings.tenant_id, actor["actor_id"]),
                ).fetchone()
                if not browser
                else None
            )
        steps = json.loads(row["completed_steps"]) if row else []
        return {
            "steps": list(STEPS),
            "completed_steps": steps,
            "completed": set(STEPS) <= set(steps),
            "dismissed": bool(row["dismissed"]) if row else False,
            "revision": row["revision"] if row else 0,
            "persist_in_browser": browser,
            "updated_at": row["updated_at"] if row else None,
        }

    def save_onboarding(self, actor, values):
        self._actor(actor)
        if self.settings.mode == "public_demo":
            raise DomainError(
                "forbidden", "Le parcours de démonstration est conservé uniquement sur votre appareil."
            )
        steps = values.get("completed_steps", [])
        dismissed = values.get("dismissed", False)
        if (
            not isinstance(steps, list)
            or len(steps) > len(STEPS)
            or any(not isinstance(x, str) or x not in STEPS for x in steps)
            or len(set(steps)) != len(steps)
            or type(dismissed) is not bool
        ):
            raise DomainError("invalid_input", "Étapes de connexion invalides.")
        with self.repo._transaction() as db:
            previous = self.onboarding(actor)
            self._revision(previous, values.get("expected_revision"))
            db.execute(
                """INSERT INTO connector_onboarding VALUES(?,?,?,?,?,?) ON CONFLICT(tenant_id,actor_id) DO UPDATE SET
                          completed_steps=excluded.completed_steps,dismissed=excluded.dismissed,revision=excluded.revision,updated_at=excluded.updated_at""",
                (
                    self.settings.tenant_id,
                    actor["actor_id"],
                    canonical_json(steps),
                    int(dismissed),
                    previous["revision"] + 1,
                    utc_now(),
                ),
            )
        return self.onboarding(actor)


def register_connection_routes(app, repo, tenant, actor, settings):
    from fastapi import Depends
    from pydantic import BaseModel, ConfigDict, Field, SecretStr

    class Values(BaseModel):
        model_config = ConfigDict(extra="forbid")
        provider: str = Field(max_length=30)
        label: str = Field(min_length=1, max_length=200)
        endpoint: str = Field(min_length=1, max_length=2000)
        username: str = Field(min_length=1, max_length=320)
        mailbox: str = Field(default="", max_length=320)
        password: SecretStr = Field(min_length=1, max_length=4000)

    class Revision(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(ge=0, strict=True)

    class Selection(Revision):
        calendar_ids: list[str] = Field(default_factory=list, max_length=100)
        folder_ids: list[str] = Field(default_factory=list, max_length=100)

    class Progress(Revision):
        completed_steps: list[str] = Field(default_factory=list, max_length=5)
        dismissed: bool = False

    hub = ConnectionHub(repo, settings)

    @app.get("/api/v1/integrations")
    def status(current=Depends(actor)):
        return hub.status(current)

    @app.post("/api/v1/integrations/connections", status_code=201)
    def create(body: Values, current=Depends(actor)):
        values = body.model_dump(exclude={"password"})
        values["password"] = body.password.get_secret_value()
        return hub.create(current, values)

    @app.post("/api/v1/integrations/connections/{ident}/probe")
    def probe(ident: str, body: Revision, current=Depends(actor)):
        return hub.probe(current, ident, expected_revision=body.expected_revision)

    @app.put("/api/v1/integrations/connections/{ident}/selection")
    def selection(ident: str, body: Selection, current=Depends(actor)):
        return hub.select(
            current,
            ident,
            calendar_ids=body.calendar_ids,
            folder_ids=body.folder_ids,
            expected_revision=body.expected_revision,
        )

    @app.post("/api/v1/integrations/connections/{ident}/disconnect")
    def disconnect(ident: str, body: Revision, current=Depends(actor)):
        return hub.disconnect(current, ident, expected_revision=body.expected_revision)

    @app.post("/api/v1/integrations/connections/{ident}/sync-mail")
    def sync_mail(ident: str, body: Revision, current=Depends(actor)):
        return hub.sync_mail(current, ident, expected_revision=body.expected_revision)

    @app.get("/api/v1/onboarding")
    def onboarding(current=Depends(actor)):
        return hub.onboarding(current)

    @app.patch("/api/v1/onboarding")
    def progress(body: Progress, current=Depends(actor)):
        return hub.save_onboarding(current, body.model_dump())

    return hub
