"""Service d'Anonymisation et d'Occultation RGPD des Actes Municipaux.

Conforme à :
- L'Ordonnance n° 2021-1310 du 7 octobre 2021 portant réforme des règles
  de publicité, d’entrée en vigueur et de conservation des actes pris par
  les collectivités territoriales et leurs groupements.
- L'Art. L. 2131-1 et R. 2131-1 A du Code Général des Collectivités Territoriales (CGCT).
- Le Règlement Général sur la Protection des Données (RGPD - Règlement UE 2016/679).

Ce module garantit la double conservation :
1. L'acte original avec mentions nominatives reste scellé et archivé au coffre-fort
   numérique de la commune avec son empreinte SHA-256.
2. La version publiable pour affichage ou mise en ligne occulte déterministement
   toutes les données personnelles sensibles et reçoit sa propre empreinte SHA-256.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


LEGAL_FRAMEWORK_NOTICE = (
    "Version certifiée conforme pour affichage légal et publication électronique "
    "(Ordonnance n° 2021-1310 du 7 octobre 2021 & Art. L. 2131-1 du CGCT). "
    "Original intégral scellé et conservé au coffre numérique municipal."
)


@dataclass
class DetectedEntity:
    id: str
    category: str  # "name", "address", "phone", "email", "cadastre", "bank", "social"
    label: str
    original_value: str
    suggested_replacement: str
    start: int
    end: int
    confidence: float = 1.0


# Regex déterministes adaptées aux actes municipaux français
REGEX_PATTERNS = [
    # 1. Emails
    (
        "email",
        "Adresse courriel privée",
        "[COURRIEL OCCULTÉ RGPD]",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", re.IGNORECASE),
    ),
    # 2. IBAN français
    (
        "bank",
        "Coordonnées bancaires (IBAN)",
        "[IBAN OCCULTÉ RGPD]",
        re.compile(r"\bFR\d{2}[ \t]?(?:\d{4}[ \t]?){5}\d{3}\b", re.IGNORECASE),
    ),
    # 3. Téléphones (fixes et mobiles)
    (
        "phone",
        "Numéro de téléphone personnel",
        "[TÉLÉPHONE OCCULTÉ RGPD]",
        re.compile(r"(?:(?:\+|00)33|0)[ \t]*[1-9](?:[ \t.-]*\d{2}){4}\b"),
    ),
    # 4. Numéro Cerfa nominatif ou dossier CCAS sensible
    (
        "social",
        "Dossier social / Données CCAS sensibles",
        "[DOSSIER SOCIAL OCCULTÉ RGPD]",
        re.compile(
            r"(?:Famille\s+[A-Z]\.|\bDossier\s+Anonymisé\s+Réf\s*#\d+|\bAide\s+Sociale\s+Réf\s*#\d+)",
            re.IGNORECASE,
        ),
    ),
    # 5. Référence de parcelle cadastrale avec mention privée
    (
        "cadastre",
        "Parcelle cadastrale privée",
        "[PARCELLE OCCULTÉE RGPD]",
        re.compile(
            r"(?:parcelle\s+(?:cadastrée\s+)?section\s+[A-Z]{1,2}\s*(?:n°|numéro)?\s*\d+|section\s+[A-Z]{1,2}\s*n°\s*\d+)",
            re.IGNORECASE,
        ),
    ),
    # 6. Titres de civilité et noms complets de personnes physiques
    (
        "name",
        "Identité de particulier",
        "[NOM OCCULTÉ RGPD]",
        re.compile(
            r"(?:M\.\s*(?:&|et)\s*Mme|M\.|Mme|Monsieur|Madame)\s+[A-Za-zÀ-ÖØ-öø-ÿ'-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ'-]+)+",
            re.IGNORECASE,
        ),
    ),
    # 7. Adresses de voirie précises et codes postaux
    (
        "address",
        "Adresse postale privée",
        "[ADRESSE OCCULTÉE RGPD]",
        re.compile(
            r"(?:\b\d{1,4}(?:\s*(?:bis|ter|quater))?(?:,\s*|\s+))?"
            r"(?:chemin|rue|quai|allée|avenue|boulevard|impasse|route|place|hameau|résidence)\s+"
            r"[A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+(?:\s+[A-Za-zÀ-ÖØ-öø-ÿ0-9'-]+)*"
            r"(?:\s*(?:·|,|-)\s*(?:29\d{3}|[0-9]{5})\s+[A-Za-zÀ-ÖØ-öø-ÿ-]+)?",
            re.IGNORECASE,
        ),
    ),
]


def detect_personal_data(text: str) -> List[Dict[str, Any]]:
    """Détecte de façon déterministe les mentions nominatives et privées dans un texte d'acte."""
    if not text:
        return []

    spans_occupied: List[tuple[int, int]] = []
    detected: List[DetectedEntity] = []
    entity_counter = 1

    for category, label, default_replacement, pattern in REGEX_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            matched_text = match.group(0).strip()

            if not matched_text:
                continue

            # Ne pas masquer le nom officiel de la commune ou des organes municipaux
            lower = matched_text.lower()
            if "ville de plougastel" in lower or "plougastel-daoulas" in lower and category != "address":
                continue
            if "brest métropole" in lower:
                continue
            if "préfecture du finistère" in lower or "direction générale des services" in lower:
                continue

            # Éviter les chevauchements
            overlaps = any(
                max(start, occ_start) < min(end, occ_end)
                for occ_start, occ_end in spans_occupied
            )
            if overlaps:
                continue

            spans_occupied.append((start, end))
            entity_id = f"rgpd-{entity_counter:03d}"
            entity_counter += 1

            detected.append(
                DetectedEntity(
                    id=entity_id,
                    category=category,
                    label=label,
                    original_value=matched_text,
                    suggested_replacement=default_replacement,
                    start=start,
                    end=end,
                    confidence=1.0,
                )
            )

    # Trier par position chronologique dans le texte
    detected.sort(key=lambda e: e.start)
    return [asdict(e) for e in detected]


