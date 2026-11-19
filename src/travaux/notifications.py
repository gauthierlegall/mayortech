"""Actor/browser-scoped in-app reminders; no external sending in this module."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, StrictBool

from .conversations import ConversationService, conversation_owner
from .domain import DomainError, utc_now
from .project_access import access_scope


class NotificationPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    in_app: StrictBool | None = None
    telegram_enabled: StrictBool | None = None
    conversation_sync: StrictBool | None = None


class NotificationService:
    def __init__(self, repo, settings, *, calendars=None):
        self.repo, self.settings = repo, settings
        self.calendars = calendars
        with repo._lock:
            repo._db.executescript("""
                CREATE TABLE IF NOT EXISTS user_notifications(
                    id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,
                    owner_scope TEXT NOT NULL,event_key TEXT NOT NULL,project_id TEXT,
                    candidate_id TEXT,kind TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,
                    href TEXT NOT NULL,created_at TEXT NOT NULL,read_at TEXT,resolved_at TEXT,
                    UNIQUE(tenant_id,actor_id,owner_scope,event_key));
                CREATE INDEX IF NOT EXISTS user_notifications_owner
                    ON user_notifications(tenant_id,actor_id,owner_scope,created_at DESC);
                CREATE TABLE IF NOT EXISTS notification_preferences(
                    tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,owner_scope TEXT NOT NULL,
                    in_app INTEGER NOT NULL DEFAULT 1,telegram_enabled INTEGER NOT NULL DEFAULT 0,
                    conversation_sync INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(tenant_id,actor_id,owner_scope));
            """)

    def preferences(self, tenant, current, owner_scope):
        identity = ConversationService._identity(tenant, current, owner_scope)
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM notification_preferences WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                (tenant, identity, owner_scope),
            ).fetchone()
        return {
            key: bool(row[key]) if row else default
            for key, default in (("in_app", True), ("telegram_enabled", False), ("conversation_sync", False))
        }

    def update_preferences(self, tenant, current, owner_scope, **values):
        identity = ConversationService._identity(tenant, current, owner_scope)
        validated = NotificationPreferences(**values).model_dump(exclude_none=True)
        existing = self.preferences(tenant, current, owner_scope)
        existing.update(validated)
        with self.repo._transaction() as db:
            db.execute(
                "INSERT INTO notification_preferences VALUES(?,?,?,?,?,?) ON CONFLICT(tenant_id,actor_id,owner_scope) DO UPDATE SET in_app=excluded.in_app,telegram_enabled=excluded.telegram_enabled,conversation_sync=excluded.conversation_sync",
                (
                    tenant,
                    identity,
                    owner_scope,
                    int(existing["in_app"]),
                    int(existing["telegram_enabled"]),
                    int(existing["conversation_sync"]),
                ),
            )
        return existing

    def refresh(self, tenant, current, owner_scope):
        identity = ConversationService._identity(tenant, current, owner_scope)
        scope = access_scope(self.repo, current)
        preferences = self.preferences(tenant, current, owner_scope)
        if not (preferences["in_app"] or preferences["telegram_enabled"]):
            return
        today = datetime.now(ZoneInfo("Europe/Paris")).date()
        appointments = []
        if self.calendars is not None:
            if self.calendars.settings.tenant_id != tenant:
                raise DomainError("forbidden", "Cet agenda n’appartient pas à cet espace.")
            now = datetime.now(ZoneInfo("Europe/Paris"))
            appointments = self.calendars.events(
                current,
                start=(now - timedelta(minutes=1)).isoformat(),
                end=(now + timedelta(days=1)).isoformat(),
            )["items"]
        calendar_keys = set()
        with self.repo._transaction() as db:
            projects = [self.repo.get_project(tenant, ident) for ident in scope.visible_project_ids] if scope.restricted else self.repo.list_projects(tenant)
            for project in projects[:200]:
                memory = scope.sanitize_memory(self.repo.get_memory(tenant, project["id"]))
                for pending in memory["pending"][:100]:
                    self._enqueue(
                        db,
                        tenant,
                        identity,
                        owner_scope,
                        "pending:" + pending["id"],
                        project["id"],
                        pending["id"],
                        "pending",
                        "Une information attend votre vérification",
                        project["name"],
                    )
                if project["status"] not in {"completed", "closed"}:
                    for fact in memory["facts"]:
                        if (
                            fact["field"] not in {"delivery_date", "deadline", "acceptance_date"}
                            or fact["kind"] != "date"
                        ):
                            continue
                        try:
                            due = date.fromisoformat(fact["value"])
                        except (ValueError, TypeError):
                            continue
                        if today - timedelta(days=30) <= due <= today + timedelta(days=7):
                            self._enqueue(
                                db,
                                tenant,
                                identity,
                                owner_scope,
                                "deadline:" + fact["id"],
                                project["id"],
                                fact["id"],
                                "deadline",
                                "Échéance du chantier",
                                f"{project['name']} · {due.isoformat()}",
                            )
            for appointment in appointments:
                if appointment["status"] == "cancelled":
                    continue
                key = f"calendar:{appointment['id']}:{appointment['revision']}"
                calendar_keys.add(key)
                self._enqueue(
                    db,
                    tenant,
                    identity,
                    owner_scope,
                    key,
                    appointment["project_id"],
                    None,
                    "calendar",
                    "Rendez-vous de l’agenda",
                    appointment["title"] + " · " + appointment["start"],
                    href="#/agenda?"
                    + urlencode({"event": appointment["id"], "date": appointment["start"][:10]}),
                )
            existing = db.execute(
                "SELECT id,candidate_id,kind,event_key FROM user_notifications WHERE tenant_id=? AND actor_id=? AND owner_scope=? AND resolved_at IS NULL",
                (tenant, identity, owner_scope),
            ).fetchall()
            for row in existing:
                if row["kind"] == "calendar":
                    if row["event_key"] not in calendar_keys:
                        db.execute(
                            "UPDATE user_notifications SET resolved_at=? WHERE id=?", (utc_now(), row["id"])
                        )
                    continue
                if not row["candidate_id"]:
                    continue
                try:
                    candidate = self.repo.get_candidate(tenant, row["candidate_id"])
                    resolved = candidate["status"] != ("pending" if row["kind"] == "pending" else "accepted")
                except DomainError:
                    resolved = True
                if resolved:
                    db.execute(
                        "UPDATE user_notifications SET resolved_at=? WHERE id=?", (utc_now(), row["id"])
                    )

    @staticmethod
    def _enqueue(
        db, tenant, identity, owner_scope, key, project_id, candidate_id, kind, title, body, *, href=None
    ):
        db.execute(
            "INSERT OR IGNORE INTO user_notifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
            (
                str(uuid4()),
                tenant,
                identity,
                owner_scope,
                key,
                project_id,
                candidate_id,
                kind,
                title,
                body,
                href or f"#/chantiers/{project_id}?view=page",
                utc_now(),
            ),
        )

    def _visible_clause(self, current):
        scope = access_scope(self.repo, current)
        if scope.all_projects:
            return '1=1', []
        clause, args = scope.project_clause('project_id')
        source_clause, source_args = scope.source_clause('acl_candidate.source_id')
        return '('+clause+") AND (candidate_id IS NULL OR EXISTS (SELECT 1 FROM candidates acl_candidate WHERE acl_candidate.tenant_id=user_notifications.tenant_id AND acl_candidate.id=user_notifications.candidate_id AND "+source_clause+'))', [*args, *source_args]

    def list(self, tenant, current, owner_scope, *, refresh=True):
        identity = ConversationService._identity(tenant, current, owner_scope)
        clause, args = self._visible_clause(current)
        if refresh:
            self.refresh(tenant, current, owner_scope)
        if not self.preferences(tenant, current, owner_scope)["in_app"]:
            return {"items": [], "unread": 0}
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT * FROM user_notifications WHERE tenant_id=? AND actor_id=? AND owner_scope=? AND "+clause+" ORDER BY created_at DESC,id LIMIT 100",
                (tenant, identity, owner_scope, *args),
            ).fetchall()
        items = [
            {
                key: row[key]
                for key in (
                    "id",
                    "project_id",
                    "kind",
                    "title",
                    "body",
                    "href",
                    "created_at",
                    "read_at",
                    "resolved_at",
                )
            }
            for row in rows
        ]
        return {
            "items": items,
            "unread": sum(not item["read_at"] and not item["resolved_at"] for item in items),
        }

    def mark_read(self, tenant, current, owner_scope, notification_id):
        identity = ConversationService._identity(tenant, current, owner_scope)
        clause, args = self._visible_clause(current)
        with self.repo._transaction() as db:
            row = db.execute(
                "SELECT id FROM user_notifications WHERE tenant_id=? AND actor_id=? AND owner_scope=? AND id=? AND "+clause,
                (tenant, identity, owner_scope, notification_id, *args),
            ).fetchone()
            if row is None:
                raise DomainError("not_found", "Cette notification n’est pas disponible dans votre espace.")
            db.execute(
                "UPDATE user_notifications SET read_at=coalesce(read_at,?) WHERE id=?",
                (utc_now(), notification_id),
            )
        return {"id": notification_id, "read": True}


def register_notification_routes(app, repo, tenant, actor, settings, *, telegram=None, calendars=None):
    service = NotificationService(repo, settings, calendars=calendars)

    @app.get("/api/v1/notifications")
    def list_notifications(request: Request, response: Response, current=Depends(actor)):
        return service.list(tenant, current, conversation_owner(request, response, current, settings))

    @app.patch("/api/v1/notifications/{notification_id}/read")
    def mark_read(notification_id: str, request: Request, response: Response, current=Depends(actor)):
        return service.mark_read(
            tenant, current, conversation_owner(request, response, current, settings), notification_id
        )

    @app.get("/api/v1/notifications/settings")
    def preferences(request: Request, response: Response, current=Depends(actor)):
        owner = conversation_owner(request, response, current, settings)
        return {
            **service.preferences(tenant, current, owner),
            "telegram": telegram.status(tenant, current, owner)
            if telegram
            else {"configured": False, "linked": False},
            "default_external_policy": "alerts_links_only",
        }

    @app.patch("/api/v1/notifications/settings")
    def update_preferences(
        body: NotificationPreferences, request: Request, response: Response, current=Depends(actor)
    ):
        owner = conversation_owner(request, response, current, settings)
        if body.telegram_enabled or body.conversation_sync:
            if telegram is None:
                raise DomainError(
                    "integration_unavailable", "Connectez d’abord une messagerie de notification."
                )
            state = telegram.status(tenant, current, owner)
            if not state["linked"] or (body.conversation_sync and not state["content_relay_approved"]):
                raise DomainError(
                    "forbidden", "Le relais de contenu n’est pas autorisé pour cet espace ou ce compte."
                )
        result = service.update_preferences(tenant, current, owner, **body.model_dump(exclude_none=True))
        if telegram and (body.conversation_sync is not None or body.telegram_enabled is not None):
            telegram.preferences_changed(tenant, current, owner)
        return result

    return service
