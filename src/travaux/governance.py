"""Tenant-scoped governance using the unmodified Apache PyCasbin domain model.

No identity provider, invitations or invented accounts: only the current local
operator/shared visitor is listed. See vendor/casbin_domains/UPSTREAM.json.
"""
from pathlib import Path
import json
import threading
from uuid import uuid4

import casbin
from fastapi import Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, require_text, utc_now
from .project_access import access_scope


RESOURCE_ACTIONS = {
    "workspace": ("read", "write"), "mail": ("read", "write", "flags"),
    "organization": ("read", "write"), "members": ("read",),
    "roles": ("read",), "audit": ("read",),
}
ALL_PERMISSIONS = {(resource, action) for resource, actions in RESOURCE_ACTIONS.items() for action in actions}
ROLE_PERMISSIONS = {
    "admin": ALL_PERMISSIONS,
    "editor": ALL_PERMISSIONS - {("organization", "write")},
    "reader": {("workspace", "read"), ("mail", "read"), ("organization", "read")},
    "visitor": {("workspace", "read"), ("workspace", "write"), ("mail", "read"), ("mail", "flags"),
                ("organization", "read"), ("members", "read"), ("roles", "read"), ("audit", "read")},
}
ROLE_NAMES = {"admin": "Administrateur", "editor": "Éditeur", "reader": "Lecteur", "visitor": "Visiteur"}
IDENTITY_CAPABILITIES = {"identity_provider": False, "member_management": False, "invitations": False}
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS organization_profiles(
        tenant_id TEXT PRIMARY KEY,name TEXT NOT NULL,service TEXT NOT NULL,
        revision INTEGER NOT NULL DEFAULT 0,updated_by TEXT NOT NULL,updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS organization_audit(
        id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,action TEXT NOT NULL,actor_id TEXT NOT NULL,
        before_json TEXT NOT NULL,after_json TEXT NOT NULL,created_at TEXT NOT NULL,
        FOREIGN KEY(tenant_id) REFERENCES organization_profiles(tenant_id))""",
)


class OrganizationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200, strict=True)
    service: str = Field(min_length=1, max_length=200, strict=True)
    expected_revision: int = Field(ge=0, strict=True)


class GovernanceService:
    def identity_capabilities(self):
        individual = self.settings.auth_mode == 'oidc'
        return {'identity_provider': individual, 'member_management': individual, 'invitations': False}

    def __init__(self, repository, tenant_id, settings):
        self.repo, self.tenant_id, self.settings = repository, tenant_id, settings
        self._acl_lock = threading.RLock()
        model = Path(__file__).parent / "vendor" / "casbin_domains" / "rbac_with_domains_model.conf"
        self.enforcer = casbin.Enforcer(str(model), enable_log=False)
        for role, permissions in ROLE_PERMISSIONS.items():
            for resource, action in sorted(permissions):
                self.enforcer.add_policy(role, tenant_id, resource, action)
        self.identity = getattr(repository, "identity_store", None)
        if settings.mode == "public_demo":
            self.bind_role("responsable-demo", "visitor")
        else:
            self.bind_role("responsable-demo" if settings.mode == "demo" else "responsable", "admin")
        with self.repo._transaction() as db:
            for statement in SCHEMA:
                db.execute(statement)
            db.execute("INSERT OR IGNORE INTO organization_profiles VALUES(?,?,?,?,?,?)",
                       (tenant_id, "Collectivité de démonstration" if settings.fixture_mode else "Organisation à renseigner",
                        "Service travaux", 0, "initialisation", utc_now()))

    @staticmethod
    def _subject(actor_id):
        # The literal actor ID "admin" must never equal a Casbin role subject.
        return "actor:" + actor_id

    def bind_role(self, actor_id, role):
        """Trusted server setup only. No HTTP role-assignment endpoint is exposed."""
        require_text(actor_id, "actor_id", maximum=200)
        if role not in ROLE_PERMISSIONS:
            raise ValueError("Unknown server-side role")
        with self._acl_lock:
            self.enforcer.add_role_for_user_in_domain(self._subject(actor_id), role, self.tenant_id)

    def authorize(self, actor, resource, action):
        if not isinstance(actor, dict) or actor.get("tenant_id") != self.tenant_id or not isinstance(actor.get("actor_id"), str) or not actor["actor_id"]:
            return False
        if not isinstance(resource, str) or not isinstance(action, str):
            return False
        if self.settings.mode == "public_demo" and (resource, action) not in ROLE_PERMISSIONS["visitor"]:
            return False
        if self.settings.auth_mode == "oidc":
            member = self.identity.get_active(actor["actor_id"]) if self.identity else None
            return bool(member and (resource, action) in ROLE_PERMISSIONS.get(member["role"], set()))
        with self._acl_lock:
            return bool(self.enforcer.enforce(self._subject(actor["actor_id"]), self.tenant_id, resource, action))

    def require_authorized(self, actor, resource, action):
        if not self.authorize(actor, resource, action):
            raise DomainError("forbidden", "Cet accès n'est pas autorisé dans le périmètre de votre espace.")

    def permissions(self, actor):
        return {resource: {action: self.authorize(actor, resource, action) for action in actions}
                for resource, actions in RESOURCE_ACTIONS.items()}

    def current_role(self, actor):
        if self.settings.mode == "public_demo":
            return "visitor"
        if self.settings.auth_mode == "oidc":
            member = self.identity.get_active(actor["actor_id"]) if self.identity else None
            return member["role"] if member else None
        with self._acl_lock:
            roles = self.enforcer.get_roles_for_user_in_domain(self._subject(actor["actor_id"]), self.tenant_id)
        return next((role for role in ("admin", "editor", "reader", "visitor") if role in roles), None)

    def organization(self, actor):
        self.require_authorized(actor, "organization", "read")
        with self.repo._lock:
            profile = dict(self.repo._db.execute("SELECT * FROM organization_profiles WHERE tenant_id=?", (self.tenant_id,)).fetchone())
        profile.pop("tenant_id")
        return {**profile, "can_manage": self.authorize(actor, "organization", "write"),
                "current_role": self.current_role(actor), "capabilities": self.identity_capabilities()}

    def update_organization(self, actor, name, service, expected_revision):
        self.require_authorized(actor, "organization", "write")
        values = {"name": require_text(name, "name", maximum=200).strip(),
                  "service": require_text(service, "service", maximum=200).strip()}
        if any(not value or not value.isprintable() for value in values.values()):
            raise DomainError("invalid_input", "Le nom et le service doivent être du texte sur une seule ligne.")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise DomainError("invalid_input", "La révision du profil relu est attendue.")
        with self.repo._transaction() as db:
            before = dict(db.execute("SELECT * FROM organization_profiles WHERE tenant_id=?", (self.tenant_id,)).fetchone())
            if before["revision"] != expected_revision:
                raise DomainError("stale_revision", "Le profil a changé. Rechargez-le avant de confirmer votre modification.")
            if any(before[key] != value for key, value in values.items()):
                now = utc_now()
                db.execute("UPDATE organization_profiles SET name=?,service=?,revision=revision+1,updated_by=?,updated_at=? WHERE tenant_id=?",
                           (values["name"], values["service"], actor["actor_id"], now, self.tenant_id))
                db.execute("INSERT INTO organization_audit VALUES(?,?,?,?,?,?,?)",
                           (str(uuid4()), self.tenant_id, "organization.updated", actor["actor_id"],
                            canonical_json({key: before[key] for key in values}), canonical_json(values), now))
        return self.organization(actor)

    def members(self, actor):
        self.require_authorized(actor, "members", "read")
        if self.settings.auth_mode == "oidc":
            admin = self.current_role(actor) == "admin"
            items = []
            for member in self.identity.list_members(include_inactive=admin):
                item = {"id": member["actor_id"], "display_name": member["display_name"], "role": member["role"], "role_label": ROLE_NAMES[member["role"]], "active": member["active"], "revision": member["revision"], "kind": "institutional_identity", "identity_verified": True, "is_current": member["actor_id"] == actor["actor_id"]}
                if admin:
                    item.update(issuer=member["issuer"], subject=member["subject"], email=member["email"])
                items.append(item)
            return {"items": items, "total": len(items), "can_manage": admin, "capabilities": {"identity_provider": True, "member_management": True, "invitations": False}}
        public = self.settings.mode == "public_demo"
        role = self.current_role(actor)
        return {"items": [{"id": actor["actor_id"], "display_name": "Visiteur" if public else "Opérateur de cet espace",
                            "role": role, "role_label": ROLE_NAMES.get(role, "Accès non attribué"),
                            "kind": "shared_access" if public else "local_operator", "is_current": True,
                            "identity_verified": False}], "total": 1, "can_manage": False,
                "capabilities": dict(IDENTITY_CAPABILITIES)}

    def roles(self, actor):
        self.require_authorized(actor, "roles", "read")
        visible = ["admin", "editor", "reader"] + (["visitor"] if self.settings.mode == "public_demo" else [])
        assignable = self.settings.auth_mode == 'oidc' and self.current_role(actor) == 'admin'
        with self._acl_lock:
            items = [{"id": role, "name": ROLE_NAMES[role], "assignable": assignable,
                      "permissions": [{"resource": resource, "action": action,
                                       "allowed": bool(self.enforcer.enforce(role, self.tenant_id, resource, action))}
                                      for resource, action in sorted(ALL_PERMISSIONS)]} for role in visible]
        return {"items": items, "current_role": self.current_role(actor), "capabilities": self.identity_capabilities(),
                "scope": "Les rôles des membres actifs se combinent avec les accès explicites aux dossiers." if self.settings.auth_mode == 'oidc' else "Permissions exécutées sur les ressources du même espace ; aucun compte Éditeur/Lecteur n'est créé par ces modèles."}

    def _provenance(self, project_id, payload, actor=None):
        scope = access_scope(self.repo, actor)
        candidate_id, source_id = payload.get("candidate_id"), payload.get("source_id")
        with self.repo._lock:
            if candidate_id:
                candidate = self.repo._db.execute("SELECT source_id FROM candidates WHERE tenant_id=? AND project_id=? AND id=?",
                                                  (self.tenant_id, project_id, candidate_id)).fetchone()
                source_id = candidate["source_id"] if candidate else None
            if not source_id and payload.get("note_id"):
                note = self.repo._db.execute("SELECT source_id FROM notes WHERE tenant_id=? AND project_id=? AND id=?",
                                             (self.tenant_id, project_id, payload["note_id"])).fetchone()
                source_id = note["source_id"] if note else None
            if not source_id:
                return None
            if not scope.permits_source(source_id):
                return None
            # Metadata only: listing the journal must not materialize note/mail bodies.
            row = self.repo._db.execute("SELECT s.id,s.body_hash,s.subject,s.version,s.metadata FROM sources s JOIN source_links l ON l.tenant_id=s.tenant_id AND l.source_id=s.id WHERE s.tenant_id=? AND s.id=? AND l.project_id=?",
                                        (self.tenant_id, source_id, project_id)).fetchone()
            if row is None:
                return None
            source = dict(row)
        metadata = json.loads(source["metadata"])
        return {"source_id": source["id"], "source_hash": source["body_hash"], "source_title": source["subject"],
                "candidate_id": candidate_id, "version": source["version"],
                "origin": "human_note" if metadata.get("note_id") else "attachment" if metadata.get("parent_source_id") else "mail"}

    def _actor_label(self, actor_id):
        if self.settings.auth_mode == 'oidc':
            with self.repo._lock:
                row = self.repo._db.execute('SELECT display_name FROM identity_members WHERE tenant_id=? AND actor_id=?', (self.tenant_id, actor_id)).fetchone()
            if row:
                return row['display_name']
        return {"responsable": "Opérateur de l'espace", "responsable-demo": "Accès de démonstration",
                "demo-initialisation": "Initialisation du corpus fictif", "initialisation": "Initialisation",
                "import-worker": "Import des documents"}.get(actor_id, "Compte ou service de l'espace")

    def audit(self, actor, project_id=None, limit=100):
        self.require_authorized(actor, "audit", "read")
        scope = access_scope(self.repo, actor)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise DomainError("invalid_input", "Choisir entre 1 et 200 entrées du journal.")
        if project_id:
            scope.require_project(project_id)
            self.repo.get_project(self.tenant_id, project_id)
        items, total = [], 0
        with self.repo._lock:
            for table, action_column, kind in (("events", "event_type", "project_event"), ("audit_events", "action", "audit")):
                where = "e.tenant_id=?" + (" AND e.project_id=?" if project_id else "")
                args = (self.tenant_id, project_id) if project_id else (self.tenant_id,)
                clause, scoped_args = scope.project_clause('e.project_id')
                where += ' AND '+clause
                args += tuple(scoped_args)
                if scope.restricted and not scope.all_projects:
                    source_clause, source_args = scope.source_clause('acl_source.id')
                    where += " AND (json_extract(e.payload,'$.source_id') IS NULL OR EXISTS (SELECT 1 FROM sources acl_source WHERE acl_source.tenant_id=e.tenant_id AND acl_source.id=json_extract(e.payload,'$.source_id') AND "+source_clause+'))'
                    args += tuple(source_args)
                    for key, reference_table in [('candidate_id', 'candidates'), ('note_id', 'notes')]:
                        source_clause, source_args = scope.source_clause('acl_reference.source_id')
                        where += f" AND (json_extract(e.payload,'$.{key}') IS NULL OR EXISTS (SELECT 1 FROM {reference_table} acl_reference WHERE acl_reference.tenant_id=e.tenant_id AND acl_reference.id=json_extract(e.payload,'$.{key}') AND "+source_clause+'))'
                        args += tuple(source_args)
                total += self.repo._db.execute(f"SELECT count(*) FROM {table} e WHERE {where}", args).fetchone()[0]
                # Identifiers above are fixed internal constants; all request values are bound.
                object_column = "NULL" if kind == "project_event" else "e.object_id"
                rows = self.repo._db.execute(f"SELECT e.id,e.{action_column} AS action,e.actor_id,e.created_at,e.project_id,e.payload,{object_column} AS object_id,p.name AS project_name,p.reference AS project_reference FROM {table} e JOIN projects p ON p.tenant_id=e.tenant_id AND p.id=e.project_id WHERE {where} ORDER BY e.created_at DESC,e.id DESC LIMIT ?", (*args, limit)).fetchall()
                for row in rows:
                    items.append({**dict(row), "kind": kind})
            if project_id is None and scope.all_projects:
                total += self.repo._db.execute("SELECT count(*) FROM organization_audit WHERE tenant_id=?", (self.tenant_id,)).fetchone()[0]
                rows = self.repo._db.execute("SELECT id,action,actor_id,created_at,before_json,after_json FROM organization_audit WHERE tenant_id=? ORDER BY created_at DESC,id DESC LIMIT ?", (self.tenant_id, limit)).fetchall()
                for row in rows:
                    items.append({"id": row["id"], "kind": "organization", "action": row["action"], "actor_id": row["actor_id"],
                                  "actor_label": self._actor_label(row["actor_id"]), "created_at": row["created_at"],
                                  "project_id": None, "project_name": None, "project_reference": None, "object_id": None,
                                  "provenance": None, "changes": {"before": json.loads(row["before_json"]), "after": json.loads(row["after_json"])}})
        items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
        visible = items[:limit]
        for item in visible:
            item["actor_label"] = self._actor_label(item["actor_id"])
            if item["kind"] != "organization":
                payload = json.loads(item.pop("payload"))
                item["object_id"] = item.get("object_id") or payload.get("candidate_id") or payload.get("note_id")
                item["provenance"] = self._provenance(item["project_id"], payload, actor)
        return {"items": visible, "total": total, "limit": limit, "capabilities": self.identity_capabilities()}


def register_governance_routes(app, repo, tenant, actor, settings):
    service = GovernanceService(repo, tenant, settings)

    @app.get("/api/v1/organization")
    def organization(current=Depends(actor)):
        return service.organization(current)

    @app.patch("/api/v1/organization")
    def update_organization(body: OrganizationPatch, current=Depends(actor)):
        return service.update_organization(current, **body.model_dump())

    @app.get("/api/v1/organization/members")
    def members(current=Depends(actor)):
        return service.members(current)

    @app.get("/api/v1/organization/roles")
    def roles(current=Depends(actor)):
        return service.roles(current)

    @app.get("/api/v1/organization/audit")
    def audit(project_id: str | None = None, limit: int = Query(default=100, ge=1, le=200), current=Depends(actor)):
        return service.audit(current, project_id, limit)

    return service
