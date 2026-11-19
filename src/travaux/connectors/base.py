"""Classe abstraite de base et modèles de données pour les adaptateurs de connecteurs souverains."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ConnectorHealth(BaseModel):
    status: str = Field(..., description="ok, warning, error, unconfigured")
    latency_ms: float = Field(default=0.0, description="Temps de réponse en millisecondes")
    message: str = Field(..., description="Message explicatif clair")
    mode: str = Field(default="sandbox", description="sandbox ou production")
    details: Dict[str, Any] = Field(default_factory=dict)


class ExternalDispatchResult(BaseModel):
    success: bool
    external_id: str
    status: str = Field(..., description="pending, signed, transmitted, rejected, error")
    message: str
    download_url: Optional[str] = None
    bordereau_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectorAdapter(ABC):
    """Classe abstraite pour tous les adaptateurs de connecteurs interopérables."""

    connector_id: str
    name: str
    description: str
    category: str  # identite, parapheur, donnees, alertes, messagerie
    icon: str
    sandbox_supported: bool = True

    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> ConnectorHealth:
        """Vérifie la disponibilité du service distant ou du bac à sable."""
        pass

    @abstractmethod
    def push_artifact(self, instance_id: str, payload: Dict[str, Any], config: Dict[str, Any]) -> ExternalDispatchResult:
        """Pousse un document ou un acte municipal vers le tiers de télétransmission."""
        pass

    @abstractmethod
    def handle_webhook(self, event_payload: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Traite une notification entrante asynchrone (ex. acte signé, bordereau @CTES)."""
        pass

    @abstractmethod
    def sync_status(self, external_ref: str, config: Dict[str, Any]) -> str:
        """Interroge l'état actuel de l'acte auprès du tiers distant."""
        pass
