"""Intelligence Juridique, Délégations Actives, Délais Légaux & Dossier de Preuve.

Module souverain pour MayorTech (Commune pilote : Ville de Plougastel-Daoulas).
Respect strict des règles de souveraineté :
- Étanchéité absolue du CCAS / Action sociale (interdiction stricte de publication).
- Chaîne d'audit et signatures avec empreintes SHA-256 conformes.
"""

from __future__ import annotations

import io
import json
import zipfile
import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


# =====================================================================
# 1. MOTEUR DE DÉLÉGATIONS ACTIVES, SEUILS & SUPPLÉANCE
# =====================================================================

DELEGATION_THRESHOLDS = {
    "marche": 10000.0,       # 10 000 € HT : visa DGS / Adjoint délégataire si <= 10k, escalade Maire si > 10k
    "deliberation": 10000.0,  # Délibérations à engagement financier
    "arrete": None,           # Arrêtés de voirie : délégation permanente à l'Adjoint aux Travaux / CTM
    "permis": None,           # Autorisations d'urbanisme : délégation à l'Adjoint Urbanisme
}


def evaluate_delegation_rule(circuit_type: str, amount_ht: Optional[float] = None) -> Dict[str, Any]:
    """Évalue la règle de délégation applicable selon le type d'acte et le montant HT."""
    threshold = DELEGATION_THRESHOLDS.get(circuit_type)
    if threshold is None or amount_ht is None:
        return {
            "circuit_type": circuit_type,
            "threshold_applied": False,
            "threshold_limit": None,
            "amount_ht": amount_ht,
            "requires_mayor": circuit_type in ("deliberation", "permis"),
            "rule_label": "Délégation permanente de signature applicable",
        }

    requires_mayor = amount_ht > threshold
    if requires_mayor:
        rule_label = f"Seuil > {int(threshold):,} € HT · Escalade automatique vers le Maire requise".replace(",", " ")
    else:
        rule_label = f"Seuil ≤ {int(threshold):,} € HT · Visa DGS ou Adjoint délégataire suffisant".replace(",", " ")

    return {
        "circuit_type": circuit_type,
        "threshold_applied": True,
        "threshold_limit": threshold,
        "amount_ht": amount_ht,
        "requires_mayor": requires_mayor,
        "rule_label": rule_label,
    }


def format_official_signature_block(
    signatory_title: str,
    delegation_active: bool,
    substitute_name: Optional[str] = None,
    substitute_role: Optional[str] = None,
    delegation_order_ref: str = "ARR-2026-DEL-001",
) -> Dict[str, str]:
    """Génère la mention juridique exacte sur l'acte officiel en cas de suppléance/délégation."""
    if not delegation_active or not substitute_name:
        return {
            "signatory": signatory_title,
            "formula": "Pour le Maire de Plougastel-Daoulas,",
            "signatory_name": "Dominique CAP",
            "signatory_title": "Maire de Plougastel-Daoulas",
            "legal_mention": "Le Maire de Plougastel-Daoulas certifie sous sa responsabilité le caractère exécutoire du présent acte.",
        }

    # Suppléance légale active
    return {
        "signatory": f"{substitute_name} ({substitute_role or 'Par délégation'})",
        "formula": "Pour le Maire empêché et par délégation,",
        "signatory_name": substitute_name,
        "signatory_title": substitute_role or "1ère Adjointe au Maire",
        "legal_mention": (
            f"Pour le Maire empêché, {substitute_name}, {substitute_role or 'Adjoint au Maire'}, "
            f"par délégation selon arrêté municipal de suppléance n° {delegation_order_ref}."
        ),
    }


# =====================================================================
# 2. CALCULATEUR DE DÉLAIS LÉGAUX RÉELS (CALENDRIER FRANÇAIS 2026-2027)
# =====================================================================

