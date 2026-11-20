"""Tests unitaires pour l'Intelligence Juridique, Délégations, Délais et Registre Public."""

import json
import zipfile
import io
from datetime import date
import pytest
from fastapi.testclient import TestClient

from travaux.intelligence_juridique import (
    evaluate_delegation_rule,
    format_official_signature_block,
    is_french_business_day,
    add_business_days,
    compute_legal_timeline,
    generate_proof_bundle_zip,
    list_public_register_acts,
    get_public_register_act,
)
from travaux.api import create_app
from travaux.config import Settings


def test_delegation_threshold_under_10k():
    """Vérifie qu'un marché <= 10 000 € HT ne requiert pas le Maire."""
    result = evaluate_delegation_rule(circuit_type="marche", amount_ht=7500.0)
    assert result["requires_mayor"] is False
    assert result["threshold_applied"] is True
    assert "Seuil ≤ 10 000 € HT" in result["rule_label"]
    assert "suffisant" in result["rule_label"]


def test_delegation_threshold_over_10k():
    """Vérifie qu'un marché > 10 000 € HT escalade vers le Maire."""
    result = evaluate_delegation_rule(circuit_type="marche", amount_ht=34850.0)
    assert result["requires_mayor"] is True
    assert result["threshold_applied"] is True
    assert "Seuil > 10 000 € HT" in result["rule_label"]
    assert "Maire requise" in result["rule_label"]


def test_signature_block_normal_and_substitution():
    """Vérifie la mention de signature officielle normale et avec suppléant en cas d'absence."""
    # Normal
    normal = format_official_signature_block("Maire", delegation_active=False)
    assert "Dominique CAP" in normal["signatory_name"]
    assert "Pour le Maire de Plougastel-Daoulas," in normal["formula"]

    # Suppléance pour Maire empêché
    suppleant = format_official_signature_block(
        signatory_title="Maire",
        delegation_active=True,
        substitute_name="Loïc Kerbrat",
        substitute_role="1er Adjoint délégué aux Travaux",
        delegation_order_ref="ARR-2026-DEL-042",
    )
    assert "Loïc Kerbrat" in suppleant["signatory_name"]
    assert "Pour le Maire empêché" in suppleant["formula"]
    assert "ARR-2026-DEL-042" in suppleant["legal_mention"]


def test_french_holidays_and_business_days():
    """Vérifie le calendrier officiel français 2026."""
    # 1er Mai 2026 (Vendredi férié)
    assert is_french_business_day(date(2026, 5, 1)) is False
    # 2 Mai 2026 (Samedi)
    assert is_french_business_day(date(2026, 5, 2)) is False
    # 3 Mai 2026 (Dimanche)
    assert is_french_business_day(date(2026, 5, 3)) is False
    # 4 Mai 2026 (Lundi ouvré)
    assert is_french_business_day(date(2026, 5, 4)) is True

    # 3 jours ouvrés à partir du 30 avril 2026 (Jeudi) -> Ven 1er mai (férié), Sam 2, Dim 3, Lun 4 (1), Mar 5 (2), Mer 6 (3)
    deadline = add_business_days(date(2026, 4, 30), 3)
    assert deadline == date(2026, 5, 6)


def test_legal_timeline_and_suspension():
    """Vérifie le calcul des délais légaux, la suspension et l'alerte tacite J-7."""
    # Calcul normal sans suspension
    tl = compute_legal_timeline(
        start_date_iso="2026-11-01",
        duration_days=30,
        reference_date_iso="2026-11-25",
    )
    assert tl["is_suspended"] is False
    assert tl["days_remaining"] == 6  # 1er déc - 25 nov = 6 jours
    assert tl["is_tacit_approaching"] is True
    assert "J-6 avant décision tacite" in tl["status_label"]

    # Suspension pour pièce manquante
    tl_susp = compute_legal_timeline(
        start_date_iso="2026-11-01",
        duration_days=60,
        suspended_date_iso="2026-11-12",
        reference_date_iso="2026-11-20",
    )
    assert tl_susp["is_suspended"] is True
    assert "Délai suspendu le 12/11/2026" in tl_susp["status_label"]
    assert tl_susp["effective_deadline"] is None


def test_proof_bundle_generation():
    """Vérifie la structure et les empreintes SHA-256 du dossier de preuve .zip."""
    dossier = {
        "id": "MP-2026-008",
        "title": "Attribution toiture Avel-Vor",
        "applicant": "SAS Charpentes d'Armor",
        "previewArticle": "ARTICLE 1ER : Le marché est attribué.",
        "auditTrail": [
            {
                "timestamp": "2026-11-12T14:00:00Z",
                "author": "Valérie Gestin",
                "role": "DGA Finances",
                "stepName": "Visa financier M57",
                "comment": "Engagement conforme",
                "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            }
        ],
    }
    zip_bytes = generate_proof_bundle_zip(dossier, "Ville de Plougastel-Daoulas")
    assert len(zip_bytes) > 500

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "01_acte_municipal.html" in namelist
        assert "02_journal_audit_visas.html" in namelist
        assert "03_manifest_sha256.json" in namelist
        assert "pieces_justificatives/annexe_descriptive.txt" in namelist

        manifest_data = json.loads(zf.read("03_manifest_sha256.json").decode("utf-8"))
        assert manifest_data["dossier_id"] == "MP-2026-008"
        assert "01_acte_municipal.html" in manifest_data["files"]
        assert "02_journal_audit_visas.html" in manifest_data["files"]


def test_public_register_ccas_hermetic_seal():
    """Vérifie l'étanchéité absolue du registre public : 0 fuite CCAS."""
    acts = list_public_register_acts()
    refs = [a["ref"] for a in acts]

    # Les actes normaux doivent être présents
    assert "ARR-2026-019" in refs
    assert "DELIB-2026-031" in refs
    assert "MP-2026-008" in refs
    assert "PC-2026-042" in refs

    # Le dossier CCAS ne DOIT JAMAIS être dans la liste publique
    assert "CCAS-2026-003" not in refs
    for a in acts:
        assert a.get("commission_id") != "enfance_sociale"
        assert a.get("is_ccas_secret") is not True

    # Vérification accès direct par ref : doit renvoyer None
    assert get_public_register_act("CCAS-2026-003") is None

    # Anonymisation des particuliers
    pc_act = get_public_register_act("PC-2026-042")
    assert pc_act is not None
    assert "LE GALL" not in pc_act["applicant"]
    assert "Identité protégée RGPD" in pc_act["applicant"]


def test_api_public_register_and_proof_bundle(tmp_path):
    """Vérifie les routes API via TestClient."""
    settings = Settings(db_path=tmp_path / "test_travaux.sqlite3")
    app = create_app(settings)
    client = TestClient(app)

    # 1. Registre public (pas besoin d'auth)
    res = client.get("/api/v1/public/registre")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 4
    for item in data:
        assert item["ref"] != "CCAS-2026-003"

    # 2. Détail acte public
    res_act = client.get("/api/v1/public/registre/ARR-2026-019")
    assert res_act.status_code == 200
    assert res_act.json()["ref"] == "ARR-2026-019"

    # 3. Tentative accès acte CCAS via API publique -> 404
    res_ccas = client.get("/api/v1/public/registre/CCAS-2026-003")
    assert res_ccas.status_code == 404
