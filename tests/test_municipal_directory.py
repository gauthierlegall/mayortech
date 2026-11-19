import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from travaux.config import Settings
from travaux.repository import Repository
from travaux.api import create_app
from travaux.municipal_directory import MunicipalDirectoryRepository, MunicipalEntryInput, MunicipalEntryUpdate, MunicipalDelegationInput, JoinDecisionInput


@pytest.fixture
def test_app_and_client(tmp_path):
    db_file = tmp_path / "test_municipal.sqlite3"
    settings = Settings(
        mode="demo",
        db_path=db_file,
        tenant_id="test-plougastel",
        password_hash="test-hash",
        auth_mode="password"
    )
    app = create_app(settings)
    client = TestClient(app, base_url="http://localhost")
    return app, client, settings


def test_directory_seed_and_list(test_app_and_client):
    app, client, settings = test_app_and_client
    directory: MunicipalDirectoryRepository = app.state.municipal_directory
    
    entries = directory.list_entries(settings.tenant_id)
    assert len(entries) >= 15
    # Verify Mayor and DGS are present
    emails = {e["email"] for e in entries}
    assert "maire@ville-plougastel.bzh" in emails
    assert "dgs@ville-plougastel.bzh" in emails
    
    # Check level 4 and level 5
    maire = next(e for e in entries if e["email"] == "maire@ville-plougastel.bzh")
    assert maire["niveau"] == 4
    assert maire["role"] == "admin"
    assert maire["delegation_signature"] is True

    dgs = next(e for e in entries if e["email"] == "dgs@ville-plougastel.bzh")
    assert dgs["niveau"] == 5
    assert dgs["role"] == "admin"


def test_directory_create_update_revoke(test_app_and_client):
    app, client, settings = test_app_and_client
    directory: MunicipalDirectoryRepository = app.state.municipal_directory

    new_agent = MunicipalEntryInput(
        matricule="AGT-999",
        nom="Morvan",
        prenom="Loïc",
        email="loic.morvan@ville-plougastel.bzh",
        statut="titulaire",
        direction="Services Techniques",
        poste="Technicien Éclairage Public",
        commission_id="commission-3",
        niveau=2,
        role="editor",
        delegation_signature=False
    )
    created = directory.create_entry(settings.tenant_id, new_agent)
    assert created["matricule"] == "AGT-999"
    assert created["nom"] == "MORVAN"
    assert created["prenom"] == "Loïc"
    assert created["active"] is True

    # Update
    updated = directory.update_entry(settings.tenant_id, created["id"], MunicipalEntryUpdate(niveau=3, poste="Chef d'Équipe Éclairage"))
    assert updated["niveau"] == 3
    assert updated["poste"] == "Chef d'Équipe Éclairage"

    # Revoke
    revoked = directory.revoke_entry(settings.tenant_id, created["id"])
    assert revoked["active"] is False

    # Check that active_only filter excludes revoked
    active_list = directory.list_entries(settings.tenant_id, active_only=True)
    assert not any(e["id"] == created["id"] for e in active_list)


def test_delegation_lifecycle(test_app_and_client):
    app, client, settings = test_app_and_client
    directory: MunicipalDirectoryRepository = app.state.municipal_directory

    entries = directory.list_entries(settings.tenant_id)
    elu_travaux = next(e for e in entries if e["matricule"] == "ELU-002")
    dst = next(e for e in entries if e["matricule"] == "AGT-010")

    del_input = MunicipalDelegationInput(
        titulaire_id=elu_travaux["id"],
        suppleant_id=dst["id"],
        scope="signature",
        start_date="2026-11-20",
        end_date="2026-11-30",
        arrete_reference="Arrêté Municipal 2026-SUPP-12"
    )
    delegation = directory.create_delegation(settings.tenant_id, del_input)
    assert delegation["scope"] == "signature"
    assert delegation["active"] is True
    assert "LE GALL" in delegation["titulaire"]
    assert "DST" in delegation["suppleant"]

    all_dels = directory.list_delegations(settings.tenant_id)
    assert len(all_dels) >= 1
    assert any(d["id"] == delegation["id"] for d in all_dels)


def test_join_request_flow(test_app_and_client):
    app, client, settings = test_app_and_client

    # 1. Invalid code rejection
    resp_bad = client.post(
        "/api/v1/organization/join-requests",
        headers={"X-Requested-With": "Travaux"},
        json={
            "email": "candidat.test@ville-plougastel.bzh",
            "nom": "Kermarrec",
            "prenom": "Anna",
            "poste_souhaite": "Instructrice ADS",
            "code_organisation": "WRONG-CODE"
        }
    )
    assert resp_bad.status_code == 422
    assert "Code confidentiel municipal invalide" in resp_bad.json()["error"]["message"]

    # 2. Valid code submission
    resp_ok = client.post(
        "/api/v1/organization/join-requests",
        headers={"X-Requested-With": "Travaux"},
        json={
            "email": "candidat.test@ville-plougastel.bzh",
            "nom": "Kermarrec",
            "prenom": "Anna",
            "poste_souhaite": "Instructrice ADS",
            "code_organisation": "PLOUGASTEL-2026"
        }
    )
    assert resp_ok.status_code == 201
    join_data = resp_ok.json()
    assert join_data["status"] == "pending"
    assert join_data["nom"] == "KERMARREC"

    # 3. Decision by DGS / Admin
    directory: MunicipalDirectoryRepository = app.state.municipal_directory
    decided = directory.decide_join_request(
        settings.tenant_id,
        join_data["id"],
        JoinDecisionInput(
            decision="approve",
            assigned_commission="commission-3",
            assigned_level=2,
            assigned_role="editor",
            reason="Profil validé par la DGS pour l'urbanisme"
        ),
        decided_by="DGS"
    )
    assert decided["status"] == "approved"

    # Verify agent was automatically added to directory
    agent = next(e for e in directory.list_entries(settings.tenant_id) if e["email"] == "candidat.test@ville-plougastel.bzh")
    assert agent["nom"] == "KERMARREC"
    assert agent["commission_id"] == "commission-3"
    assert agent["niveau"] == 2


def test_organigram_topology_and_export(test_app_and_client):
    app, client, settings = test_app_and_client

    # 1. Topology
    res_topo = client.get("/api/v1/municipal/organigram/topology")
    assert res_topo.status_code == 200
    topo = res_topo.json()
    assert topo["city"] == "Ville de Plougastel-Daoulas"
    assert topo["total_nodes"] >= 10
    assert any(n["id"] == "node-maire" for n in topo["nodes"])
    assert any(n["id"] == "node-dgs" for n in topo["nodes"])
    assert any(n["id"] == "node-commission-3" for n in topo["nodes"])

    # 2. SVG Export
    res_svg = client.post(
        "/api/v1/municipal/organigram/export",
        headers={"X-Requested-With": "Travaux"},
        json={"format": "svg"}
    )
    assert res_svg.status_code == 200
    assert res_svg.headers["content-type"] == "image/svg+xml"
    assert "<svg" in res_svg.text
    assert "PLOUGASTEL" in res_svg.text

    # 3. HTML Export
    res_html = client.post(
        "/api/v1/municipal/organigram/export",
        headers={"X-Requested-With": "Travaux"},
        json={"format": "html"}
    )
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    assert "<!DOCTYPE html>" in res_html.text
