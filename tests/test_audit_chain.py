"""Tests unitaires pour la chaîne d'audit cryptographique SHA-256 (Lot v3.4)."""

import pytest
from travaux.audit_chain import AuditChainRepository, compute_entry_hash, GENESIS_PREV_HASH
from travaux.repository import Repository


@pytest.fixture
def audit_repo(tmp_path):
    repo = Repository(tmp_path / "audit_test.sqlite3")
    service = AuditChainRepository(repo)
    yield repo, service
    repo.close()


def test_hash_calculation_is_deterministic():
    h1 = compute_entry_hash(1, "2026-11-20T08:00:00Z", "actor-1", "seal", "ARR-001", "sha-doc", GENESIS_PREV_HASH)
    h2 = compute_entry_hash(1, "2026-11-20T08:00:00Z", "actor-1", "seal", "ARR-001", "sha-doc", GENESIS_PREV_HASH)
    assert h1 == h2
    assert len(h1) == 64


def test_chain_append_and_verification(audit_repo):
    repo, audit = audit_repo
    tenant = "town-test"

    # 1. Chaîne vide
    res_empty = audit.verify_chain(tenant)
    assert res_empty["valid"] is True
    assert res_empty["total_entries"] == 0

    # 2. Ajout de 3 entrées consécutives
    e1 = audit.append_entry(tenant, "actor-1", "visa_dgs", "PC-2026-001", "hash1", actor_name="Loïc", actor_role="DGS")
    assert e1["chain_index"] == 1
    assert e1["prev_hash"] == GENESIS_PREV_HASH

    e2 = audit.append_entry(tenant, "actor-2", "signature_maire", "PC-2026-001", "hash1", actor_name="Maire", actor_role="Maire")
    assert e2["chain_index"] == 2
    assert e2["prev_hash"] == e1["entry_hash"]

    e3 = audit.append_entry(tenant, "actor-3", "teletransmission_prefecture", "PC-2026-001", "hash1", actor_name="Préfecture", actor_role="Contrôle")
    assert e3["chain_index"] == 3
    assert e3["prev_hash"] == e2["entry_hash"]

    # 3. Vérification mathématique globale
    res = audit.verify_chain(tenant)
    assert res["valid"] is True
    assert res["total_entries"] == 3
    assert res["head_hash"] == e3["entry_hash"]


def test_chain_tamper_detection(audit_repo):
    repo, audit = audit_repo
    tenant = "town-test"

    # Ajouter 2 entrées
    audit.append_entry(tenant, "actor-1", "visa", "DOC-1", "sha1")
    audit.append_entry(tenant, "actor-2", "signature", "DOC-1", "sha1")

    # Vérification initiale valide
    assert audit.verify_chain(tenant)["valid"] is True

    # Altération malveillante rétroactive dans la base SQLite
    with repo._transaction() as db:
        db.execute(
            "UPDATE audit_chain_entries SET document_ref = 'FALSIFIED-DOC' WHERE tenant_id = ? AND chain_index = 1",
            (tenant,),
        )

    # La vérification doit immédiatement échouer et détecter la fraude
    res_tampered = audit.verify_chain(tenant)
    assert res_tampered["valid"] is False
    msg = res_tampered["message"].lower()
    assert "altération" in msg or "rupture" in msg or "compromise" in msg
