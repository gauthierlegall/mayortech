"""Tests unitaires pour le module Séances du Conseil Municipal (Lot v3.2 MayorTech).

Vérifie la conformité légale CGCT :
- art. L. 2121-12 & L. 2121-11 : calcul des jours francs de convocation
- art. L. 2121-17 : quorum de présence physique (majorité absolue)
- art. L. 2121-20 : verrou strict d'un SEUL pouvoir par conseiller présent
- Décompte rapide des votes par délibération
- Scellement cryptographique SHA-256 du PV
- Export PDF du Dossier des Élus
"""

import pytest

from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.council_sessions import (
    CouncilSessionsRepository,
    calculate_cgct_convocation,
    calculate_quorum_and_stats,
    validate_council_proxies,
    generate_council_dossier_pdf,
    generate_deliberations_summary_data,
)


@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "council_test.sqlite3"
    return Repository(str(db_path))


@pytest.fixture
def council_repo(repo):
    return CouncilSessionsRepository(repo)


def test_cgct_convocation_j5_stratum():
    # Pour Plougastel-Daoulas (13 300 hab >= 3500)
    # Séance le 2026-11-26
    # 5 jours francs entiers : 25, 24, 23, 22, 21 nov
    # Date limite d'envoi légale : 20 novembre 2026 à 23h59
    convoc = calculate_cgct_convocation("2026-11-26", population=13300)
    assert convoc["clear_days_required"] == 5
    assert "L. 2121-12" in convoc["cgct_article"]
    assert convoc["deadline_date"] == "2026-11-20"
    assert "20 novembre 2026 à 23h59" in convoc["deadline_human"]
    assert "J-5" in convoc["alert_message"]


def test_cgct_convocation_j3_small_commune():
    # Commune < 3 500 hab : J-3 francs (art. L. 2121-11)
    convoc = calculate_cgct_convocation("2026-11-26", population=2800)
    assert convoc["clear_days_required"] == 3
    assert "L. 2121-11" in convoc["cgct_article"]
    assert convoc["deadline_date"] == "2026-11-22"
    assert "J-3" in convoc["alert_message"]


def test_quorum_calculation_cgct():
    # 33 conseillers au total
    # Quorum requis = 33 // 2 + 1 = 17 présents
    attendances_24 = [
        {"member_name": f"Elu {i}", "status": "present"} for i in range(24)
    ] + [
        {"member_name": f"Excusé {i}", "status": "pouvoir", "proxy_to": f"Elu {i}"} for i in range(5)
    ] + [
        {"member_name": f"Absent {i}", "status": "absent"} for i in range(4)
    ]

    stats = calculate_quorum_and_stats(attendances_24, total_members=33)
    assert stats["quorum_required"] == 17
    assert stats["present_count"] == 24
    assert stats["proxy_count"] == 5
    assert stats["absent_count"] == 4
    assert stats["total_voters"] == 29
    assert stats["quorum_reached"] is True
    assert "24 / 33 présents · Quorum atteint" in stats["gauge_label"]

    # Cas Quorum non atteint : seulement 16 présents
    attendances_16 = [
        {"member_name": f"Elu {i}", "status": "present"} for i in range(16)
    ] + [
        {"member_name": f"Absent {i}", "status": "absent"} for i in range(17)
    ]
    stats_failed = calculate_quorum_and_stats(attendances_16, total_members=33)
    assert stats_failed["present_count"] == 16
    assert stats_failed["quorum_reached"] is False
    assert "Quorum non atteint" in stats_failed["gauge_label"]


