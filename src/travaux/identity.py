"""Individual institutional identities. Browser claims never assign a role."""
from __future__ import annotations

import hashlib
from urllib.parse import urlsplit
from uuid import uuid4

from .domain import DomainError, canonical_json, require_text, utc_now


def identity_text(value, name, maximum=200, empty=False):
    result = require_text(value, name, maximum=maximum, empty=empty).strip()
    if (not result and not empty) or any(not character.isprintable() for character in result):
        raise DomainError("invalid_input", "L’identité doit contenir du texte sur une seule ligne.")
    return result


def issuer_url(value):
    value = identity_text(value, "issuer", 2000)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise DomainError("invalid_input", "Une autorité d’identité HTTPS explicite est requise.")
    return value


class IdentityStore:
    def __init__(self, repo, tenant_id, sessions):
        self.repo, self.tenant_id, self.sessions = repo, tenant_id, sessions
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS identity_members(
                tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL, issuer TEXT NOT NULL,
                subject TEXT NOT NULL, email TEXT NOT NULL DEFAULT '', display_name TEXT NOT NULL,
                role TEXT NOT NULL, active INTEGER NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,actor_id), UNIQUE(tenant_id,issuer,subject))""")
            db.execute("""CREATE TABLE IF NOT EXISTS identity_audit(
                id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, actor_id TEXT NOT NULL,
                member_id TEXT NOT NULL, action TEXT NOT NULL, changes TEXT NOT NULL, created_at TEXT NOT NULL)""")

    @staticmethod
    def actor_id(issuer, subject):
        return "oidc:" + hashlib.sha256((issuer + "\x00" + subject).encode()).hexdigest()[:40]

    @staticmethod
    def dto(row):
        return {**dict(row), "active": bool(row["active"])}

    def provision(self, issuer, subject, display_name, role, *, email="", active=True):
        issuer, subject = issuer_url(issuer), identity_text(subject, "subject", 200)
        name, email = identity_text(display_name, "display_name"), identity_text(email, "email", 320, True)
        if role not in {"admin", "editor", "reader"} or type(active) is not bool:
            raise DomainError("invalid_input", "Rôle ou activation invalide.")
        ident, now = self.actor_id(issuer, subject), utc_now()
        with self.repo._transaction() as db:
            existing = db.execute("SELECT * FROM identity_members WHERE tenant_id=? AND actor_id=?", (self.tenant_id, ident)).fetchone()
            if existing:
                return self.dto(existing)
            if db.execute("SELECT count(*) FROM identity_members WHERE tenant_id=?", (self.tenant_id,)).fetchone()[0] >= 1000:
                raise DomainError("invalid_input", "Le nombre de demandes d’accès exige une revue de l’administrateur.")
            db.execute("INSERT INTO identity_members VALUES(?,?,?,?,?,?,?,?,?,?,?)", (self.tenant_id, ident, issuer, subject, email, name, role, int(active), 0, now, now))
            db.execute("INSERT INTO identity_audit VALUES(?,?,?,?,?,?,?)", (str(uuid4()), self.tenant_id, "operator", ident, "member.provisioned" if active else "member.requested", canonical_json({"role": role, "active": active}), now))
            return self.dto(db.execute("SELECT * FROM identity_members WHERE tenant_id=? AND actor_id=?", (self.tenant_id, ident)).fetchone())

    def get_active(self, actor_id):
        with self.repo._lock:
            row = self.repo._db.execute("SELECT * FROM identity_members WHERE tenant_id=? AND actor_id=? AND active=1", (self.tenant_id, actor_id)).fetchone()
            return self.dto(row) if row else None

    def authenticate(self, issuer, claims):
        issuer, subject = issuer_url(issuer), identity_text(claims.get("sub"), "subject", 200)
        ident = self.actor_id(issuer, subject)
        member = self.get_active(ident)
        if member is None:
            # A signed identity may request access, but never grants itself a role.
            self.provision(issuer, subject, claims.get("name") or "Demande d’accès", "reader", active=False)
            raise DomainError("identity_pending", "L’accès doit être autorisé par l’administrateur de votre collectivité.")
        return member

    def list_members(self, *, include_inactive=False):
        with self.repo._lock:
            rows = self.repo._db.execute("SELECT * FROM identity_members WHERE tenant_id=?" + ("" if include_inactive else " AND active=1") + " ORDER BY display_name,actor_id LIMIT 1000", (self.tenant_id,)).fetchall()
            return [self.dto(row) for row in rows]

    def update(self, actor_id, *, role, active, expected_revision, updated_by):
        if role not in {"admin", "editor", "reader"} or type(active) is not bool or type(expected_revision) is not int or expected_revision < 0:
            raise DomainError("invalid_input", "Rôle, activation et révision explicites attendus.")
        with self.repo._transaction() as db:
            row = db.execute("SELECT * FROM identity_members WHERE tenant_id=? AND actor_id=?", (self.tenant_id, actor_id)).fetchone()
            if row is None:
                raise DomainError("not_found", "Ce membre n’existe pas dans votre espace.")
            if row["revision"] != expected_revision:
                raise DomainError("stale_revision", "Ce membre a changé. Rechargez son accès avant de confirmer.")
            if row["active"] and row["role"] == "admin" and (not active or role != "admin") and db.execute("SELECT count(*) FROM identity_members WHERE tenant_id=? AND role='admin' AND active=1", (self.tenant_id,)).fetchone()[0] <= 1:
                raise DomainError("last_administrator", "Conservez au moins un administrateur actif dans cet espace.")
            if row["role"] != role or bool(row["active"]) != active:
                now = utc_now()
                db.execute("UPDATE identity_members SET role=?,active=?,revision=revision+1,updated_at=? WHERE tenant_id=? AND actor_id=?", (role, int(active), now, self.tenant_id, actor_id))
                # Membership change and revocation commit together on the same connection.
                db.execute("DELETE FROM sessions WHERE tenant_id=? AND actor_id=?", (self.tenant_id, actor_id))
                db.execute("INSERT INTO identity_audit VALUES(?,?,?,?,?,?,?)", (str(uuid4()), self.tenant_id, updated_by, actor_id, "member.updated", canonical_json({"before": {"role": row["role"], "active": bool(row["active"])}, "after": {"role": role, "active": active}}), now))
            return self.dto(db.execute("SELECT * FROM identity_members WHERE tenant_id=? AND actor_id=?", (self.tenant_id, actor_id)).fetchone())
