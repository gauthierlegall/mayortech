"""Unit tests for Action sociale, enfance et jeunesse (Lot 4)."""

import pytest

from travaux.enfance_sociale import (
    EnfanceSocialeRepository,
    calculate_canteen_bracket,
    shift_iso_date,
    shift_year_string,
)
from travaux.repository import Repository


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "test_social.sqlite3")
    yield r
    r.close()


@pytest.fixture
def es_repo(repo):
    return EnfanceSocialeRepository(repo)


def test_calculate_canteen_bracket():
    # T1: QF <= 450
    t1 = calculate_canteen_bracket(350)
    assert t1["bracket"] == "T1"
    assert t1["meal_rate_cents"] == 100
    assert t1["commune_subsidy_cents"] == 395

    # T2: 451 to 750
    t2 = calculate_canteen_bracket(600)
    assert t2["bracket"] == "T2"
    assert t2["meal_rate_cents"] == 215

    # T3: 751 to 1100
    t3 = calculate_canteen_bracket(950)
    assert t3["bracket"] == "T3"
    assert t3["meal_rate_cents"] == 320

    # T4: 1101 to 1600
    t4 = calculate_canteen_bracket(1400)
    assert t4["bracket"] == "T4"
    assert t4["meal_rate_cents"] == 410

    # T5: > 1600
    t5 = calculate_canteen_bracket(2200)
    assert t5["bracket"] == "T5"
    assert t5["meal_rate_cents"] == 495
    assert t5["commune_subsidy_cents"] == 0

    # Edge cases
    assert calculate_canteen_bracket(0)["bracket"] == "T1"
    assert calculate_canteen_bracket(-50)["bracket"] == "T1"
    assert calculate_canteen_bracket(450)["bracket"] == "T1"
    assert calculate_canteen_bracket(451)["bracket"] == "T2"
    assert calculate_canteen_bracket(750)["bracket"] == "T2"
    assert calculate_canteen_bracket(751)["bracket"] == "T3"


def test_shift_helpers():
    assert shift_year_string("2026-2027") == "2027-2028"
    assert shift_year_string("2026-2027", delta_years=2) == "2028-2029"
    assert shift_year_string("2027") == "2028"

    assert shift_iso_date("2026-09-01") == "2027-09-01"
    assert shift_iso_date("2026-06-30", delta_years=2) == "2028-06-30"


def test_campaign_crud(es_repo):
    tenant = "plougastel-test"
    camp = es_repo.create_campaign(
        tenant_id=tenant,
        campaign_type="rentree_scolaire",
        title="Inscriptions scolaires et périscolaires 2026-2027",
        school_year="2026-2027",
        start_date="2026-05-01",
        end_date="2026-07-15",
        config={"schools": ["École des Alizés", "École du Goëland"]},
    )
    assert camp["id"].startswith("CMP-")
    assert camp["status"] == "active"
    assert camp["config"]["schools"] == ["École des Alizés", "École du Goëland"]

    fetched = es_repo.get_campaign(tenant, camp["id"])
    assert fetched is not None
    assert fetched["title"] == camp["title"]

    all_camps = es_repo.list_campaigns(tenant)
    assert len(all_camps) == 1
    assert all_camps[0]["id"] == camp["id"]


def test_campaign_dossiers(es_repo):
    tenant = "plougastel-test"
    camp = es_repo.create_campaign(
        tenant_id=tenant,
        campaign_type="rentree_scolaire",
        title="Rentrée 2026-2027",
        school_year="2026-2027",
        start_date="2026-05-01",
        end_date="2026-07-15",
    )

    d1 = es_repo.create_campaign_dossier(
        tenant_id=tenant,
        campaign_id=camp["id"],
        family_ref="FAM-29470-01",
        beneficiary_name="Mme Le Gall",
        child_name="Erwan Le Gall",
        school_name="École des Alizés",
        quotient_familial=420,  # Should give T1
        details={"meals_per_week": 4, "garderie_matin": True},
    )
    assert d1["id"].startswith("DOS-")
    assert d1["rate_bracket"] == "T1"
    assert d1["status"] == "en_instruction"

    d2 = es_repo.create_campaign_dossier(
        tenant_id=tenant,
        campaign_id=camp["id"],
        family_ref="FAM-29470-02",
        beneficiary_name="M. Tanguy",
        child_name="Soizic Tanguy",
        school_name="École du Goëland",
        quotient_familial=1250,  # Should give T4
    )
    assert d2["rate_bracket"] == "T4"

    dossiers = es_repo.list_campaign_dossiers(tenant, camp["id"])
    assert len(dossiers) == 2


