"""Tests for Culture -> Finances cross-commission domain, hall reservations, and budget arbitration."""
import pytest
from travaux.culture_finances import CultureFinancesRepository, sanitize_csv_cell
from travaux.domain import DomainError
from travaux.repository import Repository


@pytest.fixture
def repo(tmp_path):
    r = Repository(tmp_path / "test.sqlite3")
    r.create_project("tenant-alpha", "PRJ-CULT-1", "Fête de la Fraise 2027", project_id="PRJ-CULT-1", commission_id="commission-4")
    r.create_project("tenant-alpha", "PRJ-CULT-2", "Concert de Printemps", project_id="PRJ-CULT-2", commission_id="commission-4")
    r.create_project("tenant-beta", "PRJ-CULT-B", "Fête foraine", project_id="PRJ-CULT-B", commission_id="commission-4")
    yield r
    r.close()


@pytest.fixture
def cf(repo):
    return CultureFinancesRepository(repo)


def test_municipal_rooms_list(cf):
    rooms = cf.list_rooms()
    assert len(rooms) >= 4
    room_ids = [r["id"] for r in rooms]
    assert "salle-avel-vor" in room_ids
    assert "salle-roz-avel" in room_ids


def test_hall_reservation_conflict_and_adjacent_slots(cf, repo):
    # Book Avel Vor on 2027-06-12 from 14:00 to 16:00
    res1 = cf.create_reservation(
        "tenant-alpha",
        "PRJ-CULT-1",
        resource_id="salle-avel-vor",
        resource_name="Espace Avel Vor",
        start_time="2027-06-12T14:00:00+02:00",
        end_time="2027-06-12T16:00:00+02:00",
        created_by="user-culture",
    )
    assert res1["status"] == "confirmed"

    # Conflicting reservation: 15:00 to 18:00 on the same room -> must raise conflict DomainError
    with pytest.raises(DomainError) as exc:
        cf.create_reservation(
            "tenant-alpha",
            "PRJ-CULT-2",
            resource_id="salle-avel-vor",
            resource_name="Espace Avel Vor",
            start_time="2027-06-12T15:00:00+02:00",
            end_time="2027-06-12T18:00:00+02:00",
            created_by="user-other",
        )
    assert exc.value.code == "conflict"
    assert "Conflit de réservation" in str(exc.value)

    # Adjacent reservation: 16:00 to 19:00 on the same room -> semi-open interval is compatible!
    res_adj = cf.create_reservation(
        "tenant-alpha",
        "PRJ-CULT-2",
        resource_id="salle-avel-vor",
        resource_name="Espace Avel Vor",
        start_time="2027-06-12T16:00:00+02:00",
        end_time="2027-06-12T19:00:00+02:00",
        created_by="user-other",
    )
    assert res_adj["status"] == "confirmed"

    # Different tenant (tenant-beta) booking same time is isolated and does not conflict
    res_beta = cf.create_reservation(
        "tenant-beta",
        "PRJ-CULT-B",
        resource_id="salle-avel-vor",
        resource_name="Espace Avel Vor",
        start_time="2027-06-12T14:00:00+02:00",
        end_time="2027-06-12T16:00:00+02:00",
        created_by="user-beta",
    )
    assert res_beta["status"] == "confirmed"


def test_reservation_idempotency_with_operation_id(cf):
    op_id = "op-res-12345"
    r1 = cf.create_reservation(
        "tenant-alpha",
        "PRJ-CULT-1",
        resource_id="salle-roz-avel",
        resource_name="Espace Roz Avel",
        start_time="2027-07-01T10:00:00Z",
        end_time="2027-07-01T12:00:00Z",
        created_by="user-culture",
        operation_id=op_id,
    )

    # Re-call with identical operation_id returns existing record without conflict
    r2 = cf.create_reservation(
        "tenant-alpha",
        "PRJ-CULT-1",
        resource_id="salle-roz-avel",
        resource_name="Espace Roz Avel",
        start_time="2027-07-01T10:00:00Z",
        end_time="2027-07-01T12:00:00Z",
        created_by="user-culture",
        operation_id=op_id,
    )
    assert r1["id"] == r2["id"]


