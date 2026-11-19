"""Human site observations, with immutable source notes and native action links.

An action link is a reference to the project's existing Yjs document. It never
creates a Python action or silently accepts a fact extracted from a mail.
"""

from datetime import date
import json
import re
from uuid import uuid4

from .domain import DomainError, canonical_json, payload_hash, require_text, utc_now
from .project_access import access_scope

KINDS = ("Visite", "Anomalie", "Réserve")
STATUSES = ("À traiter", "Levée")
CREATE_FIELDS = {"client_id", "project_id", "kind", "date", "title", "detail", "author"}


def _line(value, label, maximum):
    value = require_text(value, label, maximum=maximum).strip()
    if not value.isprintable():
        raise DomainError("invalid_input", f"{label} doit tenir sur une ligne.")
    return value


def _revision(value):
    if type(value) is not int or value < 0:
        raise DomainError("invalid_input", "La version courante du constat est requise.")


def _native_id(value, label):
    value = require_text(value, label, maximum=200)
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", value):
        raise DomainError("invalid_input", "La référence de l’action native est invalide.")
    return value


class FieldReportService:
    def __init__(self, repo):
        self.repo = repo
        with repo._lock:
            repo._db.execute("""CREATE TABLE IF NOT EXISTS field_reports (
                id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,
                client_id TEXT NOT NULL,payload_hash TEXT NOT NULL,kind TEXT NOT NULL,
                report_date TEXT NOT NULL,title TEXT NOT NULL,detail TEXT NOT NULL,author TEXT NOT NULL,
                status TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0,source_id TEXT NOT NULL,
                last_source_id TEXT NOT NULL,created_by TEXT NOT NULL,action_link TEXT,
                created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                UNIQUE(tenant_id,id),UNIQUE(tenant_id,client_id),
                FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id),
                FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id))""")
            repo._db.execute(
                "CREATE INDEX IF NOT EXISTS field_reports_project ON field_reports(tenant_id,project_id,report_date)"
            )

    @staticmethod
    def _actor(tenant, actor, action):
        if (
            not isinstance(actor, dict)
            or actor.get("tenant_id") != tenant
            or actor.get("permissions", {}).get("workspace", {}).get(action) is not True
        ):
            raise DomainError("forbidden", "Votre accès ne permet pas cette opération sur les constats.")
        return require_text(actor.get("actor_id"), "actor_id", maximum=1000)

    def _row(self, tenant, ident):
        require_text(ident, "constat", maximum=200)
        row = self.repo._db.execute(
            "SELECT * FROM field_reports WHERE tenant_id=? AND id=?", (tenant, ident)
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Ce constat n’existe pas dans votre espace.")
        return dict(row)

    @staticmethod
    def _dto(row):
        return {
            key: row[key]
            for key in (
                "id",
                "project_id",
                "kind",
                "title",
                "detail",
                "author",
                "status",
                "revision",
                "source_id",
                "last_source_id",
                "created_at",
                "updated_at",
            )
        } | {
            "date": row["report_date"],
            "action_link": json.loads(row["action_link"]) if row["action_link"] else None,
        }

    def get(self, tenant, ident, actor):
        self._actor(tenant, actor, "read")
        access_scope(self.repo, actor).require_object('field_report', ident)
        with self.repo._lock:
            return self._dto(self._row(tenant, ident))

    def list(self, tenant, actor, *, project_id=None, status=None):
        self._actor(tenant, actor, "read")
        scope = access_scope(self.repo, actor)
        if project_id: scope.require_project(project_id)
        if status not in (None, "", "all", *STATUSES):
            raise DomainError("invalid_input", "Choisissez un statut de constat proposé.")
        with self.repo._lock:
            clause, scoped_args = scope.project_clause('project_id')
            conditions, args = ["tenant_id=?", clause], [tenant, *scoped_args]
            if project_id:
                require_text(project_id, "chantier", maximum=200)
                self.repo.get_project(tenant, project_id)
                conditions.append("project_id=?")
                args.append(project_id)
            if status and status != "all":
                conditions.append("status=?")
                args.append(status)
            where = " AND ".join(conditions)
            total = self.repo._db.execute(
                "SELECT count(*) FROM field_reports WHERE " + where, args
            ).fetchone()[0]
            rows = self.repo._db.execute(
                "SELECT * FROM field_reports WHERE "
                + where
                + " ORDER BY report_date DESC,created_at DESC,id DESC LIMIT 500",
                args,
            ).fetchall()
            return {
                "items": [self._dto(dict(row)) for row in rows],
                "total": total,
                "limit": 500,
                "can_edit": actor.get("permissions", {}).get("workspace", {}).get("write") is True,
            }

    def create(self, tenant, actor, values):
        actor_id = self._actor(tenant, actor, "write")
        if not isinstance(values, dict) or set(values) != CREATE_FIELDS:
            raise DomainError("invalid_input", "Les champs du constat sont incomplets ou inconnus.")
        client_id = _line(values.get("client_id"), "client_id", 100)
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", client_id):
            raise DomainError("invalid_input", "L’identifiant de saisie du constat est invalide.")
        prepared = {
            "client_id": client_id,
            "project_id": _line(values.get("project_id"), "Chantier", 200),
            "kind": _line(values.get("kind"), "Type", 30),
            "date": _line(values.get("date"), "Date", 10),
            "title": _line(values.get("title"), "Titre", 160),
            "detail": require_text(values.get("detail"), "Constat / compte rendu", maximum=20000),
            "author": _line(values.get("author"), "Auteur", 200),
        }
        if prepared["kind"] not in KINDS:
            raise DomainError("invalid_input", "Choisissez Visite, Anomalie ou Réserve.")
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", prepared["date"]):
                raise ValueError()
            date.fromisoformat(prepared["date"])
        except ValueError:
            raise DomainError("invalid_input", "La date du constat doit être une date valide.") from None
        digest = payload_hash({**prepared, "actor_id": actor_id})
        with self.repo._transaction() as db:
            access_scope(self.repo, actor).require_project(prepared['project_id'], write=True)
            self.repo.get_project(tenant, prepared["project_id"])
            existing = db.execute(
                "SELECT * FROM field_reports WHERE tenant_id=? AND client_id=?", (tenant, client_id)
            ).fetchone()
            if existing:
                if existing["payload_hash"] != digest:
                    raise DomainError(
                        "conflict",
                        "Cette saisie a déjà été enregistrée avec un autre contenu. Actualisez les constats.",
                    )
                return self._dto(dict(existing))
            ident, now = str(uuid4()), utc_now()
            body = (
                f"Constat terrain saisi par une personne — {prepared['kind']}\n"
                f"Date : {prepared['date']}\nTitre : {prepared['title']}\n"
                f"Auteur déclaré : {prepared['author']}\nStatut : À traiter\n\n{prepared['detail']}"
            )
            note = self.repo.add_note(
                tenant, prepared["project_id"], body, actor_id=actor_id, origin="human_field_report"
            )
            db.execute(
                """INSERT INTO field_reports(id,tenant_id,project_id,client_id,payload_hash,kind,report_date,title,detail,author,status,source_id,last_source_id,created_by,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    ident,
                    tenant,
                    prepared["project_id"],
                    client_id,
                    digest,
                    prepared["kind"],
                    prepared["date"],
                    prepared["title"],
                    prepared["detail"],
                    prepared["author"],
                    "À traiter",
                    note["source_id"],
                    note["source_id"],
                    actor_id,
                    now,
                    now,
                ),
            )
            payload = {"report_id": ident, "source_id": note["source_id"], "kind": prepared["kind"]}
            self.repo._event(db, tenant, prepared["project_id"], actor_id, "field_report.created", payload)
            self.repo._audit(
                db, tenant, prepared["project_id"], "field_report.created", actor_id, ident, payload
            )
            return self._dto(self._row(tenant, ident))

    def update(self, tenant, ident, actor, *, expected_revision, status):
        actor_id = self._actor(tenant, actor, "write")
        access_scope(self.repo, actor).require_object('field_report', ident, write=True)
        _revision(expected_revision)
        if status not in STATUSES:
            raise DomainError("invalid_input", "Choisissez À traiter ou Levée.")
        with self.repo._transaction() as db:
            access_scope(self.repo, actor).require_object('field_report', ident, write=True)
            row = self._row(tenant, ident)
            if row["revision"] != expected_revision:
                raise DomainError(
                    "stale_revision", "Ce constat a changé. Actualisez-le avant de modifier son statut."
                )
            if row["status"] == status:
                return self._dto(row)
            note = self.repo.add_note(
                tenant,
                row["project_id"],
                f"Statut du constat terrain « {row['title']} » : {row['status']} → {status}.\nConstat d’origine : {ident}.",
                actor_id=actor_id,
                origin="human_field_report",
            )
            db.execute(
                "UPDATE field_reports SET status=?,revision=revision+1,last_source_id=?,updated_at=? WHERE tenant_id=? AND id=?",
                (status, note["source_id"], utc_now(), tenant, ident),
            )
            payload = {
                "report_id": ident,
                "source_id": note["source_id"],
                "previous_status": row["status"],
                "status": status,
            }
            self.repo._event(db, tenant, row["project_id"], actor_id, "field_report.status_changed", payload)
            self.repo._audit(
                db, tenant, row["project_id"], "field_report.status_changed", actor_id, ident, payload
            )
            return self._dto(self._row(tenant, ident))

    def link_action(self, tenant, ident, actor, *, expected_revision, page_id, database_id, row_id):
        actor_id = self._actor(tenant, actor, "write")
        scope = access_scope(self.repo, actor)
        scope.require_object('field_report', ident, write=True)
        scope.require_object('page', page_id, write=True)
        _revision(expected_revision)
        link = {
            "page_id": _native_id(page_id, "page_id"),
            "database_id": _native_id(database_id, "database_id"),
            "row_id": _native_id(row_id, "row_id"),
            "source_key": "field-report:" + ident,
        }
        with self.repo._transaction() as db:
            scope.require_object('field_report', ident, write=True)
            scope.require_object('page', page_id, write=True)
            row = self._row(tenant, ident)
            if row["action_link"]:
                if json.loads(row["action_link"]) == link:
                    return self._dto(row)
                raise DomainError(
                    "conflict",
                    "Une action est déjà liée à ce constat. Retrouvez-la dans les Actions du chantier.",
                )
            if row["revision"] != expected_revision:
                raise DomainError(
                    "stale_revision", "Ce constat a changé. Actualisez-le avant de confirmer son action liée."
                )
            exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='native_pages'"
            ).fetchone()
            page = (
                db.execute(
                    "SELECT project_id FROM native_pages WHERE tenant_id=? AND id=?",
                    (tenant, link["page_id"]),
                ).fetchone()
                if exists
                else None
            )
            if not page or page["project_id"] != row["project_id"]:
                raise DomainError(
                    "invalid_input", "L’action doit appartenir à la page native de ce chantier."
                )
            note = self.repo.add_note(
                tenant,
                row["project_id"],
                f"Action native liée au constat terrain « {row['title']} ».\nConstat : {ident}\nPage : {link['page_id']}\nLigne : {link['row_id']}",
                actor_id=actor_id,
                origin="human_field_report",
            )
            db.execute(
                "UPDATE field_reports SET action_link=?,revision=revision+1,last_source_id=?,updated_at=? WHERE tenant_id=? AND id=?",
                (canonical_json(link), note["source_id"], utc_now(), tenant, ident),
            )
            payload = {"report_id": ident, "source_id": note["source_id"], "action_link": link}
            self.repo._event(db, tenant, row["project_id"], actor_id, "field_report.action_linked", payload)
            self.repo._audit(
                db, tenant, row["project_id"], "field_report.action_linked", actor_id, ident, payload
            )
            return self._dto(self._row(tenant, ident))


def register_field_report_routes(app, repo, tenant, actor, settings):
    from fastapi import Depends
    from pydantic import BaseModel, ConfigDict, Field

    class Create(BaseModel):
        model_config = ConfigDict(extra="forbid")
        client_id: str = Field(min_length=8, max_length=100)
        project_id: str = Field(min_length=1, max_length=200)
        kind: str = Field(min_length=1, max_length=30)
        date: str = Field(min_length=10, max_length=10)
        title: str = Field(min_length=1, max_length=160)
        detail: str = Field(min_length=1, max_length=20000)
        author: str = Field(min_length=1, max_length=200)

    class Status(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(strict=True, ge=0)
        status: str = Field(min_length=1, max_length=30)

    class Link(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(strict=True, ge=0)
        page_id: str = Field(min_length=1, max_length=200)
        database_id: str = Field(min_length=1, max_length=200)
        row_id: str = Field(min_length=1, max_length=200)

    service = FieldReportService(repo)

    @app.get("/api/v1/field-reports")
    def reports(project_id: str | None = None, status: str | None = None, current=Depends(actor)):
        return service.list(tenant, current, project_id=project_id, status=status)

    @app.post("/api/v1/field-reports", status_code=201)
    def create(body: Create, current=Depends(actor)):
        return service.create(tenant, current, body.model_dump())

    @app.get("/api/v1/field-reports/{ident}")
    def report(ident: str, current=Depends(actor)):
        return service.get(tenant, ident, current)

    @app.patch("/api/v1/field-reports/{ident}")
    def status(ident: str, body: Status, current=Depends(actor)):
        return service.update(tenant, ident, current, **body.model_dump())

    @app.post("/api/v1/field-reports/{ident}/action-link")
    def action(ident: str, body: Link, current=Depends(actor)):
        return service.link_action(tenant, ident, current, **body.model_dump())

    return service
