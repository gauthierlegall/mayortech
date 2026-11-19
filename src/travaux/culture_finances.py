"""Culture and Finances cross-commission domain, hall reservations, and budget arbitration.

Implements:
1. Hall & resource reservations with semi-open interval [start, end) conflict checking.
2. Associative events & subsidy requests domain extensions.
3. Budget sheets with multi-variant financial projections in integer centimes.
4. Formal Culture -> Finances transmission circuit with motivated opinions and decision tracking.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, require_text, utc_now
from .project_access import access_scope

PARIS_TZ = ZoneInfo("Europe/Paris")

CULTURE_FINANCES_SCHEMA = """
CREATE TABLE IF NOT EXISTS resource_reservations (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('requested', 'checking', 'confirmed', 'cancelled')),
    operation_id TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_reservations_resource ON resource_reservations(tenant_id, resource_id, start_time, end_time, status);
CREATE INDEX IF NOT EXISTS idx_reservations_project ON resource_reservations(tenant_id, project_id);

CREATE TABLE IF NOT EXISTS event_details (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    association_name TEXT NOT NULL DEFAULT '',
    association_ref TEXT NOT NULL DEFAULT '',
    expected_attendance INTEGER NOT NULL DEFAULT 0,
    location_name TEXT NOT NULL DEFAULT '',
    checklist_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, project_id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS budget_sheets (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    exercise INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('draft', 'transmitted', 'frozen', 'archived')),
    variants_json TEXT NOT NULL DEFAULT '[]',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_budget_sheets_project ON budget_sheets(tenant_id, project_id);

CREATE TABLE IF NOT EXISTS finance_transmissions (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    source_commission_id TEXT NOT NULL DEFAULT 'commission-4',
    destination_commission_id TEXT NOT NULL DEFAULT 'commission-1',
    status TEXT NOT NULL CHECK(status IN ('transmis', 'en_instruction', 'complements_requis', 'avis_rendu')),
    motive TEXT NOT NULL,
    budget_sheet_id TEXT NOT NULL,
    budget_snapshot_json TEXT NOT NULL,
    attached_document_ids_json TEXT NOT NULL DEFAULT '[]',
    requested_complements TEXT NOT NULL DEFAULT '',
    decision_opinion TEXT NOT NULL DEFAULT '',
    decision_motivation TEXT NOT NULL DEFAULT '',
    decision_ref TEXT NOT NULL DEFAULT '',
    decided_by TEXT NOT NULL DEFAULT '',
    decided_at TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    UNIQUE(tenant_id, project_id, version),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_transmissions_dest ON finance_transmissions(tenant_id, destination_commission_id, status);
CREATE INDEX IF NOT EXISTS idx_transmissions_project ON finance_transmissions(tenant_id, project_id);

CREATE TABLE IF NOT EXISTS finance_decision_actions (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    transmission_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    opinion TEXT NOT NULL,
    decision_ref TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_finance_actions_proj ON finance_decision_actions(tenant_id, project_id);
"""

# Municipal rooms / resources in Plougastel-Daoulas
MUNICIPAL_ROOMS = [
    {"id": "salle-avel-vor", "name": "Espace Avel Vor (Grande Salle)", "capacity": 800},
    {"id": "salle-roz-avel", "name": "Espace Roz Avel", "capacity": 200},
    {"id": "salle-bellevue", "name": "Salle de Bellevue", "capacity": 120},
    {"id": "salle-avel-dro", "name": "Salle de l'Avel Dro", "capacity": 80},
    {"id": "complexe-kerzivez", "name": "Complexe Sportif de Kerzivez", "capacity": 300},
]


def parse_iso_datetime(value: str) -> datetime:
    """Parse and validate ISO-8601 string, converting to aware UTC datetime."""
    require_text(value, "datetime", maximum=50)
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
    except Exception as exc:
        raise DomainError("invalid_input", f"Format de date/heure invalide : {value}") from exc
    if dt.tzinfo is None:
        # Default naive datetime to Europe/Paris timezone, then convert to UTC
        dt = dt.replace(tzinfo=PARIS_TZ)
    return dt.astimezone(timezone.utc)


def intervals_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    """Semi-open interval [start1, end1) and [start2, end2) overlap check."""
    return max(start1, start2) < min(end1, end2)


def sanitize_csv_cell(value: Any) -> str:
    """Prevent CSV formula injection by quoting and prefixing risky characters."""
    text = str(value if value is not None else "")
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


class CultureFinancesRepository:
    def __init__(self, repo):
        self.repo = repo
        self._migrate_schema()

    def _migrate_schema(self):
        with self.repo._lock:
            self.repo._db.executescript(CULTURE_FINANCES_SCHEMA)

    # -------------------------------------------------------------------------
    # Hall & Resource Reservations
    # -------------------------------------------------------------------------
    def list_rooms(self) -> List[Dict[str, Any]]:
        return list(MUNICIPAL_ROOMS)

    def list_reservations(
        self,
        tenant_id: str,
        *,
        project_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        require_text(tenant_id, "tenant_id", maximum=100)
        query = "SELECT * FROM resource_reservations WHERE tenant_id=?"
        params: List[Any] = [tenant_id]
        if project_id:
            query += " AND project_id=?"
            params.append(project_id)
        if resource_id:
            query += " AND resource_id=?"
            params.append(resource_id)
        if from_time:
            query += " AND end_time > ?"
            params.append(from_time)
        if to_time:
            query += " AND start_time < ?"
            params.append(to_time)
        query += " ORDER BY start_time ASC"

        with self.repo._lock:
            rows = self.repo._db.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def create_reservation(
        self,
        tenant_id: str,
        project_id: str,
        *,
        resource_id: str,
        resource_name: str,
        start_time: str,
        end_time: str,
        created_by: str,
        status: str = "confirmed",
        operation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(project_id, "project_id", maximum=100)
        require_text(resource_id, "resource_id", maximum=100)
        require_text(resource_name, "resource_name", maximum=200)
        require_text(created_by, "created_by", maximum=100)
        if status not in ("requested", "checking", "confirmed", "cancelled"):
            raise DomainError("invalid_input", f"Statut de réservation invalide : {status}")

        dt_start = parse_iso_datetime(start_time)
        dt_end = parse_iso_datetime(end_time)
        if dt_end <= dt_start:
            raise DomainError("invalid_input", "L'heure de fin doit être postérieure à l'heure de début.")

        start_iso = dt_start.isoformat()
        end_iso = dt_end.isoformat()

        with self.repo._transaction() as db:
            # Idempotency check with operation_id
            if operation_id:
                existing = db.execute(
                    "SELECT * FROM resource_reservations WHERE tenant_id=? AND operation_id=?",
                    (tenant_id, operation_id),
                ).fetchone()
                if existing:
                    return dict(existing)

            # Check overlap against confirmed bookings on the same resource
            if status == "confirmed":
                conflicts = db.execute(
                    """SELECT id, start_time, end_time, project_id FROM resource_reservations
                    WHERE tenant_id=? AND resource_id=? AND status='confirmed'""",
                    (tenant_id, resource_id),
                ).fetchall()
                for c in conflicts:
                    c_start = parse_iso_datetime(c["start_time"])
                    c_end = parse_iso_datetime(c["end_time"])
                    if intervals_overlap(dt_start, dt_end, c_start, c_end):
                        # Format readable hours for Paris timezone in error message
                        c_start_p = c_start.astimezone(PARIS_TZ).strftime("%d/%m/%Y %H:%M")
                        c_end_p = c_end.astimezone(PARIS_TZ).strftime("%H:%M")
                        raise DomainError(
                            "conflict",
                            f"Conflit de réservation : La salle '{resource_name}' est déjà occupée sur ce créneau ({c_start_p} - {c_end_p}).",
                        )

            res_id = str(uuid4())
            now = utc_now()
            db.execute(
                """INSERT INTO resource_reservations(
                    tenant_id, id, project_id, resource_id, resource_name,
                    start_time, end_time, status, operation_id, created_by,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    res_id,
                    project_id,
                    resource_id,
                    resource_name,
                    start_iso,
                    end_iso,
                    status,
                    operation_id,
                    created_by,
                    now,
                    now,
                ),
            )
            created = db.execute(
                "SELECT * FROM resource_reservations WHERE tenant_id=? AND id=?",
                (tenant_id, res_id),
            ).fetchone()
            return dict(created)

    def cancel_reservation(self, tenant_id: str, reservation_id: str, *, updated_by: str) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(reservation_id, "reservation_id", maximum=100)
        with self.repo._transaction() as db:
            existing = db.execute(
                "SELECT * FROM resource_reservations WHERE tenant_id=? AND id=?",
                (tenant_id, reservation_id),
            ).fetchone()
            if not existing:
                raise DomainError("not_found", "Réservation introuvable.")
            now = utc_now()
            db.execute(
                "UPDATE resource_reservations SET status='cancelled', updated_at=? WHERE tenant_id=? AND id=?",
                (now, tenant_id, reservation_id),
            )
            updated = db.execute(
                "SELECT * FROM resource_reservations WHERE tenant_id=? AND id=?",
                (tenant_id, reservation_id),
            ).fetchone()
            return dict(updated)

    # -------------------------------------------------------------------------
    # Event Details & Checklists
    # -------------------------------------------------------------------------
    def get_event_details(self, tenant_id: str, project_id: str) -> Dict[str, Any]:
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM event_details WHERE tenant_id=? AND project_id=?",
                (tenant_id, project_id),
            ).fetchone()
            if not row:
                return {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "association_name": "",
                    "association_ref": "",
                    "expected_attendance": 0,
                    "location_name": "",
                    "checklist": [],
                    "updated_at": utc_now(),
                }
            res = dict(row)
            import json
            try:
                res["checklist"] = json.loads(res.get("checklist_json", "[]"))
            except Exception:
                res["checklist"] = []
            return res

    def update_event_details(
        self,
        tenant_id: str,
        project_id: str,
        *,
        association_name: str = "",
        association_ref: str = "",
        expected_attendance: int = 0,
        location_name: str = "",
        checklist: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        import json
        now = utc_now()
        checklist_str = json.dumps(checklist or [], ensure_ascii=False)
        with self.repo._transaction() as db:
            db.execute(
                """INSERT INTO event_details(
                    tenant_id, project_id, association_name, association_ref,
                    expected_attendance, location_name, checklist_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, project_id) DO UPDATE SET
                    association_name=excluded.association_name,
                    association_ref=excluded.association_ref,
                    expected_attendance=excluded.expected_attendance,
                    location_name=excluded.location_name,
                    checklist_json=excluded.checklist_json,
                    updated_at=excluded.updated_at""",
                (
                    tenant_id,
                    project_id,
                    association_name,
                    association_ref,
                    int(expected_attendance or 0),
                    location_name,
                    checklist_str,
                    now,
                ),
            )
            return self.get_event_details(tenant_id, project_id)

    # -------------------------------------------------------------------------
    # Budget Sheets & Cost Variants
    # -------------------------------------------------------------------------
    def get_budget_sheet(self, tenant_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM budget_sheets WHERE tenant_id=? AND project_id=? ORDER BY version DESC LIMIT 1",
                (tenant_id, project_id),
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            import json
            try:
                res["variants"] = json.loads(res.get("variants_json", "[]"))
            except Exception:
                res["variants"] = []
            return res

    def save_budget_sheet(
        self,
        tenant_id: str,
        project_id: str,
        *,
        title: str,
        exercise: int,
        variants: List[Dict[str, Any]],
        created_by: str,
        version: Optional[int] = None,
        status: str = "draft",
    ) -> Dict[str, Any]:
        import json
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(project_id, "project_id", maximum=100)
        require_text(title, "title", maximum=200)

        # Validate and calculate integer cents for each variant
        clean_variants = []
        for idx, var in enumerate(variants):
            label = require_text(var.get("label", f"Variante {chr(65+idx)}"), "label", maximum=100)
            tax_basis = var.get("tax_basis", "ttc").lower()
            if tax_basis not in ("ht", "ttc"):
                tax_basis = "ttc"
            amount_cents = int(var.get("amount_cents", 0))
            subsidies_cents = int(var.get("subsidies_cents", 0))
            if amount_cents < 0 or subsidies_cents < 0:
                raise DomainError("invalid_input", "Les montants doivent être positifs.")
            remaining_cents = max(0, amount_cents - subsidies_cents)
            clean_variants.append({
                "id": var.get("id", f"var-{idx+1}"),
                "label": label,
                "tax_basis": tax_basis,
                "amount_cents": amount_cents,
                "subsidies_cents": subsidies_cents,
                "remaining_cents": remaining_cents,
                "hypothesis": str(var.get("hypothesis", "")).strip(),
                "currency": "EUR",
            })

        variants_json = json.dumps(clean_variants, ensure_ascii=False)
        now = utc_now()

        with self.repo._transaction() as db:
            existing = db.execute(
                "SELECT * FROM budget_sheets WHERE tenant_id=? AND project_id=? ORDER BY version DESC LIMIT 1",
                (tenant_id, project_id),
            ).fetchone()
            if existing and version is None:
                new_version = existing["version"] + 1
            else:
                new_version = version or 1

            sheet_id = str(uuid4())
            db.execute(
                """INSERT INTO budget_sheets(
                    tenant_id, id, project_id, version, title, exercise,
                    status, variants_json, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    sheet_id,
                    project_id,
                    new_version,
                    title,
                    int(exercise),
                    status,
                    variants_json,
                    created_by,
                    now,
                    now,
                ),
            )
            created = db.execute(
                "SELECT * FROM budget_sheets WHERE tenant_id=? AND id=?",
                (tenant_id, sheet_id),
            ).fetchone()
            res = dict(created)
            res["variants"] = clean_variants
            return res

    def export_budget_csv(self, tenant_id: str, project_id: str) -> str:
        sheet = self.get_budget_sheet(tenant_id, project_id)
        if not sheet:
            raise DomainError("not_found", "Fiche budgétaire introuvable.")

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["Fiche budgétaire", sanitize_csv_cell(sheet["title"])])
        writer.writerow(["Exercice", sanitize_csv_cell(sheet["exercise"])])
        writer.writerow(["Version", sanitize_csv_cell(sheet["version"])])
        writer.writerow([])
        writer.writerow([
            "Identifiant",
            "Libellé",
            "Base fiscale",
            "Montant total (€)",
            "Subventions prévues (€)",
            "Reste à charge communal (€)",
            "Hypothèses",
        ])

        for v in sheet.get("variants", []):
            writer.writerow([
                sanitize_csv_cell(v["id"]),
                sanitize_csv_cell(v["label"]),
                sanitize_csv_cell(v["tax_basis"].upper()),
                f"{v['amount_cents'] / 100:.2f}",
                f"{v['subsidies_cents'] / 100:.2f}",
                f"{v['remaining_cents'] / 100:.2f}",
                sanitize_csv_cell(v["hypothesis"]),
            ])

        return output.getvalue()

    # -------------------------------------------------------------------------
    # Formal Transmission Circuit (Culture -> Finances)
    # -------------------------------------------------------------------------
    def list_transmissions(
        self,
        tenant_id: str,
        *,
        destination_commission_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        import json
        query = "SELECT t.*, p.name as project_name, p.reference as project_reference FROM finance_transmissions t JOIN projects p ON t.tenant_id = p.tenant_id AND t.project_id = p.id WHERE t.tenant_id=?"
        params: List[Any] = [tenant_id]
        if destination_commission_id:
            query += " AND t.destination_commission_id=?"
            params.append(destination_commission_id)
        if status:
            query += " AND t.status=?"
            params.append(status)
        query += " ORDER BY t.created_at DESC"

        with self.repo._lock:
            rows = self.repo._db.execute(query, params).fetchall()
            items = []
            for r in rows:
                d = dict(r)
                try:
                    d["budget_snapshot"] = json.loads(d.get("budget_snapshot_json", "{}"))
                    d["attached_document_ids"] = json.loads(d.get("attached_document_ids_json", "[]"))
                except Exception:
                    d["budget_snapshot"] = {}
                    d["attached_document_ids"] = []
                items.append(d)
            return items

    def get_transmission(self, tenant_id: str, transmission_id: str) -> Dict[str, Any]:
        import json
        with self.repo._lock:
            row = self.repo._db.execute(
                """SELECT t.*, p.name as project_name, p.reference as project_reference
                FROM finance_transmissions t
                JOIN projects p ON t.tenant_id = p.tenant_id AND t.project_id = p.id
                WHERE t.tenant_id=? AND t.id=?""",
                (tenant_id, transmission_id),
            ).fetchone()
            if not row:
                raise DomainError("not_found", "Transmission financière introuvable.")
            d = dict(row)
            try:
                d["budget_snapshot"] = json.loads(d.get("budget_snapshot_json", "{}"))
                d["attached_document_ids"] = json.loads(d.get("attached_document_ids_json", "[]"))
            except Exception:
                d["budget_snapshot"] = {}
                d["attached_document_ids"] = []
            return d

    def get_project_transmission(self, tenant_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        import json
        with self.repo._lock:
            row = self.repo._db.execute(
                """SELECT t.*, p.name as project_name, p.reference as project_reference
                FROM finance_transmissions t
                JOIN projects p ON t.tenant_id = p.tenant_id AND t.project_id = p.id
                WHERE t.tenant_id=? AND t.project_id=?
                ORDER BY t.version DESC LIMIT 1""",
                (tenant_id, project_id),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["budget_snapshot"] = json.loads(d.get("budget_snapshot_json", "{}"))
                d["attached_document_ids"] = json.loads(d.get("attached_document_ids_json", "[]"))
            except Exception:
                d["budget_snapshot"] = {}
                d["attached_document_ids"] = []
            return d

    def create_or_update_transmission(
        self,
        tenant_id: str,
        project_id: str,
        *,
        motive: str,
        created_by: str,
        attached_document_ids: Optional[List[str]] = None,
        source_commission_id: str = "commission-4",
        destination_commission_id: str = "commission-1",
    ) -> Dict[str, Any]:
        import json
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(project_id, "project_id", maximum=100)
        require_text(motive, "motive", maximum=5000)

        # Get latest budget sheet to freeze
        sheet = self.get_budget_sheet(tenant_id, project_id)
        if not sheet or not sheet.get("variants"):
            raise DomainError("precondition_failed", "Une fiche budgétaire avec au moins une variante est requise avant transmission.")

        snapshot_str = json.dumps(sheet, ensure_ascii=False)
        docs_str = json.dumps(attached_document_ids or [], ensure_ascii=False)
        now = utc_now()

        with self.repo._transaction() as db:
            # Check existing transmission for project
            existing = db.execute(
                "SELECT * FROM finance_transmissions WHERE tenant_id=? AND project_id=? ORDER BY version DESC LIMIT 1",
                (tenant_id, project_id),
            ).fetchone()

            if existing and existing["status"] == "transmis":
                # Idempotent return of the current pending transmission
                return self.get_transmission(tenant_id, existing["id"])

            new_version = (existing["version"] + 1) if existing else 1
            trans_id = str(uuid4())

            db.execute(
                """INSERT INTO finance_transmissions(
                    tenant_id, id, project_id, version, source_commission_id,
                    destination_commission_id, status, motive, budget_sheet_id,
                    budget_snapshot_json, attached_document_ids_json,
                    requested_complements, decision_opinion, decision_motivation,
                    decision_ref, decided_by, decided_at, created_by,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'transmis', ?, ?, ?, ?, '', '', '', '', '', NULL, ?, ?, ?)""",
                (
                    tenant_id,
                    trans_id,
                    project_id,
                    new_version,
                    source_commission_id,
                    destination_commission_id,
                    motive,
                    sheet["id"],
                    snapshot_str,
                    docs_str,
                    created_by,
                    now,
                    now,
                ),
            )

            # Freeze budget sheet status
            db.execute(
                "UPDATE budget_sheets SET status='frozen', updated_at=? WHERE tenant_id=? AND id=?",
                (now, tenant_id, sheet["id"]),
            )

            return self.get_transmission(tenant_id, trans_id)

    def record_decision(
        self,
        tenant_id: str,
        transmission_id: str,
        *,
        opinion: str,
        motivation: str,
        decided_by: str,
        decision_ref: str = "",
        requested_complements: str = "",
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        require_text(tenant_id, "tenant_id", maximum=100)
        require_text(transmission_id, "transmission_id", maximum=100)
        if opinion not in ("favorable", "defavorable", "favorable_avec_reserves", "demande_complements"):
            raise DomainError("invalid_input", f"Avis invalide : {opinion}")
        require_text(motivation, "motivation", maximum=5000)

        now = utc_now()
        with self.repo._transaction() as db:
            existing = db.execute(
                "SELECT * FROM finance_transmissions WHERE tenant_id=? AND id=?",
                (tenant_id, transmission_id),
            ).fetchone()
            if not existing:
                raise DomainError("not_found", "Transmission introuvable.")

            if expected_version is not None and existing["version"] != expected_version:
                raise DomainError("conflict", "La version de transmission a été modifiée par un autre utilisateur.")

            new_status = "complements_requis" if opinion == "demande_complements" else "avis_rendu"

            db.execute(
                """UPDATE finance_transmissions SET
                    status=?,
                    decision_opinion=?,
                    decision_motivation=?,
                    decision_ref=?,
                    requested_complements=?,
                    decided_by=?,
                    decided_at=?,
                    updated_at=?
                WHERE tenant_id=? AND id=?""",
                (
                    new_status,
                    opinion,
                    motivation,
                    decision_ref.strip(),
                    requested_complements.strip(),
                    decided_by,
                    now,
                    now,
                    tenant_id,
                    transmission_id,
                ),
            )

            # If decision is rendered or complement requested, create a follow-up action and note
            project_id = existing["project_id"]
            action_title = (
                f"Avis financier ({opinion}) : {decision_ref}"
                if decision_ref
                else f"Avis financier : {opinion}"
            )
            if opinion == "demande_complements":
                action_title = "Compléments financiers requis"

            action_desc = f"Avis émis par {decided_by} le {now[:10]} : {motivation}"
            action_id = str(uuid4())
            db.execute(
                """INSERT INTO finance_decision_actions(
                    tenant_id, id, project_id, transmission_id, title, description,
                    opinion, decision_ref, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tenant_id,
                    action_id,
                    project_id,
                    transmission_id,
                    action_title,
                    action_desc,
                    opinion,
                    decision_ref.strip(),
                    decided_by,
                    now,
                ),
            )

            # Insert an official human note on the project
            note_content = (
                f"Avis financier [{opinion.upper()}] émis par {decided_by} le {now[:10]}.\n"
                + (f"Référence officielle : {decision_ref}\n" if decision_ref else "")
                + f"Motivation : {motivation}"
            )
            self.repo._insert_note(db, tenant_id, project_id, note_content, decided_by, "finance_arbitrage")

            return self.get_transmission(tenant_id, transmission_id)



# Pydantic Request / Response models
class ReservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: str = Field(..., max_length=100)
    resource_name: str = Field(..., max_length=200)
    start_time: str = Field(..., max_length=50)
    end_time: str = Field(..., max_length=50)
    status: str = Field("confirmed", pattern="^(requested|checking|confirmed|cancelled)$")
    operation_id: Optional[str] = Field(None, max_length=100)


class EventDetailsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    association_name: str = Field("", max_length=200)
    association_ref: str = Field("", max_length=100)
    expected_attendance: int = Field(0, ge=0)
    location_name: str = Field("", max_length=200)
    checklist: List[Dict[str, Any]] = Field(default_factory=list)


class BudgetVariantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., max_length=50)
    label: str = Field(..., max_length=100)
    tax_basis: str = Field("ttc", pattern="^(ht|ttc|HT|TTC)$")
    amount_cents: int = Field(..., ge=0)
    subsidies_cents: int = Field(0, ge=0)
    hypothesis: str = Field("", max_length=1000)


class BudgetSheetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(..., max_length=200)
    exercise: int = Field(..., ge=2020, le=2050)
    variants: List[BudgetVariantInput] = Field(..., min_length=1)
    status: str = Field("draft", pattern="^(draft|transmitted|frozen|archived)$")


class TransmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motive: str = Field(..., max_length=5000)
    attached_document_ids: List[str] = Field(default_factory=list)
    source_commission_id: str = Field("commission-4", max_length=100)
    destination_commission_id: str = Field("commission-1", max_length=100)


class DecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opinion: str = Field(..., pattern="^(favorable|defavorable|favorable_avec_reserves|demande_complements)$")
    motivation: str = Field(..., max_length=5000)
    decision_ref: str = Field("", max_length=100)
    requested_complements: str = Field("", max_length=2000)
    expected_version: Optional[int] = None


def setup_culture_finances_routes(
    app,
    repo,
    settings,
    cf_repo: CultureFinancesRepository,
    commissions_repo,
    actor_dep,
    require_project_write,
    require_project_read,
):
    from fastapi.responses import PlainTextResponse

    @app.get("/api/v1/culture/rooms")
    def list_rooms_route(current=Depends(actor_dep)):
        return {"items": cf_repo.list_rooms()}

    @app.get("/api/v1/projects/{project_id}/reservations")
    def list_project_reservations_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        items = cf_repo.list_reservations(settings.tenant_id, project_id=project_id)
        return {"items": items, "total": len(items)}

    @app.post("/api/v1/projects/{project_id}/reservations")
    def create_reservation_route(project_id: str, body: ReservationInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return cf_repo.create_reservation(
            settings.tenant_id,
            project_id,
            resource_id=body.resource_id,
            resource_name=body.resource_name,
            start_time=body.start_time,
            end_time=body.end_time,
            created_by=current.get("actor_id", "demo"),
            status=body.status,
            operation_id=body.operation_id,
        )

    @app.delete("/api/v1/projects/{project_id}/reservations/{reservation_id}")
    def cancel_reservation_route(project_id: str, reservation_id: str, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return cf_repo.cancel_reservation(
            settings.tenant_id,
            reservation_id,
            updated_by=current.get("actor_id", "demo"),
        )

    @app.get("/api/v1/projects/{project_id}/event-details")
    def get_event_details_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        return cf_repo.get_event_details(settings.tenant_id, project_id)

    @app.put("/api/v1/projects/{project_id}/event-details")
    def update_event_details_route(project_id: str, body: EventDetailsInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return cf_repo.update_event_details(
            settings.tenant_id,
            project_id,
            association_name=body.association_name,
            association_ref=body.association_ref,
            expected_attendance=body.expected_attendance,
            location_name=body.location_name,
            checklist=body.checklist,
        )

    @app.get("/api/v1/projects/{project_id}/budget")
    def get_budget_sheet_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        sheet = cf_repo.get_budget_sheet(settings.tenant_id, project_id)
        if not sheet:
            return {"sheet": None}
        return {"sheet": sheet}

    @app.post("/api/v1/projects/{project_id}/budget")
    def save_budget_sheet_route(project_id: str, body: BudgetSheetInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        variants = [v.model_dump() for v in body.variants]
        sheet = cf_repo.save_budget_sheet(
            settings.tenant_id,
            project_id,
            title=body.title,
            exercise=body.exercise,
            variants=variants,
            created_by=current.get("actor_id", "demo"),
            status=body.status,
        )
        return {"sheet": sheet}

    @app.get("/api/v1/projects/{project_id}/budget/export.csv")
    def export_budget_csv_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        csv_data = cf_repo.export_budget_csv(settings.tenant_id, project_id)
        return PlainTextResponse(
            csv_data,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="budget-{project_id}.csv"'},
        )

    @app.get("/api/v1/projects/{project_id}/transmissions/finance")
    def get_project_transmission_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        trans = cf_repo.get_project_transmission(settings.tenant_id, project_id)
        return {"transmission": trans}

    @app.post("/api/v1/projects/{project_id}/transmissions/finance")
    def create_project_transmission_route(project_id: str, body: TransmissionInput, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        trans = cf_repo.create_or_update_transmission(
            settings.tenant_id,
            project_id,
            motive=body.motive,
            created_by=current.get("actor_id", "demo"),
            attached_document_ids=body.attached_document_ids,
            source_commission_id=body.source_commission_id,
            destination_commission_id=body.destination_commission_id,
        )
        return {"transmission": trans}

    @app.get("/api/v1/finance/transmissions")
    def list_finance_transmissions_route(status: Optional[str] = None, current=Depends(actor_dep)):
        scope = access_scope(repo, current)
        caps = scope.commission_capabilities("commission-1")
        if not caps["can_read"]:
            raise DomainError("forbidden", "Accès réservé aux membres de la Commission Finances.")
        items = cf_repo.list_transmissions(settings.tenant_id, destination_commission_id="commission-1", status=status)
        return {"items": items, "total": len(items)}

    @app.get("/api/v1/finance/transmissions/{transmission_id}")
    def get_finance_transmission_route(transmission_id: str, current=Depends(actor_dep)):
        trans = cf_repo.get_transmission(settings.tenant_id, transmission_id)
        scope = access_scope(repo, current)
        caps = scope.commission_capabilities("commission-1")
        if not caps["can_read"]:
            require_project_read(trans["project_id"], current)
        return {"transmission": trans}

    @app.post("/api/v1/finance/transmissions/{transmission_id}/decision")
    def decide_finance_transmission_route(transmission_id: str, body: DecisionInput, current=Depends(actor_dep)):
        scope = access_scope(repo, current)
        caps = scope.commission_capabilities("commission-1")
        if not caps["can_edit"]:
            raise DomainError("forbidden", "Seuls les éditeurs ou administrateurs de la Commission Finances peuvent émettre un avis ou demander des compléments.")
        trans = cf_repo.record_decision(
            settings.tenant_id,
            transmission_id,
            opinion=body.opinion,
            motivation=body.motivation,
            decided_by=current.get("actor_id", "finances"),
            decision_ref=body.decision_ref,
            requested_complements=body.requested_complements,
            expected_version=body.expected_version,
        )
        return {"transmission": trans}

