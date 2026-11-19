"""Permanent commissions domain and persistence for municipal organisations.

Implements the four Plougastel-Daoulas permanent commissions, multi-tenant isolation,
role hierarchy and idempotent database migrations.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, require_text, utc_now
from .project_access import access_scope
from .repository import Repository

COMMISSION_1_ID = "commission-1"
COMMISSION_2_ID = "commission-2"
COMMISSION_3_ID = "commission-3"
COMMISSION_4_ID = "commission-4"

PLOUGASTEL_COMMISSIONS = [
    {
        "id": COMMISSION_1_ID,
        "name": "1. Fonctions supports et transitions",
        "code": "finances",
        "position": 1,
        "specializations": ["finances", "administration", "transitions", "patrimoine"],
    },
    {
        "id": COMMISSION_2_ID,
        "name": "2. Action sociale, enfance et jeunesse",
        "code": "enfance-jeunesse",
        "position": 2,
        "specializations": ["enfance", "jeunesse", "action_sociale", "aines"],
    },
    {
        "id": COMMISSION_3_ID,
        "name": "3. Urbanisme, travaux et ports",
        "code": "urbanisme-travaux",
        "position": 3,
        "specializations": ["travaux", "urbanisme", "ports"],
    },
    {
        "id": COMMISSION_4_ID,
        "name": "4. Culture, sport et vie associative",
        "code": "culture-vie-associative",
        "position": 4,
        "specializations": ["culture", "sport", "vie_associative", "evenements"],
    },
]

COMMISSION_SCHEMA = """
CREATE TABLE IF NOT EXISTS commissions (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    UNIQUE(tenant_id, code)
);
CREATE INDEX IF NOT EXISTS idx_commissions_tenant ON commissions(tenant_id, position);