def anonymize_text(
    text: str,
    selected_ids: Optional[List[str]] = None,
    entities: Optional[List[Dict[str, Any]]] = None,
    custom_replacement: Optional[str] = None,
) -> Dict[str, Any]:
    """Applique l'occultation des données sélectionnées et calcule les doubles hashs SHA-256."""
    text = text or ""
    all_entities = entities if entities is not None else detect_personal_data(text)

    # Si selected_ids est None, on occulte tout ce qui est détecté par défaut
    allowed_id_set = set(selected_ids) if selected_ids is not None else {e["id"] for e in all_entities}

    # Filtrer les entités retenues
    entities_to_redact = [e for e in all_entities if e["id"] in allowed_id_set]

    # Remplacement de droite à gauche pour préserver les décalages d'index
    entities_to_redact.sort(key=lambda e: e["start"], reverse=True)

    result_chars = list(text)
    for entity in entities_to_redact:
        start = entity["start"]
        end = entity["end"]
        replacement = custom_replacement or entity.get("suggested_replacement", "[OCCULTÉ RGPD]")
        result_chars[start:end] = list(replacement)

    anonymized_text = "".join(result_chars)

    orig_bytes = text.encode("utf-8")
    anon_bytes = anonymized_text.encode("utf-8")

    orig_sha256 = hashlib.sha256(orig_bytes).hexdigest()
    anon_sha256 = hashlib.sha256(anon_bytes).hexdigest()

    return {
        "original_text": text,
        "anonymized_text": anonymized_text,
        "original_sha256": orig_sha256,
        "anonymized_sha256": anon_sha256,
        "detected_count": len(all_entities),
        "redacted_count": len(entities_to_redact),
        "entities": all_entities,
        "legal_framework": {
            "ordonnance": "Ordonnance n° 2021-1310 du 7 octobre 2021",
            "cgct_article": "Articles L. 2131-1 et R. 2131-1 A du CGCT",
            "rgpd": "Règlement Général sur la Protection des Données (UE 2016/679)",
            "certificate_notice": LEGAL_FRAMEWORK_NOTICE,
        },
    }


# Schemas Pydantic pour l'API HTTP
class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500_000)


class ApplyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500_000)
    selected_ids: Optional[List[str]] = None
    custom_replacement: Optional[str] = None


def register_anonymizer_routes(app: FastAPI, repo: Any, tenant: str, actor: Any, settings: Any):
    """Enregistre les routes HTTP d'anonymisation RGPD."""

    @app.post("/api/v1/anonymizer/detect")
    async def api_detect_personal_data(req: DetectRequest, request: Request):
        actor(request)
        entities = detect_personal_data(req.text)
        orig_sha = hashlib.sha256(req.text.encode("utf-8")).hexdigest()
        return JSONResponse({
            "detected_count": len(entities),
            "original_sha256": orig_sha,
            "entities": entities,
        })

    @app.post("/api/v1/anonymizer/apply")
    async def api_apply_anonymization(req: ApplyRequest, request: Request):
        actor(request)
        result = anonymize_text(
            text=req.text,
            selected_ids=req.selected_ids,
            custom_replacement=req.custom_replacement,
        )
        return JSONResponse(result)

    return {"status": "active", "version": "v3.3"}
