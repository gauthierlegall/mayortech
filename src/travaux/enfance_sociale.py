"""Action sociale, enfance et jeunesse domain module (Lot 4 MayorTech).

Handles:
- Social campaigns management (Rentrée scolaire, Colis des aînés, Séjours d'été)
- Intelligent year-over-year campaign renewal engine with action carrying over
- Municipal canteen and childcare social rate brackets (Quotient Familial)
- Confidential social assistance registry for CCAS and Commission 2
- Recurring alerts and deadline reminders
"""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError, utc_now
from .repository import Repository

ENFANCE_SOCIALE_SCHEMA = """
CREATE TABLE IF NOT EXISTS social_campaigns (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    campaign_type TEXT NOT NULL CHECK(campaign_type IN ('rentree_scolaire', 'colis_aines', 'sejours_ete', 'aides_facultatives')),
    title TEXT NOT NULL,
    school_year TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'active', 'closed', 'archived')),
    config_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_social_campaigns_type ON social_campaigns(tenant_id, campaign_type, school_year);

CREATE TABLE IF NOT EXISTS campaign_dossiers (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    project_id TEXT,
    family_ref TEXT NOT NULL,
    beneficiary_name TEXT NOT NULL,
    child_name TEXT NOT NULL DEFAULT '',
    school_name TEXT NOT NULL DEFAULT '',
    quotient_familial INTEGER NOT NULL DEFAULT 0,
    rate_bracket TEXT NOT NULL DEFAULT 'T5',
    status TEXT NOT NULL DEFAULT 'depose' CHECK(status IN ('depose', 'en_instruction', 'valide', 'rejete', 'reconduit')),
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id),
    FOREIGN KEY(tenant_id, campaign_id) REFERENCES social_campaigns(tenant_id, id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_campaign_dossiers_camp ON campaign_dossiers(tenant_id, campaign_id);

CREATE TABLE IF NOT EXISTS campaign_renewals (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    source_campaign_id TEXT NOT NULL,
    target_campaign_id TEXT NOT NULL,
    source_year TEXT NOT NULL,
    target_year TEXT NOT NULL,
    dossiers_renewed_count INTEGER NOT NULL DEFAULT 0,
    actions_carried_over_count INTEGER NOT NULL DEFAULT 0,
    performed_by TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS social_aid_registry (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    project_id TEXT,
    aid_type TEXT NOT NULL CHECK(aid_type IN ('aide_energie', 'secours_urgence', 'aide_alimentaire', 'aide_periscolaire')),
    confidential_ref TEXT NOT NULL,
    amount_cents INTEGER NOT NULL DEFAULT 0,
    commission_decision TEXT NOT NULL DEFAULT 'ajourne' CHECK(commission_decision IN ('accorde', 'refuse', 'ajourne')),
    deliberation_ref TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_social_aid_proj ON social_aid_registry(tenant_id, project_id);

CREATE TABLE IF NOT EXISTS recurring_reminders (
    tenant_id TEXT NOT NULL,
    id TEXT NOT NULL,
    campaign_id TEXT,
    title TEXT NOT NULL,
    due_date TEXT NOT NULL,
    reminder_type TEXT NOT NULL CHECK(reminder_type IN ('inscription_deadline', 'commission_review', 'payment_reminder', 'justificatif_request')),
    is_dismissed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS idx_recurring_reminders_camp ON recurring_reminders(tenant_id, campaign_id);
"""