def test_reservation_cancellation(cf):
    r = cf.create_reservation(
        "tenant-alpha",
        "PRJ-CULT-1",
        resource_id="salle-bellevue",
        resource_name="Salle de Bellevue",
        start_time="2027-08-10T18:00:00Z",
        end_time="2027-08-10T22:00:00Z",
        created_by="user-culture",
    )
    assert r["status"] == "confirmed"

    cancelled = cf.cancel_reservation("tenant-alpha", r["id"], updated_by="user-culture")
    assert cancelled["status"] == "cancelled"

    # Now that it's cancelled, the same slot can be booked by another project
    r_new = cf.create_reservation(
        "tenant-alpha",
        "PRJ-CULT-2",
        resource_id="salle-bellevue",
        resource_name="Salle de Bellevue",
        start_time="2027-08-10T18:00:00Z",
        end_time="2027-08-10T22:00:00Z",
        created_by="user-culture",
    )
    assert r_new["status"] == "confirmed"


def test_event_details_and_checklist(cf):
    details = cf.update_event_details(
        "tenant-alpha",
        "PRJ-CULT-1",
        association_name="Comité des Fêtes de Plougastel",
        association_ref="W291004567",
        expected_attendance=500,
        location_name="Espace Avel Vor",
        checklist=[
            {"id": "c1", "label": "Convention d'occupation signée", "done": True},
            {"id": "c2", "label": "Attestation d'assurance responsabilité civile", "done": False},
            {"id": "c3", "label": "Déclaration SACEM", "done": False},
        ],
    )
    assert details["association_name"] == "Comité des Fêtes de Plougastel"
    assert details["expected_attendance"] == 500
    assert len(details["checklist"]) == 3
    assert details["checklist"][0]["done"] is True

    # Retrieve
    retrieved = cf.get_event_details("tenant-alpha", "PRJ-CULT-1")
    assert retrieved["association_ref"] == "W291004567"
    assert len(retrieved["checklist"]) == 3


def test_budget_sheet_variants_and_remaining_cents(cf):
    # Fête des associations budget:
    # Variante A : 9 600 € TTC, subvention 2 500 € -> reste à charge = 7 100 €
    # Variante B : 11 700 € TTC, subvention 2 500 € -> reste à charge = 9 200 €
    variants = [
        {
            "id": "var-a",
            "label": "Variante A (Scénario standard)",
            "tax_basis": "ttc",
            "amount_cents": 960000,
            "subsidies_cents": 250000,
            "hypothesis": "Location salle et régie technique de base",
        },
        {
            "id": "var-b",
            "label": "Variante B (Scénario étendu)",
            "tax_basis": "ttc",
            "amount_cents": 1170000,
            "subsidies_cents": 250000,
            "hypothesis": "Régie son/lumière renforcée + sécurité gardiennage",
        },
    ]

    sheet = cf.save_budget_sheet(
        "tenant-alpha",
        "PRJ-CULT-1",
        title="Budget prévisionnel Manifestation 2027",
        exercise=2027,
        variants=variants,
        created_by="user-culture",
    )

    assert sheet["version"] == 1
    assert len(sheet["variants"]) == 2
    assert sheet["variants"][0]["remaining_cents"] == 710000
    assert sheet["variants"][1]["remaining_cents"] == 920000

    # CSV Export
    csv_text = cf.export_budget_csv("tenant-alpha", "PRJ-CULT-1")
    assert "Fiche budgétaire;Budget prévisionnel Manifestation 2027" in csv_text
    assert "7100.00" in csv_text
    assert "9200.00" in csv_text


def test_csv_injection_sanitization():
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("@SUM(A1:A5)") == "'@SUM(A1:A5)"
    assert sanitize_csv_cell("-100") == "'-100"
    assert sanitize_csv_cell("+200") == "'+200"
    assert sanitize_csv_cell("Normal Text") == "Normal Text"


