import hashlib
import shutil
from pathlib import Path

import pytest

from travaux.config import Settings, ensure_public_demo_database
from travaux.documents import DocumentRepository
from travaux.domain import DomainError
from travaux.jobs import JobQueue
from travaux.repository import Repository
from travaux.storyline import seed_storyline

FIXTURES = Path(__file__).parents[1] / "fixtures/storylines/lovable-v1"
TENANT = "demo-storyline"


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "public-demo.sqlite3"
    ensure_public_demo_database(
        Settings(
            mode="public_demo",
            db_path=path,
            tenant_id=TENANT,
            public_origin="https://demo.invalid",
            allowed_hosts=("demo.invalid",),
        )
    )
    repo, queue = Repository(path), JobQueue(path)
    yield repo, queue
    repo.close()


def test_four_real_dossiers_preserve_existing_and_conflicting_announcements(database):
    repo, queue = database
    old = repo.create_project(TENANT, "OLD-001", "Dossier existant à préserver")
    result = seed_storyline(repo, queue, TENANT, FIXTURES)
    assert len(repo.list_projects(TENANT)) == 5
    assert repo.get_project(TENANT, old["id"])["name"] == "Dossier existant à préserver"
    portal = repo.get_memory(TENANT, result["projects"]["portail"])
    facts = {fact["field"]: fact["value"] for fact in portal["facts"]}
    assert facts["delivery_date"] == "2026-11-18"
    assert facts["owner"] == "Thomas Le Gall"
    assert facts["location"] == "École de Ker Avel · Plougastel"
    assert facts["category"] == "Bâtiments scolaires"
    assert any(fact["value"] == "2026-11-25" and fact["conflict_with"] for fact in portal["pending"])
    assert any(
        fact["field"] == "budget_raw" and fact["value"] == "5 120,00 EUR HT" for fact in portal["pending"]
    )
    documents = DocumentRepository(repo)
    for item in result["document_catalog"]:
        metadata, content = documents.download(TENANT, item["document_id"])
        assert content == (FIXTURES / "documents" / metadata["original_filename"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == item["sha256"]
    assert all(
        repo.get_source(TENANT, source_id)["metadata"]["fictitious"] is True
        for source_id in result["mail_sources"].values()
    )
    assert len(result["mail_sources"]) >= 9
    assert len(result["confirmed_actions"]) >= 5
    initial = repo.get_summary(TENANT, result["summary_ids"]["portail_initial"])
    current = repo.get_summary(TENANT, result["summary_ids"]["portail_current"])
    assert initial["status"] == "approved" and initial["stale"]
    assert current["status"] == "draft" and current["coverage"] == "partial"
    assert "ce report reste à confirmer" in current["content"]
    assert all(job["status"] == "done" for job in queue.list(TENANT))


def test_catalogue_has_explicit_version_validation_amount_and_exact_sources(database):
    repo, queue = database
    result = seed_storyline(repo, queue, TENANT, FIXTURES)
    assert [
        (row["version"], row["status"], row["amount"]["amount"]) for row in result["document_catalog"]
    ] == [(1, "validated", "4850.00"), (2, "under_review", "5120.00")]
    for row in result["document_catalog"]:
        assert row["family"] == "AF-2026-184"
        assert row["amount"]["currency"] == "EUR" and row["amount"]["basis"] == "HT"
        for proof in row["evidence"].values():
            assert proof["quote"] in repo.get_source(TENANT, proof["source_id"])["body"]
    catalogue = repo.get_source(TENANT, result["catalog_source_id"])
    assert catalogue["metadata"]["document_catalog"] == result["document_catalog"]
    assert result["document_catalog"][0]["evidence"]["status"]["source_id"] == result["mail_sources"]["m2"]


def test_replay_does_not_reset_human_decisions_notes_or_summary_versions(database):
    repo, queue = database
    result = seed_storyline(repo, queue, TENANT, FIXTURES)
    project_id = result["projects"]["portail"]
    repo.add_note(TENANT, project_id, "Note ajoutée après initialisation", actor_id="responsable-demo")
    pending = next(row for row in repo.list_candidates(TENANT, project_id) if row["value"] == "2026-11-25")
    repo.review_candidate(TENANT, pending["id"], "replace", actor_id="responsable-demo")
    before = repo.get_memory(TENANT, project_id)
    counts = (
        len(repo.list_sources(TENANT)),
        len(repo.list_summaries(TENANT)),
        len(repo.list_events(TENANT, project_id)),
    )
    again = seed_storyline(repo, queue, TENANT, FIXTURES)
    assert again == result
    assert repo.get_memory(TENANT, project_id) == before
    assert counts == (
        len(repo.list_sources(TENANT)),
        len(repo.list_summaries(TENANT)),
        len(repo.list_events(TENANT, project_id)),
    )


def test_existing_reference_is_never_adopted_or_overwritten(database):
    repo, queue = database
    prior = repo.create_project(TENANT, "TRV-2026-042", "Dossier saisi par un utilisateur")
    with pytest.raises(DomainError, match="référence"):
        seed_storyline(repo, queue, TENANT, FIXTURES)
    assert repo.list_projects(TENANT) == [prior]
    assert repo.list_sources(TENANT) == []


def test_modified_original_or_fixture_fails_before_mutation(database, tmp_path):
    repo, queue = database
    altered = tmp_path / "altered"
    shutil.copytree(FIXTURES, altered)
    (altered / "documents/devis-portail-v2.pdf").write_bytes(b"not the supplied original")
    with pytest.raises(DomainError):
        seed_storyline(repo, queue, TENANT, altered)
    assert repo.list_projects(TENANT) == []


def test_import_failure_rolls_back_all_storyline_data(database, monkeypatch):
    from travaux import storyline

    repo, queue = database
    original = storyline.import_mail
    calls = []

    def fail_on_second(*args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise RuntimeError("synthetic import failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(storyline, "import_mail", fail_on_second)
    with pytest.raises(RuntimeError, match="synthetic"):
        seed_storyline(repo, queue, TENANT, FIXTURES)
    assert repo.list_projects(TENANT) == []
    assert repo.list_sources(TENANT) == []
    assert queue.list(TENANT) == []


def test_only_matching_public_demo_marker_is_accepted(database, tmp_path):
    repo, queue = database
    with pytest.raises(DomainError):
        seed_storyline(repo, queue, "foreign-tenant", FIXTURES)
    private = Repository(tmp_path / "private.sqlite3")
    private_queue = JobQueue(tmp_path / "private.sqlite3")
    with pytest.raises(DomainError):
        seed_storyline(private, private_queue, TENANT, FIXTURES)
    assert private.list_projects(TENANT) == []
    private.close()


def test_explicit_local_demo_settings_allow_additive_seed_but_not_protected_modes(tmp_path):
    path = tmp_path / "local-demo.sqlite3"
    settings = Settings(mode="demo", db_path=path, tenant_id=TENANT)
    repo, queue = Repository(path), JobQueue(path)
    result = seed_storyline(repo, queue, TENANT, FIXTURES, settings=settings)
    assert len(result["projects"]) == 4
    assert seed_storyline(repo, queue, TENANT, FIXTURES, settings=settings) == result
    for forbidden in (
        Settings(mode="demo", db_path=path, tenant_id=TENANT, egress_approved=True),
        Settings(
            mode="staging",
            db_path=path,
            tenant_id=TENANT,
            password_hash="scrypt$fixture",
            public_origin="https://demo.invalid",
            allowed_hosts=("demo.invalid",),
        ),
    ):
        with pytest.raises(DomainError):
            seed_storyline(repo, queue, TENANT, FIXTURES, settings=forbidden)
    repo.close()


def test_explicit_demo_settings_cannot_bypass_public_marker(database):
    repo, queue = database
    settings = Settings(mode="demo", db_path=Path(repo.path), tenant_id=TENANT)
    with pytest.raises(DomainError):
        seed_storyline(repo, queue, TENANT, FIXTURES, settings=settings)
    assert repo.list_projects(TENANT) == []
