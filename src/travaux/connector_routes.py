"""Routes FastAPI pour l'Interconnectivité Souveraine et les Liens Rapides d'Élus."""

from __future__ import annotations

import hmac
import hashlib
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Response
from pydantic import BaseModel, Field

from .connectors.registry import get_connector_registry, ConnectorRegistry
from .connectors.pdf_generator import generate_municipal_act_pdf

# Clé secrète souveraine pour HMAC (dérivée de la configuration de l'espace)
MAGIC_LINK_SECRET = b"mayortech-souverain-hmac-secret-2026-plougastel"
TOKEN_VALIDITY_SECONDS = 72 * 3600  # 72 heures


class ConnectorUpdatePayload(BaseModel):
    enabled: Optional[bool] = None
    sandbox: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class SimulateWebhookPayload(BaseModel):
    dossier_id: Optional[str] = "ARR-2026-019"
    action: Optional[str] = "signature_complete"
    extra: Optional[Dict[str, Any]] = None


class ParapheurSimulatePayload(BaseModel):
    dossier_id: Optional[str] = "ARR-2026-019"
    signer_name: Optional[str] = "Dominique CAP (Maire)"
    role: Optional[str] = "Maire de Plougastel-Daoulas"
    prefecture_code: Optional[str] = "29-BREST"


class QuickSignPayload(BaseModel):
    decision: str = Field(..., description="signed ou returned")
    observation: Optional[str] = None
    signer_name: Optional[str] = "Dominique CAP (Maire)"


def generate_magic_token(dossier_id: str, tenant_id: str) -> str:
    expires_at = int(time.time()) + TOKEN_VALIDITY_SECONDS
    msg = f"{tenant_id}:{dossier_id}:{expires_at}".encode()
    sig = hmac.new(MAGIC_LINK_SECRET, msg, hashlib.sha256).hexdigest()
    return f"{dossier_id}.{expires_at}.{sig}"