def test_culture_to_finance_arbitrage_loop(cf):
    # 1. Setup budget v1
    cf.save_budget_sheet(
        "tenant-alpha",
        "PRJ-CULT-1",
        title="Budget fête v1",
        exercise=2027,
        variants=[{
            "id": "var-a",
            "label": "Variante A",
            "tax_basis": "ttc",
            "amount_cents": 960000,
            "subsidies_cents": 250000,
            "hypothesis": "Version initiale",
        }],
        created_by="user-culture",
    )

    # 2. Transmit to Finances (Commission 1)
    trans = cf.create_or_update_transmission(
        "tenant-alpha",
        "PRJ-CULT-1",
        motive="Demande d'arbitrage sur subvention municipale 2027",
        created_by="user-culture",
        attached_document_ids=["doc-devis-v1"],
    )
    assert trans["status"] == "transmis"
    assert trans["version"] == 1
    assert trans["attached_document_ids"] == ["doc-devis-v1"]
    assert trans["budget_snapshot"]["variants"][0]["remaining_cents"] == 710000

    # 3. Finances reviews and requests complements
    decision1 = cf.record_decision(
        "tenant-alpha",
        trans["id"],
        opinion="demande_complements",
        motivation="Merci de détailler les frais de gardiennage et actualiser le devis régie.",
        decided_by="elu-finances",
        requested_complements="Devis actualisé v2 requis",
        expected_version=1,
    )
    assert decision1["status"] == "complements_requis"
    assert decision1["decision_opinion"] == "demande_complements"

    # 4. Culture updates budget sheet to v2 and re-transmits
    cf.save_budget_sheet(
        "tenant-alpha",
        "PRJ-CULT-1",
        title="Budget fête v2 actualisé",
        exercise=2027,
        variants=[{
            "id": "var-a",
            "label": "Variante A Révisée",
            "tax_basis": "ttc",
            "amount_cents": 1070000,
            "subsidies_cents": 250000,
            "hypothesis": "Devis révisé avec gardiennage",
        }],
        created_by="user-culture",
    )

    trans2 = cf.create_or_update_transmission(
        "tenant-alpha",
        "PRJ-CULT-1",
        motive="Envoi devis v2 avec gardiennage conformément à la demande",
        created_by="user-culture",
        attached_document_ids=["doc-devis-v2"],
    )
    assert trans2["version"] == 2
    assert trans2["status"] == "transmis"
    assert trans2["attached_document_ids"] == ["doc-devis-v2"]
    assert trans2["budget_snapshot"]["variants"][0]["remaining_cents"] == 820000

    # 5. Finances issues final favorable motivated opinion with deliberation ref
    decision2 = cf.record_decision(
        "tenant-alpha",
        trans2["id"],
        opinion="favorable",
        motivation="Le surcoût gardiennage est justifié pour la sécurité du public. Avis favorable sous réserve de convention.",
        decision_ref="DELIB-2027-06-42",
        decided_by="elu-finances",
        expected_version=2,
    )
    assert decision2["status"] == "avis_rendu"
    assert decision2["decision_opinion"] == "favorable"
    assert decision2["decision_ref"] == "DELIB-2027-06-42"

    # 6. Verify tracking action was automatically created in finance_decision_actions and note in notes
    with cf.repo._lock:
        actions = cf.repo._db.execute(
            "SELECT * FROM finance_decision_actions WHERE tenant_id=? AND project_id=?",
            ("tenant-alpha", "PRJ-CULT-1"),
        ).fetchall()
        assert len(actions) == 2  # one for complement requested, one for final opinion
        titles = [a["title"] for a in actions]
        assert any("DELIB-2027-06-42" in t for t in titles)

        # Check official note on project
        notes = cf.repo._db.execute(
            "SELECT * FROM notes WHERE tenant_id=? AND project_id=?",
            ("tenant-alpha", "PRJ-CULT-1"),
        ).fetchall()
        assert len(notes) >= 2
        note_texts = [n["content"] for n in notes]
        assert any("DELIB-2027-06-42" in text for text in note_texts)


