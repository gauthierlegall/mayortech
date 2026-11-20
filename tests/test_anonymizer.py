"""Tests unitaires et d'intégration pour le service d'Anonymisation RGPD (Lot v3.3).

Vérifie :
- Détection déterministe des entités nominatives (noms, adresses, téléphones, courriels, cadastre, IBAN)
- Occultation sélective selon l'Ordonnance n° 2021-1310 du 7 octobre 2021
- Conservation de l'intégrité SHA-256 de l'original et scellement de la version publiable
- Endpoints API FastAPI /api/v1/anonymizer/detect et /api/v1/anonymizer/apply
"""

import hashlib
import pytest
from starlette.testclient import TestClient

from travaux.anonymizer import (
    LEGAL_FRAMEWORK_NOTICE,
    anonymize_text,
    detect_personal_data,
)
from travaux.api import create_app
from travaux.config import Settings


SAMPLE_ACT_TEXT = """RÉPUBLIQUE FRANÇAISE
VILLE DE PLOUGASTEL-DAOULAS
Direction Générale des Services · Pôle Aménagement

Arrêté Municipal n° PC-2026-042

Vu la demande déposée le 17/11/2026 par M. & Mme Tanguy KERVADEC,
demeurant 14 Chemin de Ty-Ar-Braz · 29470 Plougastel-Daoulas,
contact joignable au 02 98 37 57 57 ou par courriel tanguy.kervadec@orange.fr,
concernant la parcelle cadastrée section AB n° 142.

Règlement des frais de voirie par virement IBAN FR76 3000 4000 5000 6000 7000 123.

ARTICLE 1ER : Les travaux déclarés sous le formulaire Cerfa 13406*12 numéro PC-2026-042
portant sur la rénovation de toiture en ardoise naturelle et extension de 38 m² sont AUTORISÉS.

ARTICLE 2 : Le présent arrêté est transmis au contrôle de légalité (@CTES) et certifié exécutoire.
"""


def test_detect_personal_data():
    entities = detect_personal_data(SAMPLE_ACT_TEXT)
    assert len(entities) >= 5

    categories = {e["category"] for e in entities}
    assert "name" in categories
    assert "address" in categories
    assert "phone" in categories
    assert "email" in categories
    assert "cadastre" in categories
    assert "bank" in categories

    # Vérification des valeurs extraites
    name_entity = next(e for e in entities if e["category"] == "name")
    assert "Tanguy KERVADEC" in name_entity["original_value"]
    assert name_entity["suggested_replacement"] == "[NOM OCCULTÉ RGPD]"

    email_entity = next(e for e in entities if e["category"] == "email")
    assert email_entity["original_value"] == "tanguy.kervadec@orange.fr"

    phone_entity = next(e for e in entities if e["category"] == "phone")
    assert "02 98 37 57 57" in phone_entity["original_value"]

    cadastre_entity = next(e for e in entities if e["category"] == "cadastre")
    assert "section AB n° 142" in cadastre_entity["original_value"]


def test_anonymize_text_all_default():
    result = anonymize_text(SAMPLE_ACT_TEXT)

    assert result["detected_count"] >= 5
    assert result["redacted_count"] == result["detected_count"]

    anon_text = result["anonymized_text"]
    assert "Tanguy KERVADEC" not in anon_text
    assert "tanguy.kervadec@orange.fr" not in anon_text
    assert "02 98 37 57 57" not in anon_text
    assert "FR76 3000" not in anon_text
    assert "[NOM OCCULTÉ RGPD]" in anon_text
    assert "[COURRIEL OCCULTÉ RGPD]" in anon_text

    # Vérifie que les données institutionnelles ne sont JAMAIS biffées
    assert "VILLE DE PLOUGASTEL-DAOULAS" in anon_text
    assert "RÉPUBLIQUE FRANÇAISE" in anon_text
    assert "PC-2026-042" in anon_text
    assert "ARTICLE 1ER" in anon_text

    # Doubles empreintes SHA-256
    expected_orig_sha = hashlib.sha256(SAMPLE_ACT_TEXT.encode("utf-8")).hexdigest()
    expected_anon_sha = hashlib.sha256(anon_text.encode("utf-8")).hexdigest()
    assert result["original_sha256"] == expected_orig_sha
    assert result["anonymized_sha256"] == expected_anon_sha
    assert result["original_sha256"] != result["anonymized_sha256"]

    # Cadre juridique
    assert "2021-1310" in result["legal_framework"]["ordonnance"]
    assert "L. 2131-1" in result["legal_framework"]["cgct_article"]


def test_anonymize_selective():
    entities = detect_personal_data(SAMPLE_ACT_TEXT)
    # L'utilisateur choisit d'occulter uniquement le nom et l'email, en gardant le reste
    name_entity = next(e for e in entities if e["category"] == "name")
    email_entity = next(e for e in entities if e["category"] == "email")

    selected_ids = [name_entity["id"], email_entity["id"]]
    result = anonymize_text(SAMPLE_ACT_TEXT, selected_ids=selected_ids, entities=entities)

    assert result["redacted_count"] == 2
    anon_text = result["anonymized_text"]
    assert "Tanguy KERVADEC" not in anon_text
    assert "tanguy.kervadec@orange.fr" not in anon_text
    # Les autres mentions restent visibles
    assert "02 98 37 57 57" in anon_text
    assert "section AB n° 142" in anon_text


def test_anonymizer_http_api(tmp_path):
    settings = Settings(
        mode="demo",
        db_path=tmp_path / "anon_test.sqlite3",
    )
    app = create_app(settings)
    client = TestClient(app)

    # 1. Détection via POST /api/v1/anonymizer/detect
    res_detect = client.post(
        "/api/v1/anonymizer/detect",
        json={"text": SAMPLE_ACT_TEXT},
        headers={"X-Requested-With": "Travaux"},
    )
    assert res_detect.status_code == 200
    data_detect = res_detect.json()
    assert data_detect["detected_count"] >= 5
    assert len(data_detect["entities"]) >= 5

    # 2. Application via POST /api/v1/anonymizer/apply
    res_apply = client.post(
        "/api/v1/anonymizer/apply",
        json={"text": SAMPLE_ACT_TEXT},
        headers={"X-Requested-With": "Travaux"},
    )
    assert res_apply.status_code == 200
    data_apply = res_apply.json()
    assert data_apply["redacted_count"] >= 5
    assert "[NOM OCCULTÉ RGPD]" in data_apply["anonymized_text"]
    assert "Ordonnance n° 2021-1310" in data_apply["legal_framework"]["ordonnance"]