def test_verrou_legal_maximum_un_pouvoir_par_conseiller():
    # Règle de l'article L. 2121-20 du CGCT : 1 pouvoir max par conseiller présent
    valid_atts = [
        {"member_name": "Dominique CAP", "status": "present"},
        {"member_name": "Jean-Luc LE GALL", "status": "present"},
        {"member_name": "Rozenn LE BOT", "status": "pouvoir", "proxy_to": "Dominique CAP"},
        {"member_name": "Michel TANGUY", "status": "pouvoir", "proxy_to": "Jean-Luc LE GALL"},
    ]
    # Doit passer sans erreur
    validate_council_proxies(valid_atts)

    # Violation : Dominique CAP reçoit DEUX pouvoirs
    invalid_atts = [
        {"member_name": "Dominique CAP", "status": "present"},
        {"member_name": "Jean-Luc LE GALL", "status": "present"},
        {"member_name": "Rozenn LE BOT", "status": "pouvoir", "proxy_to": "Dominique CAP"},
        {"member_name": "Michel TANGUY", "status": "pouvoir", "proxy_to": "Dominique CAP"},  # 2e pouvoir !
    ]
    with pytest.raises(DomainError) as exc_info:
        validate_council_proxies(invalid_atts)
    assert exc_info.value.code == "proxy_limit_exceeded"
    assert "L. 2121-20 du CGCT" in exc_info.value.message


def test_proxy_to_absent_member_rejected():
    # Mandataire absent
    atts = [
        {"member_name": "Dominique CAP", "status": "absent"},
        {"member_name": "Rozenn LE BOT", "status": "pouvoir", "proxy_to": "Dominique CAP"},
    ]
    with pytest.raises(DomainError) as exc_info:
        validate_council_proxies(atts)
    assert exc_info.value.code == "proxy_holder_not_present"


def test_council_sessions_lifecycle_and_voting(council_repo):
    tenant_id = "tenant-plougastel"

    # 1. Seed & fetch session
    sessions = council_repo.list_council_sessions(tenant_id)
    assert len(sessions) >= 1
    session = council_repo.get_council_session(tenant_id, sessions[0]["id"])
    assert session is not None
    assert session["id"] == "CS-2026-11-26"
    assert len(session["agenda_items"]) == 4
    assert len(session["attendances"]) == 33
    assert session["quorum_stats"]["quorum_reached"] is True

    # 2. Vote on deliberation DELIB-2026-033
    # 25 Pour, 2 Contre, 2 Abstentions -> Adopté
    updated = council_repo.record_vote(
        tenant_id=tenant_id,
        session_id=session["id"],
        item_id="DELIB-2026-033",
        votes_pour=25,
        votes_contre=2,
        votes_abstention=2,
        votes_nppv=0,
    )
    item3 = next(it for it in updated["agenda_items"] if it["deliberation_ref"] == "DELIB-2026-033")
    assert item3["vote_result"] == "adopte"
    assert item3["votes_pour"] == 25
    assert item3["votes_contre"] == 2

    # 3. Vote rejeté si Contre > Pour
    updated2 = council_repo.record_vote(
        tenant_id=tenant_id,
        session_id=session["id"],
        item_id="DELIB-2026-034",
        votes_pour=5,
        votes_contre=22,
        votes_abstention=2,
        votes_nppv=0,
    )
    item4 = next(it for it in updated2["agenda_items"] if it["deliberation_ref"] == "DELIB-2026-034")
    assert item4["vote_result"] == "rejete"

    # 4. Transmission Mégalis Bretagne
    transmitted = council_repo.transmit_megalis(tenant_id, session["id"], "DELIB-2026-033")
    item3_trans = next(it for it in transmitted["agenda_items"] if it["deliberation_ref"] == "DELIB-2026-033")
    assert item3_trans["transmission_megalis_status"] == "transmis"

    # 5. Compilation Dossier des Élus PDF
    pdf_bytes = generate_council_dossier_pdf(session)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"PLOUGASTEL-DAOULAS" in pdf_bytes
    assert b"DOSSIER DES ELUS" in pdf_bytes

    # 6. Synthèse des délibérations publiable
    summary = generate_deliberations_summary_data(session)
    assert summary["commune"] == "Ville de Plougastel-Daoulas"
    assert len(summary["deliberations"]) == 4
    assert "L. 2121-25" in summary["mentions_legales"]

    # 7. Clôture et scellement SHA-256
    closed = council_repo.close_council_session(tenant_id, session["id"], closed_by="Dominique CAP")
    assert closed["status"] == "closed"
    assert len(closed["pv_hash"]) == 64