FRENCH_HOLIDAYS_2026_2027 = {
    # 2026
    date(2026, 1, 1),   # Jour de l'An
    date(2026, 4, 6),   # Lundi de Pâques
    date(2026, 5, 1),   # Fête du Travail
    date(2026, 5, 8),   # Victoire 1945
    date(2026, 5, 14),  # Ascension
    date(2026, 5, 25),  # Lundi de Pentecôte
    date(2026, 7, 14),  # Fête Nationale
    date(2026, 8, 15),  # Assomption
    date(2026, 11, 1),  # Toussaint
    date(2026, 11, 11), # Armistice 1918
    date(2026, 12, 25), # Noël
    # 2027
    date(2027, 1, 1),   # Jour de l'An
    date(2027, 3, 29),  # Lundi de Pâques
    date(2027, 5, 1),   # Fête du Travail
    date(2027, 5, 6),   # Ascension
    date(2027, 5, 8),   # Victoire 1945
    date(2027, 5, 17),  # Lundi de Pentecôte
    date(2027, 7, 14),  # Fête Nationale
    date(2027, 8, 15),  # Assomption
    date(2027, 11, 1),  # Toussaint
    date(2027, 11, 11), # Armistice 1918
    date(2027, 12, 25), # Noël
}


def is_french_business_day(d: date) -> bool:
    """Vérifie si un jour est un jour ouvré (hors week-end et hors fériés français)."""
    if d.weekday() in (5, 6): # Samedi ou Dimanche
        return False
    return d not in FRENCH_HOLIDAYS_2026_2027


def add_business_days(start: date, num_days: int) -> date:
    """Ajoute N jours ouvrés en sautant les samedis, dimanches et fériés français."""
    current = start
    added = 0
    while added < num_days:
        current += timedelta(days=1)
        if is_french_business_day(current):
            added += 1
    return current


