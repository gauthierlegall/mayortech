"""Durable, bounded historical Exchange recovery. No live cursor is reused.

A batch is read without holding a database transaction. Before importing it,
the lease, cancellation state and approved connection scope are rechecked.
Originals, ingestion jobs, receipts, counters and the historical cursor commit
together, so replay is safe and a paused in-flight batch cannot advance it.
"""

from datetime import date, datetime, timedelta, timezone
from email import policy as email_policy
from email.parser import BytesHeaderParser
import hashlib
import json
from pathlib import Path
import re
import secrets
import time
from uuid import uuid4
from zoneinfo import ZoneInfo

from .documents import DocumentRepository
from .domain import DomainError, canonical_json, payload_hash
from .importing import import_mail
from .integrations.exchange_backfill import HistoryItem, HistoryPage, find_existing_exchange_original
from .integrations.mail import MailParseError
from .jobs import JobQueue


BATCH_SIZE = 5
LEASE_SECONDS = 360
ERRORS = {
    "batch_failed": (
        "Le lot historique n’a pas pu être enregistré. Les données et le curseur précédents sont conservés ; vous pouvez reprendre.",
        True,
    ),
    "backfill_read_failed": (
        "Le lot Exchange n’a pas pu être lu. Le curseur précédent est conservé ; vérifiez la connexion puis reprenez.",
        True,
    ),
    "backfill_cursor_invalid": (
        "Le curseur Exchange historique a expiré. Annulez cette reprise puis créez-en une nouvelle ; les originaux déjà enregistrés seront dédupliqués.",
        False,
    ),
    "connection_scope_changed": (
        "Le périmètre de la connexion a changé. Vérifiez les dossiers et le compte autorisés avant de reprendre.",
        True,
    ),
}


def _progress():
    return {
        name: 0
        for name in (
            "scanned",
            "imported",
            "already_present",
            "out_of_range",
            "unavailable",
            "quarantined",
            "read_flags",
            "batches",
            "folders_completed",
        )
    }