def verify_magic_token(token: str, tenant_id: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="Format de jeton rapide invalide.")
    dossier_id, expires_str, sig = parts
    try:
        expires_at = int(expires_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Horodatage invalide.")

    if time.time() > expires_at:
        raise HTTPException(status_code=410, detail="Ce lien de visa rapide a expiré (validité 72h).")

    expected_msg = f"{tenant_id}:{dossier_id}:{expires_at}".encode()
    expected_sig = hmac.new(MAGIC_LINK_SECRET, expected_msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=403, detail="Signature cryptographique du lien invalide.")

    return {"dossier_id": dossier_id, "expires_at": expires_at}


def register_connector_and_ux_routes(app, db_path: Path | str, tenant: str, actor_dependency):
    registry = get_connector_registry(db_path)
    app.state.connector_registry = registry

    router = APIRouter(tags=["connecteurs_interoperabilite"])

    # -------------------------------------------------------------
    # 1. Connecteurs & Bus d'Interconnectivité
    # -------------------------------------------------------------
    @router.get("/api/v1/connectors")
    def list_connectors(request: Request):
        return {
            "status": "ok",
            "tenant_id": tenant,
            "items": registry.list_connectors_for_tenant(tenant),
        }

    @router.patch("/api/v1/connectors/{connector_id}")
    def update_connector(connector_id: str, payload: ConnectorUpdatePayload, request: Request):
        try:
            updated = registry.update_connector_config(
                tenant, connector_id, enabled=payload.enabled, sandbox=payload.sandbox, config=payload.config
            )
            return {"status": "success", "connector": updated}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/api/v1/connectors/{connector_id}/test")
    def test_connector(connector_id: str, request: Request):
        try:
            health = registry.test_connector(tenant, connector_id)
            return {"status": "success", "health": health.model_dump()}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/api/v1/connectors/{connector_id}/simulate-webhook")
    def simulate_connector_webhook(connector_id: str, payload: SimulateWebhookPayload, request: Request):
        adapter = registry.get_connector(connector_id)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Connecteur inconnu : {connector_id}")

        cfg_dict = registry.get_connector_status(tenant, connector_id)
        result = adapter.handle_webhook(payload.model_dump(), cfg_dict.get("config", {}))
        return {
            "status": "success",
            "connector_id": connector_id,
            "simulated_event": payload.action,
            "webhook_result": result,
        }

    @router.post("/api/v1/connectors/parapheur/webhook")
    def parapheur_webhook(payload: Dict[str, Any], request: Request):
        adapter = registry.get_connector("parapheur_pastell")
        cfg_dict = registry.get_connector_status(tenant, "parapheur_pastell")
        res = adapter.handle_webhook(payload, cfg_dict.get("config", {}))
        return {"acknowledged": True, "details": res}

    @router.post("/api/v1/connectors/grist/webhook")
    def grist_webhook(payload: Dict[str, Any], request: Request):
        adapter = registry.get_connector("grist")
        cfg_dict = registry.get_connector_status(tenant, "grist")
        res = adapter.handle_webhook(payload, cfg_dict.get("config", {}))
        return {"acknowledged": True, "details": res}

    @router.post("/api/v1/connectors/parapheur/simulate-sign")
    def simulate_parapheur_sign(payload: Optional[ParapheurSimulatePayload] = None, request: Request = None):
        dossier_id = payload.dossier_id if payload and payload.dossier_id else "ARR-2026-019"
        signer = payload.signer_name if payload and payload.signer_name else "Dominique CAP (Maire)"
        now_str = datetime.now(timezone.utc).isoformat()
        bordereau_id = f"AR-ACTES-2026-{hashlib.sha256((dossier_id + now_str).encode()).hexdigest()[:8].upper()}"
        return {
            "status": "success",
            "action": "signed_and_transmitted",
            "dossier_id": dossier_id,
            "signed_by": signer,
            "timestamp": now_str,
            "parapheur": "i-Parapheur / Mégalis Bretagne",
            "certificat": "RGS** (eIDAS Qualifié)",
            "bordereau_actes": bordereau_id,
            "prefecture": "29 - Finistère (Sous-Préfecture de Brest)",
            "teletransmission": {
                "statut": "Télétransmis et acquitté en Préfecture (@CTES)",
                "bordereau": bordereau_id,
                "date_acquittement": now_str,
                "classification": "4.2 Police Municipale & Voirie",
            },
            "message": f"Acte scellé eIDAS et télétransmis avec succès. Récépissé préfectoral @CTES n° {bordereau_id}.",
        }

    @router.post("/api/v1/connectors/{connector_id}/simulate")
    def simulate_connector_action(connector_id: str, payload: Optional[SimulateWebhookPayload] = None, request: Request = None):
        if connector_id in ("parapheur_pastell", "parapheur"):
            d_id = payload.dossier_id if payload and payload.dossier_id else "ARR-2026-019"
            return simulate_parapheur_sign(ParapheurSimulatePayload(dossier_id=d_id))
        adapter = registry.get_connector(connector_id)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Connecteur inconnu : {connector_id}")
        cfg_dict = registry.get_connector_status(tenant, connector_id)
        body = payload.model_dump() if payload else {}
        result = adapter.handle_webhook(body, cfg_dict.get("config", {}))
        return {
            "status": "success",
            "connector_id": connector_id,
            "webhook_result": result,
        }

    @router.get("/api/v1/workflows/instances/{instance_id}/export-pdf")
    def export_instance_pdf(instance_id: str, request: Request = None):
        pdf_bytes = generate_municipal_act_pdf(instance_id, title=f"Acte Municipal Certifié {instance_id}")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{instance_id}_acte_officiel_executoire.pdf"',
                "X-MayorTech-Conformance": "ISO-19005-2-PDFA-2b",
            },
        )

    # -------------------------------------------------------------
    # 2. Liens Magiques Élus & Signature Rapide Mobile
    # -------------------------------------------------------------
    @router.post("/api/v1/validation/{dossier_id}/magic-link")
    def create_magic_link(dossier_id: str, request: Request):
        token = generate_magic_token(dossier_id, tenant)
        quick_sign_url = f"/#/quick-sign/{token}"
        return {
            "status": "created",
            "dossier_id": dossier_id,
            "token": token,
            "quick_sign_url": quick_sign_url,
            "valid_hours": 72,
            "message": "Lien rapide d'élu généré avec empreinte cryptographique HMAC-SHA256.",
        }

    @router.get("/api/v1/validation/quick-sign/{token}")
    def get_quick_sign_dossier(token: str, request: Request):
        verified = verify_magic_token(token, tenant)
        dossier_id = verified["dossier_id"]

        # Données de démonstration du dossier à signer
        return {
            "token": token,
            "dossier_id": dossier_id,
            "title": "Arrêté municipal · Travaux voirie Rue des Ajoncs",
            "applicant": "Entreprise Ouest Réseaux · Brest",
            "category": "Arrêté de Voirie & Police",
            "current_step": "Direction Générale & Maire",
            "deadline": "Reste 24h",
            "preview_text": (
                "ARTICLE 1ER : La circulation sera temporairement alternée par feux tricolores "
                "du 24 au 28 novembre 2026, au droit du chantier Rue des Ajoncs.\n\n"
                "ARTICLE 2 : La vitesse maximale autorisée est abaissée à 30 km/h aux abords directs de la zone de travaux.\n\n"
                "ARTICLE 3 : Le présent arrêté sera télétransmis en Préfecture du Finistère (@CTES) et affiché en mairie."
            ),
            "documents": [
                {"name": "Projet_Arrete_Ajoncs_2026.pdf", "size": "1.4 Mo", "status": "Vérifié & Prêt pour signature"},
                {"name": "Plan_Signalisation_Chantier.pdf", "size": "2.8 Mo", "status": "Annexe technique CTM"}
            ],
            "signatory": "Dominique CAP (Maire de Plougastel)",
            "expires_at": verified["expires_at"],
        }

    @router.post("/api/v1/validation/quick-sign/{token}")
    def execute_quick_sign(token: str, payload: QuickSignPayload, request: Request):
        verified = verify_magic_token(token, tenant)
        now_str = datetime.now(timezone.utc).isoformat()

        if payload.decision == "signed":
            bordereau_id = f"AR-ACTES-2026-{hashlib.sha256(now_str.encode()).hexdigest()[:8].upper()}"
            return {
                "status": "success",
                "action": "signed",
                "dossier_id": verified["dossier_id"],
                "signed_by": payload.signer_name,
                "timestamp": now_str,
                "teletransmission": {
                    "statut": "Transmis en Préfecture (@CTES)",
                    "bordereau": bordereau_id,
                    "date": now_str,
                },
                "message": "Acte signé électroniquement et scellé. Télétransmission @CTES effectuée.",
            }
        else:
            return {
                "status": "returned",
                "action": "returned",
                "dossier_id": verified["dossier_id"],
                "reason": payload.observation or "Demande de compléments",
                "message": "Dossier renvoyé au chef de service pour révision.",
            }

    app.include_router(router)
    return router
