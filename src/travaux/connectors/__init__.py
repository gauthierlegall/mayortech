"""Connecteurs Souverains et Interopérabilité MayorTech.

Fournit le bus d'interconnectivité avec les services de l'État (ProConnect),
les parapheurs homologués (Pastell, i-Parapheur, Maarch) et les outils de
La Suite Numérique (Grist, Tchap / Matrix / Ntfy).
"""

from .base import ConnectorAdapter, ConnectorHealth, ExternalDispatchResult
from .registry import ConnectorRegistry, get_connector_registry

__all__ = [
    "ConnectorAdapter",
    "ConnectorHealth",
    "ExternalDispatchResult",
    "ConnectorRegistry",
    "get_connector_registry",
]
