"""Presentation of newly generated summaries; stored versions are never rewritten."""

FIELD_LABELS = {
    "deadline": "Échéance",
    "delivery_date": "Livraison",
    "acceptance_date": "Réception",
    "budget_raw": "Budget",
    "progress": "Avancement",
    "decision": "Décision",
    "contractor": "Entreprise",
    "owner": "Responsable",
    "location": "Lieu",
    "category": "Catégorie",
}


def summary_field_label(field: str) -> str:
    if field.startswith("action."):
        return "Action"
    # Preserve an unknown business field rather than invent its meaning.
    return FIELD_LABELS.get(field, field)
