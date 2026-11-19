"""Séances et instances spécialisées domain module (Lot 5 MayorTech).

Handles:
- Municipal commission sessions lifecycle (Convocation/Brouillon -> En cours -> Clôturée/Scellée)
- Agenda items with strict ordering, project dossier attachments, snapshots and deliberation references
- Roll call, attendance recording, and quorum validation (CGCT compliance)
- Voting engine (Pour / Contre / Abstention / Résultat)
- Formal session closure with SHA-256 cryptographic seal of the minutes (inspired by Decidim CloseMeeting)
- Specialized instances:
  * CAO (Commission d'Appel d'Offres - Marchés publics, Mégalis Bretagne, ouverture des plis)
  * CCSPL (Commission Consultative des Services Publics Locaux - Délégations de service public, eau, assainissement)
  * CCID (Commission Communale des Impôts Directs - Évaluations cadastrales, locaux commerciaux et d'habitation)
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, canonical_json, utc_now
from .repository import Repository

SEANCES_INSTANCES_SCHEMA = """
CREATE TABLE IF NOT EXISTS commission_sessions (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    commission_id TEXT NOT NULL,
    session_type TEXT NOT NULL DEFAULT 'commission' CHECK(session_type IN ('commission', 'cao', 'ccspl', 'ccid')),
    title TEXT NOT NULL,
    session_date TEXT NOT NULL,
    session_time TEXT NOT NULL,
    location TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'en_cours', 'closed', 'archived')),
    quorum_required INTEGER NOT NULL DEFAULT 3,
    quorum_present INTEGER NOT NULL DEFAULT 0,
    pv_hash TEXT NOT NULL DEFAULT '',
    closed_at TEXT NOT NULL DEFAULT '',
    closed_by TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_commission_sessions_type ON commission_sessions(tenant_id, commission_id, session_date);