def test_campaign_renewal_engine(es_repo):
    tenant = "plougastel-test"
    # 1. Source campaign
    src_camp = es_repo.create_campaign(
        tenant_id=tenant,
        campaign_type="rentree_scolaire",
        title="Inscriptions scolaires 2026-2027",
        school_year="2026-2027",
        start_date="2026-05-01",
        end_date="2026-07-15",
        config={"target_cycle": "maternelle_primaire"},
    )

    # 2. Add dossiers
    es_repo.create_campaign_dossier(
        tenant_id=tenant,
        campaign_id=src_camp["id"],
        family_ref="FAM-29470-01",
        beneficiary_name="Famille Morvan",
        child_name="Yann Morvan",
        school_name="École des Alizés",
        quotient_familial=650,
    )

    # 3. Add reminder
    es_repo.create_reminder(
        tenant_id=tenant,
        campaign_id=src_camp["id"],
        title="Clôture des inscriptions cantine",
        due_date="2026-07-10",
        reminder_type="inscription_deadline",
    )

    # 4. Perform renewal for 2027-2028
    renewal = es_repo.renew_campaign_for_year(
        tenant_id=tenant,
        source_campaign_id=src_camp["id"],
        target_school_year="2027-2028",
        performed_by="directrice-scolaire@plougastel.bzh",
    )

    assert renewal["renewal_id"].startswith("RNW-")
    assert renewal["dossiers_renewed_count"] == 1
    assert renewal["reminders_carried_count"] == 1

    tgt_camp = renewal["target_campaign"]
    assert tgt_camp["school_year"] == "2027-2028"
    assert "2027-2028" in tgt_camp["title"]
    assert tgt_camp["start_date"] == "2027-05-01"
    assert tgt_camp["end_date"] == "2027-07-15"

    # Verify duplicated dossier in target campaign
    renewed_dossiers = es_repo.list_campaign_dossiers(tenant, tgt_camp["id"])
    assert len(renewed_dossiers) == 1
    assert renewed_dossiers[0]["beneficiary_name"] == "Famille Morvan"
    assert renewed_dossiers[0]["status"] == "reconduit"

    # Verify duplicated reminder with shifted date
    reminders = es_repo.list_reminders(tenant, campaign_id=tgt_camp["id"])
    assert len(reminders) == 1
    assert reminders[0]["due_date"] == "2027-07-10"


def test_social_aid_and_reminders(es_repo):
    tenant = "plougastel-test"
    aid = es_repo.record_social_aid(
        tenant_id=tenant,
        project_id="PRJ-CCAS-001",
        aid_type="aide_energie",
        confidential_ref="CCAS-DOSSIER-42",
        amount_cents=25000,
        commission_decision="accorde",
        deliberation_ref="DELIB-CCAS-2027-01",
        notes="Aide d'urgence chauffage hivernal",
    )
    assert aid["id"].startswith("AID-")
    assert aid["amount_cents"] == 25000
    assert aid["commission_decision"] == "accorde"

    records = es_repo.list_social_aid_for_project(tenant, "PRJ-CCAS-001")
    assert len(records) == 1
    assert records[0]["confidential_ref"] == "CCAS-DOSSIER-42"

    # Reminders
    rem = es_repo.create_reminder(
        tenant_id=tenant,
        title="Commission CCAS mensuelle",
        due_date="2027-02-15",
        reminder_type="commission_review",
    )
    assert rem["id"].startswith("REM-")
    assert rem["is_dismissed"] is False

    active_rems = es_repo.list_reminders(tenant)
    assert any(r["id"] == rem["id"] for r in active_rems)

    es_repo.dismiss_reminder(tenant, rem["id"])
    active_after = es_repo.list_reminders(tenant)
    assert not any(r["id"] == rem["id"] for r in active_after)

    all_with_dismissed = es_repo.list_reminders(tenant, include_dismissed=True)
    assert any(r["id"] == rem["id"] for r in all_with_dismissed)