class MailBackfillService:
    def __init__(self, repo, settings, *, hub, clock=None):
        self.repo, self.settings, self.hub = repo, settings, hub
        self.clock = clock or time.time
        self.queue = JobQueue(Path(settings.db_path))
        self.documents = DocumentRepository(repo)
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS mail_backfill_jobs(
                id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,connection_id TEXT NOT NULL,created_by TEXT NOT NULL,status TEXT NOT NULL,
                start_date TEXT NOT NULL,end_date TEXT NOT NULL,start_at TEXT NOT NULL,end_at TEXT NOT NULL,
                folders TEXT NOT NULL,connection_label TEXT NOT NULL,mailbox TEXT NOT NULL,connection_scope_hash TEXT NOT NULL,
                progress TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0,last_error TEXT,lease_token TEXT,lease_until REAL,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(tenant_id,id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS mail_backfill_folders(
                tenant_id TEXT NOT NULL,job_id TEXT NOT NULL,folder_id TEXT NOT NULL,sync_state TEXT,done INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(tenant_id,job_id,folder_id),FOREIGN KEY(tenant_id,job_id) REFERENCES mail_backfill_jobs(tenant_id,id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS mail_backfill_receipts(
                tenant_id TEXT NOT NULL,job_id TEXT NOT NULL,event_key TEXT NOT NULL,source_id TEXT,outcome TEXT NOT NULL,created_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,job_id,event_key),FOREIGN KEY(tenant_id,job_id) REFERENCES mail_backfill_jobs(tenant_id,id))""")
            db.execute(
                "CREATE INDEX IF NOT EXISTS mail_backfill_jobs_tenant_connection ON mail_backfill_jobs(tenant_id,connection_id,created_at)"
            )

    def _now(self):
        return datetime.fromtimestamp(self.clock(), timezone.utc).isoformat()

    def _authorize(self, actor, *, write=False, external=False):
        self.hub._actor(actor, manage=write, external=external)
        permissions = actor.get("permissions", {}).get("organization", {})
        if not (permissions.get("read") is True or permissions.get("write") is True):
            raise DomainError(
                "forbidden", "Vous ne disposez pas des droits sur les connexions de cet espace."
            )
        if write and (not self.settings.auth_required or self.settings.mode == "public_demo"):
            raise DomainError(
                "forbidden", "La reprise de courriels réels est réservée à un espace privé protégé."
            )

    def _can_manage(self, actor):
        return bool(
            self.settings.auth_required
            and self.settings.mode != "public_demo"
            and actor.get("permissions", {}).get("organization", {}).get("write") is True
        )

    def _row(self, ident):
        row = self.repo._db.execute(
            "SELECT * FROM mail_backfill_jobs WHERE tenant_id=? AND id=?", (self.settings.tenant_id, ident)
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Cette reprise n’existe pas dans votre espace.")
        return dict(row)

    @staticmethod
    def _fingerprint(connection):
        return payload_hash(
            [
                connection[key]
                for key in ("id", "provider", "endpoint", "username", "mailbox", "secret_ciphertext")
            ]
        )

    def _connection(self, ident, folders, scope=None):
        row = self.hub._row(self.settings.tenant_id, ident)
        selected = json.loads(row["selected_folders"])
        if (
            row["provider"] != "exchange"
            or row["status"] not in {"verified", "synced"}
            or not row["secret_ciphertext"]
            or any(folder not in selected for folder in folders)
        ):
            raise DomainError(
                "connection_scope_changed",
                "Le compte ou les dossiers Exchange ne sont plus autorisés pour cette reprise.",
            )
        if scope is not None and self._fingerprint(row) != scope:
            raise DomainError(
                "connection_scope_changed",
                "Le compte Exchange a changé depuis la préparation de cette reprise.",
            )
        self.hub.policy.endpoint(row["endpoint"])
        return row

    def preview(self, actor, values):
        self._authorize(actor, write=True)
        if not isinstance(values, dict) or set(values) - {
            "connection_id",
            "folder_ids",
            "start",
            "end",
            "expected_connection_revision",
        }:
            raise DomainError("invalid_input", "Paramètres de reprise inconnus.")
        folders = values.get("folder_ids")
        if (
            not isinstance(folders, list)
            or not 1 <= len(folders) <= 20
            or any(not isinstance(item, str) or not item or len(item) > 1024 for item in folders)
            or len(set(folders)) != len(folders)
        ):
            raise DomainError(
                "invalid_input", "Choisissez de un à vingt dossiers Exchange vérifiés distincts."
            )
        with self.repo._lock:
            row = self._connection(values.get("connection_id"), folders)
            self.hub._revision(row, values.get("expected_connection_revision"))
            choices = {item["id"]: item["name"] for item in json.loads(row["folder_choices"])}
        if any(folder not in choices for folder in folders):
            raise DomainError("invalid_input", "Un dossier n’a pas été vérifié dans cette connexion.")
        try:
            first, last = values.get("start"), values.get("end")
            if (
                not isinstance(first, str)
                or not isinstance(last, str)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", first)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", last)
            ):
                raise ValueError("iso_dates_required")
            lower, upper = date.fromisoformat(first), date.fromisoformat(last)
            today = datetime.fromtimestamp(self.clock(), ZoneInfo("Europe/Paris")).date()
            if lower > upper or upper > today:
                raise ValueError("historical_period_required")
            begin = datetime.combine(lower, datetime.min.time(), ZoneInfo("Europe/Paris")).astimezone(
                timezone.utc
            )
            finish = datetime.combine(
                upper + timedelta(days=1), datetime.min.time(), ZoneInfo("Europe/Paris")
            ).astimezone(timezone.utc)
            finish = min(finish, datetime.fromtimestamp(self.clock(), timezone.utc))
            if begin >= finish:
                raise ValueError("empty_period")
        except (ValueError, TypeError, OverflowError):
            raise DomainError(
                "invalid_input",
                "Choisissez une période historique valide, avec une fin inclusive au plus tard aujourd’hui.",
            ) from None
        return {
            "connection_id": row["id"],
            "connection_label": row["label"],
            "mailbox": row["mailbox"],
            "start": first,
            "end": last,
            "end_inclusive": True,
            "timezone": "Europe/Paris",
            "start_at": begin.isoformat(),
            "end_at": finish.isoformat(),
            "folders": [{"id": folder, "name": choices[folder]} for folder in folders],
            "batch_size": BATCH_SIZE,
            "scan_mode": "ews_initial_inventory",
            "total": None,
            "percent": None,
            "expected_connection_revision": row["revision"],
            "can_create": bool(self.hub.policy.egress_approved),
            "explanation": "Exchange parcourt l’inventaire des dossiers sélectionnés. Des éléments hors période peuvent être comptés, mais leur contenu MIME n’est pas repris. Seuls les courriels reçus dans la période sont importés ; leurs informations restent à vérifier.",
        }

    def create(self, actor, values):
        self._authorize(actor, write=True, external=True)
        plan = self.preview(actor, values)
        with self.repo._transaction() as db:
            connection = self._connection(plan["connection_id"], values["folder_ids"])
            self.hub._revision(connection, values["expected_connection_revision"])
            existing = db.execute(
                "SELECT 1 FROM mail_backfill_jobs WHERE tenant_id=? AND connection_id=? AND status NOT IN ('completed','cancelled')",
                (self.settings.tenant_id, connection["id"]),
            ).fetchone()
            if existing:
                raise DomainError(
                    "conflict",
                    "Une reprise existe déjà pour cette connexion. Reprenez-la ou annulez-la avant de préparer une autre période.",
                )
            ident, now = str(uuid4()), self._now()
            db.execute(
                """INSERT INTO mail_backfill_jobs(id,tenant_id,connection_id,created_by,status,start_date,end_date,start_at,end_at,folders,connection_label,mailbox,connection_scope_hash,progress,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ident,
                    self.settings.tenant_id,
                    connection["id"],
                    actor["actor_id"],
                    "ready",
                    plan["start"],
                    plan["end"],
                    plan["start_at"],
                    plan["end_at"],
                    canonical_json(plan["folders"]),
                    connection["label"],
                    connection["mailbox"],
                    self._fingerprint(connection),
                    canonical_json(_progress()),
                    now,
                    now,
                ),
            )
            for folder in plan["folders"]:
                db.execute(
                    "INSERT INTO mail_backfill_folders VALUES(?,?,?,?,0)",
                    (self.settings.tenant_id, ident, folder["id"], None),
                )
            return self._dto(self._row(ident), actor)

    def _dto(self, row, actor):
        folders = json.loads(row["folders"])
        states = {
            value["folder_id"]: dict(value)
            for value in self.repo._db.execute(
                "SELECT * FROM mail_backfill_folders WHERE tenant_id=? AND job_id=?",
                (self.settings.tenant_id, row["id"]),
            )
        }
        current = next((item for item in folders if not states[item["id"]]["done"]), None)
        progress = json.loads(row["progress"])
        progress["folders_total"] = len(folders)
        error = json.loads(row["last_error"]) if row["last_error"] else None
        interrupted = row["status"] == "running" and (row["lease_until"] or 0) <= self.clock()
        manage = self._can_manage(actor)
        return {
            "id": row["id"],
            "connection_id": row["connection_id"],
            "connection_label": row["connection_label"],
            "mailbox": row["mailbox"],
            "start": row["start_date"],
            "end": row["end_date"],
            "start_at": row["start_at"],
            "end_at": row["end_at"],
            "end_inclusive": True,
            "timezone": "Europe/Paris",
            "folders": folders,
            "current_folder": current,
            "status": row["status"],
            "revision": row["revision"],
            "progress": progress,
            "batch_size": BATCH_SIZE,
            "scan_mode": "ews_initial_inventory",
            "has_more": current is not None,
            "total": None,
            "percent": None,
            "has_warnings": bool(progress["unavailable"] or progress["quarantined"]),
            "last_error": error,
            "interrupted": interrupted,
            "can_manage": manage,
            "can_pause": manage and row["status"] in {"ready", "running"},
            "can_resume": manage
            and (
                row["status"] == "paused"
                or interrupted
                or (row["status"] == "failed" and (error or {}).get("retryable", True))
            ),
            "can_cancel": manage and row["status"] not in {"completed", "cancelled"},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get(self, actor, ident):
        self._authorize(actor)
        with self.repo._lock:
            return self._dto(self._row(ident), actor)

    def list(self, actor, *, connection_id=None):
        self._authorize(actor)
        with self.repo._lock:
            condition = "tenant_id=?" + (" AND connection_id=?" if connection_id else "")
            args = (self.settings.tenant_id, connection_id) if connection_id else (self.settings.tenant_id,)
            rows = self.repo._db.execute(
                "SELECT * FROM mail_backfill_jobs WHERE "
                + condition
                + " ORDER BY created_at DESC,id DESC LIMIT 100",
                args,
            ).fetchall()
            total = self.repo._db.execute(
                "SELECT count(*) FROM mail_backfill_jobs WHERE " + condition, args
            ).fetchone()[0]
            return {
                "items": [self._dto(dict(row), actor) for row in rows],
                "total": total,
                "limit": 100,
                "can_manage": self._can_manage(actor),
                "public_demo": self.settings.mode == "public_demo",
            }

    def control(self, actor, ident, action, *, expected_revision):
        self._authorize(actor, write=True)
        if action not in {"pause", "resume", "cancel"}:
            raise DomainError("invalid_input", "Commande de reprise inconnue.")
        with self.repo._transaction() as db:
            row = self._row(ident)
            self.hub._revision(row, expected_revision)
            if action == "pause":
                if row["status"] not in {"ready", "running"}:
                    raise DomainError("invalid_state", "Cette reprise ne peut pas être mise en pause.")
                status = "paused"
            elif action == "cancel":
                if row["status"] in {"completed", "cancelled"}:
                    raise DomainError("invalid_state", "Cette reprise est déjà terminée.")
                status = "cancelled"
            else:
                error = json.loads(row["last_error"]) if row["last_error"] else {}
                expired = row["status"] == "running" and (row["lease_until"] or 0) <= self.clock()
                if row["status"] not in {"paused", "failed"} and not expired:
                    raise DomainError("invalid_state", "Cette reprise ne peut pas être relancée.")
                if row["status"] == "failed" and not error.get("retryable", True):
                    raise DomainError("invalid_state", error["message"])
                self.hub._actor(actor, manage=True, external=True)
                self._connection(
                    row["connection_id"],
                    [item["id"] for item in json.loads(row["folders"])],
                    row["connection_scope_hash"],
                )
                status = "ready"
            db.execute(
                "UPDATE mail_backfill_jobs SET status=?,revision=revision+1,lease_token=NULL,lease_until=NULL,last_error=NULL,updated_at=? WHERE tenant_id=? AND id=?",
                (status, self._now(), self.settings.tenant_id, ident),
            )
            return self._dto(self._row(ident), actor)

    def _claim(self, actor, ident, expected_revision):
        self._authorize(actor, write=True, external=True)
        with self.repo._transaction() as db:
            row = self._row(ident)
            self.hub._revision(row, expected_revision)
            expired = row["status"] == "running" and (row["lease_until"] or 0) <= self.clock()
            if row["status"] != "ready" and not expired:
                raise DomainError("invalid_state", "Un lot est déjà en cours ou cette reprise est arrêtée.")
            connection = self._connection(
                row["connection_id"],
                [item["id"] for item in json.loads(row["folders"])],
                row["connection_scope_hash"],
            )
            folder = next(
                (
                    item
                    for item in json.loads(row["folders"])
                    if not db.execute(
                        "SELECT done FROM mail_backfill_folders WHERE tenant_id=? AND job_id=? AND folder_id=?",
                        (self.settings.tenant_id, ident, item["id"]),
                    ).fetchone()["done"]
                ),
                None,
            )
            if folder is None:
                raise DomainError("invalid_state", "Cette reprise n’a plus de dossier à parcourir.")
            cursor = db.execute(
                "SELECT sync_state FROM mail_backfill_folders WHERE tenant_id=? AND job_id=? AND folder_id=?",
                (self.settings.tenant_id, ident, folder["id"]),
            ).fetchone()["sync_state"]
            token = secrets.token_hex(24)
            db.execute(
                "UPDATE mail_backfill_jobs SET status=?,revision=revision+1,lease_token=?,lease_until=?,last_error=NULL,updated_at=? WHERE tenant_id=? AND id=?",
                ("running", token, self.clock() + LEASE_SECONDS, self._now(), self.settings.tenant_id, ident),
            )
            return self._row(ident), connection, folder, cursor, token

    def _valid_page(self, page, start, end, cursor):
        if (
            not isinstance(page, HistoryPage)
            or len(page.items) > BATCH_SIZE
            or type(page.has_more) is not bool
            or not isinstance(page.next_sync_state, str)
            or not 1 <= len(page.next_sync_state) <= 100_000
            or (page.has_more and page.next_sync_state == cursor)
        ):
            raise DomainError("backfill_read_failed", "Réponse historique incomplète.")
        total = 0
        for item in page.items:
            if (
                not isinstance(item, HistoryItem)
                or item.kind not in {"mail", "out_of_range", "unavailable", "read_flag"}
                or not isinstance(item.remote_id, str)
                or len(item.remote_id) > 900
                or (item.kind != "read_flag" and not item.remote_id)
            ):
                raise ValueError("invalid_history_item")
            if item.kind in {"mail", "out_of_range"}:
                if not isinstance(item.received_at, datetime) or item.received_at.tzinfo is None:
                    raise ValueError("server_date_required")
                inside = start <= item.received_at < end
                if inside != (item.kind == "mail"):
                    raise ValueError("history_date_scope_mismatch")
            if item.kind == "mail":
                if not isinstance(item.mime, bytes) or len(item.mime) > 10_000_000:
                    raise ValueError("history_mime_limit")
                total += len(item.mime)
            elif item.mime is not None:
                raise ValueError("unexpected_history_mime")
        if total > 50_000_000:
            raise ValueError("history_batch_limit")

    def _existing_source(self, db, connection_id, digest):
        return find_existing_exchange_original(db, self.settings.tenant_id, connection_id, digest)

    def _accept(self, db, row, folder, item, progress):
        progress["scanned"] += 1
        if item.kind != "mail":
            progress[
                {"out_of_range": "out_of_range", "unavailable": "unavailable", "read_flag": "read_flags"}[
                    item.kind
                ]
            ] += 1
            return
        digest = hashlib.sha256(item.mime).hexdigest()
        key = payload_hash(
            [folder["id"], item.remote_id, item.change_key, digest, item.received_at.isoformat()]
        )
        existing = self._existing_source(db, row["connection_id"], digest)
        if existing:
            source_id = existing["id"]
            outcome = "already_present"
            progress["already_present"] += 1
        else:
            metadata = {
                "connection_id": row["connection_id"],
                "folder_id": folder["id"],
                "remote_id": item.remote_id,
                "change_key": item.change_key,
                "event_kind": "historical",
                "historical_backfill": True,
                "backfill_job_id": row["id"],
                "server_received_at": item.received_at.isoformat(),
            }
            try:
                source = import_mail(
                    self.repo,
                    self.queue,
                    self.settings.tenant_id,
                    item.mime,
                    external_id=f"ews:{row['connection_id']}:{item.remote_id}",
                    metadata=metadata,
                )["source"]
                outcome = "imported"
                progress["imported"] += 1
            except MailParseError:
                header = BytesHeaderParser(policy=email_policy.default).parsebytes(
                    item.mime[:65536].split(b"\r\n\r\n", 1)[0]
                )
                source = self.repo.ingest_source(
                    self.settings.tenant_id,
                    f"ews-history-quarantine:{row['connection_id']}:{digest}",
                    str(header.get("Subject", "Courriel historique non analysé"))[:1000],
                    "Courriel historique non analysé. Consulter son original et vérifier son rattachement avant toute synthèse.",
                    received_at=item.received_at.isoformat(),
                    metadata={
                        **metadata,
                        "raw_sha256": digest,
                        "review_required": True,
                        "warnings": ["historical_mail_quarantined"],
                    },
                )
                self.documents.store(
                    self.settings.tenant_id,
                    source["id"],
                    item.mime,
                    "courrier.eml",
                    "message/rfc822",
                    kind="email",
                )
                outcome = "quarantined"
                progress["quarantined"] += 1
            source_id = source["id"]
        db.execute(
            "INSERT OR IGNORE INTO mail_backfill_receipts VALUES(?,?,?,?,?,?)",
            (self.settings.tenant_id, row["id"], key, source_id, outcome, self._now()),
        )

    def _commit(self, actor, ident, token, folder, page):
        with self.repo._transaction() as db:
            row = self._row(ident)
            if (
                row["status"] != "running"
                or row["lease_token"] != token
                or (row["lease_until"] or 0) <= self.clock()
            ):
                return self._dto(row, actor)
            self.hub._actor(actor, manage=True, external=True)
            self._connection(
                row["connection_id"],
                [item["id"] for item in json.loads(row["folders"])],
                row["connection_scope_hash"],
            )
            progress = json.loads(row["progress"])
            for item in page.items:
                self._accept(db, row, folder, item, progress)
            db.execute(
                "UPDATE mail_backfill_folders SET sync_state=?,done=? WHERE tenant_id=? AND job_id=? AND folder_id=?",
                (page.next_sync_state, int(not page.has_more), self.settings.tenant_id, ident, folder["id"]),
            )
            progress["batches"] += 1
            progress["folders_completed"] = db.execute(
                "SELECT count(*) FROM mail_backfill_folders WHERE tenant_id=? AND job_id=? AND done=1",
                (self.settings.tenant_id, ident),
            ).fetchone()[0]
            status = (
                "completed" if progress["folders_completed"] == len(json.loads(row["folders"])) else "ready"
            )
            db.execute(
                "UPDATE mail_backfill_jobs SET status=?,progress=?,revision=revision+1,lease_token=NULL,lease_until=NULL,last_error=NULL,updated_at=? WHERE tenant_id=? AND id=?",
                (status, canonical_json(progress), self._now(), self.settings.tenant_id, ident),
            )
            return self._dto(self._row(ident), actor)

    def _fail(self, actor, ident, token, error):
        code = error.code if isinstance(error, DomainError) and error.code in ERRORS else "batch_failed"
        message, retryable = ERRORS[code]
        with self.repo._transaction() as db:
            row = self._row(ident)
            if (
                row["status"] != "running"
                or row["lease_token"] != token
                or (row["lease_until"] or 0) <= self.clock()
            ):
                return self._dto(row, actor)
            db.execute(
                "UPDATE mail_backfill_jobs SET status=?,revision=revision+1,lease_token=NULL,lease_until=NULL,last_error=?,updated_at=? WHERE tenant_id=? AND id=?",
                (
                    "failed",
                    canonical_json({"code": code, "message": message, "retryable": retryable}),
                    self._now(),
                    self.settings.tenant_id,
                    ident,
                ),
            )
            return self._dto(self._row(ident), actor)

    def run(self, actor, ident, *, expected_revision):
        row, connection, folder, cursor, token = self._claim(actor, ident, expected_revision)
        reader = None
        try:
            reader = self.hub.reader(connection)
            start = datetime.fromisoformat(row["start_at"])
            end = datetime.fromisoformat(row["end_at"])
            page = reader.read_history_page(
                folder["id"], sync_state=cursor, start=start, end=end, page_size=BATCH_SIZE
            )
            self._valid_page(page, start, end, cursor)
            return self._commit(actor, ident, token, folder, page)
        except Exception as error:
            return self._fail(actor, ident, token, error)
        finally:
            if reader is not None:
                try:
                    reader.close()
                except Exception:
                    pass


def register_mail_backfill_routes(app, repo, tenant, actor, settings, *, hub):
    from fastapi import Depends
    from pydantic import BaseModel, ConfigDict, Field

    class Plan(BaseModel):
        model_config = ConfigDict(extra="forbid")
        connection_id: str = Field(min_length=1, max_length=200)
        folder_ids: list[str] = Field(min_length=1, max_length=20)
        start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", max_length=10)
        end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$", max_length=10)
        expected_connection_revision: int = Field(ge=0, strict=True)

    class Revision(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(ge=0, strict=True)

    service = MailBackfillService(repo, settings, hub=hub)

    @app.get("/api/v1/mail-backfills")
    def jobs(connection_id: str | None = None, current=Depends(actor)):
        return service.list(current, connection_id=connection_id)

    @app.post("/api/v1/mail-backfills/preview")
    def preview(body: Plan, current=Depends(actor)):
        return service.preview(current, body.model_dump())

    @app.post("/api/v1/mail-backfills", status_code=201)
    def create(body: Plan, current=Depends(actor)):
        return service.create(current, body.model_dump())

    @app.get("/api/v1/mail-backfills/{ident}")
    def job(ident: str, current=Depends(actor)):
        return service.get(current, ident)

    @app.post("/api/v1/mail-backfills/{ident}/run")
    def run(ident: str, body: Revision, current=Depends(actor)):
        return service.run(current, ident, expected_revision=body.expected_revision)

    @app.post("/api/v1/mail-backfills/{ident}/pause")
    def pause(ident: str, body: Revision, current=Depends(actor)):
        return service.control(current, ident, "pause", expected_revision=body.expected_revision)

    @app.post("/api/v1/mail-backfills/{ident}/resume")
    def resume(ident: str, body: Revision, current=Depends(actor)):
        return service.control(current, ident, "resume", expected_revision=body.expected_revision)

    @app.post("/api/v1/mail-backfills/{ident}/cancel")
    def cancel(ident: str, body: Revision, current=Depends(actor)):
        return service.control(current, ident, "cancel", expected_revision=body.expected_revision)

    return service
