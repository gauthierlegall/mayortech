"""Unit tests for Séances et Instances Spécialisées (Lot 5 MayorTech)."""

import pytest

from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.seances_instances import (
    SeancesInstancesRepository,
    format_deliberation_ref,
)


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "seances_test.sqlite3"
    return Repository(str(db_path))


@pytest.fixture
def seances_repo(repo):
    return SeancesInstancesRepository(repo)


def test_format_deliberation_ref():
    ref1 = format_deliberation_ref("2027-03-15", "commission-3", 1)
    assert ref1 == "DELIB-2027-COM3-01"

    ref2 = format_deliberation_ref("2027-06-20", "cao", 4)
    assert ref2 == "DELIB-2027-CAO-04"


def test_specialized_instances_auto_seed(seances_repo):
    tenant_id = "tenant-plougastel"
    instances = seances_repo.list_specialized_instances(tenant_id)
    assert len(instances) == 3
    ids = {i["id"] for i in instances}
    assert ids == {"cao", "ccspl", "ccid"}

    cao = seances_repo.get_specialized_instance(tenant_id, "cao")
    assert cao["instance_type"] == "CAO"
    assert "Mégalis" in cao["config"]["platform"]

    ccspl = seances_repo.get_specialized_instance(tenant_id, "ccspl")
    assert ccspl["instance_type"] == "CCSPL"
    assert len(ccspl["config"]["delegations"]) >= 2

    ccid = seances_repo.get_specialized_instance(tenant_id, "ccid")
    assert ccid["instance_type"] == "CCID"
    assert ccid["config"]["cadastral_commissaires"] == 8


def test_session_lifecycle_and_agenda(seances_repo, repo):
    tenant_id = "tenant-plougastel"

    # Create dummy project
    proj = repo.create_project(
        tenant_id,
        "TIN-001",
        "Aménagement du Tinduff",
        status="in_progress",
        commission_id="commission-3",
        specialization="travaux",
    )
    proj_id = proj["id"]

    # 1. Create session
    session = seances_repo.create_session(
        tenant_id=tenant_id,
        commission_id="commission-3",
        title="Commission Urbanisme & Travaux - Séance ordinaire",
        session_date="2027-03-20",
        session_time="14:30",
        location="Salle du Conseil, Mairie de Plougastel",
        quorum_required=3,
    )
    session_id = session["id"]
    assert session["status"] == "draft"
    assert session["quorum_present"] == 0

    # 2. Add agenda items
    seances_repo.add_agenda_item(
        tenant_id=tenant_id,
        session_id=session_id,
        title="Approbation du plan de réfection du Tinduff",
        project_id=proj_id,
        rapporteur="Jean-Luc Le Gall",
    )
    seances_repo.add_agenda_item(
        tenant_id=tenant_id,
        session_id=session_id,
        title="Point divers - Éclairage public économe",
        rapporteur="Marie Le Meur",
    )

    s_updated = seances_repo.get_session(tenant_id, session_id)
    assert len(s_updated["agenda_items"]) == 2
    item1 = s_updated["agenda_items"][0]
    item2 = s_updated["agenda_items"][1]
    assert item1["item_order"] == 1
    assert item1["deliberation_ref"] == "DELIB-2027-COM3-01"
    assert item2["item_order"] == 2
    assert item2["deliberation_ref"] == "DELIB-2027-COM3-02"

    # 3. Reorder agenda items
    seances_repo.reorder_agenda_items(
        tenant_id=tenant_id,
        session_id=session_id,
        ordered_item_ids=[item2["id"], item1["id"]],
    )
    s_reordered = seances_repo.get_session(tenant_id, session_id)
    assert s_reordered["agenda_items"][0]["id"] == item2["id"]
    assert s_reordered["agenda_items"][0]["item_order"] == 1
    assert s_reordered["agenda_items"][1]["id"] == item1["id"]
    assert s_reordered["agenda_items"][1]["item_order"] == 2

    # 4. Record attendance
    seances_repo.update_attendance(
        tenant_id=tenant_id,
        session_id=session_id,
        attendances=[
            {"member_name": "Jean-Luc Le Gall", "member_role": "titulaire", "status": "present"},
            {"member_name": "Marie Le Meur", "member_role": "titulaire", "status": "present"},
            {"member_name": "Yvon Kervella", "member_role": "titulaire", "status": "pouvoir", "proxy_to": "Jean-Luc Le Gall"},
            {"member_name": "Sophie Tanguy", "member_role": "suppleant", "status": "absent_excuse"},
        ],
    )
    s_att = seances_repo.get_session(tenant_id, session_id)
    assert s_att["quorum_present"] == 3  # 2 present + 1 pouvoir
    assert len(s_att["attendances"]) == 4

    # 5. Record votes on item
    seances_repo.record_item_vote(
        tenant_id=tenant_id,
        session_id=session_id,
        item_id=item1["id"],
        vote_result="favorable",
        votes_for=3,
        votes_against=0,
        votes_abstention=0,
        official_decision="Avis favorable unanime de la commission",
    )
    s_voted = seances_repo.get_session(tenant_id, session_id)
    target_item = next(it for it in s_voted["agenda_items"] if it["id"] == item1["id"])
    assert target_item["vote_result"] == "favorable"
    assert target_item["votes_for"] == 3


