"""Administrative member approval and optimistic dossier access management."""
from uuid import uuid4

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, utc_now
from .project_access import access_scope


class MemberAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(admin|editor|reader)$", strict=True)
    active: bool = Field(strict=True)
    expected_revision: int = Field(ge=0, strict=True)


class DossierAccess(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed: bool = Field(strict=True)
    expected_revision: int = Field(ge=0, strict=True)


def register_member_routes(app, repo, tenant, actor, settings, *, members, governance):
    with repo._transaction() as db:
        db.execute("CREATE TABLE IF NOT EXISTS project_acl_versions(tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(tenant_id,project_id))")

    def admin(current):
        if settings.auth_mode != "oidc":
            raise DomainError("forbidden", "La gestion individuelle exige la connexion institutionnelle.")
        governance.require_authorized(current, "organization", "write")

    def access(project_id, current):
        admin(current)
        access_scope(repo, current).require_project(project_id)
        with repo._lock:
            version = repo._db.execute("SELECT revision FROM project_acl_versions WHERE tenant_id=? AND project_id=?", (tenant, project_id)).fetchone()
            rows = repo._db.execute("SELECT m.actor_id AS id,m.display_name,m.role FROM project_grants g JOIN identity_members m ON m.tenant_id=g.tenant_id AND m.actor_id=g.actor_id WHERE g.tenant_id=? AND g.project_id=? AND m.active=1 ORDER BY m.display_name,m.actor_id", (tenant, project_id)).fetchall()
        return {"project_id": project_id, "revision": version[0] if version else 0, "items": [dict(row) for row in rows], "administrators_have_access": True}

    @app.patch("/api/v1/organization/members/{member_id}")
    def update_member(member_id: str, body: MemberAccess, current=Depends(actor)):
        admin(current)
        return members.update(member_id, **body.model_dump(), updated_by=current["actor_id"])

    @app.get("/api/v1/projects/{project_id}/access")
    def get_project_access(project_id: str, current=Depends(actor)):
        return access(project_id, current)

    @app.put("/api/v1/projects/{project_id}/access/{member_id}")
    def change_project_access(project_id: str, member_id: str, body: DossierAccess, current=Depends(actor)):
        admin(current)
        with repo._transaction() as db:
            access_scope(repo, current).require_project(project_id)
            if members.get_active(member_id) is None:
                raise DomainError("not_found", "Ce membre actif n’existe pas dans votre espace.")
            before = db.execute("SELECT revision FROM project_acl_versions WHERE tenant_id=? AND project_id=?", (tenant, project_id)).fetchone()
            revision = before[0] if before else 0
            if revision != body.expected_revision:
                raise DomainError("stale_revision", "Les accès ont changé. Rechargez la liste avant de confirmer.")
            existed = db.execute("SELECT 1 FROM project_grants WHERE tenant_id=? AND actor_id=? AND project_id=?", (tenant, member_id, project_id)).fetchone() is not None
            if existed != body.allowed:
                if body.allowed:
                    db.execute("INSERT INTO project_grants VALUES(?,?,?,?,?)", (tenant, member_id, project_id, current["actor_id"], utc_now()))
                else:
                    db.execute("DELETE FROM project_grants WHERE tenant_id=? AND actor_id=? AND project_id=?", (tenant, member_id, project_id))
                db.execute("INSERT INTO project_acl_versions VALUES(?,?,?) ON CONFLICT(tenant_id,project_id) DO UPDATE SET revision=excluded.revision", (tenant, project_id, revision+1))
                db.execute("INSERT INTO identity_audit VALUES(?,?,?,?,?,?,?)", (str(uuid4()), tenant, current["actor_id"], member_id, "project.access.changed", canonical_json({"project_id": project_id, "allowed": body.allowed}), utc_now()))
        return access(project_id, current)
