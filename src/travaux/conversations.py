"""Private, durable, read-only dossier conversations with exact source evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import secrets
from uuid import uuid4

from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, content_hash, require_text, utc_now
from .retrieval import DossierRetrieval
from .project_access import access_scope

COOKIE = "travaux_chat_session"
RETENTION_DAYS = 30


def conversation_owner(request, response, current, settings):
    """Anonymous demo visitors must never share the server's common actor ID."""
    if settings.auth_required:
        return "private:" + current["actor_id"]
    token = request.cookies.get(COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        token = secrets.token_urlsafe(32)
    response.set_cookie(
        COOKIE,
        token,
        max_age=RETENTION_DAYS * 86400,
        httponly=True,
        secure=settings.mode != "demo",
        samesite="strict",
        path="/api/v1",
    )
    return "guest:" + hashlib.sha256(token.encode()).hexdigest()


class ThreadInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str | None = Field(default=None, max_length=160)
    title: str = Field(default="Nouvelle conversation", min_length=1, max_length=120)


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=2000)
    client_id: str = Field(min_length=1, max_length=100)
    intent: str = Field(default="question", pattern="^(question|change)$")


class ChangeConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_plan_hash: str = Field(pattern="^[a-f0-9]{64}$")


class ConversationService:
    def __init__(self, repo, settings, *, retrieval=None):
        self.repo, self.settings = repo, settings
        self.retrieval = retrieval or DossierRetrieval(repo, settings)
        with repo._lock:
            repo._db.executescript("""
                CREATE TABLE IF NOT EXISTS chat_conversations(
                    id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,
                    owner_scope TEXT NOT NULL,project_id TEXT,title TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chat_conversation_owner
                    ON chat_conversations(tenant_id,actor_id,owner_scope,updated_at DESC);
                CREATE TABLE IF NOT EXISTS chat_messages(
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,
                    conversation_id TEXT NOT NULL,client_id TEXT NOT NULL,content_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant')),content TEXT NOT NULL,
                    mode TEXT NOT NULL,citations_json TEXT NOT NULL,context_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,channel TEXT NOT NULL,created_at TEXT NOT NULL,
                    UNIQUE(conversation_id,client_id,role),
                    FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE);
            """)
        from .assistant_changes import AssistantChanges
        self.changes = AssistantChanges(repo, settings)

    @staticmethod
    def _identity(tenant, current, owner_scope):
        if (
            not isinstance(current, dict)
            or current.get("tenant_id") != tenant
            or current.get("permissions", {}).get("workspace", {}).get("read") is not True
        ):
            raise DomainError("forbidden", "Vous n’êtes pas autorisé à consulter ces dossiers.")
        identity = require_text(current.get("actor_id"), "actor_id", maximum=200)
        require_text(owner_scope, "conversation_scope", maximum=300)
        return identity

    @staticmethod
    def _expiry():
        return (datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS)).isoformat()

    def _purge(self, db):
        # Executed by the trusted service, never on a client-supplied table name.
        db.execute("DELETE FROM chat_conversations WHERE expires_at<=?", (utc_now(),))

    def _thread(self, db, tenant, identity, owner_scope, thread_id):
        row = db.execute(
            "SELECT * FROM chat_conversations WHERE id=? AND tenant_id=? AND actor_id=? AND owner_scope=? AND expires_at>?",
            (thread_id, tenant, identity, owner_scope, utc_now()),
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Cette conversation n’est pas disponible dans votre espace.")
        if row["project_id"]:
            access_scope(self.repo, {'tenant_id': tenant, 'actor_id': identity}).require_project(row['project_id'])
            self.repo.get_project(tenant, row["project_id"])
        scope = access_scope(self.repo, {'tenant_id': tenant, 'actor_id': identity})
        if scope.restricted:
            for message in db.execute("SELECT context_json,citations_json FROM chat_messages WHERE conversation_id=? AND role='assistant'", (thread_id,)):
                scope.require_context(json.loads(message['context_json']), json.loads(message['citations_json']))
        return dict(row)

    @staticmethod
    def _public_thread(row):
        return {
            key: row[key]
            for key in ("id", "project_id", "title", "version", "created_at", "updated_at", "expires_at")
        }

    @staticmethod
    def _message(row):
        return {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "mode": row["mode"],
            "citations": json.loads(row["citations_json"]),
            "context": json.loads(row["context_json"]),
            "warnings": json.loads(row["warnings_json"]),
            "channel": row["channel"],
            "created_at": row["created_at"],
        }

    def create(self, tenant, current, owner_scope, *, project_id=None, title="Nouvelle conversation"):
        identity = self._identity(tenant, current, owner_scope)
        scope = access_scope(self.repo, current)
        title = require_text(title, "title", maximum=120).strip()
        if project_id:
            scope.require_project(project_id)
            self.repo.get_project(tenant, project_id)
        now, thread_id = utc_now(), str(uuid4())
        with self.repo._transaction() as db:
            self._purge(db)
            count = db.execute(
                "SELECT count(*) FROM chat_conversations WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                (tenant, identity, owner_scope),
            ).fetchone()[0]
            if count >= 100:
                raise DomainError(
                    "conversation_limit", "Supprimez une ancienne conversation avant d’en créer une nouvelle."
                )
            db.execute(
                "INSERT INTO chat_conversations VALUES(?,?,?,?,?,?,0,?,?,?)",
                (thread_id, tenant, identity, owner_scope, project_id, title, now, now, self._expiry()),
            )
            row = self._thread(db, tenant, identity, owner_scope, thread_id)
        return self._public_thread(row)

    def list(self, tenant, current, owner_scope):
        identity = self._identity(tenant, current, owner_scope)
        scope = access_scope(self.repo, current)
        clause, args = scope.project_clause('project_id')
        with self.repo._transaction() as db:
            self._purge(db)
            rows = db.execute(
                "SELECT * FROM chat_conversations WHERE tenant_id=? AND actor_id=? AND owner_scope=? AND (project_id IS NULL OR "+clause+") ORDER BY updated_at DESC,id",
                (tenant, identity, owner_scope, *args),
            ).fetchall()
            visible = []
            for row in rows:
                try:
                    self._thread(db, tenant, identity, owner_scope, row['id'])
                except DomainError:
                    continue
                visible.append(self._public_thread(row))
                if len(visible) >= 100: break
        return visible

    def get(self, tenant, current, owner_scope, thread_id):
        identity = self._identity(tenant, current, owner_scope)
        with self.repo._lock:
            thread = self._thread(self.repo._db, tenant, identity, owner_scope, thread_id)
            rows = self.repo._db.execute(
                "SELECT * FROM chat_messages WHERE conversation_id=? ORDER BY sequence", (thread_id,)
            ).fetchall()
        return {
            **self._public_thread(thread),
            "messages": [self._message(row) for row in rows],
            "retention_days": RETENTION_DAYS,
        }

    def delete(self, tenant, current, owner_scope, thread_id):
        identity = self._identity(tenant, current, owner_scope)
        with self.repo._transaction() as db:
            self._thread(db, tenant, identity, owner_scope, thread_id)
            db.execute("DELETE FROM chat_conversations WHERE id=?", (thread_id,))

    def _existing_pair(self, db, thread_id, client_id, question_hash):
        rows = db.execute(
            "SELECT * FROM chat_messages WHERE conversation_id=? AND client_id=? ORDER BY sequence",
            (thread_id, client_id),
        ).fetchall()
        if not rows:
            return None
        if rows[0]["content_hash"] != question_hash:
            raise DomainError(
                "idempotency_conflict",
                "Cet identifiant correspond à une autre question. Votre texte reste à envoyer.",
            )
        return [self._message(row) for row in rows]

    def send(self, tenant, current, owner_scope, thread_id, content, client_id, *, channel="web", intent="question"):
        identity = self._identity(tenant, current, owner_scope)
        content = require_text(content, "question", maximum=2000).strip()
        if (
            not content
            or "\x00" in content
            or not isinstance(client_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", client_id)
        ):
            raise DomainError("invalid_input", "La question ou son identifiant est invalide.")
        if channel not in {"web", "telegram"}:
            raise DomainError("invalid_input", "Canal de conversation inconnu.")
        if intent not in {"question", "change"}:
            raise DomainError("invalid_input", "Type de demande inconnu.")
        digest = content_hash(content if intent == "question" else "change:"+content)
        with self.repo._lock:
            thread = self._thread(self.repo._db, tenant, identity, owner_scope, thread_id)
            existing = self._existing_pair(self.repo._db, thread_id, client_id, digest)
            if existing:
                return {"conversation_id": thread_id, "messages": existing, "replayed": True}
            previous = self.repo._db.execute(
                "SELECT content FROM chat_messages WHERE conversation_id=? AND role='user' ORDER BY sequence DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
            if thread["version"] >= 100:
                raise DomainError(
                    "conversation_limit",
                    "Cette conversation est longue. Ouvrez une nouvelle conversation pour continuer.",
                )
        # Network/model work is outside a transaction. No partial message pair
        # or fictitious successful reply is saved if retrieval/model fails.
        if intent == "change":
            proposal = self.changes.prepare(tenant, current, thread["project_id"], content, client_id=client_id, conversation_id=thread_id)
            answer = {"content": "Voici la modification proposée. Relisez le dossier et la valeur avant de confirmer. Aucun changement n’est appliqué sans votre confirmation.", "mode": "change_proposal", "citations": [], "context": {"scope_project_id": proposal["project_id"], "project_revisions": {proposal["project_id"]: proposal["project_revision"]}, "change_proposal_id": proposal["id"]}, "warnings": []}
        else:
            answer = self.retrieval.answer(
                tenant,
                content,
                project_id=thread["project_id"],
                actor=current,
                previous_query=previous["content"] if previous else "",
            )
        access_scope(self.repo, current).require_context(answer.get('context', {}), answer.get('citations', []))
        now = utc_now()
        with self.repo._transaction() as db:
            latest = self._thread(db, tenant, identity, owner_scope, thread_id)
            existing = self._existing_pair(db, thread_id, client_id, digest)
            if existing:
                return {"conversation_id": thread_id, "messages": existing, "replayed": True}
            if latest["version"] != thread["version"]:
                raise DomainError(
                    "conversation_changed",
                    "La conversation a évolué. Rechargez ses messages avant de réessayer ; votre texte reste à envoyer.",
                )
            for role, text, mode, citations, context, warnings in (
                ("user", content, "question", [], {}, []),
                (
                    "assistant",
                    answer["content"],
                    answer["mode"],
                    answer["citations"],
                    answer["context"],
                    answer["warnings"],
                ),
            ):
                db.execute(
                    "INSERT INTO chat_messages(id,conversation_id,client_id,content_hash,role,content,mode,citations_json,context_json,warnings_json,channel,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid4()),
                        thread_id,
                        client_id,
                        digest,
                        role,
                        text,
                        mode,
                        canonical_json(citations),
                        canonical_json(context),
                        canonical_json(warnings),
                        channel,
                        now,
                    ),
                )
            title = content[:90] if thread["title"] == "Nouvelle conversation" else thread["title"]
            db.execute(
                "UPDATE chat_conversations SET version=version+1,title=?,updated_at=?,expires_at=? WHERE id=?",
                (title, now, self._expiry(), thread_id),
            )
            pair = self._existing_pair(db, thread_id, client_id, digest)
        return {"conversation_id": thread_id, "messages": pair, "replayed": False}


def register_conversation_routes(app, repo, tenant, actor, settings, *, calendars=None):
    service = ConversationService(
        repo, settings, retrieval=DossierRetrieval(repo, settings, calendars=calendars)
    )

    @app.get("/api/v1/conversations")
    def list_threads(request: Request, response: Response, current=Depends(actor)):
        owner = conversation_owner(request, response, current, settings)
        return {
            "items": service.list(tenant, current, owner),
            "retention_days": RETENTION_DAYS,
            "anonymous_private_history": not settings.auth_required,
            "engine": "sqlite-fts5-bm25",
            "model_configured": settings.llm == "mistral",
            "model_connected": False,
        }

    @app.post("/api/v1/conversations", status_code=201)
    def create_thread(body: ThreadInput, request: Request, response: Response, current=Depends(actor)):
        owner = conversation_owner(request, response, current, settings)
        return service.create(tenant, current, owner, **body.model_dump())

    @app.get("/api/v1/conversations/{thread_id}")
    def get_thread(thread_id: str, request: Request, response: Response, current=Depends(actor)):
        return service.get(
            tenant, current, conversation_owner(request, response, current, settings), thread_id
        )

    @app.delete("/api/v1/conversations/{thread_id}", status_code=204)
    def delete_thread(thread_id: str, request: Request, response: Response, current=Depends(actor)):
        service.delete(tenant, current, conversation_owner(request, response, current, settings), thread_id)
        response.status_code = 204
        return response

    @app.post("/api/v1/conversations/{thread_id}/messages")
    def send(
        thread_id: str, body: MessageInput, request: Request, response: Response, current=Depends(actor)
    ):
        return service.send(
            tenant,
            current,
            conversation_owner(request, response, current, settings),
            thread_id,
            body.content,
            body.client_id,
            intent=body.intent,
        )

    def proposal_for(ident, request, response, current):
        proposal = service.changes.get(tenant, current, ident)
        service.get(tenant, current, conversation_owner(request, response, current, settings), proposal["conversation_id"])
        return proposal

    @app.get("/api/v1/assistant-changes/{ident}")
    def get_change(ident: str, request: Request, response: Response, current=Depends(actor)):
        return proposal_for(ident, request, response, current)

    @app.post("/api/v1/assistant-changes/{ident}/confirm")
    def confirm_change(ident: str, body: ChangeConfirmation, request: Request, response: Response, current=Depends(actor)):
        proposal_for(ident, request, response, current)
        return service.changes.confirm(tenant, current, ident, expected_plan_hash=body.expected_plan_hash)

    @app.post("/api/v1/assistant-changes/{ident}/reject")
    def reject_change(ident: str, request: Request, response: Response, current=Depends(actor)):
        proposal_for(ident, request, response, current)
        return service.changes.reject(tenant, current, ident)

    @app.get("/api/v1/projects/{project_id}/retrieval")
    def search(project_id: str, q: str, current=Depends(actor)):
        ConversationService._identity(tenant, current, "retrieval")
        return service.retrieval.search(tenant, q, project_id=project_id, actor=current)

    return service
