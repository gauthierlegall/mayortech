from __future__ import annotations

import datetime
import uuid
import re
from typing import Any, Callable, Dict, List, Optional
from fastapi import FastAPI, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .domain import DomainError


class MunicipalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MunicipalEntryInput(MunicipalInput):
    matricule: str = Field(min_length=2, max_length=50)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    statut: str = Field(pattern="^(elu|titulaire|contractuel|vacataire|prestataire)$")
    direction: str = Field(min_length=1, max_length=150)
    poste: str = Field(min_length=1, max_length=150)
    commission_id: Optional[str] = Field(default="commission-3", max_length=100)
    niveau: int = Field(default=1, ge=0, le=5)
    role: str = Field(pattern="^(reader|editor|admin)$")
    delegation_signature: bool = Field(default=False)
    arrete_delegation: Optional[str] = Field(default=None, max_length=100)
    suppleant_id: Optional[str] = Field(default=None, max_length=100)
    telephone: Optional[str] = Field(default=None, max_length=30)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Adresse email invalide")
        return clean


class MunicipalEntryUpdate(MunicipalInput):
    nom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    prenom: Optional[str] = Field(default=None, min_length=1, max_length=100)
    statut: Optional[str] = Field(default=None, pattern="^(elu|titulaire|contractuel|vacataire|prestataire)$")
    direction: Optional[str] = Field(default=None, min_length=1, max_length=150)
    poste: Optional[str] = Field(default=None, min_length=1, max_length=150)
    commission_id: Optional[str] = Field(default=None, max_length=100)
    niveau: Optional[int] = Field(default=None, ge=0, le=5)
    role: Optional[str] = Field(default=None, pattern="^(reader|editor|admin)$")
    delegation_signature: Optional[bool] = None
    arrete_delegation: Optional[str] = Field(default=None, max_length=100)
    suppleant_id: Optional[str] = Field(default=None, max_length=100)
    telephone: Optional[str] = Field(default=None, max_length=30)
    active: Optional[bool] = None


class MunicipalDelegationInput(MunicipalInput):
    titulaire_id: str = Field(min_length=1, max_length=100)
    suppleant_id: str = Field(min_length=1, max_length=100)
    scope: str = Field(default="all", pattern="^(all|signature|visa|commission)$")
    start_date: str = Field(min_length=10, max_length=30)
    end_date: Optional[str] = Field(default=None, max_length=30)
    arrete_reference: Optional[str] = Field(default=None, max_length=100)


class JoinDecisionInput(MunicipalInput):
    decision: str = Field(pattern="^(approve|reject)$")
    assigned_commission: Optional[str] = Field(default="commission-3", max_length=100)
    assigned_level: int = Field(default=2, ge=0, le=5)
    assigned_role: str = Field(default="editor", pattern="^(reader|editor|admin)$")
    reason: Optional[str] = Field(default=None, max_length=500)


class JoinRequestSubmission(MunicipalInput):
    email: str = Field(min_length=3, max_length=255)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    poste_souhaite: Optional[str] = Field(default="", max_length=150)
    code_organisation: str = Field(min_length=4, max_length=64)


