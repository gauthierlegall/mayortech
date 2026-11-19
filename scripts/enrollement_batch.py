#!/usr/bin/env python3
"""
Pipeline d'ingestion massive CSV pour l'enrôlement du personnel communal de Plougastel-Daoulas.
Pôle 1 · Lot 02
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from travaux.config import Settings
from travaux.repository import Repository
from travaux.municipal_directory import MunicipalDirectoryRepository, MunicipalEntryInput


def run_batch_enrollment(csv_path: Path, tenant_id: str, dry_run: bool = True) -> dict:
    if not csv_path.exists():
        print(f"[ERREUR] Le fichier CSV '{csv_path}' est introuvable.", file=sys.stderr)
        sys.exit(1)

    settings = Settings()
    repo = Repository(settings.db_path)
    directory = MunicipalDirectoryRepository(repo)

    results = {
        "file": str(csv_path),
        "tenant_id": tenant_id,
        "mode": "DRY-RUN (Simulation sans écriture)" if dry_run else "APPLY (Ingestion réelle)",
        "total_rows": 0,
        "valid_count": 0,
        "error_count": 0,
        "entries": [],
        "errors": []
    }

    seen_matricules = set()
    seen_emails = set()

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            results["total_rows"] += 1
            matricule = row.get("matricule", "").strip()
            email = row.get("email", "").strip().lower()

            # Detection of duplicates within CSV
            if matricule in seen_matricules:
                results["errors"].append({"line": idx, "matricule": matricule, "error": "Matricule en doublon dans le fichier CSV"})
                results["error_count"] += 1
                continue
            if email in seen_emails:
                results["errors"].append({"line": idx, "email": email, "error": "Email en doublon dans le fichier CSV"})
                results["error_count"] += 1
                continue

            try:
                delegation_sig = str(row.get("delegation_signature", "")).strip().lower() in ("true", "1", "yes", "oui")
                entry_data = MunicipalEntryInput(
                    matricule=matricule,
                    nom=row.get("nom", "").strip(),
                    prenom=row.get("prenom", "").strip(),
                    email=email,
                    statut=row.get("statut", "").strip(),
                    direction=row.get("direction", "").strip(),
                    poste=row.get("poste", "").strip(),
                    commission_id=row.get("commission_id", "").strip() or "commission-3",
                    niveau=int(row.get("niveau", "1")),
                    role=row.get("role", "reader").strip(),
                    delegation_signature=delegation_sig,
                    arrete_delegation=row.get("arrete_delegation", "").strip() or None,
                    suppleant_id=row.get("suppleant_id", "").strip() or None,
                    telephone=row.get("telephone", "").strip() or None,
                )
                seen_matricules.add(matricule)
                seen_emails.add(email)

                if not dry_run:
                    entry = directory.create_entry(tenant_id, entry_data, actor_id="script-enrollement-batch")
                    results["entries"].append({"line": idx, "id": entry["id"], "matricule": matricule, "email": email, "statut": "inséré"})
                else:
                    results["entries"].append({"line": idx, "matricule": matricule, "email": email, "statut": "valide (prêt)"})
                results["valid_count"] += 1

            except Exception as err:
                results["error_count"] += 1
                results["errors"].append({"line": idx, "matricule": matricule, "error": str(err)})

    return results


def main():
    parser = argparse.ArgumentParser(description="Ingestion massive CSV pour l'enrôlement municipal.")
    parser.add_argument("--file", "-f", required=True, help="Chemin vers le fichier CSV normalisé")
    parser.add_argument("--tenant", "-t", default="public-fiction", help="ID du tenant cible (défaut: public-fiction)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Vérifie le format sans écrire dans la base")
    group.add_argument("--apply", action="store_true", help="Insère les agents dans l'annuaire municipal")

    args = parser.parse_args()
    res = run_batch_enrollment(Path(args.file), args.tenant, dry_run=args.dry_run)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if res["error_count"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