CREATE TABLE IF NOT EXISTS commission_members (
    tenant_id TEXT NOT NULL,
    commission_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'editor', 'reader')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, commission_id, actor_id),
    FOREIGN KEY(tenant_id, commission_id) REFERENCES commissions(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_commission_members_actor ON commission_members(tenant_id, actor_id);

CREATE TABLE IF NOT EXISTS commission_acl_versions (
    tenant_id TEXT NOT NULL,
    commission_id TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(tenant_id, commission_id)
);
"""


def _commission_id(value: str) -> str:
    val = require_text(value, "commission_id", maximum=100)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", val):
        raise DomainError("invalid_input", "Identifiant de commission invalide.")
    return val


class CommissionRepository:
    def __init__(self, repo):
        self.repo = repo
        self._migrate_schema()

    def _migrate_schema(self):
        with self.repo._lock:
            self.repo._db.executescript(COMMISSION_SCHEMA)
            existing_project_columns = {
                r[1] for r in self.repo._db.execute("PRAGMA table_info(projects)")
            }
            for column, declaration in (
                ("commission_id", "TEXT NOT NULL DEFAULT 'commission-3'"),
                ("specialization", "TEXT NOT NULL DEFAULT 'travaux'"),
                ("visibility", "TEXT NOT NULL DEFAULT 'standard'"),
            ):
                if column not in existing_project_columns:
                    self.repo._db.execute(
                        f"ALTER TABLE projects ADD COLUMN {column} {declaration}"
                    )

    def ensure_default_commissions(self, tenant_id: str) -> List[Dict[str, Any]]:
        require_text(tenant_id, "tenant_id", maximum=100)
        now = utc_now()
        with self.repo._transaction() as db:
            for item in PLOUGASTEL_COMMISSIONS:
                db.execute(
                    """INSERT OR IGNORE INTO commissions(tenant_id, id, name, code, position, active, created_at)
                    VALUES(?, ?, ?, ?, ?, 1, ?)""",
                    (tenant_id, item["id"], item["name"], item["code"], item["position"], now),
                )
            rows = db.execute(
                "SELECT * FROM commissions WHERE tenant_id=? ORDER BY position, id",
                (tenant_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def backfill_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Idempotent backfill attaching historical projects to Commission 3 (Travaux)."""
        require_text(tenant_id, "tenant_id", maximum=100)
        self.ensure_default_commissions(tenant_id)
        with self.repo._transaction() as db:
            # Fix any NULL or empty commission_id
            updated = db.execute(
                """UPDATE projects
                SET commission_id='commission-3',
                    specialization=CASE WHEN specialization IS NULL OR specialization='' THEN 'travaux' ELSE specialization END,
                    visibility=CASE WHEN visibility IS NULL OR visibility='' THEN 'standard' ELSE visibility END
                WHERE tenant_id=? AND (commission_id IS NULL OR commission_id='' OR commission_id='travaux')""",
                (tenant_id,),
            ).rowcount
            # Ensure commission_id='commission-3' for projects with legacy empty strings
            db.execute(
                "UPDATE projects SET commission_id='commission-3' WHERE tenant_id=? AND commission_id NOT IN (SELECT id FROM commissions WHERE tenant_id=?)",
                (tenant_id, tenant_id),
            )
            total = db.execute(
                "SELECT count(*) FROM projects WHERE tenant_id=?", (tenant_id,)
            ).fetchone()[0]
            commissions_count = db.execute(
                "SELECT count(*) FROM commissions WHERE tenant_id=?", (tenant_id,)
            ).fetchone()[0]
            return {
                "tenant_id": tenant_id,
                "updated_projects": updated,
                "total_projects": total,
                "commissions_count": commissions_count,
            }

    def list_commissions(self, tenant_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        require_text(tenant_id, "tenant_id", maximum=100)
        self.ensure_default_commissions(tenant_id)
        with self.repo._lock:
            where = "tenant_id=?"
            if active_only:
                where += " AND active=1"
            rows = self.repo._db.execute(
                f"SELECT * FROM commissions WHERE {where} ORDER BY position, id",
                (tenant_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_commission(self, tenant_id: str, commission_id: str) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        cid = _commission_id(commission_id)
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM commissions WHERE tenant_id=? AND id=?",
                (tenant_id, cid),
            ).fetchone()
            if row is None:
                raise DomainError("not_found", "Commission introuvable dans cette organisation.")
            return dict(row)

    def list_member_commissions(self, tenant_id: str, actor_id: str) -> List[Dict[str, Any]]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(actor_id, "actor_id", maximum=200)
        with self.repo._lock:
            rows = self.repo._db.execute(
                """SELECT c.*, cm.role AS member_role, cm.created_at AS assigned_at
                FROM commissions c
                JOIN commission_members cm ON cm.tenant_id=c.tenant_id AND cm.commission_id=c.id
                WHERE c.tenant_id=? AND cm.actor_id=? AND c.active=1
                ORDER BY c.position, c.id""",
                (tenant_id, actor_id),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_member_commission_role(
        self, tenant_id: str, commission_id: str, actor_id: str
    ) -> Optional[str]:
        require_text(tenant_id, "tenant_id", maximum=100)
        cid = _commission_id(commission_id)
        require_text(actor_id, "actor_id", maximum=200)
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT role FROM commission_members WHERE tenant_id=? AND commission_id=? AND actor_id=?",
                (tenant_id, cid, actor_id),
            ).fetchone()
            return row["role"] if row else None

    def set_member_commission_role(
        self,
        tenant_id: str,
        commission_id: str,
        actor_id: str,
        role: str,
        *,
        updated_by: str,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        cid = _commission_id(commission_id)
        require_text(actor_id, "actor_id", maximum=200)
        require_text(updated_by, "updated_by", maximum=200)
        if role not in {"admin", "editor", "reader"}:
            raise DomainError("invalid_input", "Rôle de commission invalide.")
        now = utc_now()
        with self.repo._transaction() as db:
            # Check commission exists
            comm = db.execute(
                "SELECT 1 FROM commissions WHERE tenant_id=? AND id=?", (tenant_id, cid)
            ).fetchone()
            if comm is None:
                raise DomainError("not_found", "Commission introuvable.")
            # Check member is an active member of organisation
            member = db.execute(
                "SELECT active FROM identity_members WHERE tenant_id=? AND actor_id=?",
                (tenant_id, actor_id),
            ).fetchone()
            if member is None or not member["active"]:
                raise DomainError("not_found", "Ce membre actif n’existe pas dans l’organisation.")

            # Check revision if provided
            rev_row = db.execute(
                "SELECT revision FROM commission_acl_versions WHERE tenant_id=? AND commission_id=?",
                (tenant_id, cid),
            ).fetchone()
            current_rev = rev_row["revision"] if rev_row else 0
            if expected_revision is not None and expected_revision != current_rev:
                raise DomainError(
                    "stale_revision",
                    "Les habilitations de cette commission ont changé. Rechargez avant de confirmer.",
                )

            db.execute(
                """INSERT INTO commission_members(tenant_id, commission_id, actor_id, role, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, commission_id, actor_id) DO UPDATE SET
                    role=excluded.role, updated_at=excluded.updated_at""",
                (tenant_id, cid, actor_id, role, now, now),
            )
            new_rev = current_rev + 1
            db.execute(
                """INSERT INTO commission_acl_versions(tenant_id, commission_id, revision)
                VALUES(?, ?, ?) ON CONFLICT(tenant_id, commission_id) DO UPDATE SET revision=excluded.revision""",
                (tenant_id, cid, new_rev),
            )
            db.execute(
                "INSERT INTO identity_audit VALUES(?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    tenant_id,
                    updated_by,
                    actor_id,
                    "commission.role_assigned",
                    canonical_json({"commission_id": cid, "role": role}),
                    now,
                ),
            )
            return {
                "commission_id": cid,
                "actor_id": actor_id,
                "role": role,
                "revision": new_rev,
                "updated_at": now,
            }

    def remove_member_commission_role(
        self,
        tenant_id: str,
        commission_id: str,
        actor_id: str,
        *,
        updated_by: str,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        cid = _commission_id(commission_id)
        require_text(actor_id, "actor_id", maximum=200)
        require_text(updated_by, "updated_by", maximum=200)
        now = utc_now()
        with self.repo._transaction() as db:
            rev_row = db.execute(
                "SELECT revision FROM commission_acl_versions WHERE tenant_id=? AND commission_id=?",
                (tenant_id, cid),
            ).fetchone()
            current_rev = rev_row["revision"] if rev_row else 0
            if expected_revision is not None and expected_revision != current_rev:
                raise DomainError(
                    "stale_revision",
                    "Les habilitations de cette commission ont changé. Rechargez avant de confirmer.",
                )
            deleted = db.execute(
                "DELETE FROM commission_members WHERE tenant_id=? AND commission_id=? AND actor_id=?",
                (tenant_id, cid, actor_id),
            ).rowcount
            if not deleted:
                raise DomainError("not_found", "Ce membre n’était pas affecté à cette commission.")
            new_rev = current_rev + 1
            db.execute(
                """INSERT INTO commission_acl_versions(tenant_id, commission_id, revision)
                VALUES(?, ?, ?) ON CONFLICT(tenant_id, commission_id) DO UPDATE SET revision=excluded.revision""",
                (tenant_id, cid, new_rev),
            )
            db.execute(
                "INSERT INTO identity_audit VALUES(?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    tenant_id,
                    updated_by,
                    actor_id,
                    "commission.role_removed",
                    canonical_json({"commission_id": cid}),
                    now,
                ),
            )
            return {"commission_id": cid, "actor_id": actor_id, "removed": True, "revision": new_rev}


class CommissionMemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(admin|editor|reader)$", strict=True)
    expected_revision: Optional[int] = Field(default=None, ge=0)


def register_commission_routes(app, repo, tenant, actor, settings, *, commissions, governance):
    def require_org_admin(current):
        if settings.auth_mode != "oidc":
            raise DomainError("forbidden", "La gestion individuelle exige la connexion institutionnelle.")
        governance.require_authorized(current, "organization", "write")

    def require_org_read(current):
        if settings.auth_mode != "oidc":
            raise DomainError("forbidden", "La consultation exige la connexion institutionnelle.")
        governance.require_authorized(current, "organization", "read")

    @app.get("/api/v1/commissions")
    def list_commissions_route(current=Depends(actor)):
        scope = access_scope(repo, current)
        items = commissions.list_commissions(tenant)
        result = []
        for comm in items:
            caps = scope.commission_capabilities(comm["id"])
            result.append(
                {
                    **comm,
                    "capabilities": caps,
                    "can_read": caps["can_read"],
                    "can_edit": caps["can_edit"],
                    "can_submit_for_review": caps["can_submit_for_review"],
                    "role": caps["role"],
                }
            )
        return {"items": result, "total": len(result)}

    @app.get("/api/v1/commissions/{commission_id}")
    def get_commission_route(commission_id: str, current=Depends(actor)):
        comm = commissions.get_commission(tenant, commission_id)
        scope = access_scope(repo, current)
        caps = scope.commission_capabilities(comm["id"])
        return {
            **comm,
            "capabilities": caps,
            "can_read": caps["can_read"],
            "can_edit": caps["can_edit"],
            "can_submit_for_review": caps["can_submit_for_review"],
            "role": caps["role"],
        }

    @app.get("/api/v1/commissions/{commission_id}/members")
    def list_commission_members_route(commission_id: str, current=Depends(actor)):
        require_org_read(current)
        comm = commissions.get_commission(tenant, commission_id)
        with repo._lock:
            rows = repo._db.execute(
                """SELECT cm.commission_id, cm.actor_id AS id, cm.role, cm.created_at, cm.updated_at,
                          m.display_name, m.email, m.role AS organization_role
                FROM commission_members cm
                JOIN identity_members m ON m.tenant_id=cm.tenant_id AND m.actor_id=cm.actor_id
                WHERE cm.tenant_id=? AND cm.commission_id=? AND m.active=1
                ORDER BY m.display_name, cm.actor_id""",
                (tenant, comm["id"]),
            ).fetchall()
            rev = repo._db.execute(
                "SELECT revision FROM commission_acl_versions WHERE tenant_id=? AND commission_id=?",
                (tenant, comm["id"]),
            ).fetchone()
        return {
            "commission_id": comm["id"],
            "revision": rev["revision"] if rev else 0,
            "items": [dict(r) for r in rows],
            "total": len(rows),
        }

    @app.put("/api/v1/commissions/{commission_id}/members/{member_id}")
    def set_commission_member_route(
        commission_id: str,
        member_id: str,
        body: CommissionMemberInput,
        current=Depends(actor),
    ):
        require_org_admin(current)
        return commissions.set_member_commission_role(
            tenant,
            commission_id,
            member_id,
            body.role,
            updated_by=current["actor_id"],
            expected_revision=body.expected_revision,
        )

    @app.delete("/api/v1/commissions/{commission_id}/members/{member_id}")
    def remove_commission_member_route(
        commission_id: str,
        member_id: str,
        expected_revision: Optional[int] = None,
        current=Depends(actor),
    ):
        require_org_admin(current)
        return commissions.remove_member_commission_role(
            tenant,
            commission_id,
            member_id,
            updated_by=current["actor_id"],
            expected_revision=expected_revision,
        )

    return commissions


_orig_repo_init = Repository.__init__
_orig_create_project = Repository.create_project


def _commission_repo_init(self, *args, **kwargs):
    _orig_repo_init(self, *args, **kwargs)
    CommissionRepository(self)
    from .culture_finances import CultureFinancesRepository
    CultureFinancesRepository(self)




def _commission_create_project(
    self,
    tenant_id,
    reference,
    name,
    project_id=None,
    description="",
    status="active",
    commission_id="commission-3",
    specialization="travaux",
    visibility="standard",
):
    project = _orig_create_project(
        self,
        tenant_id,
        reference,
        name,
        project_id=project_id,
        description=description,
        status=status,
    )
    with self._transaction() as db:
        db.execute(
            "UPDATE projects SET commission_id=?, specialization=?, visibility=? WHERE tenant_id=? AND id=?",
            (
                commission_id or "commission-3",
                specialization or "travaux",
                visibility or "standard",
                tenant_id,
                project["id"],
            ),
        )
        return self._project(db, tenant_id, project["id"])


if getattr(Repository, "_commission_hooked", False) is False:
    Repository.__init__ = _commission_repo_init
    Repository.create_project = _commission_create_project
    Repository._commission_hooked = True

