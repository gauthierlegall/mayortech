"""Operator fixtures must not multiply source versions/documents on redeploy."""

import importlib.util
from pathlib import Path
from travaux.repository import Repository
from travaux.documents import DocumentRepository


def test_public_fixture_replay_preserves_originals_and_confirmed_actions(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / "scripts/seed_public_examples.py"
    spec = importlib.util.spec_from_file_location("public_examples", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    database = tmp_path / "demo.sqlite3"
    monkeypatch.setenv("TRAVAUX_MODE", "demo")
    monkeypatch.setenv("TRAVAUX_DB", str(database))
    monkeypatch.setenv("TRAVAUX_TENANT", "invented-examples")
    module.main()
    repo = Repository(database)
    project = next(p for p in repo.list_projects("invented-examples") if p["reference"] == "TRV-2026-014")

    def counts():
        return tuple(
            repo._db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("sources", "original_documents", "candidates")
        )

    before = counts()
    module.main()
    assert counts() == before
    actions = [
        candidate
        for candidate in repo.list_candidates("invented-examples", project_id=project["id"])
        if candidate["field"].startswith("action.") and candidate["status"] == "accepted"
    ]
    assert len(actions) == 3
    documents = DocumentRepository(repo).list_project("invented-examples", project["id"])
    assert len([item for item in documents if item["kind"] == "attachment"]) == 2
    repo.close()
