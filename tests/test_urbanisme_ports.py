"""Tests for Urbanisme, Travaux et Ports domain repository and geo features."""
import pytest
from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.urbanisme_ports import (
    UrbanismePortsRepository,
    is_within_plougastel,
    validate_coordinates,
)


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "test.sqlite3")
    r.create_project("tenant-alpha", "PRJ-URB-1", "Permis Centre Bourg", project_id="PRJ-URB-1", commission_id="commission-3")
    r.create_project("tenant-alpha", "PRJ-PORT-1", "Réfection Ponton Tinduff", project_id="PRJ-PORT-1", commission_id="commission-3")
    r.create_project("tenant-beta", "PRJ-BETA-1", "Projet Autre Commune", project_id="PRJ-BETA-1", commission_id="commission-3")
    yield r
    r.close()


@pytest.fixture
def up_repo(repo):
    return UrbanismePortsRepository(repo)


def test_coordinates_validation_and_plougastel_bbox():
    # Valid Plougastel coords: Tinduff [-4.3820, 48.3370]
    lon, lat = validate_coordinates(-4.3820, 48.3370)
    assert lon == -4.3820
    assert lat == 48.3370
    assert is_within_plougastel(lon, lat) is True

    # Valid Earth coords, but outside Plougastel (e.g. Paris [2.3522, 48.8566])
    p_lon, p_lat = validate_coordinates(2.3522, 48.8566)
    assert is_within_plougastel(p_lon, p_lat) is False

    # Invalid non-numeric or out-of-range coordinates
    with pytest.raises(DomainError):
        validate_coordinates("invalid", 48.0)  # type: ignore

    with pytest.raises(DomainError):
        validate_coordinates(-190.0, 48.0)

    with pytest.raises(DomainError):
        validate_coordinates(-4.38, 95.0)


def test_save_and_list_geo_features(up_repo):
    # Save Tinduff port feature
    feat1 = up_repo.save_geo_feature(
        "tenant-alpha",
        "PRJ-PORT-1",
        feature_type="port_ouvrage",
        name="Port du Tinduff — Ponton",
        longitude=-4.3820,
        latitude=48.3370,
        properties={"ouvrage": "ponton_plaisance"},
        feature_id="feat-tinduff",
    )
    assert feat1["id"] == "feat-tinduff"
    assert feat1["feature_type"] == "port_ouvrage"

    # Save Parcelle feature
    feat2 = up_repo.save_geo_feature(
        "tenant-alpha",
        "PRJ-URB-1",
        feature_type="parcelle",
        name="Parcelle Exemple A-12",
        longitude=-4.3680,
        latitude=48.3750,
        properties={"cadastre": "A-12"},
        feature_id="feat-parcelle-12",
    )
    assert feat2["id"] == "feat-parcelle-12"

    # List features for tenant
    all_features = up_repo.list_geo_features("tenant-alpha")
    assert len(all_features) == 2

    # Filter by feature_type
    port_features = up_repo.list_geo_features("tenant-alpha", feature_type="port_ouvrage")
    assert len(port_features) == 1
    assert port_features[0]["id"] == "feat-tinduff"

    # Filter by project_id
    proj_features = up_repo.list_geo_features("tenant-alpha", project_ids=["PRJ-URB-1"])
    assert len(proj_features) == 1
    assert proj_features[0]["id"] == "feat-parcelle-12"

    # Tenant isolation: tenant-beta cannot see tenant-alpha features
    assert len(up_repo.list_geo_features("tenant-beta")) == 0


def test_to_geojson_feature_collection(up_repo):
    up_repo.save_geo_feature(
        "tenant-alpha",
        "PRJ-PORT-1",
        feature_type="port_ouvrage",
        name="Port du Passage",
        longitude=-4.4210,
        latitude=48.3615,
        properties={"cale": True},
    )

    rows = up_repo.list_geo_features("tenant-alpha")
    geojson = up_repo.to_geojson(rows)

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1
    feat = geojson["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Point"
    assert feat["geometry"]["coordinates"] == [-4.4210, 48.3615]
    assert feat["properties"]["name"] == "Port du Passage"
    assert feat["properties"]["cale"] is True


def test_save_and_get_urbanisme_dossier(up_repo):
    checklist = [
        {"id": "pcmi1", "label": "Plan de situation", "checked": True},
        {"id": "pcmi2", "label": "Plan de masse", "checked": False},
    ]

    saved = up_repo.save_urbanisme_dossier(
        "tenant-alpha",
        "PRJ-URB-1",
        parcel_ref="Section B Parcelle 42",
        request_type="permis_construire",
        regulation_source="PLU Zone Ub",
        checklist=checklist,
        advice_status="en_cours",
        follow_up_date="2027-03-01",
    )
    assert saved["parcel_ref"] == "Section B Parcelle 42"
    assert saved["advice_status"] == "en_cours"
    assert len(saved["checklist"]) == 2

    # Retrieve dossier
    retrieved = up_repo.get_urbanisme_dossier("tenant-alpha", "PRJ-URB-1")
    assert retrieved is not None
    assert retrieved["parcel_ref"] == "Section B Parcelle 42"
    assert retrieved["checklist"][0]["checked"] is True

    # Update advice status to favorable
    updated = up_repo.save_urbanisme_dossier(
        "tenant-alpha",
        "PRJ-URB-1",
        parcel_ref="Section B Parcelle 42",
        request_type="permis_construire",
        regulation_source="PLU Zone Ub",
        checklist=checklist,
        advice_status="favorable",
        follow_up_date="2027-03-01",
    )
    assert updated["advice_status"] == "favorable"

    # Non-existent project returns None
    assert up_repo.get_urbanisme_dossier("tenant-alpha", "NON-EXISTENT") is None


def test_port_inspections_crud_and_status(up_repo):
    # Create inspection
    insp1 = up_repo.save_port_inspection(
        "tenant-alpha",
        "PRJ-PORT-1",
        port_name="Port du Tinduff",
        ouvrage_type="Ponton principal",
        inspector="Jean-Yves Maritime",
        inspection_date="2026-11-18",
        condition_rating="degrade",
        observations="Corrosion sur les chaînes de retenue, remplacement à planifier d'urgence.",
        linked_action_id="act-12345",
    )
    assert insp1["port_name"] == "Port du Tinduff"
    assert insp1["condition_rating"] == "degrade"
    assert insp1["linked_action_id"] == "act-12345"

    # List inspections
    inspections = up_repo.list_port_inspections("tenant-alpha", project_id="PRJ-PORT-1")
    assert len(inspections) == 1
    assert inspections[0]["id"] == insp1["id"]

    # Invalid condition rating
    with pytest.raises(DomainError):
        up_repo.save_port_inspection(
            "tenant-alpha",
            "PRJ-PORT-1",
            port_name="Port du Tinduff",
            ouvrage_type="Ponton",
            inspector="Jean-Yves",
            inspection_date="2026-11-18",
            condition_rating="inconnu",  # Invalid
            observations="Test",
        )
