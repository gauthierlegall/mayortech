"""
Module de gestion et de configuration modulaire des organisations (Feature Flags par collectivité).
Garantit l'intégrité souveraine sans altérer les 5 noyaux protégés (repository, workspace, auth, governance, jobs).
Persistance isolée dans SQLite WAL : table organization_module_configs.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Catalogue Canonique des Modules MayorTech
# -----------------------------------------------------------------------------

MODULES_CATALOG = [
    # Socle obligatoire (locked: true)
    {
        "key": "core_directory",
        "name": "Annuaire & Organigramme",
        "description": "Double hiérarchie élus et administration, délégations d'arrêtés et suppléances",
        "category": "socle",
        "locked": True,
        "circuits": ["Tous les circuits"],
        "icon": "Users",
    },
    {
        "key": "core_workflows",
        "name": "Circuits de validation BPMN",
        "description": "Moteur de circuits BPMN 2.0, visas régaliens, signatures et journal d'audit",
        "category": "socle",
        "locked": True,
        "circuits": ["Moteur BPMN 2.0"],
        "icon": "GitBranch",
    },
    {
        "key": "core_documents",
        "name": "Documents & Coffre SHA-256",
        "description": "Coffre-fort d'actes scellés, pièces Cerfa et empreinte d'intégrité SHA-256 (compatible parapheur eIDAS)",
        "category": "socle",
        "locked": True,
        "circuits": ["Contrôle légalité"],
        "icon": "FileCheck2",
    },
    # Modules métiers (toggleable)
    {
        "key": "urbanisme_ads",
        "name": "Urbanisme, PLU & Cadastre",
        "description": "Instruction ADS, conformité zonage PLU, consultations ABF et avis voirie CTM",
        "category": "metier",
        "locked": False,
        "circuits": ["Permis de Construire (ADS)", "Déclaration Préalable"],
        "icon": "Building",
    },
    {
        "key": "ports_littoral",
        "name": "Ports, Mouillages & Littoral",
        "description": "Gestion des cales, concessions portuaires, mouillages et autorisations domaine maritime",
        "category": "metier",
        "locked": False,
        "circuits": ["Autorisation d'Occupation Temporaire (AOT)"],
        "icon": "Anchor",
    },
    {
        "key": "travaux_terrain",
        "name": "Chantiers, Gantt & Suivi Terrain",
        "description": "Pilotage des arrêtés de voirie, chantiers municipaux et interventions des équipes CTM",
        "category": "metier",
        "locked": False,
        "circuits": ["Arrêté de Voirie & Police", "Intervention CTM"],
        "icon": "HardHat",
    },
    {
        "key": "enfance_ccas",
        "name": "Enfance, Scolaire, QF & CCAS",
        "description": "Inscriptions scolaires, quotient familial CAF, restauration scolaire et aides sociales",
        "category": "metier",
        "locked": False,
        "circuits": ["Aide Sociale CCAS", "Dérogation Scolaire"],
        "icon": "GraduationCap",
    },
    {
        "key": "finances_m57",
        "name": "Finances M57 & Marchés Publics",
        "description": "Engagements budgétaires M57, seuils CAO et commissions d'appel d'offres",
        "category": "metier",
        "locked": False,
        "circuits": ["Marché Public (CAO)", "Subvention Municipale"],
        "icon": "Coins",
    },
    {
        "key": "conseil_seances",
        "name": "Séances du Conseil & Délibérations",
        "description": "Ordre du jour, gestion des présences/quorum, et télétransmission des délibérations",
        "category": "metier",
        "locked": False,
        "circuits": ["Délibération du Conseil"],
        "icon": "Landmark",
    },
    {
        "key": "messagerie_eml",
        "name": "Messagerie & Archives EML",
        "description": "Collecte, tri et archivage des courriels citoyens et échanges administratifs",
        "category": "metier",
        "locked": False,
        "circuits": ["Signalement Courriel"],
        "icon": "Mail",
    },
    # Options & Connecteurs
    {
        "key": "ai_assistant",
        "name": "Assistant IA & Prompt-to-BPMN",
        "description": "Génération automatique de processus BPMN 2.0 et assistance à la rédaction d'arrêtés",
        "category": "options",
        "locked": False,
        "circuits": ["Studio IA"],
        "icon": "Sparkles",
    },
    {
        "key": "connector_ctes",
        "name": "Télétransmission @CTES / Pastell",
        "description": "Liaison directe avec le contrôle de légalité en Préfecture et bordereaux d'acquittement",
        "category": "options",
        "locked": False,
        "circuits": ["Télétransmission Préfecture"],
        "icon": "Send",
    },
    {
        "key": "connector_eidas",
        "name": "Parapheur eIDAS / RGS**",
        "description": "Délégation de signature qualifiée avec certificat cryptographique matériel du Maire",
        "category": "options",
        "locked": False,
        "circuits": ["Signature RGS**"],
        "icon": "ShieldCheck",
    },
    {
        "key": "mobile_alerts",
        "name": "Alertes mobiles terrain souveraines",
        "description": "Notifications push Ntfy temps réel pour les agents de voirie et alertes SLA 24h",
        "category": "options",
        "locked": False,
        "circuits": ["Alerte SLA SMS/Push"],
        "icon": "Smartphone",
    },
]

# Clés de socle obligatoire
CORE_LOCKED_KEYS = {m["key"] for m in MODULES_CATALOG if m.get("locked")}

# Presets en 1 clic
PRESETS = {
    "iterop_pure": {
        "id": "iterop_pure",
        "label": "Circuits seuls",
        "description": "Socle uniquement : circuits de validation, documents et coffre certifié",
        "modules": ["core_directory", "core_workflows", "core_documents"],
    },
    "commune_rurale": {
        "id": "commune_rurale",
        "label": "Commune rurale",
        "description": "Socle + Travaux & Voirie + Conseil Municipal + Messagerie",
        "modules": [
            "core_directory",
            "core_workflows",
            "core_documents",
            "travaux_terrain",
            "conseil_seances",
            "messagerie_eml",
            "mobile_alerts",
        ],
    },
    "ville_complete": {
        "id": "ville_complete",
        "label": "Ville complète",
        "description": "Tous les services et options activés, sauf Ports & Littoral",
        "modules": [
            "core_directory",
            "core_workflows",
            "core_documents",
            "urbanisme_ads",
            "travaux_terrain",
            "enfance_ccas",
            "finances_m57",
            "conseil_seances",
            "messagerie_eml",
            "ai_assistant",
            "connector_ctes",
            "connector_eidas",
            "mobile_alerts",
        ],
    },
    "commune_littorale": {
        "id": "commune_littorale",
        "label": "Commune littorale",
        "description": "Tous les modules activés (y compris Ports, Mouillages & Littoral)",
        "modules": [m["key"] for m in MODULES_CATALOG],
    },
}

ALL_MODULE_KEYS = [m["key"] for m in MODULES_CATALOG]


# -----------------------------------------------------------------------------
# Modèles Pydantic pour l'API
# -----------------------------------------------------------------------------

class OrganizationCreateInput(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    insee_code: str = Field(default="", max_length=10)
    stratum: str = Field(default="3500-15000", max_length=50)
    email_domain: str = Field(default="", max_length=100)
    enabled_modules: List[str] = Field(default_factory=lambda: list(ALL_MODULE_KEYS))


class OrganizationModulesUpdateInput(BaseModel):
    enabled_modules: List[str] = Field(min_length=1)


# -----------------------------------------------------------------------------
# Repository SQLite Isolé (WAL)
# -----------------------------------------------------------------------------

class OrganizationModulesRepository:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_module_configs (
                    tenant_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    insee_code TEXT NOT NULL DEFAULT '',
                    stratum TEXT NOT NULL DEFAULT '3500-15000',
                    email_domain TEXT NOT NULL DEFAULT '',
                    enabled_modules_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def get_or_create_default(self, tenant_id: str, default_name: str = "Ville de Plougastel-Daoulas") -> Dict[str, Any]:
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM organization_module_configs WHERE tenant_id = ?",
                (tenant_id,)
            )
            row = cur.fetchone()
            if row:
                modules = json.loads(row["enabled_modules_json"])
                # Assure that all locked core modules are present
                modules = list(set(modules).union(CORE_LOCKED_KEYS))
                return {
                    "tenant_id": row["tenant_id"],
                    "name": row["name"],
                    "insee_code": row["insee_code"],
                    "stratum": row["stratum"],
                    "email_domain": row["email_domain"],
                    "enabled_modules": modules,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }

            # Create default with all modules enabled (Commune littorale Plougastel)
            now = datetime.now(timezone.utc).isoformat()
            modules_json = json.dumps(ALL_MODULE_KEYS)
            insee = "29189" if "plougastel" in tenant_id.lower() or "demo" in tenant_id.lower() else ""
            domain = "plougastel.fr" if "plougastel" in tenant_id.lower() or "demo" in tenant_id.lower() else ""
            conn.execute(
                """
                INSERT INTO organization_module_configs 
                (tenant_id, name, insee_code, stratum, email_domain, enabled_modules_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, default_name, insee, "3500-15000", domain, modules_json, now, now)
            )
            conn.commit()
            return {
                "tenant_id": tenant_id,
                "name": default_name,
                "insee_code": insee,
                "stratum": "3500-15000",
                "email_domain": domain,
                "enabled_modules": list(ALL_MODULE_KEYS),
                "created_at": now,
                "updated_at": now,
            }

    def update_modules(self, tenant_id: str, enabled_modules: List[str]) -> Dict[str, Any]:
        # Enforce locked modules presence
        final_modules = list(set(enabled_modules).union(CORE_LOCKED_KEYS))
        now = datetime.now(timezone.utc).isoformat()
        modules_json = json.dumps(final_modules)

        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT tenant_id FROM organization_module_configs WHERE tenant_id = ?",
                (tenant_id,)
            )
            if not cur.fetchone():
                self.get_or_create_default(tenant_id)

            conn.execute(
                """
                UPDATE organization_module_configs 
                SET enabled_modules_json = ?, updated_at = ?
                WHERE tenant_id = ?
                """,
                (modules_json, now, tenant_id)
            )
            conn.commit()

        return self.get_or_create_default(tenant_id)

    def create_organization(self, data: OrganizationCreateInput) -> Dict[str, Any]:
        slug = re.sub(r"[^a-z0-9]+", "-", data.name.lower()).strip("-")
        if not slug:
            slug = "mairie-nouvelle"
        tenant_id = f"org-{slug}-{int(datetime.now().timestamp()) % 10000}"

        final_modules = list(set(data.enabled_modules).union(CORE_LOCKED_KEYS))
        now = datetime.now(timezone.utc).isoformat()
        modules_json = json.dumps(final_modules)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO organization_module_configs 
                (tenant_id, name, insee_code, stratum, email_domain, enabled_modules_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tenant_id, data.name, data.insee_code, data.stratum, data.email_domain, modules_json, now, now)
            )
            conn.commit()

        return {
            "tenant_id": tenant_id,
            "name": data.name,
            "insee_code": data.insee_code,
            "stratum": data.stratum,
            "email_domain": data.email_domain,
            "enabled_modules": final_modules,
            "created_at": now,
            "updated_at": now,
        }

    def is_module_enabled(self, tenant_id: str, module_key: str) -> bool:
        if module_key in CORE_LOCKED_KEYS:
            return True
        cfg = self.get_or_create_default(tenant_id)
        return module_key in cfg.get("enabled_modules", [])