CREATE TABLE IF NOT EXISTS session_agenda_items (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    item_order INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    project_id TEXT NOT NULL DEFAULT '',
    project_version_snapshot TEXT NOT NULL DEFAULT '{}',
    rapporteur TEXT NOT NULL DEFAULT '',
    deliberation_ref TEXT NOT NULL DEFAULT '',
    vote_result TEXT NOT NULL DEFAULT 'en_attente' CHECK(vote_result IN ('en_attente', 'favorable', 'defavorable', 'reserve', 'ajourne')),
    votes_for INTEGER NOT NULL DEFAULT 0,
    votes_against INTEGER NOT NULL DEFAULT 0,
    votes_abstention INTEGER NOT NULL DEFAULT 0,
    official_decision TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, session_id) REFERENCES commission_sessions(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_session_agenda_items_order ON session_agenda_items(tenant_id, session_id, item_order);

CREATE TABLE IF NOT EXISTS session_attendances (
    tenant_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    member_name TEXT NOT NULL,
    member_role TEXT NOT NULL DEFAULT 'titulaire' CHECK(member_role IN ('titulaire', 'suppleant', 'invite', 'secretaire')),
    status TEXT NOT NULL DEFAULT 'present' CHECK(status IN ('present', 'absent_excuse', 'absent', 'pouvoir')),
    proxy_to TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, session_id, member_name),
    FOREIGN KEY(tenant_id, session_id) REFERENCES commission_sessions(tenant_id, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS specialized_instances (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    instance_type TEXT NOT NULL CHECK(instance_type IN ('CAO', 'CCSPL', 'CCID')),
    name TEXT NOT NULL,
    mandate_period TEXT NOT NULL,
    president_name TEXT NOT NULL,
    megalis_reference TEXT NOT NULL DEFAULT '',
    cadastre_scope TEXT NOT NULL DEFAULT '',
    public_service_delegations TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS specialized_instance_records (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    instance_id TEXT NOT NULL,
    record_type TEXT NOT NULL CHECK(record_type IN ('cao_marche', 'ccspl_rapport', 'ccid_evaluation')),
    reference TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'en_cours' CHECK(status IN ('en_cours', 'valide', 'clos', 'rejete')),
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, instance_id) REFERENCES specialized_instances(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_spec_instance_records ON specialized_instance_records(tenant_id, instance_id, record_type);
"""

# Default Specialized Instances for Plougastel-Daoulas
DEFAULT_SPECIALIZED_INSTANCES = [
    {
        "id": "cao",
        "instance_type": "CAO",
        "name": "Commission d'Appel d'Offres (CAO)",
        "mandate_period": "2026-2032",
        "president_name": "Maire de Plougastel-Daoulas",
        "megalis_reference": "MEGALIS-BRETAGNE-2027-PRO",
        "cadastre_scope": "",
        "public_service_delegations": "",
        "config": {
            "platform": "Mégalis Bretagne",
            "threshold_travaux_eur": 5382000,
            "threshold_fournitures_eur": 215000,
            "secretariat": "Direction de la Commande Publique",
        },
    },
    {
        "id": "ccspl",
        "instance_type": "CCSPL",
        "name": "Commission Consultative des Services Publics Locaux (CCSPL)",
        "mandate_period": "2026-2032",
        "president_name": "Adjoint délégué aux services publics",
        "megalis_reference": "",
        "cadastre_scope": "",
        "public_service_delegations": "Eau potable, Assainissement collectif, Déchets ménagers, Port du Tinduff",
        "config": {
            "delegations": [
                {"service": "Eau potable", "delegataire": "Eau du Ponant", "echeance": "2031"},
                {"service": "Assainissement", "delegataire": "Eau du Ponant", "echeance": "2031"},
                {"service": "Port de plaisance Tinduff", "delegataire": "Régie municipale", "echeance": "2030"},
            ],
            "periodicite_rapports": "Annuelle",
        },
    },
    {
        "id": "ccid",
        "instance_type": "CCID",
        "name": "Commission Communale des Impôts Directs (CCID)",
        "mandate_period": "2026-2032",
        "president_name": "Adjoint aux Finances & Fiscalité",
        "megalis_reference": "",
        "cadastre_scope": "Sections A à Z - Commune de Plougastel-Daoulas",
        "public_service_delegations": "",
        "config": {
            "cadastral_commissaires": 8,
            "suppleants": 8,
            "filiere_dgi": "SIP Brest Ouest",
            "scope": "Évaluation valeurs locatives cadastrales et locaux professionnels",
        },
    },
]


def format_deliberation_ref(session_date: str, commission_code: str, seq: int) -> str:
    """Generate canonical municipal deliberation reference format.
    
    Example: DELIB-2027-COM3-01 or DELIB-2027-CAO-02
    """
    year = session_date[:4] if len(session_date) >= 4 else "2027"
    code = re.sub(r"[^A-Za-z0-9]", "", commission_code).upper()
    if code.startswith("COMMISSION"):
        code = f"COM{code.replace('COMMISSION', '')}"
    return f"DELIB-{year}-{code}-{seq:02d}"


# Pydantic Schemas for API validation
class CommissionSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commission_id: str = Field(..., min_length=1, max_length=64)
    session_type: str = Field(default="commission", pattern="^(commission|cao|ccspl|ccid)$")
    title: str = Field(..., min_length=2, max_length=250)
    session_date: str = Field(..., min_length=10, max_length=10)
    session_time: str = Field(..., min_length=4, max_length=8)
    location: str = Field(default="Hôtel de Ville de Plougastel-Daoulas", max_length=200)
    quorum_required: int = Field(default=3, ge=1, le=50)
    notes: str = Field(default="", max_length=2000)


class AgendaItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., min_length=2, max_length=250)
    description: str = Field(default="", max_length=2000)
    project_id: str = Field(default="", max_length=64)
    rapporteur: str = Field(default="", max_length=120)
    deliberation_ref: str = Field(default="", max_length=64)


class AgendaItemReorder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ordered_item_ids: List[str] = Field(..., min_length=1)


class VoteRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vote_result: str = Field(..., pattern="^(en_attente|favorable|defavorable|reserve|ajourne)$")
    votes_for: int = Field(default=0, ge=0)
    votes_against: int = Field(default=0, ge=0)
    votes_abstention: int = Field(default=0, ge=0)
    official_decision: str = Field(default="", max_length=500)


class AttendanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_name: str = Field(..., min_length=2, max_length=120)
    member_role: str = Field(default="titulaire", pattern="^(titulaire|suppleant|invite|secretaire)$")
    status: str = Field(default="present", pattern="^(present|absent_excuse|absent|pouvoir)$")
    proxy_to: str = Field(default="", max_length=120)


class SessionAttendanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    attendances: List[AttendanceItem] = Field(default_factory=list)


class SessionCloseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    closed_by: str = Field(..., min_length=2, max_length=120)
    force_quorum: bool = False


class SpecializedRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_type: str = Field(..., pattern="^(cao_marche|ccspl_rapport|ccid_evaluation)$")
    reference: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=250)
    status: str = Field(default="en_cours", pattern="^(en_cours|valide|clos|rejete)$")
    details: Dict[str, Any] = Field(default_factory=dict)


class SeancesInstancesRepository:
    def __init__(self, repo: Repository):
        self._repo = repo
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._repo._lock:
            for statement in SEANCES_INSTANCES_SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    self._repo._db.execute(stmt)

    def _seed_specialized_instances_if_empty(self, tenant_id: str) -> None:
        with self._repo._transaction() as db:
            row = db.execute(
                "SELECT COUNT(*) FROM specialized_instances WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if row and row[0] > 0:
                return
            now = utc_now()
            for inst in DEFAULT_SPECIALIZED_INSTANCES:
                db.execute(
                    """
                    INSERT INTO specialized_instances (
                        tenant_id, id, instance_type, name, mandate_period,
                        president_name, megalis_reference, cadastre_scope,
                        public_service_delegations, config_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tenant_id,
                        inst["id"],
                        inst["instance_type"],
                        inst["name"],
                        inst["mandate_period"],
                        inst["president_name"],
                        inst["megalis_reference"],
                        inst["cadastre_scope"],
                        inst["public_service_delegations"],
                        json.dumps(inst["config"], ensure_ascii=False),
                        now,
                    ),
                )

    # -------------------------------------------------------------------------
    # Sessions Management
    # -------------------------------------------------------------------------
    def create_session(
        self,
        tenant_id: str,
        commission_id: str,
        title: str,
        session_date: str,
        session_time: str,
        location: str = "Hôtel de Ville de Plougastel-Daoulas",
        session_type: str = "commission",
        quorum_required: int = 3,
        notes: str = "",
    ) -> Dict[str, Any]:
        session_id = f"SES-{uuid4().hex[:8].upper()}"
        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO commission_sessions (
                    tenant_id, id, commission_id, session_type, title,
                    session_date, session_time, location, status,
                    quorum_required, quorum_present, pv_hash, closed_at,
                    closed_by, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, 0, '', '', '', ?, ?, ?)
                """,
                (
                    tenant_id,
                    session_id,
                    commission_id,
                    session_type,
                    title,
                    session_date,
                    session_time,
                    location,
                    quorum_required,
                    notes,
                    now,
                    now,
                ),
            )
        return self.get_session(tenant_id, session_id)

    def get_session(self, tenant_id: str, session_id: str) -> Dict[str, Any]:
        self._seed_specialized_instances_if_empty(tenant_id)
        with self._repo._lock:
            cur = self._repo._db.execute(
                """
                SELECT tenant_id, id, commission_id, session_type, title,
                       session_date, session_time, location, status,
                       quorum_required, quorum_present, pv_hash, closed_at,
                       closed_by, notes, created_at, updated_at
                FROM commission_sessions
                WHERE tenant_id = ? AND id = ?
                """,
                (tenant_id, session_id),
            )
            row = cur.fetchone()
            if not row:
                raise DomainError("session_not_found", f"Séance '{session_id}' introuvable.")

            cols = [
                "tenant_id", "id", "commission_id", "session_type", "title",
                "session_date", "session_time", "location", "status",
                "quorum_required", "quorum_present", "pv_hash", "closed_at",
                "closed_by", "notes", "created_at", "updated_at"
            ]
            session = dict(zip(cols, row))

            # Fetch agenda items ordered
            items_cur = self._repo._db.execute(
                """
                SELECT tenant_id, id, session_id, item_order, title, description,
                       project_id, project_version_snapshot, rapporteur, deliberation_ref,
                       vote_result, votes_for, votes_against, votes_abstention,
                       official_decision, created_at, updated_at
                FROM session_agenda_items
                WHERE tenant_id = ? AND session_id = ?
                ORDER BY item_order ASC
                """,
                (tenant_id, session_id),
            )
            item_cols = [
                "tenant_id", "id", "session_id", "item_order", "title", "description",
                "project_id", "project_version_snapshot", "rapporteur", "deliberation_ref",
                "vote_result", "votes_for", "votes_against", "votes_abstention",
                "official_decision", "created_at", "updated_at"
            ]
            items = []
            for item_row in items_cur.fetchall():
                item_dict = dict(zip(item_cols, item_row))
                try:
                    item_dict["project_version_snapshot"] = json.loads(item_dict["project_version_snapshot"] or "{}")
                except Exception:
                    item_dict["project_version_snapshot"] = {}
                items.append(item_dict)
            session["agenda_items"] = items

            # Fetch attendances
            att_cur = self._repo._db.execute(
                """
                SELECT member_name, member_role, status, proxy_to, updated_at
                FROM session_attendances
                WHERE tenant_id = ? AND session_id = ?
                ORDER BY member_name ASC
                """,
                (tenant_id, session_id),
            )
            att_cols = ["member_name", "member_role", "status", "proxy_to", "updated_at"]
            attendances = [dict(zip(att_cols, r)) for r in att_cur.fetchall()]
            session["attendances"] = attendances

            return session

    def list_sessions(
        self,
        tenant_id: str,
        commission_id: Optional[str] = None,
        session_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._seed_specialized_instances_if_empty(tenant_id)
        query = """
            SELECT tenant_id, id, commission_id, session_type, title,
                   session_date, session_time, location, status,
                   quorum_required, quorum_present, pv_hash, closed_at,
                   closed_by, notes, created_at, updated_at
            FROM commission_sessions
            WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if commission_id:
            query += " AND commission_id = ?"
            params.append(commission_id)
        if session_type:
            query += " AND session_type = ?"
            params.append(session_type)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY session_date DESC, session_time DESC"

        with self._repo._lock:
            cur = self._repo._db.execute(query, tuple(params))
            cols = [
                "tenant_id", "id", "commission_id", "session_type", "title",
                "session_date", "session_time", "location", "status",
                "quorum_required", "quorum_present", "pv_hash", "closed_at",
                "closed_by", "notes", "created_at", "updated_at"
            ]
            sessions = []
            for row in cur.fetchall():
                s = dict(zip(cols, row))
                # Add item count
                count_cur = self._repo._db.execute(
                    "SELECT COUNT(*) FROM session_agenda_items WHERE tenant_id = ? AND session_id = ?",
                    (tenant_id, s["id"]),
                )
                s["items_count"] = count_cur.fetchone()[0]
                sessions.append(s)
            return sessions

    def update_session_status(self, tenant_id: str, session_id: str, new_status: str) -> Dict[str, Any]:
        valid_statuses = ("draft", "en_cours", "closed", "archived")
        if new_status not in valid_statuses:
            raise DomainError("invalid_status", f"Statut de séance invalide: {new_status}")
        session = self.get_session(tenant_id, session_id)
        if session["status"] == "closed" and new_status != "archived":
            raise DomainError("session_closed", "Impossible de modifier une séance déjà clôturée.")
        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                "UPDATE commission_sessions SET status = ?, updated_at = ? WHERE tenant_id = ? AND id = ?",
                (new_status, now, tenant_id, session_id),
            )
        return self.get_session(tenant_id, session_id)

    # -------------------------------------------------------------------------
    # Agenda Items Management
    # -------------------------------------------------------------------------
    def add_agenda_item(
        self,
        tenant_id: str,
        session_id: str,
        title: str,
        description: str = "",
        project_id: str = "",
        rapporteur: str = "",
        deliberation_ref: str = "",
    ) -> Dict[str, Any]:
        session = self.get_session(tenant_id, session_id)
        if session["status"] == "closed":
            raise DomainError("session_closed", "Impossible d'ajouter un point à une séance déjà clôturée.")

        # Determine next item order
        with self._repo._lock:
            cur = self._repo._db.execute(
                "SELECT COALESCE(MAX(item_order), 0) FROM session_agenda_items WHERE tenant_id = ? AND session_id = ?",
                (tenant_id, session_id),
            )
            next_order = cur.fetchone()[0] + 1

        if not deliberation_ref:
            deliberation_ref = format_deliberation_ref(
                session["session_date"], session["commission_id"], next_order
            )

        item_id = f"ITM-{uuid4().hex[:8].upper()}"
        now = utc_now()

        # Build initial project snapshot if linked to a project
        snapshot = {}
        if project_id:
            try:
                proj = self._repo.get_project(tenant_id, project_id)
                if proj:
                    snapshot = {
                        "title": proj.get("name") or proj.get("title", ""),
                        "category": proj.get("specialization") or proj.get("category", ""),
                        "status": proj.get("status", ""),
                        "created_at": proj.get("created_at", ""),
                    }
            except Exception:
                snapshot = {"project_id": project_id}

        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO session_agenda_items (
                    tenant_id, id, session_id, item_order, title, description,
                    project_id, project_version_snapshot, rapporteur, deliberation_ref,
                    vote_result, votes_for, votes_against, votes_abstention,
                    official_decision, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_attente', 0, 0, 0, '', ?, ?)
                """,
                (
                    tenant_id,
                    item_id,
                    session_id,
                    next_order,
                    title,
                    description,
                    project_id,
                    json.dumps(snapshot, ensure_ascii=False),
                    rapporteur,
                    deliberation_ref,
                    now,
                    now,
                ),
            )
        return self.get_session(tenant_id, session_id)

    def reorder_agenda_items(
        self, tenant_id: str, session_id: str, ordered_item_ids: List[str]
    ) -> Dict[str, Any]:
        session = self.get_session(tenant_id, session_id)
        if session["status"] == "closed":
            raise DomainError("session_closed", "Impossible de réordonner l'ordre du jour d'une séance clôturée.")

        now = utc_now()
        with self._repo._transaction() as db:
            for idx, item_id in enumerate(ordered_item_ids, start=1):
                db.execute(
                    """
                    UPDATE session_agenda_items
                    SET item_order = ?, updated_at = ?
                    WHERE tenant_id = ? AND session_id = ? AND id = ?
                    """,
                    (idx, now, tenant_id, session_id, item_id),
                )
        return self.get_session(tenant_id, session_id)

    def record_item_vote(
        self,
        tenant_id: str,
        session_id: str,
        item_id: str,
        vote_result: str,
        votes_for: int = 0,
        votes_against: int = 0,
        votes_abstention: int = 0,
        official_decision: str = "",
    ) -> Dict[str, Any]:
        session = self.get_session(tenant_id, session_id)
        if session["status"] == "closed":
            raise DomainError("session_closed", "Impossible de modifier les votes d'une séance déjà clôturée.")

        valid_results = ("en_attente", "favorable", "defavorable", "reserve", "ajourne")
        if vote_result not in valid_results:
            raise DomainError("invalid_vote_result", f"Résultat de vote non reconnu: {vote_result}")

        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                """
                UPDATE session_agenda_items
                SET vote_result = ?, votes_for = ?, votes_against = ?,
                    votes_abstention = ?, official_decision = ?, updated_at = ?
                WHERE tenant_id = ? AND session_id = ? AND id = ?
                """,
                (
                    vote_result,
                    votes_for,
                    votes_against,
                    votes_abstention,
                    official_decision,
                    now,
                    tenant_id,
                    session_id,
                    item_id,
                ),
            )
        return self.get_session(tenant_id, session_id)

    # -------------------------------------------------------------------------
    # Attendance & Quorum
    # -------------------------------------------------------------------------
    def update_attendance(
        self,
        tenant_id: str,
        session_id: str,
        attendances: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        session = self.get_session(tenant_id, session_id)
        if session["status"] == "closed":
            raise DomainError("session_closed", "Impossible de modifier les présences d'une séance clôturée.")

        now = utc_now()
        quorum_present = 0

        with self._repo._transaction() as db:
            # Delete existing attendances
            db.execute(
                "DELETE FROM session_attendances WHERE tenant_id = ? AND session_id = ?",
                (tenant_id, session_id),
            )
            for att in attendances:
                name = att["member_name"].strip()
                if not name:
                    continue
                role = att.get("member_role", "titulaire")
                status = att.get("status", "present")
                proxy = att.get("proxy_to", "").strip()

                if status in ("present", "pouvoir"):
                    quorum_present += 1

                db.execute(
                    """
                    INSERT INTO session_attendances (
                        tenant_id, session_id, member_name, member_role, status, proxy_to, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, session_id, name, role, status, proxy, now),
                )

            # Update session quorum_present
            db.execute(
                "UPDATE commission_sessions SET quorum_present = ?, updated_at = ? WHERE tenant_id = ? AND id = ?",
                (quorum_present, now, tenant_id, session_id),
            )

        return self.get_session(tenant_id, session_id)

    # -------------------------------------------------------------------------
    # Decidim-Inspired Formal Close & Cryptographic Sealing
    # -------------------------------------------------------------------------
    def close_session(
        self,
        tenant_id: str,
        session_id: str,
        closed_by: str,
        force_quorum: bool = False,
    ) -> Dict[str, Any]:
        session = self.get_session(tenant_id, session_id)
        if session["status"] == "closed":
            raise DomainError("already_closed", "Cette séance est déjà clôturée et scellée.")

        # Quorum validation
        if not force_quorum and session["quorum_present"] < session["quorum_required"]:
            raise DomainError(
                "quorum_not_reached",
                f"Quorum non atteint : {session['quorum_present']} membres présents/représentés sur {session['quorum_required']} requis.",
            )

        now = utc_now()

        # Update project snapshots for all items before sealing
        for item in session["agenda_items"]:
            if item.get("project_id"):
                try:
                    p = self._repo.get_project(tenant_id, item["project_id"])
                    if p:
                        snap = {
                            "title": p.get("name") or p.get("title", ""),
                            "category": p.get("specialization") or p.get("category", ""),
                            "status": p.get("status", ""),
                            "snapshot_date": now,
                        }
                        with self._repo._transaction() as db:
                            db.execute(
                                "UPDATE session_agenda_items SET project_version_snapshot = ? WHERE tenant_id = ? AND id = ?",
                                (json.dumps(snap, ensure_ascii=False), tenant_id, item["id"]),
                            )
                except Exception:
                    pass

        # Re-fetch session data with updated snapshots
        refreshed = self.get_session(tenant_id, session_id)

        # Cryptographic seal generation (SHA-256 canonical hash)
        seal_payload = {
            "tenant_id": tenant_id,
            "session_id": session_id,
            "title": refreshed["title"],
            "session_date": refreshed["session_date"],
            "session_time": refreshed["session_time"],
            "location": refreshed["location"],
            "quorum_present": refreshed["quorum_present"],
            "quorum_required": refreshed["quorum_required"],
            "closed_by": closed_by,
            "closed_at": now,
            "attendances": [
                {"name": a["member_name"], "status": a["status"], "role": a["member_role"]}
                for a in refreshed["attendances"]
            ],
            "agenda_items": [
                {
                    "order": it["item_order"],
                    "title": it["title"],
                    "rapporteur": it["rapporteur"],
                    "deliberation_ref": it["deliberation_ref"],
                    "vote_result": it["vote_result"],
                    "votes_for": it["votes_for"],
                    "votes_against": it["votes_against"],
                    "votes_abstention": it["votes_abstention"],
                    "official_decision": it["official_decision"],
                    "snapshot": it["project_version_snapshot"],
                }
                for it in refreshed["agenda_items"]
            ],
        }

        canonical_bytes = canonical_json(seal_payload).encode("utf-8")
        pv_hash = hashlib.sha256(canonical_bytes).hexdigest()

        with self._repo._transaction() as db:
            db.execute(
                """
                UPDATE commission_sessions
                SET status = 'closed', pv_hash = ?, closed_at = ?, closed_by = ?, updated_at = ?
                WHERE tenant_id = ? AND id = ?
                """,
                (pv_hash, now, closed_by, now, tenant_id, session_id),
            )

        return self.get_session(tenant_id, session_id)

    # -------------------------------------------------------------------------
    # Specialized Instances (CAO, CCSPL, CCID)
    # -------------------------------------------------------------------------
    def list_specialized_instances(self, tenant_id: str) -> List[Dict[str, Any]]:
        self._seed_specialized_instances_if_empty(tenant_id)
        with self._repo._lock:
            cur = self._repo._db.execute(
                """
                SELECT tenant_id, id, instance_type, name, mandate_period,
                       president_name, megalis_reference, cadastre_scope,
                       public_service_delegations, config_json, created_at
                FROM specialized_instances
                WHERE tenant_id = ?
                ORDER BY id ASC
                """,
                (tenant_id,),
            )
            cols = [
                "tenant_id", "id", "instance_type", "name", "mandate_period",
                "president_name", "megalis_reference", "cadastre_scope",
                "public_service_delegations", "config_json", "created_at"
            ]
            results = []
            for row in cur.fetchall():
                inst = dict(zip(cols, row))
                try:
                    inst["config"] = json.loads(inst["config_json"] or "{}")
                except Exception:
                    inst["config"] = {}
                results.append(inst)
            return results

    def get_specialized_instance(self, tenant_id: str, instance_id: str) -> Dict[str, Any]:
        self._seed_specialized_instances_if_empty(tenant_id)
        with self._repo._lock:
            cur = self._repo._db.execute(
                """
                SELECT tenant_id, id, instance_type, name, mandate_period,
                       president_name, megalis_reference, cadastre_scope,
                       public_service_delegations, config_json, created_at
                FROM specialized_instances
                WHERE tenant_id = ? AND id = ?
                """,
                (tenant_id, instance_id),
            )
            row = cur.fetchone()
            if not row:
                raise DomainError("instance_not_found", f"Instance spécialisée '{instance_id}' introuvable.")
            cols = [
                "tenant_id", "id", "instance_type", "name", "mandate_period",
                "president_name", "megalis_reference", "cadastre_scope",
                "public_service_delegations", "config_json", "created_at"
            ]
            inst = dict(zip(cols, row))
            try:
                inst["config"] = json.loads(inst["config_json"] or "{}")
            except Exception:
                inst["config"] = {}
            return inst

    def create_specialized_record(
        self,
        tenant_id: str,
        instance_id: str,
        record_type: str,
        reference: str,
        title: str,
        details: Optional[Dict[str, Any]] = None,
        status: str = "en_cours",
    ) -> Dict[str, Any]:
        self.get_specialized_instance(tenant_id, instance_id)
        valid_types = ("cao_marche", "ccspl_rapport", "ccid_evaluation")
        if record_type not in valid_types:
            raise DomainError("invalid_record_type", f"Type d'enregistrement spécialisé invalide: {record_type}")

        record_id = f"REC-{uuid4().hex[:8].upper()}"
        now = utc_now()
        details_json = json.dumps(details or {}, ensure_ascii=False)

        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO specialized_instance_records (
                    tenant_id, id, instance_id, record_type, reference, title,
                    status, details_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    record_id,
                    instance_id,
                    record_type,
                    reference,
                    title,
                    status,
                    details_json,
                    now,
                    now,
                ),
            )
        return self.get_specialized_record(tenant_id, record_id)

    def get_specialized_record(self, tenant_id: str, record_id: str) -> Dict[str, Any]:
        with self._repo._lock:
            cur = self._repo._db.execute(
                """
                SELECT tenant_id, id, instance_id, record_type, reference, title,
                       status, details_json, created_at, updated_at
                FROM specialized_instance_records
                WHERE tenant_id = ? AND id = ?
                """,
                (tenant_id, record_id),
            )
            row = cur.fetchone()
            if not row:
                raise DomainError("record_not_found", f"Enregistrement spécialisé '{record_id}' introuvable.")
            cols = [
                "tenant_id", "id", "instance_id", "record_type", "reference", "title",
                "status", "details_json", "created_at", "updated_at"
            ]
            rec = dict(zip(cols, row))
            try:
                rec["details"] = json.loads(rec["details_json"] or "{}")
            except Exception:
                rec["details"] = {}
            return rec

    def list_specialized_records(
        self,
        tenant_id: str,
        instance_id: Optional[str] = None,
        record_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._seed_specialized_instances_if_empty(tenant_id)
        query = """
            SELECT tenant_id, id, instance_id, record_type, reference, title,
                   status, details_json, created_at, updated_at
            FROM specialized_instance_records
            WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if instance_id:
            query += " AND instance_id = ?"
            params.append(instance_id)
        if record_type:
            query += " AND record_type = ?"
            params.append(record_type)

        query += " ORDER BY created_at DESC"

        with self._repo._lock:
            cur = self._repo._db.execute(query, tuple(params))
            cols = [
                "tenant_id", "id", "instance_id", "record_type", "reference", "title",
                "status", "details_json", "created_at", "updated_at"
            ]
            records = []
            for row in cur.fetchall():
                rec = dict(zip(cols, row))
                try:
                    rec["details"] = json.loads(rec["details_json"] or "{}")
                except Exception:
                    rec["details"] = {}
                records.append(rec)
            return records


def setup_seances_instances_routes(
    app,
    repo: Repository,
    settings,
    seances_repo: SeancesInstancesRepository,
    actor_dep,
    require_project_write,
    require_project_read,
):
    from fastapi import Depends, HTTPException

    @app.get("/api/v1/sessions")
    def list_sessions_route(
        commission_id: Optional[str] = None,
        session_type: Optional[str] = None,
        status: Optional[str] = None,
        current=Depends(actor_dep),
    ):
        sessions = seances_repo.list_sessions(
            settings.tenant_id,
            commission_id=commission_id,
            session_type=session_type,
            status=status,
        )
        return {"items": sessions, "total": len(sessions)}

    @app.post("/api/v1/sessions")
    def create_session_route(
        body: CommissionSessionCreate,
        current=Depends(actor_dep),
    ):
        return seances_repo.create_session(
            settings.tenant_id,
            commission_id=body.commission_id,
            title=body.title,
            session_date=body.session_date,
            session_time=body.session_time,
            location=body.location,
            session_type=body.session_type,
            quorum_required=body.quorum_required,
            notes=body.notes,
        )

    @app.get("/api/v1/sessions/{session_id}")
    def get_session_route(session_id: str, current=Depends(actor_dep)):
        session = seances_repo.get_session(settings.tenant_id, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Séance introuvable")
        return session

    @app.patch("/api/v1/sessions/{session_id}/status")
    def update_session_status_route(session_id: str, new_status: str, current=Depends(actor_dep)):
        return seances_repo.update_session_status(settings.tenant_id, session_id, new_status)

    @app.post("/api/v1/sessions/{session_id}/agenda")
    def add_agenda_item_route(
        session_id: str,
        body: AgendaItemCreate,
        current=Depends(actor_dep),
    ):
        if body.project_id:
            require_project_read(body.project_id, current)
        return seances_repo.add_agenda_item(
            settings.tenant_id,
            session_id=session_id,
            title=body.title,
            description=body.description,
            project_id=body.project_id,
            rapporteur=body.rapporteur,
            deliberation_ref=body.deliberation_ref,
        )

    @app.put("/api/v1/sessions/{session_id}/agenda/reorder")
    def reorder_agenda_route(
        session_id: str,
        body: AgendaItemReorder,
        current=Depends(actor_dep),
    ):
        return seances_repo.reorder_agenda_items(
            settings.tenant_id,
            session_id=session_id,
            ordered_item_ids=body.ordered_item_ids,
        )

    @app.post("/api/v1/sessions/{session_id}/items/{item_id}/vote")
    def record_vote_route(
        session_id: str,
        item_id: str,
        body: VoteRecordRequest,
        current=Depends(actor_dep),
    ):
        return seances_repo.record_item_vote(
            settings.tenant_id,
            session_id=session_id,
            item_id=item_id,
            vote_result=body.vote_result,
            votes_for=body.votes_for,
            votes_against=body.votes_against,
            votes_abstention=body.votes_abstention,
            official_decision=body.official_decision,
        )

    @app.post("/api/v1/sessions/{session_id}/attendance")
    def update_attendance_route(
        session_id: str,
        body: SessionAttendanceUpdate,
        current=Depends(actor_dep),
    ):
        attendances = [att.model_dump() for att in body.attendances]
        return seances_repo.update_attendance(
            settings.tenant_id,
            session_id=session_id,
            attendances=attendances,
        )

    @app.post("/api/v1/sessions/{session_id}/close")
    def close_session_route(
        session_id: str,
        body: SessionCloseRequest,
        current=Depends(actor_dep),
    ):
        return seances_repo.close_session(
            settings.tenant_id,
            session_id=session_id,
            closed_by=body.closed_by,
            force_quorum=body.force_quorum,
        )

    @app.get("/api/v1/instances/specialized")
    def list_specialized_instances_route(current=Depends(actor_dep)):
        items = seances_repo.list_specialized_instances(settings.tenant_id)
        return {"items": items, "total": len(items)}

    @app.get("/api/v1/instances/specialized/{instance_id}")
    def get_specialized_instance_route(instance_id: str, current=Depends(actor_dep)):
        return seances_repo.get_specialized_instance(settings.tenant_id, instance_id)

    @app.get("/api/v1/instances/specialized/{instance_id}/records")
    def list_instance_records_route(
        instance_id: str,
        record_type: Optional[str] = None,
        current=Depends(actor_dep),
    ):
        items = seances_repo.list_specialized_records(
            settings.tenant_id,
            instance_id=instance_id,
            record_type=record_type,
        )
        return {"items": items, "total": len(items)}

    @app.post("/api/v1/instances/specialized/{instance_id}/records")
    def create_instance_record_route(
        instance_id: str,
        body: SpecializedRecordCreate,
        current=Depends(actor_dep),
    ):
        return seances_repo.create_specialized_record(
            settings.tenant_id,
            instance_id=instance_id,
            record_type=body.record_type,
            reference=body.reference,
            title=body.title,
            details=body.details,
            status=body.status,
        )

    @app.get("/api/v1/instances/records")
    def list_all_records_route(
        record_type: Optional[str] = None,
        current=Depends(actor_dep),
    ):
        items = seances_repo.list_specialized_records(
            settings.tenant_id,
            instance_id=None,
            record_type=record_type,
        )
        return {"items": items, "total": len(items)}