def test_decidim_close_meeting_and_cryptographic_seal(seances_repo, repo):
    tenant_id = "tenant-plougastel"
    proj = repo.create_project(
        tenant_id,
        "AVE-001",
        "Passerelle piétonne Avel Vor",
        status="in_progress",
        commission_id="commission-3",
        specialization="travaux",
    )
    session = seances_repo.create_session(
        tenant_id=tenant_id,
        commission_id="commission-3",
        title="Séance Spéciale Travaux",
        session_date="2027-04-10",
        session_time="10:00",
        quorum_required=3,
    )
    session_id = session["id"]

    seances_repo.add_agenda_item(
        tenant_id=tenant_id,
        session_id=session_id,
        title="Validation avant-projet passerelle",
        project_id=proj["id"],
        rapporteur="Jean-Luc Le Gall",
    )

    # Quorum fail check
    seances_repo.update_attendance(
        tenant_id=tenant_id,
        session_id=session_id,
        attendances=[
            {"member_name": "Jean-Luc Le Gall", "status": "present"},
            {"member_name": "Marie Le Meur", "status": "absent"},
        ],
    )
    with pytest.raises(DomainError) as exc_info:
        seances_repo.close_session(tenant_id, session_id, closed_by="Directeur Général des Services")
    assert exc_info.value.code == "quorum_not_reached"

    # Satisfy quorum
    seances_repo.update_attendance(
        tenant_id=tenant_id,
        session_id=session_id,
        attendances=[
            {"member_name": "Jean-Luc Le Gall", "status": "present"},
            {"member_name": "Marie Le Meur", "status": "present"},
            {"member_name": "Yvon Kervella", "status": "present"},
        ],
    )

    # Close session
    closed_session = seances_repo.close_session(
        tenant_id, session_id, closed_by="Directeur Général des Services"
    )
    assert closed_session["status"] == "closed"
    assert len(closed_session["pv_hash"]) == 64  # SHA-256
    assert closed_session["closed_by"] == "Directeur Général des Services"

    # Verify project snapshot is preserved
    item = closed_session["agenda_items"][0]
    assert item["project_version_snapshot"]["title"] == "Passerelle piétonne Avel Vor"
    assert item["project_version_snapshot"]["category"] == "travaux"

    # Invariants: Mutating closed session must be rejected
    with pytest.raises(DomainError) as exc_item:
        seances_repo.add_agenda_item(tenant_id, session_id, "Nouveau point interdit")
    assert exc_item.value.code == "session_closed"

    with pytest.raises(DomainError) as exc_att:
        seances_repo.update_attendance(tenant_id, session_id, [])
    assert exc_att.value.code == "session_closed"


def test_specialized_records_cao_ccspl_ccid(seances_repo):
    tenant_id = "tenant-plougastel"

    # 1. CAO Tender
    rec_cao = seances_repo.create_specialized_record(
        tenant_id=tenant_id,
        instance_id="cao",
        record_type="cao_marche",
        reference="MEGALIS-BRETAGNE-2027-T08",
        title="Marché public de voirie communale - Lot 1 Enrobés",
        details={
            "platform": "Mégalis Bretagne",
            "lots_count": 3,
            "bids_received": 4,
            "winning_bidder": "Eurovia Bretagne",
            "amount_eur": 284000,
        },
    )
    assert rec_cao["reference"] == "MEGALIS-BRETAGNE-2027-T08"
    assert rec_cao["details"]["amount_eur"] == 284000

    # 2. CCSPL Report
    rec_ccspl = seances_repo.create_specialized_record(
        tenant_id=tenant_id,
        instance_id="ccspl",
        record_type="ccspl_rapport",
        reference="RAPPORT-DSP-EAU-2026",
        title="Rapport annuel sur le prix et la qualité du service public d'eau potable",
        details={
            "service": "Eau potable",
            "delegataire": "Eau du Ponant",
            "conformite_bacteriologique_pct": 100,
            "taux_rendement_reseau_pct": 84.5,
        },
    )
    assert rec_ccspl["reference"] == "RAPPORT-DSP-EAU-2026"

    # 3. CCID Cadastral Valuation
    rec_ccid = seances_repo.create_specialized_record(
        tenant_id=tenant_id,
        instance_id="ccid",
        record_type="ccid_evaluation",
        reference="CCID-2027-PARCELLE-AD-14",
        title="Évaluation de la valeur locative - Nouveau local d'activité ZA Ty-Ar-Menez",
        details={
            "section": "AD",
            "parcelle": "14",
            "surface_m2": 420,
            "categorie_locaux": "Commerce",
            "vl_retenue_eur": 38500,
        },
    )
    assert rec_ccid["reference"] == "CCID-2027-PARCELLE-AD-14"

    # List records
    all_recs = seances_repo.list_specialized_records(tenant_id)
    assert len(all_recs) == 3

    cao_recs = seances_repo.list_specialized_records(tenant_id, instance_id="cao")
    assert len(cao_recs) == 1
    assert cao_recs[0]["reference"] == "MEGALIS-BRETAGNE-2027-T08"
