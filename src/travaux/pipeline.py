"""Rattachement serveur puis extraction; le modèle ne choisit jamais le chantier."""
import hashlib
import re

from .domain import DomainError, normalize_value, validate_field, evidence_span
from .llm import ExtractionError


LABELS = {"deadline": "Échéance", "delivery_date": "Livraison", "acceptance_date": "Réception", "budget_raw": "Budget", "progress": "Avancement", "decision": "Décision", "contractor": "Entreprise"}
FIELDS = {value.casefold(): key for key, value in LABELS.items()}


def extract_source(repo, tenant, source_id, extractor):
    source = repo.get_source(tenant, source_id)
    if not source.get("project_id"):
        return {"status": "needs_assignment", "candidates": 0, "warnings": ["Rattacher ce message à un chantier avant l'analyse."]}
    result = extractor.extract(source["body"])
    proposed = []
    for item in result.candidates:
        key = FIELDS.get(item.field.casefold())
        if item.kind == "action" or item.field.casefold() == "action":
            key = "action." + hashlib.sha256(item.value.casefold().encode()).hexdigest()[:12]
        if key is None:
            safe = re.sub(r"[^a-z0-9]+", "_", item.field.casefold()).strip("_")[:40]
            key = "info." + (safe or hashlib.sha256(item.field.encode()).hexdigest()[:12])
        kind = "date" if key in {"deadline", "delivery_date", "acceptance_date"} else "text"
        value = item.value
        # Keep an ambiguous/relative date as raw text rather than inventing a calendar anchor.
        if kind == "date" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            kind = "text"
            key += "_raw"
        try:
            # Validate the whole batch before the first write. Invalid dates and
            # evidence must not leave the beginning of a failed extraction behind.
            validate_field(key)
            normalize_value(kind, value)
            evidence_span(source, item.quote)
            proposed.append((key, value, item.quote, kind))
        except DomainError as exc:
            raise ExtractionError(f"Proposition métier refusée : {exc.code}") from None
    created = repo.add_candidates(tenant, source["project_id"], source_id, [{"field": key, "value": value, "quote": quote, "kind": kind} for key, value, quote, kind in proposed])
    return {"status": "needs_review", "candidates": len(created), "warnings": result.warnings}


def process_one(queue, repo, extractor, worker="local-worker"):
    job = queue.claim(worker)
    if not job:
        return False
    try:
        if job["kind"] != "extract":
            raise ExtractionError("Type de traitement inconnu")
        result = extract_source(repo, job["tenant_id"], job["payload"]["source_id"], extractor)
        queue.complete(job["id"], job["lease_token"], result)
    except (ExtractionError, DomainError):
        queue.fail(job["id"], job["lease_token"], "extraction_failed_review_required")
    return True
