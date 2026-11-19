import pytest
from pathlib import Path
from travaux.organization_modules import (
    OrganizationModulesRepository,
    OrganizationCreateInput,
    MODULES_CATALOG,
    CORE_LOCKED_KEYS,
    PRESETS,
)

def test_organization_modules_repository(tmp_path: Path):
    db_file = tmp_path / "test_modules.sqlite3"
    repo = OrganizationModulesRepository(db_file)

    # 1. Default creation
    cfg = repo.get_or_create_default("tenant-test", "Commune Test")
    assert cfg["name"] == "Commune Test"
    assert "core_directory" in cfg["enabled_modules"]
    assert "core_workflows" in cfg["enabled_modules"]
    assert "core_documents" in cfg["enabled_modules"]

    # 2. Update modules with partial list (must keep core locked keys)
    updated = repo.update_modules("tenant-test", ["travaux_terrain"])
    assert "core_directory" in updated["enabled_modules"]
    assert "travaux_terrain" in updated["enabled_modules"]
    assert "urbanisme_ads" not in updated["enabled_modules"]

    # 3. Create new organization
    created = repo.create_organization(OrganizationCreateInput(
        name="Mairie de Plougastel",
        insee_code="29189",
        stratum="3500-15000",
        email_domain="plougastel.fr",
        enabled_modules=PRESETS["commune_rurale"]["modules"]
    ))
    assert created["name"] == "Mairie de Plougastel"
    assert created["insee_code"] == "29189"
    assert "travaux_terrain" in created["enabled_modules"]
    assert "ports_littoral" not in created["enabled_modules"]

    # 4. Check is_module_enabled
    assert repo.is_module_enabled(created["tenant_id"], "core_workflows") is True
    assert repo.is_module_enabled(created["tenant_id"], "ports_littoral") is False
    assert repo.is_module_enabled(created["tenant_id"], "travaux_terrain") is True
