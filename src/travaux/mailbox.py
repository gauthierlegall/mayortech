"""Local mailbox views over immutable imported sources, plus private drafts.

There is no SMTP/EWS write transport here. Folder/read/star changes affect only
this application's actor-scoped overlay; they never modify or delete evidence.
"""

from __future__ import annotations

from email import policy
from email.errors import HeaderParseError
from email.headerregistry import Address
import hashlib
import json
from uuid import UUID, uuid4

from fastapi import Depends, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from .domain import DomainError, canonical_json, require_text, utc_now
from .project_access import access_scope


class MailboxError(DomainError):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(code, message)
        self.status = status


def recipients(values):
    """Parse individual RFC mailbox entries with Python's email parser.

    No CR/LF or control character can enter a header. Lists/groups belong in
    separate array entries, not an ambiguously parsed single recipient field.
    No DNS lookup or network operation occurs during validation.
    """
    if not isinstance(values, list) or len(values) > 100:
        raise ValueError("invalid_recipient_list")
    result = []
    for value in values:
        if (
            not isinstance(value, str)
            or len(value) > 1000
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise ValueError("invalid_recipient")
        try:
            header = policy.default.header_factory("To", value.strip())
            if (
                header.defects
                or len(header.addresses) != 1
                or any(group.display_name is not None for group in header.groups)
            ):
                raise ValueError()
            address = header.addresses[0]
            if not address.username or not address.domain:
                raise ValueError()
            domain = address.domain.encode("idna").decode("ascii").lower()
            normalized = Address(display_name=address.display_name, username=address.username, domain=domain)
            if len(normalized.addr_spec) > 254:
                raise ValueError()
        except (ValueError, TypeError, IndexError, UnicodeError, HeaderParseError, RecursionError):
            raise ValueError("invalid_recipient") from None
        formatted = str(normalized)
        if formatted not in result:
            result.append(formatted)
    return result


class MailFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")
    read: StrictBool | None = None
    starred: StrictBool | None = None
    folder: str | None = Field(default=None, max_length=20)
    expected_revision: StrictInt | None = Field(default=None, ge=0)

    @field_validator("folder")
    @classmethod
    def folder_name(cls, value):
        if value is not None and value not in {"inbox", "archive", "trash"}:
            raise ValueError("invalid_folder")
        return value


class DraftFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: list[str] = Field(default_factory=list, max_length=100)
    cc: list[str] = Field(default_factory=list, max_length=100)
    bcc: list[str] = Field(default_factory=list, max_length=100)
    subject: str = Field(default="", max_length=2000)
    body: str = Field(default="", max_length=200_000)
    in_reply_to: str | None = Field(default=None, max_length=200)
    mode: str = Field(default="compose", max_length=20)

    @field_validator("to", "cc", "bcc")
    @classmethod
    def recipient_fields(cls, value):
        return recipients(value)

    @field_validator("subject", "in_reply_to")
    @classmethod
    def header_field(cls, value):
        if value is not None and any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("invalid_header")
        return value

    @field_validator("body")
    @classmethod
    def plain_body(cls, value):
        if "\x00" in value:
            raise ValueError("invalid_body")
        return value

    @field_validator("mode")
    @classmethod
    def draft_mode(cls, value):
        if value not in {"compose", "reply", "forward"}:
            raise ValueError("invalid_draft_mode")
        return value


class CreateDraft(DraftFields):
    client_id: str | None = Field(default=None, max_length=36)

    @field_validator("client_id")
    @classmethod
    def valid_client_id(cls, value):
        if value is not None:
            value = str(UUID(value))
        return value


class PatchDraft(DraftFields):
    expected_revision: StrictInt | None = Field(default=None, ge=1)


class SendDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: str | None = Field(default=None, max_length=200)
    expected_revision: StrictInt | None = Field(default=None, ge=1)


SCHEMA = (
    """CREATE TABLE IF NOT EXISTS mailbox_message_state(
        tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL, source_id TEXT NOT NULL,
        folder TEXT NOT NULL DEFAULT 'inbox' CHECK(folder IN ('inbox','archive','trash')),
        is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0,1)),
        starred INTEGER NOT NULL DEFAULT 0 CHECK(starred IN (0,1)),
        revision INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
        PRIMARY KEY(tenant_id,actor_id,source_id),
        FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id))""",
    """CREATE TABLE IF NOT EXISTS mailbox_drafts(
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
        content TEXT NOT NULL, revision INTEGER NOT NULL, client_id TEXT,
        creation_hash TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        UNIQUE(tenant_id,actor_id,client_id))""",
    """CREATE TABLE IF NOT EXISTS mailbox_events(
        id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
        source_id TEXT, draft_id TEXT, action TEXT NOT NULL, metadata TEXT NOT NULL,
        created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_mailbox_drafts_owner ON mailbox_drafts(tenant_id,actor_id,updated_at)",
)


class MailboxRepository:
    def __init__(self, repo):
        self.repo = repo
        with repo._transaction() as db:
            for statement in SCHEMA:
                db.execute(statement)
            db.create_function(
                "mailbox_casefold", 1, lambda value: str(value or "").casefold(), deterministic=True
            )

    @staticmethod
    def _identity(tenant, actor):
        require_text(tenant, "tenant_id", maximum=100)
        require_text(actor, "actor_id", maximum=200)

    @staticmethod
    def _message_where():
        return """s.tenant_id=? AND json_extract(s.metadata,'$.note_id') IS NULL
            AND json_extract(s.metadata,'$.parent_source_id') IS NULL
            AND (coalesce(json_extract(s.metadata,'$.filename'),'')='' OR lower(json_extract(s.metadata,'$.filename')) LIKE '%.eml')"""

    @staticmethod
    def _is_mail(source):
        metadata = source["metadata"]
        filename = metadata.get("filename")
        return (
            not metadata.get("note_id")
            and not metadata.get("parent_source_id")
            and (not filename or str(filename).lower().endswith(".eml"))
        )

    def _source(self, tenant, source_id, *, fictitious_only=False):
        source = self.repo.get_source(tenant, source_id)
        if not self._is_mail(source):
            raise DomainError("not_found", "Courriel introuvable dans le périmètre autorisé.")
        if fictitious_only and source["metadata"].get("fictitious") is not True:
            raise MailboxError(
                403,
                "public_demo_restricted",
                "Seuls les courriels fictifs sont accessibles dans cette démonstration.",
            )
        return source

    def _event(self, db, tenant, actor, action, *, source_id=None, draft_id=None, metadata=None):
        # Audit contains identifiers/revisions only, never subject/body/recipients.
        db.execute(
            "INSERT INTO mailbox_events VALUES(?,?,?,?,?,?,?,?)",
            (
                str(uuid4()),
                tenant,
                actor,
                source_id,
                draft_id,
                action,
                canonical_json(metadata or {}),
                utc_now(),
            ),
        )

    @staticmethod
    def _overlay(source, state=None, *, preview=False):
        result = {
            **source,
            "folder": state["folder"] if state else "inbox",
            "read": bool(state["is_read"]) if state else False,
            "starred": bool(state["starred"]) if state else False,
            "mailbox_revision": state["revision"] if state else 0,
            "mailbox_updated_at": state["updated_at"] if state else None,
        }
        if preview:
            result.update(
                preview=source["body"][:1000],
                body=source["body"][:1000],
                body_truncated=len(source["body"]) > 1000,
            )
        return result

    def get_message(self, tenant, actor, source_id, *, fictitious_only=False):
        self._identity(tenant, actor)
        scope = access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor})
        scope.require_source(source_id)
        with self.repo._lock:
            source = self._source(tenant, source_id, fictitious_only=fictitious_only)
            state = self.repo._db.execute(
                "SELECT * FROM mailbox_message_state WHERE tenant_id=? AND actor_id=? AND source_id=?",
                (tenant, actor, source_id),
            ).fetchone()
            return self._overlay(scope.sanitize_source(source), state)

    def list_messages(
        self,
        tenant,
        actor,
        *,
        folder="inbox",
        project_id=None,
        q="",
        read=None,
        starred=None,
        limit=100,
        offset=0,
        fictitious_only=False,
    ):
        self._identity(tenant, actor)
        scope = access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor})
        if project_id is not None: scope.require_project(project_id)
        if (
            folder not in {"inbox", "archive", "trash", "all", "starred", "unread", "sent"}
            or len(q) > 200
            or not 1 <= limit <= 200
            or not 0 <= offset <= 100_000
            or (project_id is not None and (not isinstance(project_id, str) or not project_id.strip() or len(project_id) > 100))
        ):
            raise DomainError("invalid_input", "Filtre de messagerie invalide.")
        if folder == "sent":
            return {"items": [], "total": 0, "limit": limit, "offset": offset}
        where = self._message_where()
        args = [actor, tenant]
        clause, scoped_args = scope.source_clause('s.id')
        where += ' AND '+clause
        args.extend(scoped_args)
        if project_id is not None:
            # Membership is an immutable source link, never a title/body search.
            # EXISTS keeps totals and pagination correct even with multiple links.
            where += " AND EXISTS (SELECT 1 FROM source_links l WHERE l.tenant_id=s.tenant_id AND l.source_id=s.id AND l.project_id=?)"
            args.append(project_id)
        if fictitious_only:
            where += " AND json_type(s.metadata,'$.fictitious')='true'"
        if folder in {"inbox", "archive", "trash"}:
            where += " AND coalesce(m.folder,'inbox')=?"
            args.append(folder)
        if folder in {"starred", "unread"}:
            where += " AND coalesce(m.folder,'inbox')<>'trash'"
            where += " AND coalesce(m.starred,0)=1" if folder == "starred" else " AND coalesce(m.is_read,0)=0"
        for column, value in [("is_read", read), ("starred", starred)]:
            if value is not None:
                where += f" AND coalesce(m.{column},0)=?"
                args.append(int(value))
        if q.strip():
            where += " AND instr(mailbox_casefold(s.subject||char(10)||s.sender||char(10)||s.body),?)>0"
            args.append(q.strip().casefold())
        relation = (
            "FROM sources s LEFT JOIN mailbox_message_state m ON m.tenant_id=s.tenant_id AND m.source_id=s.id AND m.actor_id=? WHERE "
            + where
        )
        with self.repo._lock:
            total = self.repo._db.execute("SELECT count(*) " + relation, args).fetchone()[0]
            rows = self.repo._db.execute(
                "SELECT s.id,m.folder,m.is_read,m.starred,m.revision,m.updated_at "
                + relation
                + " ORDER BY s.received_at DESC,s.created_at DESC,s.id DESC LIMIT ? OFFSET ?",
                [*args, limit, offset],
            ).fetchall()
            items = [
                self._overlay(
                    scope.sanitize_source(self.repo.get_source(tenant, row["id"])),
                    row if row["folder"] is not None else None,
                    preview=True,
                )
                for row in rows
            ]
            return {"items": items, "total": total, "limit": limit, "offset": offset}

    def update_message(
        self, tenant, actor, source_id, changes, *, expected_revision=None, fictitious_only=False
    ):
        self._identity(tenant, actor)
        access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor}).require_source(source_id)
        changes = {
            key: value
            for key, value in changes.items()
            if key in {"folder", "read", "starred"} and value is not None
        }
        MailFlags.model_validate(changes)
        if not changes:
            raise DomainError("invalid_input", "Aucun indicateur de courrier à modifier.")
        with self.repo._transaction() as db:
            access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor}).require_source(source_id)
            self._source(tenant, source_id, fictitious_only=fictitious_only)
            old = db.execute(
                "SELECT * FROM mailbox_message_state WHERE tenant_id=? AND actor_id=? AND source_id=?",
                (tenant, actor, source_id),
            ).fetchone()
            revision = old["revision"] if old else 0
            if expected_revision is not None and expected_revision != revision:
                raise MailboxError(
                    409,
                    "stale_mail_flags",
                    "Les indicateurs ont changé. Rechargez ce courrier avant de réessayer.",
                )
            current = {
                "folder": old["folder"] if old else "inbox",
                "read": bool(old["is_read"]) if old else False,
                "starred": bool(old["starred"]) if old else False,
            }
            updated = {**current, **changes}
            if updated != current:
                db.execute(
                    "INSERT INTO mailbox_message_state VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(tenant_id,actor_id,source_id) DO UPDATE SET folder=excluded.folder,is_read=excluded.is_read,starred=excluded.starred,revision=excluded.revision,updated_at=excluded.updated_at",
                    (
                        tenant,
                        actor,
                        source_id,
                        updated["folder"],
                        int(updated["read"]),
                        int(updated["starred"]),
                        revision + 1,
                        utc_now(),
                    ),
                )
                self._event(
                    db,
                    tenant,
                    actor,
                    "mail.flags_changed",
                    source_id=source_id,
                    metadata={"changes": changes, "revision": revision + 1},
                )
            return self.get_message(tenant, actor, source_id, fictitious_only=fictitious_only)

    def folders(self, tenant, actor, *, include_drafts=True, fictitious_only=False):
        self._identity(tenant, actor)
        totals = {}
        for folder, name in [
            ("inbox", "Boîte de réception"),
            ("starred", "Favoris"),
            ("unread", "Non lus"),
            ("archive", "Archives"),
            ("trash", "Corbeille"),
            ("all", "Tous les courriels"),
        ]:
            total = self.list_messages(
                tenant, actor, folder=folder, limit=1, fictitious_only=fictitious_only
            )["total"]
            unread = self.list_messages(
                tenant, actor, folder=folder, read=False, limit=1, fictitious_only=fictitious_only
            )["total"]
            totals[folder] = {"id": folder, "name": name, "total": total, "unread": unread}
        drafts = self.list_drafts(tenant, actor)["total"] if include_drafts else 0
        return [
            *totals.values(),
            {"id": "drafts", "name": "Brouillons", "total": drafts, "unread": 0},
            {"id": "sent", "name": "Envoyés", "total": 0, "unread": 0},
        ]

    @staticmethod
    def _draft(row):
        return {
            "id": row["id"],
            **json.loads(row["content"]),
            "client_id": row["client_id"],
            "revision": row["revision"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _draft_row(self, db, tenant, actor, draft_id):
        scope = access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor})
        row = db.execute(
            "SELECT * FROM mailbox_drafts WHERE tenant_id=? AND actor_id=? AND id=?",
            (tenant, actor, draft_id),
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Brouillon introuvable dans le périmètre autorisé.")
        linked = json.loads(row['content']).get('in_reply_to')
        if linked: scope.require_source(linked)
        return row

    def get_draft(self, tenant, actor, draft_id):
        self._identity(tenant, actor)
        with self.repo._lock:
            return self._draft(self._draft_row(self.repo._db, tenant, actor, draft_id))

    def list_drafts(self, tenant, actor):
        self._identity(tenant, actor)
        scope = access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor})
        clause, args = scope.source_clause('s.id')
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT * FROM mailbox_drafts d WHERE tenant_id=? AND actor_id=? AND (json_extract(d.content,'$.in_reply_to') IS NULL OR EXISTS (SELECT 1 FROM sources s WHERE s.id=json_extract(d.content,'$.in_reply_to') AND "+clause+")) ORDER BY updated_at DESC,id DESC",
                (tenant, actor, *args),
            ).fetchall()
            return {"items": [self._draft(row) for row in rows], "total": len(rows), "storage": "server"}

    def create_draft(self, tenant, actor, values):
        self._identity(tenant, actor)
        parsed = CreateDraft.model_validate(values)
        content = parsed.model_dump(exclude={"client_id"})
        encoded = canonical_json(content)
        fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
        with self.repo._transaction() as db:
            if content["in_reply_to"]:
                access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor}).require_source(content['in_reply_to'])
                self._source(tenant, content["in_reply_to"])
            if parsed.client_id:
                old = db.execute(
                    "SELECT * FROM mailbox_drafts WHERE tenant_id=? AND actor_id=? AND client_id=?",
                    (tenant, actor, parsed.client_id),
                ).fetchone()
                if old:
                    if old["creation_hash"] != fingerprint:
                        raise MailboxError(
                            409,
                            "draft_creation_conflict",
                            "Cet identifiant de création appartient déjà à un brouillon. Rechargez-le avant de continuer.",
                        )
                    return self._draft(old)
            draft_id, now = str(uuid4()), utc_now()
            db.execute(
                "INSERT INTO mailbox_drafts VALUES(?,?,?,?,?,?,?,?,?)",
                (draft_id, tenant, actor, encoded, 1, parsed.client_id, fingerprint, now, now),
            )
            self._event(db, tenant, actor, "draft.created", draft_id=draft_id, metadata={"revision": 1})
            return self.get_draft(tenant, actor, draft_id)

    def update_draft(self, tenant, actor, draft_id, values, *, expected_revision=None):
        self._identity(tenant, actor)
        with self.repo._transaction() as db:
            old = self._draft_row(db, tenant, actor, draft_id)
            if expected_revision is not None and old["revision"] != expected_revision:
                raise MailboxError(
                    409,
                    "stale_draft",
                    "Une autre version du brouillon a été enregistrée. Votre saisie reste à comparer avant de remplacer son contenu.",
                )
            before = json.loads(old["content"])
            content = DraftFields.model_validate({**before, **values}).model_dump()
            if content["in_reply_to"]:
                access_scope(self.repo, {'tenant_id': tenant, 'actor_id': actor}).require_source(content['in_reply_to'])
                self._source(tenant, content["in_reply_to"])
            encoded = canonical_json(content)
            if encoded != old["content"]:
                db.execute(
                    "UPDATE mailbox_drafts SET content=?,revision=revision+1,updated_at=? WHERE tenant_id=? AND actor_id=? AND id=?",
                    (encoded, utc_now(), tenant, actor, draft_id),
                )
                self._event(
                    db,
                    tenant,
                    actor,
                    "draft.updated",
                    draft_id=draft_id,
                    metadata={"revision": old["revision"] + 1, "fields": sorted(values)},
                )
            return self.get_draft(tenant, actor, draft_id)

    def delete_draft(self, tenant, actor, draft_id, *, expected_revision=None):
        self._identity(tenant, actor)
        with self.repo._transaction() as db:
            old = self._draft_row(db, tenant, actor, draft_id)
            if expected_revision is not None and old["revision"] != expected_revision:
                raise MailboxError(409, "stale_draft", "Le brouillon a changé depuis son ouverture.")
            db.execute(
                "DELETE FROM mailbox_drafts WHERE tenant_id=? AND actor_id=? AND id=?",
                (tenant, actor, draft_id),
            )
            self._event(
                db, tenant, actor, "draft.deleted", draft_id=draft_id, metadata={"revision": old["revision"]}
            )


def register_mailbox_routes(app, repo, tenant, actor, settings):
    mailbox = MailboxRepository(repo)

    @app.exception_handler(MailboxError)
    async def mailbox_error(request, error):
        return JSONResponse(
            {"error": {"code": error.code, "message": error.message}}, status_code=error.status
        )

    def identity(current):
        if (
            not isinstance(current, dict)
            or not isinstance(current.get("actor_id"), str)
            or not current["actor_id"]
        ):
            raise MailboxError(401, "unauthenticated", "Connectez-vous pour accéder à la messagerie.")
        if current.get("tenant_id") != tenant:
            raise MailboxError(403, "forbidden", "Ce compte n'appartient pas à cet espace.")
        return current["actor_id"]

    def allowed(current, action):
        governance = getattr(app.state, "governance", None)
        if governance is not None:
            return bool(governance.authorize(current, "mail", action))
        permission = current.get("permissions", {}).get("mail", {}).get(action)
        return permission is not False

    def private_write(current):
        owner = identity(current)
        if not settings.auth_required or not allowed(current, "write"):
            raise MailboxError(
                403,
                "private_drafts_required",
                "Les brouillons serveur nécessitent un compte connecté autorisé. Dans la démonstration publique, ils restent dans votre navigateur.",
            )
        return owner

    def capability(current):
        hub = getattr(app.state, "connections", None)
        provider = hub.mail_status(current) if hub is not None else {"status": "not_connected"}
        return {
            "can_send": False,
            "server_drafts": bool(settings.auth_required and allowed(current, "write")),
            "can_compose": bool(settings.auth_required and allowed(current, "write")),
            "can_manage_flags": allowed(current, "flags"),
            "provider_status": provider["status"],
        }

    def fixture_only():
        return settings.mode == "public_demo"

    @app.get("/api/v1/mailbox/capabilities")
    def capabilities(current=Depends(actor)):
        identity(current)
        return capability(current)

    @app.get("/api/v1/mailbox/folders")
    def folders(current=Depends(actor)):
        owner = identity(current)
        hub = getattr(app.state, "connections", None)
        status = hub.mail_status(current) if hub is not None else {"status": "not_connected", "can_read": False, "connections": [], "last_successful_mail_sync_at": None}
        return {
            "items": mailbox.folders(
                tenant, owner, include_drafts=settings.auth_required, fictitious_only=fixture_only()
            ),
            "capabilities": capability(current),
            "account": {"name": "Messagerie institutionnelle" if status["can_read"] else "Courriels importés", "address": status["connections"][0]["mailbox"] if len(status["connections"]) == 1 else None, "status": status["status"], "last_sync_at": status.get("last_successful_mail_sync_at")},
        }

    @app.get("/api/v1/mailbox/messages")
    def messages(
        folder: str = "inbox",
        project_id: str | None = Query(default=None, min_length=1, max_length=100),
        q: str = Query(default="", max_length=200),
        read: bool | None = None,
        starred: bool | None = None,
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0, le=100_000),
        current=Depends(actor),
    ):
        return mailbox.list_messages(
            tenant,
            identity(current),
            folder=folder,
            project_id=project_id,
            q=q,
            read=read,
            starred=starred,
            limit=limit,
            offset=offset,
            fictitious_only=fixture_only(),
        )

    @app.get("/api/v1/mailbox/messages/{source_id}")
    def message(source_id: str, current=Depends(actor)):
        return mailbox.get_message(tenant, identity(current), source_id, fictitious_only=fixture_only())

    @app.patch("/api/v1/mailbox/messages/{source_id}")
    def flags(source_id: str, body: MailFlags, current=Depends(actor)):
        owner = identity(current)
        if not allowed(current, "flags"):
            raise MailboxError(
                403, "forbidden", "Ce compte ne peut pas modifier les indicateurs de courrier."
            )
        return mailbox.update_message(
            tenant,
            owner,
            source_id,
            body.model_dump(exclude={"expected_revision"}, exclude_none=True),
            expected_revision=body.expected_revision,
            fictitious_only=fixture_only(),
        )

    @app.get("/api/v1/mailbox/drafts")
    def drafts(current=Depends(actor)):
        owner = identity(current)
        if not settings.auth_required:
            return {"items": [], "total": 0, "storage": "browser", "capabilities": capability(current)}
        return {**mailbox.list_drafts(tenant, owner), "capabilities": capability(current)}

    @app.post("/api/v1/mailbox/drafts", status_code=201)
    def create_draft(body: CreateDraft, current=Depends(actor)):
        return mailbox.create_draft(tenant, private_write(current), body.model_dump())

    @app.get("/api/v1/mailbox/drafts/{draft_id}")
    def draft(draft_id: str, current=Depends(actor)):
        owner = identity(current)
        if not settings.auth_required:
            raise MailboxError(
                403, "private_drafts_required", "Les brouillons restent dans votre navigateur."
            )
        return mailbox.get_draft(tenant, owner, draft_id)

    @app.patch("/api/v1/mailbox/drafts/{draft_id}")
    def update_draft(draft_id: str, body: PatchDraft, current=Depends(actor)):
        return mailbox.update_draft(
            tenant,
            private_write(current),
            draft_id,
            body.model_dump(exclude_unset=True, exclude={"expected_revision"}),
            expected_revision=body.expected_revision,
        )

    @app.delete("/api/v1/mailbox/drafts/{draft_id}", status_code=204)
    def delete_draft(
        draft_id: str, expected_revision: int | None = Query(default=None, ge=1), current=Depends(actor)
    ):
        mailbox.delete_draft(tenant, private_write(current), draft_id, expected_revision=expected_revision)
        return Response(status_code=204)

    @app.post("/api/v1/mailbox/send")
    def send(body: SendDraft, current=Depends(actor)):
        identity(current)
        # No draft/source mutation and no network-capable transport is reachable.
        return JSONResponse(
            {
                "error": {
                    "code": "mail_transport_not_configured",
                    "message": "Aucun compte de messagerie n'est connecté. Aucun courrier n'a été envoyé ; votre brouillon est conservé.",
                }
            },
            status_code=503,
        )

    return mailbox
