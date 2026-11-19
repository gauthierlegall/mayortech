"""Choose the instance's organization after verified IdP authentication.

An onboarding session is intentionally not a workspace principal. Only the
explicit fictional staging profile can activate a first request by itself.
"""

import hmac
import secrets
import time
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .config import normalize_organization_join_code
from .domain import DomainError, canonical_json, utc_now


class AccountOnboardingService:
    def __init__(self, repo, settings, sessions, members):
        self.repo, self.settings, self.sessions, self.members = repo, settings, sessions, members
        self.tenant = settings.tenant_id
        self.onboarding_tenant = "onboarding:" + self.tenant
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS account_join_requests(
                tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,status TEXT NOT NULL,
                requested_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,actor_id))""")

    def _member(self, current):
        if (
            self.settings.auth_mode != "oidc"
            or not self.settings.auth_required
            or not isinstance(current, dict)
            or current.get("tenant_id") not in {self.tenant, self.onboarding_tenant}
            or not isinstance(current.get("actor_id"), str)
        ):
            return None
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM identity_members WHERE tenant_id=? AND actor_id=?",
                (self.tenant, current["actor_id"]),
            ).fetchone()
        if row is None or (current["tenant_id"] == self.tenant and not row["active"]):
            return None
        return dict(row)

    def session_state(self, current):
        member = self._member(current)
        if member is None:
            return {"authenticated": False, "organization_required": False, "actor": None, "account": None}
        onboarding = current["tenant_id"] == self.onboarding_tenant
        return {
            "authenticated": True,
            "organization_required": onboarding,
            "actor": None if onboarding else {"actor_id": member["actor_id"], "tenant_id": self.tenant},
            "account": {"id": member["actor_id"], "display_name": member["display_name"]},
        }

    def principal(self, token):
        current = self.sessions.resolve(token)
        if self._member(current) is None:
            raise DomainError("unauthenticated", "Connectez-vous pour choisir votre organisation.")
        return current

    def _organization(self):
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT name FROM organization_profiles WHERE tenant_id=?", (self.tenant,)
            ).fetchone()
        if row is None:
            raise DomainError(
                "integration_unavailable",
                "L’organisation doit être préparée par l’administrateur de cette instance.",
            )
        return {
            "id": self.tenant,
            "name": row["name"],
            "is_test": bool(self.settings.test_organization_self_join),
        }

    def _can_self_join(self, member, request):
        return bool(
            self.settings.test_organization_self_join
            and not member["active"]
            and member["role"] == "reader"
            and member["revision"] == 0
            and request is None
        )

    def organizations(self, current):
        member = self._member(current)
        if member is None:
            raise DomainError("unauthenticated", "Connectez-vous pour choisir votre organisation.")
        with self.repo._lock:
            request = self.repo._db.execute(
                "SELECT status FROM account_join_requests WHERE tenant_id=? AND actor_id=?",
                (self.tenant, member["actor_id"]),
            ).fetchone()
        active = bool(member["active"])
        can_self_join = self._can_self_join(member, request)
        status = (
            "joined"
            if active
            else request["status"]
            if request is not None and request["status"] in {"pending", "rejected"}
            else "not_joined"
        )
        item = {
            **self._organization(),
            "can_self_join": can_self_join,
            "membership_status": status,
            "can_enter": active,
        }
        if self.settings.test_organization_self_join:
            item["test_join_code"] = self.settings.effective_organization_join_code
        catalog = {"items": [item], "organization_required": current["tenant_id"] == self.onboarding_tenant}
        if self.settings.test_organization_self_join:
            catalog["test_join_code"] = self.settings.effective_organization_join_code
        return catalog

    def _audit(self, db, member_id, action, changes, *, updated_by=None):
        db.execute(
            "INSERT INTO identity_audit VALUES(?,?,?,?,?,?,?)",
            (
                str(uuid4()),
                self.tenant,
                updated_by or member_id,
                member_id,
                action,
                canonical_json(changes),
                utc_now(),
            ),
        )

    def _issue_session(self, db, actor_id):
        # Same opaque token and digest contract as SessionStore.issue(). Use the
        # active SQLite transaction so a failed session insert grants no access.
        token = secrets.token_urlsafe(48)
        db.execute(
            "INSERT INTO sessions VALUES(?,?,?,?)",
            (self.sessions.digest(token), actor_id, self.tenant, time.time() + 8 * 3600),
        )
        return token

    def _validate_code(self, current, code):
        key = "organization-code:" + self.tenant + ":" + current["actor_id"]
        if not self.sessions.allow_attempt(key):
            raise DomainError(
                "conversation_limit", "Trop de tentatives de code. Réessayez dans quelques minutes."
            )
        try:
            normalized = normalize_organization_join_code(code)
        except ValueError:
            normalized = ""
        expected = self.settings.effective_organization_join_code
        # Both operands are bounded ASCII. Never include the code in an audit,
        # error message, request key or public DTO for a real organization.
        matches = hmac.compare_digest(normalized.encode("ascii"), expected.encode("ascii"))
        if not normalized or not expected or not matches:
            raise DomainError(
                "invalid_input",
                "Le code de l’organisation est invalide. Vérifiez le code transmis par votre administrateur.",
            )

    def _fictional_grants(self, db, actor_id):
        projects = list(db.execute("SELECT id FROM projects WHERE tenant_id=?", (self.tenant,)))
        for project in projects:
            db.execute(
                "INSERT OR IGNORE INTO project_grants VALUES(?,?,?,?,?)",
                (self.tenant, actor_id, project["id"], "test-organization-self-join", utc_now()),
            )
        return len(projects)

    def join_code(self, token, code):
        return self.join(token, self.tenant, code=code)

    def join(self, token, organization_id, *, code=None):
        current = self.principal(token)
        if organization_id != self.tenant:
            raise DomainError("not_found", "Cette organisation n’est pas disponible sur cette instance.")
        organization, replacement = self._organization(), None
        observed = self._member(current)
        if observed is None:
            raise DomainError("unauthenticated", "Votre accès a changé. Reconnectez-vous avant de continuer.")
        code_validated = False
        if not observed["active"] or code is not None:
            # SessionStore owns a separate serialized connection. Apply this
            # account-bound limit before taking the repository write lock.
            self._validate_code(current, code)
            code_validated = True
        with self.repo._transaction() as db:
            live = db.execute(
                "SELECT 1 FROM sessions WHERE digest=? AND actor_id=? AND tenant_id=? AND expires>?",
                (self.sessions.digest(token), current["actor_id"], current["tenant_id"], time.time()),
            ).fetchone()
            member = self._member(current)
            if live is None or member is None:
                raise DomainError(
                    "unauthenticated", "Votre connexion a expiré. Reconnectez-vous avant de continuer."
                )
            previous = db.execute(
                "SELECT status FROM account_join_requests WHERE tenant_id=? AND actor_id=?",
                (self.tenant, member["actor_id"]),
            ).fetchone()
            if not member["active"] and not code_validated:
                raise DomainError("invalid_input", "Un code valide est nécessaire pour demander cet accès.")
            if not member["active"] and previous is not None and previous["status"] == "rejected":
                return {
                    "status": "rejected",
                    "organization": organization,
                    "message": "Votre demande a été refusée. Contactez l’administrateur de l’organisation.",
                }, None
            self_join = self._can_self_join(member, previous)
            if self_join:
                db.execute(
                    "UPDATE identity_members SET role='editor',active=1,revision=revision+1,updated_at=? WHERE tenant_id=? AND actor_id=? AND active=0 AND role='reader' AND revision=0",
                    (utc_now(), self.tenant, member["actor_id"]),
                )
                project_count = self._fictional_grants(db, member["actor_id"])
                self._audit(
                    db,
                    member["actor_id"],
                    "organization.test_joined",
                    {
                        "organization_id": self.tenant,
                        "role": "editor",
                        "fictional": True,
                        "project_count": project_count,
                    },
                )
            if member["active"] or self_join:
                now = utc_now()
                db.execute(
                    "INSERT INTO account_join_requests VALUES(?,?,?,?,?) ON CONFLICT(tenant_id,actor_id) DO UPDATE SET status='joined',updated_at=excluded.updated_at",
                    (self.tenant, member["actor_id"], "joined", now, now),
                )
                if self_join:
                    db.execute(
                        "DELETE FROM sessions WHERE actor_id=? AND tenant_id IN (?,?)",
                        (member["actor_id"], self.tenant, self.onboarding_tenant),
                    )
                else:
                    db.execute("DELETE FROM sessions WHERE digest=?", (self.sessions.digest(token),))
                    self._audit(
                        db, member["actor_id"], "organization.entered", {"organization_id": self.tenant}
                    )
                replacement = self._issue_session(db, member["actor_id"])
                status = "joined"
            else:
                if previous is None or previous["status"] != "pending":
                    now = utc_now()
                    db.execute(
                        "INSERT INTO account_join_requests VALUES(?,?,?,?,?) ON CONFLICT(tenant_id,actor_id) DO UPDATE SET status='pending',updated_at=excluded.updated_at",
                        (self.tenant, member["actor_id"], "pending", now, now),
                    )
                    db.execute(
                        "UPDATE identity_members SET revision=revision+1,updated_at=? WHERE tenant_id=? AND actor_id=?",
                        (now, self.tenant, member["actor_id"]),
                    )
                    self._audit(
                        db,
                        member["actor_id"],
                        "organization.join_requested",
                        {"organization_id": self.tenant, "active": False},
                    )
                status = "pending"
        message = (
            "Vous avez rejoint Mairie test. Utilisez uniquement ses données fictives."
            if status == "joined" and organization["is_test"]
            else "Votre accès à l’organisation est ouvert."
            if status == "joined"
            else "Votre demande a été transmise à l’administrateur de l’organisation. Aucun accès aux dossiers n’est encore accordé."
        )
        return {"status": status, "organization": organization, "message": message}, replacement

    def _admin(self, db, current, token):
        live = db.execute(
            "SELECT m.* FROM sessions s JOIN identity_members m ON m.tenant_id=s.tenant_id AND m.actor_id=s.actor_id WHERE s.digest=? AND s.tenant_id=? AND s.expires>? AND m.active=1 AND m.role='admin'",
            (self.sessions.digest(token), self.tenant, time.time()),
        ).fetchone()
        if current["tenant_id"] != self.tenant or live is None or live["actor_id"] != current["actor_id"]:
            raise DomainError(
                "forbidden",
                "Seul un administrateur actif de cette organisation peut gérer les demandes d’accès.",
            )
        return live

    def join_requests(self, token):
        current = self.principal(token)
        with self.repo._transaction() as db:
            self._admin(db, current, token)
            rows = db.execute(
                "SELECT m.actor_id,m.display_name,m.email,r.status,m.revision,r.requested_at FROM account_join_requests r JOIN identity_members m ON m.tenant_id=r.tenant_id AND m.actor_id=r.actor_id WHERE r.tenant_id=? ORDER BY r.requested_at,m.actor_id LIMIT 1000",
                (self.tenant,),
            ).fetchall()
            return {"items": [dict(row) for row in rows]}

    def decide(self, token, actor_id, decision, expected_revision):
        current = self.principal(token)
        if (
            not isinstance(actor_id, str)
            or len(actor_id) > 200
            or decision not in {"approve", "reject"}
            or type(expected_revision) is not int
            or expected_revision < 0
        ):
            raise DomainError("invalid_input", "Une décision et une révision explicites sont nécessaires.")
        with self.repo._transaction() as db:
            admin = self._admin(db, current, token)
            row = db.execute(
                "SELECT m.*,r.status AS request_status FROM identity_members m JOIN account_join_requests r ON r.tenant_id=m.tenant_id AND r.actor_id=m.actor_id WHERE m.tenant_id=? AND m.actor_id=?",
                (self.tenant, actor_id),
            ).fetchone()
            if row is None:
                raise DomainError("not_found", "Cette demande n’existe pas dans votre organisation.")
            if row["revision"] != expected_revision:
                raise DomainError("stale_revision", "Cette demande a changé. Rechargez-la avant de décider.")
            if row["request_status"] != "pending" or row["active"]:
                raise DomainError(
                    "conflict",
                    "Cette demande a déjà été traitée. Utilisez la gestion des membres pour modifier un accès existant.",
                )
            approved = decision == "approve"
            status = "joined" if approved else "rejected"
            role = (
                ("editor" if self.settings.test_organization_self_join else "reader")
                if approved
                else row["role"]
            )
            now = utc_now()
            db.execute(
                "UPDATE identity_members SET role=?,active=?,revision=revision+1,updated_at=? WHERE tenant_id=? AND actor_id=?",
                (role, int(approved), now, self.tenant, actor_id),
            )
            db.execute(
                "UPDATE account_join_requests SET status=?,updated_at=? WHERE tenant_id=? AND actor_id=?",
                (status, now, self.tenant, actor_id),
            )
            # Old dossier grants never return implicitly after a withdrawal.
            db.execute("DELETE FROM project_grants WHERE tenant_id=? AND actor_id=?", (self.tenant, actor_id))
            if approved and self.settings.test_organization_self_join:
                self._fictional_grants(db, actor_id)
            # The non-privileged onboarding session remains to display the
            # decision. No workspace session is created by an administrator.
            db.execute("DELETE FROM sessions WHERE tenant_id=? AND actor_id=?", (self.tenant, actor_id))
            self._audit(
                db,
                actor_id,
                "organization.join_approved" if approved else "organization.join_rejected",
                {"status": status, "role": role, "active": approved},
                updated_by=admin["actor_id"],
            )
        return {"status": status, "member_id": actor_id}


def register_account_onboarding_routes(app, repo, settings, sessions, members):
    service = AccountOnboardingService(repo, settings, sessions, members)

    class Join(BaseModel):
        model_config = ConfigDict(extra="forbid")
        code: str | None = Field(default=None, max_length=256, strict=True)

    class JoinCode(BaseModel):
        model_config = ConfigDict(extra="forbid")
        code: str = Field(max_length=256, strict=True)

    class Decision(BaseModel):
        model_config = ConfigDict(extra="forbid")
        decision: str = Field(pattern="^(approve|reject)$", strict=True)
        expected_revision: int = Field(ge=0, strict=True)

    def joined_response(result, token):
        response = JSONResponse(result)
        if token:
            response.set_cookie(
                "travaux_session", token, secure=True, httponly=True, samesite="strict", max_age=8 * 3600
            )
        return response

    @app.get("/api/v1/account/organizations")
    def organizations(request: Request):
        return service.organizations(service.principal(request.cookies.get("travaux_session")))

    @app.post("/api/v1/account/organizations/join")
    def join_by_code(request: Request, body: JoinCode):
        result, token = service.join_code(request.cookies.get("travaux_session"), body.code)
        return joined_response(result, token)

    @app.post("/api/v1/account/organizations/{organization_id}/join")
    def join(organization_id: str, request: Request, body: Join):
        result, token = service.join(request.cookies.get("travaux_session"), organization_id, code=body.code)
        return joined_response(result, token)

    @app.get("/api/v1/organization/join-requests")
    def join_requests(request: Request):
        return service.join_requests(request.cookies.get("travaux_session"))

    @app.post("/api/v1/organization/join-requests/{actor_id}/decision")
    def decide(actor_id: str, request: Request, body: Decision):
        return service.decide(
            request.cookies.get("travaux_session"), actor_id, body.decision, body.expected_revision
        )

    return service