# Plougastel-Daoulas Municipal Canteen Rate Brackets (Tarification sociale)
MUNICIPAL_CANTEEN_BRACKETS = [
    {
        "bracket": "T1",
        "max_qf": 450,
        "meal_rate_cents": 100,  # 1.00 € (Tarif social de solidarité)
        "label": "Tranche 1 (QF ≤ 450 €) - Tarif solidaire",
        "commune_subsidy_cents": 395,
    },
    {
        "bracket": "T2",
        "max_qf": 750,
        "meal_rate_cents": 215,  # 2.15 €
        "label": "Tranche 2 (451 € à 750 €)",
        "commune_subsidy_cents": 280,
    },
    {
        "bracket": "T3",
        "max_qf": 1100,
        "meal_rate_cents": 320,  # 3.20 €
        "label": "Tranche 3 (751 € à 1 100 €)",
        "commune_subsidy_cents": 175,
    },
    {
        "bracket": "T4",
        "max_qf": 1600,
        "meal_rate_cents": 410,  # 4.10 €
        "label": "Tranche 4 (1 101 € à 1 600 €)",
        "commune_subsidy_cents": 85,
    },
    {
        "bracket": "T5",
        "max_qf": 999999,
        "meal_rate_cents": 495,  # 4.95 € (Tarif plein)
        "label": "Tranche 5 (> 1 600 €) - Tarif plein",
        "commune_subsidy_cents": 0,
    },
]


def calculate_canteen_bracket(quotient_familial: int) -> Dict[str, Any]:
    """Calculate the municipal canteen rate bracket for a given Quotient Familial."""
    if quotient_familial < 0:
        quotient_familial = 0
    for b in MUNICIPAL_CANTEEN_BRACKETS:
        if quotient_familial <= b["max_qf"]:
            return {
                "bracket": b["bracket"],
                "meal_rate_cents": b["meal_rate_cents"],
                "label": b["label"],
                "commune_subsidy_cents": b["commune_subsidy_cents"],
                "quotient_familial": quotient_familial,
            }
    last = MUNICIPAL_CANTEEN_BRACKETS[-1]
    return {
        "bracket": last["bracket"],
        "meal_rate_cents": last["meal_rate_cents"],
        "label": last["label"],
        "commune_subsidy_cents": last["commune_subsidy_cents"],
        "quotient_familial": quotient_familial,
    }


def shift_year_string(school_year: str, delta_years: int = 1) -> str:
    """Shift a school year string like '2026-2027' by delta_years."""
    match = re.match(r"^(\d{4})-(\d{4})$", school_year.strip())
    if match:
        start_y = int(match.group(1)) + delta_years
        end_y = int(match.group(2)) + delta_years
        return f"{start_y}-{end_y}"
    # Fallback to single year
    match_single = re.match(r"^(\d{4})$", school_year.strip())
    if match_single:
        return str(int(match_single.group(1)) + delta_years)
    return f"{school_year} (+{delta_years})"


def shift_iso_date(date_str: str, delta_years: int = 1) -> str:
    """Shift an ISO YYYY-MM-DD date by delta_years."""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        new_dt = dt.replace(year=dt.year + delta_years)
        return new_dt.strftime("%Y-%m-%d")
    except Exception:
        return date_str


# Pydantic Schemas
class SocialCampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_type: str = Field(..., pattern="^(rentree_scolaire|colis_aines|sejours_ete|aides_facultatives)$")
    title: str = Field(..., min_length=2, max_length=200)
    school_year: str = Field(..., min_length=4, max_length=20)
    start_date: str = Field(..., min_length=10, max_length=10)
    end_date: str = Field(..., min_length=10, max_length=10)
    config: Dict[str, Any] = Field(default_factory=dict)


class CampaignDossierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family_ref: str = Field(..., min_length=1, max_length=64)
    beneficiary_name: str = Field(..., min_length=2, max_length=120)
    child_name: str = Field(default="", max_length=120)
    school_name: str = Field(default="", max_length=120)
    quotient_familial: int = Field(default=0, ge=0)
    project_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CampaignRenewalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_school_year: str = Field(..., min_length=4, max_length=20)
    carry_over_dossiers: bool = True
    carry_over_reminders: bool = True


class SocialAidRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    aid_type: str = Field(..., pattern="^(aide_energie|secours_urgence|aide_alimentaire|aide_periscolaire)$")
    confidential_ref: str = Field(..., min_length=1, max_length=64)
    amount_cents: int = Field(..., ge=0)
    commission_decision: str = Field(default="ajourne", pattern="^(accorde|refuse|ajourne)$")
    deliberation_ref: str = Field(default="", max_length=64)
    notes: str = Field(default="", max_length=2000)


class RecurringReminderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    campaign_id: Optional[str] = None
    title: str = Field(..., min_length=2, max_length=200)
    due_date: str = Field(..., min_length=10, max_length=10)
    reminder_type: str = Field(..., pattern="^(inscription_deadline|commission_review|payment_reminder|justificatif_request)$")


class EnfanceSocialeRepository:
    def __init__(self, repo: Repository):
        self._repo = repo
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._repo._lock:
            for statement in ENFANCE_SOCIALE_SCHEMA.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    self._repo._db.execute(stmt)

    # 1. Social Campaigns
    def create_campaign(
        self,
        tenant_id: str,
        campaign_type: str,
        title: str,
        school_year: str,
        start_date: str,
        end_date: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        campaign_id = f"CMP-{uuid4().hex[:8].upper()}"
        now = utc_now()
        config_json = json.dumps(config or {}, ensure_ascii=False)
        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO social_campaigns (tenant_id, id, campaign_type, title, school_year, start_date, end_date, status, config_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (tenant_id, campaign_id, campaign_type, title, school_year, start_date, end_date, config_json, now, now),
            )
        return self.get_campaign(tenant_id, campaign_id) or {}

    def get_campaign(self, tenant_id: str, campaign_id: str) -> Optional[Dict[str, Any]]:
        with self._repo._transaction() as db:
            row = db.execute(
                """
                SELECT id, campaign_type, title, school_year, start_date, end_date, status, config_json, created_at, updated_at
                FROM social_campaigns
                WHERE tenant_id = ? AND id = ?
                """,
                (tenant_id, campaign_id),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "campaign_type": row[1],
                "title": row[2],
                "school_year": row[3],
                "start_date": row[4],
                "end_date": row[5],
                "status": row[6],
                "config": json.loads(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
            }

    def list_campaigns(self, tenant_id: str, campaign_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._repo._transaction() as db:
            query = """
                SELECT id, campaign_type, title, school_year, start_date, end_date, status, config_json, created_at, updated_at
                FROM social_campaigns
                WHERE tenant_id = ?
            """
            params: List[Any] = [tenant_id]
            if campaign_type:
                query += " AND campaign_type = ?"
                params.append(campaign_type)
            query += " ORDER BY start_date DESC"
            rows = db.execute(query, tuple(params)).fetchall()
            return [
                {
                    "id": r[0],
                    "campaign_type": r[1],
                    "title": r[2],
                    "school_year": r[3],
                    "start_date": r[4],
                    "end_date": r[5],
                    "status": r[6],
                    "config": json.loads(r[7]),
                    "created_at": r[8],
                    "updated_at": r[9],
                }
                for r in rows
            ]

    # 2. Campaign Dossiers
    def create_campaign_dossier(
        self,
        tenant_id: str,
        campaign_id: str,
        family_ref: str,
        beneficiary_name: str,
        child_name: str = "",
        school_name: str = "",
        quotient_familial: int = 0,
        project_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        dossier_id = f"DOS-{uuid4().hex[:8].upper()}"
        bracket_info = calculate_canteen_bracket(quotient_familial)
        rate_bracket = bracket_info["bracket"]
        now = utc_now()
        details_json = json.dumps(details or {}, ensure_ascii=False)
        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO campaign_dossiers (
                    tenant_id, id, campaign_id, project_id, family_ref, beneficiary_name,
                    child_name, school_name, quotient_familial, rate_bracket, status,
                    details_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en_instruction', ?, ?, ?)
                """,
                (
                    tenant_id,
                    dossier_id,
                    campaign_id,
                    project_id,
                    family_ref,
                    beneficiary_name,
                    child_name,
                    school_name,
                    quotient_familial,
                    rate_bracket,
                    details_json,
                    now,
                    now,
                ),
            )
        return {
            "id": dossier_id,
            "campaign_id": campaign_id,
            "project_id": project_id,
            "family_ref": family_ref,
            "beneficiary_name": beneficiary_name,
            "child_name": child_name,
            "school_name": school_name,
            "quotient_familial": quotient_familial,
            "rate_bracket": rate_bracket,
            "status": "en_instruction",
            "details": details or {},
            "created_at": now,
            "updated_at": now,
        }

    def list_campaign_dossiers(self, tenant_id: str, campaign_id: str) -> List[Dict[str, Any]]:
        with self._repo._transaction() as db:
            rows = db.execute(
                """
                SELECT id, campaign_id, project_id, family_ref, beneficiary_name,
                       child_name, school_name, quotient_familial, rate_bracket, status,
                       details_json, created_at, updated_at
                FROM campaign_dossiers
                WHERE tenant_id = ? AND campaign_id = ?
                ORDER BY created_at DESC
                """,
                (tenant_id, campaign_id),
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "campaign_id": r[1],
                    "project_id": r[2],
                    "family_ref": r[3],
                    "beneficiary_name": r[4],
                    "child_name": r[5],
                    "school_name": r[6],
                    "quotient_familial": r[7],
                    "rate_bracket": r[8],
                    "status": r[9],
                    "details": json.loads(r[10]),
                    "created_at": r[11],
                    "updated_at": r[12],
                }
                for r in rows
            ]

    # 3. Campaign Renewal Engine
    def renew_campaign_for_year(
        self,
        tenant_id: str,
        source_campaign_id: str,
        target_school_year: str,
        performed_by: str = "commission-agent",
        carry_over_dossiers: bool = True,
        carry_over_reminders: bool = True,
    ) -> Dict[str, Any]:
        """Intelligent renewal of an annual campaign for the next school year."""
        src = self.get_campaign(tenant_id, source_campaign_id)
        if not src:
            raise DomainError("social_campaign_not_found", "Campagne source introuvable.")

        # Compute year delta
        delta_years = 1
        src_match = re.search(r"\b(\d{4})\b", src["school_year"])
        tgt_match = re.search(r"\b(\d{4})\b", target_school_year)
        if src_match and tgt_match:
            delta_years = max(1, int(tgt_match.group(1)) - int(src_match.group(1)))

        new_title = f"{src['title']} ({target_school_year})"
        if src["school_year"] in src["title"]:
            new_title = src["title"].replace(src["school_year"], target_school_year)

        new_start_date = shift_iso_date(src["start_date"], delta_years)
        new_end_date = shift_iso_date(src["end_date"], delta_years)

        target_campaign_id = f"CMP-{uuid4().hex[:8].upper()}"
        now = utc_now()
        config_json = json.dumps(src["config"], ensure_ascii=False)

        dossiers_renewed_count = 0
        reminders_carried_count = 0

        with self._repo._transaction() as db:
            # 1. Insert new target campaign
            db.execute(
                """
                INSERT INTO social_campaigns (
                    tenant_id, id, campaign_type, title, school_year, start_date, end_date,
                    status, config_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    tenant_id,
                    target_campaign_id,
                    src["campaign_type"],
                    new_title,
                    target_school_year,
                    new_start_date,
                    new_end_date,
                    config_json,
                    now,
                    now,
                ),
            )

            # 2. Duplicate active dossiers if requested
            if carry_over_dossiers:
                src_dossiers = db.execute(
                    """
                    SELECT family_ref, beneficiary_name, child_name, school_name, quotient_familial, rate_bracket, details_json
                    FROM campaign_dossiers
                    WHERE tenant_id = ? AND campaign_id = ? AND status != 'rejete'
                    """,
                    (tenant_id, source_campaign_id),
                ).fetchall()

                for d in src_dossiers:
                    new_dos_id = f"DOS-{uuid4().hex[:8].upper()}"
                    db.execute(
                        """
                        INSERT INTO campaign_dossiers (
                            tenant_id, id, campaign_id, project_id, family_ref, beneficiary_name,
                            child_name, school_name, quotient_familial, rate_bracket, status,
                            details_json, created_at, updated_at
                        )
                        VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, 'reconduit', ?, ?, ?)
                        """,
                        (
                            tenant_id,
                            new_dos_id,
                            target_campaign_id,
                            d[0],
                            d[1],
                            d[2],
                            d[3],
                            d[4],
                            d[5],
                            d[6],
                            now,
                            now,
                        ),
                    )
                    dossiers_renewed_count += 1

            # 3. Duplicate reminders shifted in time if requested
            if carry_over_reminders:
                src_reminders = db.execute(
                    """
                    SELECT title, due_date, reminder_type
                    FROM recurring_reminders
                    WHERE tenant_id = ? AND campaign_id = ?
                    """,
                    (tenant_id, source_campaign_id),
                ).fetchall()

                for r in src_reminders:
                    new_rem_id = f"REM-{uuid4().hex[:8].upper()}"
                    shifted_due = shift_iso_date(r[1], delta_years)
                    db.execute(
                        """
                        INSERT INTO recurring_reminders (
                            tenant_id, id, campaign_id, title, due_date, reminder_type, is_dismissed, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                        """,
                        (
                            tenant_id,
                            new_rem_id,
                            target_campaign_id,
                            f"{r[0]} ({target_school_year})",
                            shifted_due,
                            r[2],
                            now,
                        ),
                    )
                    reminders_carried_count += 1

            # 4. Record renewal log
            renewal_id = f"RNW-{uuid4().hex[:8].upper()}"
            db.execute(
                """
                INSERT INTO campaign_renewals (
                    tenant_id, id, source_campaign_id, target_campaign_id, source_year, target_year,
                    dossiers_renewed_count, actions_carried_over_count, performed_by, performed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    renewal_id,
                    source_campaign_id,
                    target_campaign_id,
                    src["school_year"],
                    target_school_year,
                    dossiers_renewed_count,
                    reminders_carried_count,
                    performed_by,
                    now,
                ),
            )

        return {
            "renewal_id": renewal_id,
            "source_campaign_id": source_campaign_id,
            "target_campaign": self.get_campaign(tenant_id, target_campaign_id),
            "dossiers_renewed_count": dossiers_renewed_count,
            "reminders_carried_count": reminders_carried_count,
            "performed_at": now,
        }

    # 4. Confidential Social Aid Registry
    def record_social_aid(
        self,
        tenant_id: str,
        project_id: Optional[str],
        aid_type: str,
        confidential_ref: str,
        amount_cents: int,
        commission_decision: str = "ajourne",
        deliberation_ref: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        aid_id = f"AID-{uuid4().hex[:8].upper()}"
        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO social_aid_registry (
                    tenant_id, id, project_id, aid_type, confidential_ref, amount_cents,
                    commission_decision, deliberation_ref, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    aid_id,
                    project_id,
                    aid_type,
                    confidential_ref,
                    amount_cents,
                    commission_decision,
                    deliberation_ref,
                    notes,
                    now,
                    now,
                ),
            )
        return {
            "id": aid_id,
            "project_id": project_id,
            "aid_type": aid_type,
            "confidential_ref": confidential_ref,
            "amount_cents": amount_cents,
            "commission_decision": commission_decision,
            "deliberation_ref": deliberation_ref,
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }

    def list_social_aid_for_project(self, tenant_id: str, project_id: str) -> List[Dict[str, Any]]:
        with self._repo._transaction() as db:
            rows = db.execute(
                """
                SELECT id, project_id, aid_type, confidential_ref, amount_cents,
                       commission_decision, deliberation_ref, notes, created_at, updated_at
                FROM social_aid_registry
                WHERE tenant_id = ? AND project_id = ?
                ORDER BY created_at DESC
                """,
                (tenant_id, project_id),
            ).fetchall()
            return [
                {
                    "id": r[0],
                    "project_id": r[1],
                    "aid_type": r[2],
                    "confidential_ref": r[3],
                    "amount_cents": r[4],
                    "commission_decision": r[5],
                    "deliberation_ref": r[6],
                    "notes": r[7],
                    "created_at": r[8],
                    "updated_at": r[9],
                }
                for r in rows
            ]

    # 5. Recurring Reminders
    def create_reminder(
        self,
        tenant_id: str,
        title: str,
        due_date: str,
        reminder_type: str,
        campaign_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        rem_id = f"REM-{uuid4().hex[:8].upper()}"
        now = utc_now()
        with self._repo._transaction() as db:
            db.execute(
                """
                INSERT INTO recurring_reminders (
                    tenant_id, id, campaign_id, title, due_date, reminder_type, is_dismissed, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (tenant_id, rem_id, campaign_id, title, due_date, reminder_type, now),
            )
        return {
            "id": rem_id,
            "campaign_id": campaign_id,
            "title": title,
            "due_date": due_date,
            "reminder_type": reminder_type,
            "is_dismissed": False,
            "created_at": now,
        }

    def list_reminders(self, tenant_id: str, campaign_id: Optional[str] = None, include_dismissed: bool = False) -> List[Dict[str, Any]]:
        with self._repo._transaction() as db:
            query = "SELECT id, campaign_id, title, due_date, reminder_type, is_dismissed, created_at FROM recurring_reminders WHERE tenant_id = ?"
            params: List[Any] = [tenant_id]
            if campaign_id:
                query += " AND campaign_id = ?"
                params.append(campaign_id)
            if not include_dismissed:
                query += " AND is_dismissed = 0"
            query += " ORDER BY due_date ASC"
            rows = db.execute(query, tuple(params)).fetchall()
            return [
                {
                    "id": r[0],
                    "campaign_id": r[1],
                    "title": r[2],
                    "due_date": r[3],
                    "reminder_type": r[4],
                    "is_dismissed": bool(r[5]),
                    "created_at": r[6],
                }
                for r in rows
            ]

    def dismiss_reminder(self, tenant_id: str, reminder_id: str) -> bool:
        with self._repo._transaction() as db:
            cursor = db.execute(
                "UPDATE recurring_reminders SET is_dismissed = 1 WHERE tenant_id = ? AND id = ?",
                (tenant_id, reminder_id),
            )
            return cursor.rowcount > 0


def setup_enfance_sociale_routes(
    app,
    repo,
    settings,
    es_repo: EnfanceSocialeRepository,
    actor_dep,
    require_project_write,
    require_project_read,
):
    @app.get("/api/v1/social/campaigns")
    def list_social_campaigns_route(campaign_type: Optional[str] = None, current=Depends(actor_dep)):
        return {"items": es_repo.list_campaigns(settings.tenant_id, campaign_type=campaign_type)}

    @app.post("/api/v1/social/campaigns")
    def create_social_campaign_route(body: SocialCampaignCreate, current=Depends(actor_dep)):
        return es_repo.create_campaign(
            settings.tenant_id,
            campaign_type=body.campaign_type,
            title=body.title,
            school_year=body.school_year,
            start_date=body.start_date,
            end_date=body.end_date,
            config=body.config,
        )

    @app.get("/api/v1/social/campaigns/{campaign_id}")
    def get_social_campaign_route(campaign_id: str, current=Depends(actor_dep)):
        campaign = es_repo.get_campaign(settings.tenant_id, campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campagne introuvable")
        return campaign

    @app.post("/api/v1/social/campaigns/{campaign_id}/renew")
    def renew_social_campaign_route(campaign_id: str, body: CampaignRenewalRequest, current=Depends(actor_dep)):
        return es_repo.renew_campaign_for_year(
            settings.tenant_id,
            source_campaign_id=campaign_id,
            target_school_year=body.target_school_year,
            performed_by=current.get("email") or current.get("sub") or "agent",
            carry_over_dossiers=body.carry_over_dossiers,
            carry_over_reminders=body.carry_over_reminders,
        )

    @app.get("/api/v1/social/campaigns/{campaign_id}/dossiers")
    def list_campaign_dossiers_route(campaign_id: str, current=Depends(actor_dep)):
        return {"items": es_repo.list_campaign_dossiers(settings.tenant_id, campaign_id)}

    @app.post("/api/v1/social/campaigns/{campaign_id}/dossiers")
    def create_campaign_dossier_route(campaign_id: str, body: CampaignDossierCreate, current=Depends(actor_dep)):
        return es_repo.create_campaign_dossier(
            settings.tenant_id,
            campaign_id=campaign_id,
            family_ref=body.family_ref,
            beneficiary_name=body.beneficiary_name,
            child_name=body.child_name,
            school_name=body.school_name,
            quotient_familial=body.quotient_familial,
            project_id=body.project_id,
            details=body.details,
        )

    @app.get("/api/v1/social/quotient-calculator")
    def calculate_quotient_route(quotient_familial: int = 0, current=Depends(actor_dep)):
        return calculate_canteen_bracket(quotient_familial)

    @app.get("/api/v1/projects/{project_id}/social-aid")
    def list_project_social_aid_route(project_id: str, current=Depends(actor_dep)):
        require_project_read(project_id, current)
        items = es_repo.list_social_aid_for_project(settings.tenant_id, project_id)
        if hasattr(app.state, "audit_chain"):
            import hashlib
            actor_id = current.get("actor_id") or current.get("sub") or "unknown"
            actor_name = current.get("display_name") or current.get("email") or "Agent CCAS"
            app.state.audit_chain.append_entry(
                tenant_id=settings.tenant_id,
                actor_id=actor_id,
                actor_name=actor_name,
                actor_role=current.get("role") or "agent",
                action="rgpd_consultation_dossier_ccas",
                document_ref=f"CCAS-{project_id}",
                document_sha256=hashlib.sha256(f"CCAS-{project_id}".encode("utf-8")).hexdigest(),
                details={"project_id": project_id, "category": "RGPD Art. 9 Données Sensibles CCAS"},
            )
        return {"items": items, "total": len(items)}

    @app.post("/api/v1/projects/{project_id}/social-aid")
    def create_project_social_aid_route(project_id: str, body: SocialAidRecordCreate, current=Depends(actor_dep)):
        require_project_write(project_id, current)
        return es_repo.record_social_aid(
            settings.tenant_id,
            project_id=project_id,
            aid_type=body.aid_type,
            confidential_ref=body.confidential_ref,
            amount_cents=body.amount_cents,
            commission_decision=body.commission_decision,
            deliberation_ref=body.deliberation_ref,
            notes=body.notes,
        )

    @app.get("/api/v1/social/reminders")
    def list_social_reminders_route(campaign_id: Optional[str] = None, include_dismissed: bool = False, current=Depends(actor_dep)):
        items = es_repo.list_reminders(settings.tenant_id, campaign_id=campaign_id, include_dismissed=include_dismissed)
        return {"items": items, "total": len(items)}

    @app.post("/api/v1/social/reminders")
    def create_social_reminder_route(body: RecurringReminderCreate, current=Depends(actor_dep)):
        return es_repo.create_reminder(
            settings.tenant_id,
            title=body.title,
            due_date=body.due_date,
            reminder_type=body.reminder_type,
            campaign_id=body.campaign_id,
        )

    @app.post("/api/v1/social/reminders/{reminder_id}/dismiss")
    def dismiss_social_reminder_route(reminder_id: str, current=Depends(actor_dep)):
        success = es_repo.dismiss_reminder(settings.tenant_id, reminder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rappel introuvable")
        return {"dismissed": True}