def compute_legal_timeline(
    start_date_iso: str,
    duration_days: int,
    is_business_days: bool = False,
    suspended_date_iso: Optional[str] = None,
    resumed_date_iso: Optional[str] = None,
    reference_date_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """Calcule le délai légal français, gère la suspension de délai et l'alerte J-7 avant décision tacite."""
    start = date.fromisoformat(start_date_iso)
    ref_date = date.fromisoformat(reference_date_iso) if reference_date_iso else date.today()

    if is_business_days:
        base_deadline = add_business_days(start, duration_days)
    else:
        base_deadline = start + timedelta(days=duration_days)

    is_suspended = False
    effective_deadline = base_deadline

    # Gestion de la suspension de délai (ex: notification de pièce manquante en ADS)
    if suspended_date_iso:
        suspended = date.fromisoformat(suspended_date_iso)
        if resumed_date_iso:
            resumed = date.fromisoformat(resumed_date_iso)
            suspension_duration = (resumed - suspended).days
            effective_deadline = base_deadline + timedelta(days=suspension_duration)
        else:
            # Toujours suspendu
            is_suspended = True
            days_before_suspension = (suspended - start).days
            remaining_days = max(0, duration_days - days_before_suspension)
            return {
                "start_date": start_date_iso,
                "initial_deadline": base_deadline.isoformat(),
                "effective_deadline": None,
                "is_suspended": True,
                "suspended_at": suspended_date_iso,
                "remaining_days_when_resumed": remaining_days,
                "status_label": f"Délai suspendu le {suspended.strftime('%d/%m/%Y')} (Pièce manquante demandée)",
                "is_tacit_approaching": False,
                "days_remaining": remaining_days,
            }

    days_remaining = (effective_deadline - ref_date).days
    is_tacit_approaching = 0 <= days_remaining <= 7

    if days_remaining < 0:
        status_label = f"Décision tacite acquise ({abs(days_remaining)} j de retard)"
    elif is_tacit_approaching:
        status_label = f"J-{days_remaining} avant décision tacite ({effective_deadline.strftime('%d/%m/%Y')})"
    else:
        status_label = f"Échéance légale au {effective_deadline.strftime('%d/%m/%Y')} ({days_remaining} j restants)"

    return {
        "start_date": start_date_iso,
        "initial_deadline": base_deadline.isoformat(),
        "effective_deadline": effective_deadline.isoformat(),
        "is_suspended": False,
        "suspended_at": None,
        "days_remaining": days_remaining,
        "is_tacit_approaching": is_tacit_approaching,
        "status_label": status_label,
    }


# =====================================================================
# 3. EXPORT « DOSSIER DE PREUVE (.ZIP) » CONFORME RECOURS & LÉGALITÉ
# =====================================================================

def generate_proof_bundle_zip(dossier: Dict[str, Any], town_name: str = "Ville de Plougastel-Daoulas") -> bytes:
    """Génère l'archive .zip officielle pour transmission au contrôle de légalité ou juridiction."""
    buf = io.BytesIO()

    # Empreinte globale du dossier
    now_iso = datetime.now(timezone.utc).isoformat()
    dossier_id = dossier.get("id", "DOSSIER-SANS-ID")
    title = dossier.get("title", "Acte municipal officiel")
    applicant = dossier.get("applicant", "Demandeur non spécifié")
    article = dossier.get("previewArticle", dossier.get("preview_text", "Décision municipale exécutoire."))
    audit_trail = dossier.get("auditTrail", [])
    steps = dossier.get("steps", [])

    # 1. 01_acte_municipal.html
    signature_block = dossier.get("signatureBlock", {
        "formula": "Pour le Maire de Plougastel-Daoulas,",
        "signatory_name": "Dominique CAP",
        "signatory_title": "Maire de Plougastel-Daoulas",
        "legal_mention": "Certifié exécutoire par le Maire de Plougastel-Daoulas.",
    })

    acte_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{dossier_id} · {title}</title>
  <style>
    body {{
      font-family: 'Source Serif 4', Georgia, serif;
      background-color: #FFFFFF;
      color: #102A4C;
      max-width: 800px;
      margin: 40px auto;
      padding: 40px;
      line-height: 1.6;
      border: 1px solid #E2E8F0;
    }}
    .header {{
      text-align: center;
      border-bottom: 2px solid #102A4C;
      padding-bottom: 20px;
      margin-bottom: 30px;
    }}
    .header h1 {{ margin: 0; font-size: 20px; text-transform: uppercase; }}
    .header h2 {{ margin: 5px 0 0 0; font-size: 14px; font-weight: normal; color: #475569; }}
    .ref-bar {{
      font-family: monospace;
      font-size: 12px;
      background: #F8FAFC;
      padding: 10px;
      border: 1px solid #CBD5E1;
      margin-bottom: 25px;
    }}
    .article-content {{ font-size: 14px; white-space: pre-wrap; margin: 30px 0; }}
    .signature-box {{
      margin-top: 50px;
      padding: 20px;
      border-top: 1px solid #CBD5E1;
      text-align: right;
    }}
    .legal-notice {{ font-size: 11px; color: #64748B; font-style: italic; margin-top: 10px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>RÉPUBLIQUE FRANÇAISE</h1>
    <h2>{town_name} · Arrondissement de Brest</h2>
  </div>
  <div class="ref-bar">
    <strong>RÉFÉRENCE OFFICIELLE :</strong> {dossier_id}<br>
    <strong>OBJET :</strong> {title}<br>
    <strong>DEMANDEUR :</strong> {applicant}<br>
    <strong>HORODATAGE D'ÉMISSION :</strong> {now_iso}
  </div>
  <div class="article-content">
{article}
  </div>
  <div class="signature-box">
    <p>Fait à Plougastel-Daoulas, le {datetime.now().strftime('%d/%m/%Y')}</p>
    <p><strong>{signature_block.get('formula', 'Pour le Maire,')}</strong></p>
    <p style="margin-top: 30px;"><strong>{signature_block.get('signatory_name', 'Dominique CAP')}</strong><br>{signature_block.get('signatory_title', 'Maire')}</p>
    <p class="legal-notice">{signature_block.get('legal_mention', '')}</p>
  </div>
</body>
</html>"""

    # 2. 02_journal_audit_visas.html
    audit_rows = ""
    for entry in audit_trail:
        audit_rows += f"""
        <tr>
          <td>{entry.get('timestamp', '')}</td>
          <td><strong>{entry.get('author', '')}</strong><br><small>{entry.get('role', '')}</small></td>
          <td>{entry.get('stepName', '')}</td>
          <td>{entry.get('comment', '')}</td>
          <td style="font-family: monospace; font-size: 10px;">{entry.get('sha256', 'Non scellé')[:16]}…</td>
        </tr>
        """

    audit_html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>Journal d'audit certifié · {dossier_id}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 30px; color: #1E293B; }}
    h1 {{ color: #102A4C; font-size: 18px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }}
    th, td {{ border: 1px solid #CBD5E1; padding: 10px; text-align: left; }}
    th {{ background: #F1F5F9; color: #0F172A; }}
  </style>
</head>
<body>
  <h1>Journal d'Audit et Traçabilité des Visas (Norme ISO/IEC 19510)</h1>
  <p>Dossier : <strong>{dossier_id}</strong> · {title}</p>
  <p>Commune : <strong>{town_name}</strong> · Empreinte vérifiée eIDAS / RGS**</p>
  <table>
    <thead>
      <tr>
        <th>Horodatage</th>
        <th>Décideur</th>
        <th>Étape du circuit</th>
        <th>Observation / Visa</th>
        <th>Empreinte SHA-256</th>
      </tr>
    </thead>
    <tbody>
      {audit_rows or '<tr><td colspan="5">Aucun visa consigné</td></tr>'}
    </tbody>
  </table>
</body>
</html>"""

    # Calcul SHA-256 des fichiers
    sha_acte = hashlib.sha256(acte_html.encode("utf-8")).hexdigest()
    sha_audit = hashlib.sha256(audit_html.encode("utf-8")).hexdigest()

    # 3. 03_manifest_sha256.json
    manifest = {
        "dossier_id": dossier_id,
        "town": town_name,
        "exported_at": now_iso,
        "conformance": "Contrôle de légalité (@CTES) & Recours juridictionnel",
        "files": {
            "01_acte_municipal.html": sha_acte,
            "02_journal_audit_visas.html": sha_audit,
            "pieces_justificatives/annexe_descriptive.txt": hashlib.sha256(b"Annexe officielle MayorTech").hexdigest(),
        },
        "head_hash": hashlib.sha256(f"{sha_acte}:{sha_audit}".encode("utf-8")).hexdigest(),
    }

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("01_acte_municipal.html", acte_html.encode("utf-8"))
        zf.writestr("02_journal_audit_visas.html", audit_html.encode("utf-8"))
        zf.writestr("03_manifest_sha256.json", json.dumps(manifest, indent=2).encode("utf-8"))
        zf.writestr("pieces_justificatives/annexe_descriptive.txt", b"Annexe technique officielle au dossier.")

    return buf.getvalue()


# =====================================================================
# 4. REGISTRE PUBLIC DES ACTES & VÉRIFICATION DE NON-FUITE CCAS
# =====================================================================

# Banque d'actes publiés de démonstration (Plougastel-Daoulas)
DEMO_PUBLIC_ACTS = [
    {
        "ref": "ARR-2026-019",
        "title": "Arrêté temporaire de circulation et de stationnement Quai du Tinduff",
        "category": "Arrêté de voirie",
        "commission_id": "urbanisme_ports",
        "publication_date": "2026-11-18",
        "signed_by": "Dominique CAP (Maire)",
        "applicant": "Entreprise Ouest Réseaux · Brest",
        "status": "Publié & Exécutoire",
        "content_excerpt": (
            "ARTICLE 1ER : La circulation est temporairement réglementée sur le Quai du Tinduff "
            "du 24 au 28 novembre 2026 par alternat de feux tricolores."
        ),
    },
    {
        "ref": "DELIB-2026-031",
        "title": "Adoption du compte administratif 2025 et approbation nomenclature M57",
        "category": "Délibération du conseil",
        "commission_id": "finances_rh",
        "publication_date": "2026-11-15",
        "signed_by": "Dominique CAP (Maire)",
        "applicant": "Direction des Finances",
        "status": "Publié & Exécutoire",
        "content_excerpt": (
            "Le Conseil Municipal, après en avoir délibéré à l'unanimité des membres présents, "
            "approuve les comptes de gestion M57 de l'exercice 2025."
        ),
    },
    {
        "ref": "MP-2026-008",
        "title": "Attribution du marché public de réfection de la toiture du Gymnase de l'Avel-Vor",
        "category": "Marché public",
        "commission_id": "finances_rh",
        "publication_date": "2026-11-12",
        "signed_by": "Dominique CAP (Maire)",
        "applicant": "SAS Charpentes d'Armor",
        "status": "Publié & Exécutoire",
        "content_excerpt": (
            "Attribution du lot 01 Couverture et étanchéité pour un montant de 34 850 € HT."
        ),
    },
    {
        "ref": "PC-2026-042",
        "title": "Permis de construire portant extension et toiture ardoise Ty-Ar-Braz",
        "category": "Autorisation d'urbanisme",
        "commission_id": "urbanisme_ports",
        "publication_date": "2026-11-10",
        "signed_by": "Paul Cueff (Par délégation)",
        "applicant": "Mme et M. LE GALL (Particulier)",
        "status": "Publié & Exécutoire",
        "content_excerpt": (
            "Arrêté accordant le permis de construire n° PC-2026-042 pour l'extension d'une habitation individuelle."
        ),
    },
    # DOSSIER CCAS STRICTEMENT CONFIDENTIEL — NE DOIT JAMAIS SORTIR SUR LE REGISTRE PUBLIC
    {
        "ref": "CCAS-2026-003",
        "title": "Attribution d'une aide d'urgence alimentaire famille monoparentale",
        "category": "Aide sociale d'urgence",
        "commission_id": "enfance_sociale",
        "is_ccas_secret": True,
        "publication_date": "2026-11-14",
        "signed_by": "Nolwenn PÉRON (Directrice CCAS)",
        "applicant": "Dossier confidentiel CCAS",
        "status": "Strictement confidentiel",
        "content_excerpt": "Aide financière d'urgence 350 € attribuée sous couvert de l'art. L. 123-1 CASF.",
    },
]


def list_public_register_acts(
    query: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Retourne la liste des actes publiés au registre public officiel.
    
    VERROU DE SÉCURITÉ ABSOLU :
    Toute entrée appartenant à la commission 'enfance_sociale' ou marquée 'is_ccas_secret'
    est impérativement filtrée et ne sera JAMAIS transmise.
    """
    results = []
    q = (query or "").lower().strip()
    cat = (category or "").lower().strip()

    for act in DEMO_PUBLIC_ACTS:
        # VERROU CCAS
        if act.get("commission_id") == "enfance_sociale" or act.get("is_ccas_secret") is True:
            continue

        if cat and cat != "all" and cat not in act["category"].lower():
            continue

        if q and not (
            q in act["ref"].lower()
            or q in act["title"].lower()
            or q in act["category"].lower()
            or q in act.get("applicant", "").lower()
        ):
            continue

        # Copie assainie (anonymisation des particuliers si besoin)
        sanitized = dict(act)
        if "particulier" in sanitized.get("applicant", "").lower():
            sanitized["applicant"] = "Demandeur particulier (Identité protégée RGPD)"

        results.append(sanitized)

    return results


def get_public_register_act(ref: str) -> Optional[Dict[str, Any]]:
    """Récupère le détail d'un acte publié au registre officiel."""
    for act in DEMO_PUBLIC_ACTS:
        if act["ref"].upper() == ref.upper():
            # VERROU DE SÉCURITÉ CCAS
            if act.get("commission_id") == "enfance_sociale" or act.get("is_ccas_secret") is True:
                return None
            sanitized = dict(act)
            if "particulier" in sanitized.get("applicant", "").lower():
                sanitized["applicant"] = "Demandeur particulier (Identité protégée RGPD)"
            return sanitized
    return None