class MunicipalDirectoryRepository:
    def __init__(self, repo_or_db):
        import threading
        if hasattr(repo_or_db, "_db"):
            self.repo = repo_or_db
            self._db = repo_or_db._db
            self._lock = repo_or_db._lock
        else:
            self.repo = None
            self._db = repo_or_db
            self._lock = threading.RLock()
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with self._lock:
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS municipal_directory_entries (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    matricule TEXT NOT NULL,
                    nom TEXT NOT NULL,
                    prenom TEXT NOT NULL,
                    email TEXT NOT NULL,
                    statut TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    poste TEXT NOT NULL,
                    commission_id TEXT NOT NULL DEFAULT 'commission-3',
                    niveau INTEGER NOT NULL DEFAULT 1,
                    role TEXT NOT NULL DEFAULT 'reader',
                    delegation_signature INTEGER NOT NULL DEFAULT 0,
                    arrete_delegation TEXT,
                    suppleant_id TEXT,
                    telephone TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, matricule),
                    UNIQUE(tenant_id, email)
                )
                """
            )
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS municipal_departments (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    label TEXT NOT NULL,
                    responsable_id TEXT,
                    commission_id TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(tenant_id, code)
                )
                """
            )
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS municipal_delegations (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    titulaire_id TEXT NOT NULL,
                    suppleant_id TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'all',
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    arrete_reference TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS municipal_join_requests (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    nom TEXT NOT NULL,
                    prenom TEXT NOT NULL,
                    poste_souhaite TEXT,
                    code_organisation TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    assigned_commission TEXT,
                    assigned_level INTEGER,
                    assigned_role TEXT,
                    decided_by TEXT,
                    decided_at TEXT,
                    decision_reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._db.commit()

    def create_entry(self, tenant_id: str, data: MunicipalEntryInput, actor_id: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        entry_id = str(uuid.uuid4())
        try:
            with self._lock:
                self._db.execute(
                    """
                    INSERT INTO municipal_directory_entries (
                        id, tenant_id, matricule, nom, prenom, email, statut,
                        direction, poste, commission_id, niveau, role,
                        delegation_signature, arrete_delegation, suppleant_id,
                        telephone, active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        entry_id, tenant_id, data.matricule.strip(),
                        data.nom.strip().upper(), data.prenom.strip().title(),
                        data.email.strip().lower(), data.statut,
                        data.direction.strip(), data.poste.strip(),
                        data.commission_id or "commission-3", data.niveau, data.role,
                        1 if data.delegation_signature else 0,
                        data.arrete_delegation, data.suppleant_id,
                        data.telephone, now, now
                    )
                )
                self._db.commit()
        except Exception as e:
            if "UNIQUE" in str(e):
                raise DomainError("conflict", f"Un agent avec le matricule '{data.matricule}' ou le courriel '{data.email}' existe déjà.")
            raise DomainError("db_error", str(e))
        return self.get_entry(tenant_id, entry_id)

    def get_entry(self, tenant_id: str, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(
                """
                SELECT id, tenant_id, matricule, nom, prenom, email, statut,
                       direction, poste, commission_id, niveau, role,
                       delegation_signature, arrete_delegation, suppleant_id,
                       telephone, active, created_at, updated_at
                FROM municipal_directory_entries
                WHERE tenant_id = ? AND (id = ? OR matricule = ?)
                """,
                (tenant_id, entry_id, entry_id)
            )
            row = cursor.fetchone()
        if not row:
            raise DomainError("not_found", f"Agent introuvable : {entry_id}")
        return self._row_to_entry(row)

    def update_entry(self, tenant_id: str, entry_id: str, data: MunicipalEntryUpdate) -> Dict[str, Any]:
        existing = self.get_entry(tenant_id, entry_id)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        updates = []
        params = []
        if data.nom is not None:
            updates.append("nom = ?")
            params.append(data.nom.strip().upper())
        if data.prenom is not None:
            updates.append("prenom = ?")
            params.append(data.prenom.strip().title())
        if data.statut is not None:
            updates.append("statut = ?")
            params.append(data.statut)
        if data.direction is not None:
            updates.append("direction = ?")
            params.append(data.direction.strip())
        if data.poste is not None:
            updates.append("poste = ?")
            params.append(data.poste.strip())
        if data.commission_id is not None:
            updates.append("commission_id = ?")
            params.append(data.commission_id)
        if data.niveau is not None:
            updates.append("niveau = ?")
            params.append(data.niveau)
        if data.role is not None:
            updates.append("role = ?")
            params.append(data.role)
        if data.delegation_signature is not None:
            updates.append("delegation_signature = ?")
            params.append(1 if data.delegation_signature else 0)
        if data.arrete_delegation is not None:
            updates.append("arrete_delegation = ?")
            params.append(data.arrete_delegation)
        if data.suppleant_id is not None:
            updates.append("suppleant_id = ?")
            params.append(data.suppleant_id)
        if data.telephone is not None:
            updates.append("telephone = ?")
            params.append(data.telephone)
        if data.active is not None:
            updates.append("active = ?")
            params.append(1 if data.active else 0)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(now)
        params.extend([tenant_id, existing["id"]])

        with self._lock:
            self._db.execute(
                f"""
                UPDATE municipal_directory_entries
                SET {', '.join(updates)}
                WHERE tenant_id = ? AND id = ?
                """,
                params
            )
            self._db.commit()
        return self.get_entry(tenant_id, existing["id"])

    def revoke_entry(self, tenant_id: str, entry_id: str, actor_id: Optional[str] = None) -> Dict[str, Any]:
        existing = self.get_entry(tenant_id, entry_id)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock:
            self._db.execute(
                """
                UPDATE municipal_directory_entries
                SET active = 0, updated_at = ?
                WHERE tenant_id = ? AND id = ?
                """,
                (now, tenant_id, existing["id"])
            )
            self._db.commit()
        return self.get_entry(tenant_id, existing["id"])

    def list_entries(
        self,
        tenant_id: str,
        commission_id: Optional[str] = None,
        direction: Optional[str] = None,
        statut: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT id, tenant_id, matricule, nom, prenom, email, statut,
                   direction, poste, commission_id, niveau, role,
                   delegation_signature, arrete_delegation, suppleant_id,
                   telephone, active, created_at, updated_at
            FROM municipal_directory_entries
            WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if active_only:
            query += " AND active = 1"
        if commission_id and commission_id != "all":
            query += " AND (commission_id = ? OR commission_id = 'all')"
            params.append(commission_id)
        if direction:
            query += " AND direction = ?"
            params.append(direction)
        if statut:
            query += " AND statut = ?"
            params.append(statut)
        query += " ORDER BY niveau DESC, nom ASC"

        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [self._row_to_entry(r) for r in rows]

    def create_delegation(self, tenant_id: str, data: MunicipalDelegationInput) -> Dict[str, Any]:
        self.get_entry(tenant_id, data.titulaire_id)
        self.get_entry(tenant_id, data.suppleant_id)
        del_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock:
            self._db.execute(
                """
                INSERT INTO municipal_delegations (
                    id, tenant_id, titulaire_id, suppleant_id, scope,
                    start_date, end_date, arrete_reference, active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    del_id, tenant_id, data.titulaire_id, data.suppleant_id,
                    data.scope, data.start_date, data.end_date,
                    data.arrete_reference, now
                )
            )
            self._db.commit()
        return self.get_delegation(tenant_id, del_id)

    def get_delegation(self, tenant_id: str, delegation_id: str) -> Dict[str, Any]:
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(
                """
                SELECT d.id, d.tenant_id, d.titulaire_id, d.suppleant_id, d.scope,
                       d.start_date, d.end_date, d.arrete_reference, d.active, d.created_at,
                       t.nom as titulaire_nom, t.prenom as titulaire_prenom, t.poste as titulaire_poste,
                       s.nom as suppleant_nom, s.prenom as suppleant_prenom, s.poste as suppleant_poste
                FROM municipal_delegations d
                JOIN municipal_directory_entries t ON d.titulaire_id = t.id
                JOIN municipal_directory_entries s ON d.suppleant_id = s.id
                WHERE d.tenant_id = ? AND d.id = ?
                """,
                (tenant_id, delegation_id)
            )
            row = cursor.fetchone()
        if not row:
            raise DomainError("not_found", f"Délégation introuvable : {delegation_id}")
        return {
            "id": row[0],
            "tenant_id": row[1],
            "titulaire_id": row[2],
            "suppleant_id": row[3],
            "scope": row[4],
            "start_date": row[5],
            "end_date": row[6],
            "arrete_reference": row[7],
            "active": bool(row[8]),
            "created_at": row[9],
            "titulaire": f"{row[11]} {row[10]} ({row[12]})",
            "suppleant": f"{row[14]} {row[13]} ({row[15]})"
        }

    def list_delegations(self, tenant_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        query = """
            SELECT d.id, d.tenant_id, d.titulaire_id, d.suppleant_id, d.scope,
                   d.start_date, d.end_date, d.arrete_reference, d.active, d.created_at,
                   t.nom as titulaire_nom, t.prenom as titulaire_prenom, t.poste as titulaire_poste,
                   s.nom as suppleant_nom, s.prenom as suppleant_prenom, s.poste as suppleant_poste
            FROM municipal_delegations d
            JOIN municipal_directory_entries t ON d.titulaire_id = t.id
            JOIN municipal_directory_entries s ON d.suppleant_id = s.id
            WHERE d.tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if active_only:
            query += " AND d.active = 1"
        query += " ORDER BY d.created_at DESC"
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "tenant_id": r[1],
                "titulaire_id": r[2],
                "suppleant_id": r[3],
                "scope": r[4],
                "start_date": r[5],
                "end_date": r[6],
                "arrete_reference": r[7],
                "active": bool(r[8]),
                "created_at": r[9],
                "titulaire": f"{r[11]} {r[10]} ({r[12]})",
                "suppleant": f"{r[14]} {r[13]} ({r[15]})"
            }
            for r in rows
        ]

    # Join requests methods
    def request_join(self, tenant_id: str, email: str, nom: str, prenom: str, poste_souhaite: str, code_organisation: str) -> Dict[str, Any]:
        clean_code = code_organisation.strip().upper()
        if clean_code != "PLOUGASTEL-2026":
            raise DomainError("invalid_input", "Code confidentiel municipal invalide ou expiré.")
        req_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock:
            self._db.execute(
                """
                INSERT INTO municipal_join_requests (
                    id, tenant_id, email, nom, prenom, poste_souhaite,
                    code_organisation, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (req_id, tenant_id, email.strip().lower(), nom.strip().upper(), prenom.strip().title(), poste_souhaite, clean_code, now)
            )
            self._db.commit()
        return self.get_join_request(tenant_id, req_id)

    def get_join_request(self, tenant_id: str, request_id: str) -> Dict[str, Any]:
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(
                """
                SELECT id, tenant_id, email, nom, prenom, poste_souhaite,
                       code_organisation, status, assigned_commission, assigned_level,
                       assigned_role, decided_by, decided_at, decision_reason, created_at
                FROM municipal_join_requests
                WHERE tenant_id = ? AND id = ?
                """,
                (tenant_id, request_id)
            )
            row = cursor.fetchone()
        if not row:
            raise DomainError("not_found", f"Demande d'enrôlement introuvable : {request_id}")
        return {
            "id": row[0],
            "tenant_id": row[1],
            "email": row[2],
            "nom": row[3],
            "prenom": row[4],
            "poste_souhaite": row[5],
            "code_organisation": row[6],
            "status": row[7],
            "assigned_commission": row[8],
            "assigned_level": row[9],
            "assigned_role": row[10],
            "decided_by": row[11],
            "decided_at": row[12],
            "decision_reason": row[13],
            "created_at": row[14],
        }

    def list_join_requests(self, tenant_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        query = """
            SELECT id, tenant_id, email, nom, prenom, poste_souhaite,
                   code_organisation, status, assigned_commission, assigned_level,
                   assigned_role, decided_by, decided_at, decision_reason, created_at
            FROM municipal_join_requests
            WHERE tenant_id = ?
        """
        params: List[Any] = [tenant_id]
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC"
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "tenant_id": r[1],
                "email": r[2],
                "nom": r[3],
                "prenom": r[4],
                "poste_souhaite": r[5],
                "code_organisation": r[6],
                "status": r[7],
                "assigned_commission": r[8],
                "assigned_level": r[9],
                "assigned_role": r[10],
                "decided_by": r[11],
                "decided_at": r[12],
                "decision_reason": r[13],
                "created_at": r[14],
            }
            for r in rows
        ]

    def decide_join_request(self, tenant_id: str, request_id: str, decision: JoinDecisionInput, decided_by: str) -> Dict[str, Any]:
        req = self.get_join_request(tenant_id, request_id)
        if req["status"] != "pending":
            raise DomainError("invalid_state", "Cette demande a déjà été traitée.")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        new_status = "approved" if decision.decision == "approve" else "rejected"

        with self._lock:
            self._db.execute(
                """
                UPDATE municipal_join_requests
                SET status = ?, assigned_commission = ?, assigned_level = ?,
                    assigned_role = ?, decided_by = ?, decided_at = ?, decision_reason = ?
                WHERE tenant_id = ? AND id = ?
                """,
                (
                    new_status, decision.assigned_commission, decision.assigned_level,
                    decision.assigned_role, decided_by, now, decision.reason,
                    tenant_id, request_id
                )
            )
            self._db.commit()

        if new_status == "approved":
            # Auto-create or activate in directory
            matricule_generated = f"AGT-{abs(hash(req['email'])) % 900 + 100}"
            entry_data = MunicipalEntryInput(
                matricule=matricule_generated,
                nom=req["nom"],
                prenom=req["prenom"],
                email=req["email"],
                statut="titulaire",
                direction="Services Municipaux",
                poste=req["poste_souhaite"] or "Agent Municipal",
                commission_id=decision.assigned_commission or "commission-3",
                niveau=decision.assigned_level,
                role=decision.assigned_role,
                delegation_signature=False
            )
            try:
                self.create_entry(tenant_id, entry_data, actor_id=decided_by)
            except DomainError as err:
                if err.code != "conflict":
                    raise

        return self.get_join_request(tenant_id, request_id)

    def seed_default_directory(self, tenant_id: str) -> None:
        """Seeds initial municipal directory for Plougastel-Daoulas if empty."""
        with self._lock:
            cursor = self._db.cursor()
            cursor.execute("SELECT COUNT(*) FROM municipal_directory_entries WHERE tenant_id = ?", (tenant_id,))
            if cursor.fetchone()[0] > 0:
                return

        defaults = [
            # ELUS
            ("ELU-001", "CAP", "Dominique", "maire@ville-plougastel.bzh", "elu", "Exécutif Municipal", "Maire de Plougastel-Daoulas", "all", 4, "admin", 1, "Arrêté 2026-01", None, "02 98 37 57 57"),
            ("ELU-002", "LE GALL", "Jean-Luc", "travaux.elu@ville-plougastel.bzh", "elu", "Exécutif Municipal", "Adjoint aux Travaux, Ports & Urbanisme", "commission-3", 4, "admin", 1, "Arrêté 2026-03", None, "02 98 37 57 60"),
            ("ELU-003", "MORVAN", "Françoise", "finances.elu@ville-plougastel.bzh", "elu", "Exécutif Municipal", "Adjointe aux Finances & Budget", "commission-1", 4, "admin", 1, "Arrêté 2026-02", None, "02 98 37 57 61"),
            ("ELU-004", "QUÉRÉ", "Hélène", "culture.elu@ville-plougastel.bzh", "elu", "Exécutif Municipal", "Adjointe à la Culture & Vie Associative", "commission-4", 4, "admin", 1, "Arrêté 2026-04", None, "02 98 37 57 62"),
            ("ELU-005", "BOURHIS", "Marc", "social.elu@ville-plougastel.bzh", "elu", "Exécutif Municipal", "Adjoint aux Solidarités & Enfance", "commission-2", 4, "admin", 1, "Arrêté 2026-05", None, "02 98 37 57 63"),
            # ADMINISTRATION & CADRES
            ("AGT-001", "DGS", "Titulaire", "dgs@ville-plougastel.bzh", "titulaire", "Direction Générale", "Directeur Général des Services", "all", 5, "admin", 1, "Délégation DGS 2026", None, "02 98 37 57 58"),
            ("AGT-010", "DST", "Titulaire", "dst@ville-plougastel.bzh", "titulaire", "Services Techniques", "Directeur des Services Techniques", "commission-3", 3, "editor", 0, None, None, "02 98 37 57 70"),
            ("AGT-011", "DUPONT", "Marie", "urbanisme@ville-plougastel.bzh", "titulaire", "Urbanisme & Foncier", "Instructeur Droit des Sols", "commission-3", 2, "editor", 0, None, None, "02 98 37 57 71"),
            ("AGT-012", "KERVELLA", "Yann", "ports.tinduff@ville-plougastel.bzh", "titulaire", "Ports & Littoral", "Responsable Ports du Tinduff & Cales", "commission-3", 2, "editor", 0, None, None, "02 98 37 57 72"),
            ("AGT-020", "LE BRIS", "Anne", "comptabilite@ville-plougastel.bzh", "titulaire", "Finances & Commande", "Responsable Budget & Dette", "commission-1", 3, "editor", 0, None, None, "02 98 37 57 80"),
            ("AGT-021", "ROUX", "Sébastien", "marches@ville-plougastel.bzh", "contractuel", "Finances & Commande", "Gestionnaire Marchés Publics (CAO)", "commission-1", 2, "editor", 0, None, None, "02 98 37 57 81"),
            ("AGT-030", "SALAUN", "Guillaume", "avelvor@ville-plougastel.bzh", "titulaire", "Culture & Animation", "Régisseur Général Salle Avel Vor", "commission-4", 3, "editor", 0, None, None, "02 98 37 57 90"),
            ("AGT-031", "THOMAS", "Cécile", "associations@ville-plougastel.bzh", "titulaire", "Culture & Animation", "Gestionnaire Vie Associative & Salles", "commission-4", 2, "editor", 0, None, None, "02 98 37 57 91"),
            ("AGT-040", "JEZEQUEL", "Solange", "ccas@ville-plougastel.bzh", "titulaire", "Action Sociale", "Directrice de l'Action Sociale CCAS", "commission-2", 3, "editor", 0, None, None, "02 98 37 57 85"),
            ("AGT-041", "MADEC", "Benoît", "scolaire@ville-plougastel.bzh", "titulaire", "Enfance & Écoles", "Responsable Affaires Scolaires & Restauration", "commission-2", 2, "editor", 0, None, None, "02 98 37 57 86"),
        ]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._lock:
            for item in defaults:
                self._db.execute(
                    """
                    INSERT INTO municipal_directory_entries (
                        id, tenant_id, matricule, nom, prenom, email, statut,
                        direction, poste, commission_id, niveau, role,
                        delegation_signature, arrete_delegation, suppleant_id,
                        telephone, active, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()), tenant_id, item[0], item[1], item[2], item[3],
                        item[4], item[5], item[6], item[7], item[8], item[9],
                        item[10], item[11], item[12], item[13], now, now
                    )
                )
            self._db.commit()

    def _row_to_entry(self, row: Any) -> Dict[str, Any]:
        return {
            "id": row[0],
            "tenant_id": row[1],
            "matricule": row[2],
            "nom": row[3],
            "prenom": row[4],
            "email": row[5],
            "statut": row[6],
            "direction": row[7],
            "poste": row[8],
            "commission_id": row[9],
            "niveau": row[10],
            "role": row[11],
            "delegation_signature": bool(row[12]),
            "arrete_delegation": row[13],
            "suppleant_id": row[14],
            "telephone": row[15],
            "active": bool(row[16]),
            "created_at": row[17],
            "updated_at": row[18],
            "display_name": f"{row[4]} {row[3]}",
        }


def register_municipal_directory_routes(app: FastAPI, repo, tenant_id: str, actor_dep, directory: MunicipalDirectoryRepository):
    @app.get("/api/v1/municipal/directory")
    def list_municipal_directory(
        commission_id: Optional[str] = None,
        direction: Optional[str] = None,
        statut: Optional[str] = None,
        active_only: bool = True,
        current=Depends(actor_dep)
    ):
        return directory.list_entries(tenant_id, commission_id=commission_id, direction=direction, statut=statut, active_only=active_only)

    @app.post("/api/v1/municipal/directory", status_code=status.HTTP_201_CREATED)
    def create_municipal_entry(body: MunicipalEntryInput, current=Depends(actor_dep)):
        if current.get("role") != "admin":
            raise DomainError("forbidden", "Seul un administrateur ou la DGS peut inscrire un agent au répertoire municipal.")
        return directory.create_entry(tenant_id, body, actor_id=current.get("actor_id"))

    @app.get("/api/v1/municipal/directory/{entry_id}")
    def get_municipal_entry(entry_id: str, current=Depends(actor_dep)):
        return directory.get_entry(tenant_id, entry_id)

    @app.patch("/api/v1/municipal/directory/{entry_id}")
    def update_municipal_entry(entry_id: str, body: MunicipalEntryUpdate, current=Depends(actor_dep)):
        if current.get("role") != "admin":
            raise DomainError("forbidden", "Seul un administrateur ou la DGS peut modifier une fiche d'habilitation municipale.")
        return directory.update_entry(tenant_id, entry_id, body)

    @app.post("/api/v1/municipal/directory/{entry_id}/revoke")
    def revoke_municipal_entry(entry_id: str, current=Depends(actor_dep)):
        if current.get("role") != "admin":
            raise DomainError("forbidden", "Seul un administrateur ou la DGS peut révoquer un agent municipal.")
        return directory.revoke_entry(tenant_id, entry_id, actor_id=current.get("actor_id"))

    @app.get("/api/v1/municipal/delegations")
    def list_delegations(active_only: bool = True, current=Depends(actor_dep)):
        return directory.list_delegations(tenant_id, active_only=active_only)

    @app.post("/api/v1/municipal/delegations", status_code=status.HTTP_201_CREATED)
    def create_delegation(body: MunicipalDelegationInput, current=Depends(actor_dep)):
        if current.get("role") != "admin":
            raise DomainError("forbidden", "Seul un administrateur ou la DGS peut enregistrer un arrêté de délégation ou suppléance.")
        return directory.create_delegation(tenant_id, body)

    @app.post("/api/v1/organization/join-requests", status_code=status.HTTP_201_CREATED)
    def submit_join_request(body: JoinRequestSubmission):
        return directory.request_join(
            tenant_id,
            email=body.email,
            nom=body.nom,
            prenom=body.prenom,
            poste_souhaite=body.poste_souhaite or "",
            code_organisation=body.code_organisation
        )

    @app.get("/api/v1/organization/join-requests/pending")
    def list_pending_join_requests(current=Depends(actor_dep)):
        if current.get("role") != "admin":
            raise DomainError("forbidden", "Seul un administrateur peut examiner les demandes d'enrôlement.")
        return directory.list_join_requests(tenant_id, status_filter="pending")

    @app.post("/api/v1/organization/join-requests/{request_id}/decision")
    def decide_join_request(request_id: str, body: JoinDecisionInput, current=Depends(actor_dep)):
        if current.get("role") != "admin":
            raise DomainError("forbidden", "Seul un administrateur peut statuer sur une demande d'enrôlement.")
        return directory.decide_join_request(tenant_id, request_id, body, decided_by=current.get("actor_id") or "DGS")