# -----------------------------------------------------------------------------
# Enregistrement des Routes FastAPI
# -----------------------------------------------------------------------------

def register_organization_modules_routes(app, db_path: Path | str, tenant: str, actor_dependency):
    modules_repo = OrganizationModulesRepository(db_path)
    app.state.organization_modules_repo = modules_repo

    router = APIRouter(prefix="/api/v1/organizations", tags=["organizations_modules"])

    @router.get("/current/modules")
    def get_current_modules(request: Request):
        cfg = modules_repo.get_or_create_default(tenant)
        return {
            **cfg,
            "catalog": MODULES_CATALOG,
            "presets": PRESETS,
        }

    @router.patch("/current/modules")
    def update_current_modules(payload: OrganizationModulesUpdateInput, request: Request):
        updated = modules_repo.update_modules(tenant, payload.enabled_modules)
        return {
            "status": "success",
            "message": "Configuration des modules mise à jour avec succès (non destructive).",
            **updated,
            "catalog": MODULES_CATALOG,
            "presets": PRESETS,
        }

    @router.post("")
    def create_organization_endpoint(payload: OrganizationCreateInput, request: Request):
        created = modules_repo.create_organization(payload)
        return {
            "status": "created",
            "message": f"Collectivité '{payload.name}' initialisée avec succès.",
            **created,
            "catalog": MODULES_CATALOG,
            "presets": PRESETS,
        }

    app.include_router(router)
    return modules_repo
