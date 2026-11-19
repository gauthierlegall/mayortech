"""Explicit dossier authorization for active OIDC identities, before retrieval.

Scopes retain only trusted identity keys, never cached roles or grants. Every
predicate reloads authority so revocation also applies to an existing scope.
Supports municipal commissions, restricted dossiers, and role-based permissions.
"""
from __future__ import annotations

import json
import re

from .domain import DomainError


def _denied():
    raise DomainError("not_found", "Cet objet n’est pas disponible dans votre périmètre.")


def _column(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?", value
    ):
        raise ValueError("Internal SQL column expected")
    return value


class ProjectAccess:
    def __init__(self, repo, settings):
        self.repo = repo
        self.enabled = getattr(settings, "auth_mode", None) == "oidc"
        with repo._transaction() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS project_grants(
                tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,project_id TEXT NOT NULL,
                granted_by TEXT NOT NULL,created_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,actor_id,project_id),
                FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id))"""
            )

    def scope(self, actor, commission_id=None):
        if not self.enabled:
            return UnrestrictedScope(self.repo)
        if (
            not isinstance(actor, dict)
            or not isinstance(actor.get("tenant_id"), str)
            or not isinstance(actor.get("actor_id"), str)
            or not actor["tenant_id"]
            or not actor["actor_id"]
        ):
            _denied()
        result = AccessScope(self.repo, actor["tenant_id"], actor["actor_id"], commission_id=commission_id)
        result._role()
        return result


class UnrestrictedScope:
    restricted = False
    all_projects = True
    visible_project_ids = ()

    def __init__(self, repo):
        self.repo = repo

    def require_project(self, ident, write=False):
        return None

    def require_project_contents(self, ident, write=False):
        return None

    def require_source(self, ident):
        return None

    def require_object(self, kind, ident, write=False):
        return None

    def project_clause(self, column):
        return "1=1", []

    def source_clause(self, column):
        return "1=1", []

    def sanitize_source(self, source):
        return source

    def sanitize_memory(self, memory):
        return memory

    def require_context(self, context, citations=()):
        return None

    def permits_source(self, ident):
        return True

    def permits_project(self, ident, write=False):
        return True

    def project_effective_role(self, ident):
        return "admin"

    def project_capabilities(self, ident):
        return {
            "can_read": True,
            "can_edit": True,
            "can_submit_for_review": True,
            "role": "admin",
        }

    def commission_capabilities(self, commission_id):
        return {
            "can_read": True,
            "can_edit": True,
            "can_submit_for_review": True,
            "role": "admin",
        }


class AccessScope(UnrestrictedScope):
    restricted = True

    def __init__(self, repo, tenant, actor, commission_id=None):
        super().__init__(repo)
        self.tenant, self.actor = tenant, actor
        self.commission_id = commission_id

    def _role(self):
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT role FROM identity_members WHERE tenant_id=? AND actor_id=? AND active=1",
                (self.tenant, self.actor),
            ).fetchone()
        if row is None or row["role"] not in {"admin", "editor", "reader"}:
            _denied()
        return row["role"]

    @property
    def all_projects(self):
        return self._role() == "admin"

    @property
    def visible_project_ids(self):
        clause, args = self.project_clause("p.id")
        with self.repo._lock:
            return tuple(
                row[0]
                for row in self.repo._db.execute(
                    "SELECT p.id FROM projects p WHERE p.tenant_id=? AND "
                    + clause
                    + " ORDER BY p.id",
                    [self.tenant, *args],
                )
            )

    def project_clause(self, column):
        column = _column(column)
        comm_filter = ""
        comm_args = []
        if self.commission_id:
            comm_filter = " AND p_acl.commission_id=?"
            comm_args = [self.commission_id]

        sql = f"""{column} IN (
            SELECT p_acl.id FROM projects p_acl
            WHERE p_acl.tenant_id=? {comm_filter} AND (
                EXISTS (
                    SELECT 1 FROM project_grants g
                    JOIN identity_members m ON m.tenant_id=g.tenant_id AND m.actor_id=g.actor_id AND m.active=1
                    WHERE g.tenant_id=p_acl.tenant_id AND g.actor_id=? AND g.project_id=p_acl.id
                )
                OR (
                    p_acl.visibility != 'restricted' AND EXISTS (
                        SELECT 1 FROM commission_members cm
                        JOIN identity_members m ON m.tenant_id=cm.tenant_id AND m.actor_id=cm.actor_id AND m.active=1
                        WHERE cm.tenant_id=p_acl.tenant_id AND cm.commission_id=p_acl.commission_id AND cm.actor_id=?
                    )
                )
                OR (
                    p_acl.visibility != 'restricted' AND p_acl.commission_id='commission-3' AND EXISTS (
                        SELECT 1 FROM identity_members m
                        WHERE m.tenant_id=p_acl.tenant_id AND m.actor_id=? AND m.active=1 AND m.role='admin'
                    )
                )
            )
        )"""
        args = [self.tenant, *comm_args, self.actor, self.actor, self.actor]
        return sql, args

    def source_clause(self, column):
        column = _column(column)
        if self.all_projects:
            return f"{column} IN (SELECT id FROM sources WHERE tenant_id=?)", [self.tenant]
        allowed, args = self.project_clause("acl_link.project_id")
        return (
            f"{column} IN (SELECT acl_source.id FROM sources acl_source WHERE acl_source.tenant_id=? "
            "AND EXISTS (SELECT 1 FROM source_links acl_any WHERE acl_any.tenant_id=acl_source.tenant_id AND acl_any.source_id=acl_source.id) "
            "AND NOT EXISTS (SELECT 1 FROM source_links acl_link WHERE acl_link.tenant_id=acl_source.tenant_id AND acl_link.source_id=acl_source.id AND NOT ("
            + allowed
            + ")))",
            [self.tenant, *args],
        )

    def require_project(self, ident, write=False):
        org_role = self._role()
        if write and org_role not in {"admin", "editor"}:
            _denied()
        with self.repo._lock:
            p = self.repo._db.execute(
                "SELECT id, commission_id, visibility FROM projects WHERE tenant_id=? AND id=?",
                (self.tenant, ident),
            ).fetchone()
            if p is None:
                _denied()
            comm_id = p["commission_id"] or "commission-3"
            visibility = p["visibility"] or "standard"

            has_grant = (
                self.repo._db.execute(
                    "SELECT 1 FROM project_grants g JOIN identity_members m ON m.tenant_id=g.tenant_id AND m.actor_id=g.actor_id AND m.active=1 WHERE g.tenant_id=? AND g.actor_id=? AND g.project_id=?",
                    (self.tenant, self.actor, ident),
                ).fetchone()
                is not None
            )

            cm = self.repo._db.execute(
                "SELECT cm.role FROM commission_members cm JOIN identity_members m ON m.tenant_id=cm.tenant_id AND m.actor_id=cm.actor_id AND m.active=1 WHERE cm.tenant_id=? AND cm.commission_id=? AND cm.actor_id=?",
                (self.tenant, comm_id, self.actor),
            ).fetchone()
            c_role = cm["role"] if cm else None

        if visibility == "restricted":
            if not has_grant:
                _denied()
            if write:
                if org_role not in {"admin", "editor"}:
                    _denied()
                if c_role not in {"admin", "editor"} and not (
                    comm_id == "commission-3" and org_role in {"admin", "editor"}
                ):
                    _denied()
            return

        if comm_id == "commission-3":
            if org_role == "admin":
                return
            if has_grant:
                if write and org_role not in {"admin", "editor"}:
                    _denied()
                return
            if c_role is not None:
                if write and (
                    org_role not in {"admin", "editor"} or c_role not in {"admin", "editor"}
                ):
                    _denied()
                return
            _denied()

        if has_grant:
            if write and org_role not in {"admin", "editor"}:
                _denied()
            return
        if c_role is not None:
            if write and (
                org_role not in {"admin", "editor"} or c_role not in {"admin", "editor"}
            ):
                _denied()
            return
        _denied()

    def require_source(self, ident):
        clause, args = self.source_clause("s.id")
        with self.repo._lock:
            if (
                self.repo._db.execute(
                    "SELECT 1 FROM sources s WHERE s.tenant_id=? AND s.id=? AND " + clause,
                    [self.tenant, ident, *args],
                ).fetchone()
                is None
            ):
                _denied()

    def require_project_contents(self, ident, write=False):
        self.require_project(ident, write=write)
        clause, args = self.source_clause("s.id")
        with self.repo._lock:
            if self.repo._db.execute(
                "SELECT 1 FROM sources s JOIN source_links l ON l.tenant_id=s.tenant_id AND l.source_id=s.id WHERE l.tenant_id=? AND l.project_id=? AND NOT ("
                + clause
                + ") LIMIT 1",
                [self.tenant, ident, *args],
            ).fetchone():
                _denied()

    def permits_source(self, ident):
        try:
            self.require_source(ident)
            return True
        except DomainError:
            return False

    def permits_project(self, ident, write=False):
        try:
            self.require_project(ident, write=write)
            return True
        except DomainError:
            return False

    def project_effective_role(self, ident):
        try:
            self.require_project(ident, write=True)
            return "editor" if self._role() != "admin" else "admin"
        except DomainError:
            try:
                self.require_project(ident, write=False)
                return "reader"
            except DomainError:
                return None

    def project_capabilities(self, ident):
        role = self.project_effective_role(ident)
        if role is None:
            return {
                "can_read": False,
                "can_edit": False,
                "can_submit_for_review": False,
                "role": None,
            }
        can_edit = role in {"admin", "editor"}
        return {
            "can_read": True,
            "can_edit": can_edit,
            "can_submit_for_review": can_edit,
            "role": role,
        }

    def commission_capabilities(self, commission_id):
        org_role = self._role()
        with self.repo._lock:
            cm = self.repo._db.execute(
                "SELECT cm.role FROM commission_members cm JOIN identity_members m ON m.tenant_id=cm.tenant_id AND m.actor_id=cm.actor_id AND m.active=1 WHERE cm.tenant_id=? AND cm.commission_id=? AND cm.actor_id=?",
                (self.tenant, commission_id, self.actor),
            ).fetchone()
            c_role = cm["role"] if cm else None
        if commission_id == "commission-3" and org_role == "admin":
            return {
                "can_read": True,
                "can_edit": True,
                "can_submit_for_review": True,
                "role": "admin",
            }
        if c_role is None:
            return {
                "can_read": False,
                "can_edit": False,
                "can_submit_for_review": False,
                "role": None,
            }
        effective_role = "reader" if org_role == "reader" else c_role
        can_edit = effective_role in {"admin", "editor"}
        return {
            "can_read": True,
            "can_edit": can_edit,
            "can_submit_for_review": can_edit,
            "role": effective_role,
        }

    def require_object(self, kind, ident, write=False):
        if write and self._role() not in {"admin", "editor"}:
            _denied()
        if kind in {"source", "mail"}:
            return self.require_source(ident)
        if kind == "project":
            return self.require_project(ident, write=write)
        tables = {
            "page": ("native_pages", "project_id"),
            "candidate": ("candidates", "project_id"),
            "review": ("candidates", "project_id"),
            "summary": ("summaries", "project_id"),
            "document": ("original_documents", "source_id"),
            "calendar_event": ("calendar_events", "project_id"),
            "field_report": ("field_reports", "project_id"),
        }
        if kind not in tables:
            _denied()
        table, column = tables[kind]
        with self.repo._lock:
            row = self.repo._db.execute(
                f"SELECT {column} FROM {table} WHERE tenant_id=? AND id=?",
                (self.tenant, ident),
            ).fetchone()
        if row is None:
            _denied()
        if column == "source_id":
            return self.require_source(row[0])
        if row[0] is None:
            if not self.all_projects:
                _denied()
            return None
        self.require_project(row[0], write=write)
        if kind in {"page", "summary"}:
            self.require_project_contents(row[0], write=write)
        if kind in {"candidate", "review"}:
            with self.repo._lock:
                candidate = self.repo._db.execute(
                    "SELECT source_id FROM candidates WHERE tenant_id=? AND id=?",
                    (self.tenant, ident),
                ).fetchone()
            self.require_source(candidate[0])
        if kind == "summary":
            with self.repo._lock:
                summary = self.repo._db.execute(
                    "SELECT snapshot,citations FROM summaries WHERE tenant_id=? AND id=?",
                    (self.tenant, ident),
                ).fetchone()
            snapshot, citations = json.loads(summary[0]), json.loads(summary[1])
            for source in snapshot.get("source_versions", []):
                self.require_source(source["id"])
            self.require_context({"scope_project_id": row[0]}, citations)

    def sanitize_source(self, source):
        self.require_source(source["id"])
        result = dict(source)
        result["candidate_project_ids"] = [
            ident for ident in source.get("candidate_project_ids", []) if self.permits_project(ident)
        ]
        if source.get("metadata", {}).get("parent_source_id") and not self.permits_source(
            source["metadata"]["parent_source_id"]
        ):
            result["metadata"] = {
                key: value
                for key, value in source["metadata"].items()
                if key != "parent_source_id"
            }
        return result

    def sanitize_memory(self, memory):
        self.require_project(memory["project"]["id"])
        result = dict(memory)
        result["sources"] = [
            self.sanitize_source(source)
            for source in memory["sources"]
            if self.permits_source(source["id"])
        ]
        allowed = {source["id"] for source in result["sources"]}
        for key in ("facts", "pending", "conflicts", "notes", "candidates", "history_candidates"):
            if key in result:
                result[key] = [
                    row
                    for row in result[key]
                    if row.get("source_id") in allowed
                    and all(proof.get("source_id") in allowed for proof in row.get("evidence", []))
                ]
        result["project"] = dict(result["project"])
        result["project"]["stats"] = {
            **result["project"].get("stats", {}),
            "sources": len(result["sources"]),
            "notes": len(result.get("notes", [])),
            "pending": len(result.get("pending", [])),
            "accepted": len(result.get("facts", [])),
        }
        return result

    def require_context(self, context, citations=()):
        if not isinstance(context, dict):
            _denied()
        for ident in context.get("project_revisions", {}):
            self.require_project(ident)
        if context.get("scope_project_id"):
            self.require_project(context["scope_project_id"])
        for ident in context.get("source_ids", []):
            self.require_source(ident)
        for ident in context.get("calendar_revisions", {}):
            self.require_object("calendar_event", ident)
        for citation in citations:
            if citation.get("project_id"):
                self.require_project(citation["project_id"])
            if citation.get("source_id"):
                self.require_source(citation["source_id"])
            if citation.get("calendar_event_id"):
                self.require_object("calendar_event", citation["calendar_event_id"])


def access_scope(repo, actor, commission_id=None):
    service = getattr(repo, "project_access", None)
    return service.scope(actor, commission_id=commission_id) if service is not None else UnrestrictedScope(repo)
