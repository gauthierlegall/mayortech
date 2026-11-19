import base64

import pytest

from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.workspace import WorkspaceRepository


def test_native_page_save_versions_and_materializes_current_context_atomically(tmp_path):
    repo = Repository(tmp_path / "workspace.sqlite3")
    try:
        project = repo.create_project("a", "TR-1", "Chantier fictif")
        pages = WorkspaceRepository(repo)
        page = pages.ensure_main("a", project["id"])
        first = pages.save("a", page["id"], base64.b64encode(b"native-yjs-fixture-v1").decode(), None, "Maintenir l'accès piéton.", "blocksuite-0.22.4", "father")
        assert first["revision"] == 1
        assert repo.get_memory("a", project["id"])["notes"][0]["content"] == "Maintenir l'accès piéton."
        replay = pages.save("a", page["id"], first["state_base64"], None, first["text"], "blocksuite-0.22.4", "father")
        assert replay["revision"] == 1
        second = pages.save("a", page["id"], base64.b64encode(b"native-yjs-fixture-v2").decode(), first["revision_hash"], "Accès piéton validé.", "blocksuite-0.22.4", "father")
        assert second["revision"] == 2
        assert len(repo.get_memory("a", project["id"])["notes"]) == 1
        assert repo.get_memory("a", project["id"])["notes"][0]["content"] == "Accès piéton validé."
        assert len(pages.history("a", page["id"])) == 2
        with pytest.raises(DomainError, match="version"):
            pages.save("a", page["id"], base64.b64encode(b"late").decode(), first["revision_hash"], "Old late tab", "blocksuite-0.22.4", "father")
        with pytest.raises(DomainError):
            pages.get("other-town", page["id"])
    finally:
        repo.close()


def test_failed_materialization_rolls_back_native_state_and_version(tmp_path, monkeypatch):
    repo = Repository(tmp_path / "rollback.sqlite3")
    try:
        project = repo.create_project("a", "TR-1", "Chantier fictif")
        pages = WorkspaceRepository(repo)
        page = pages.ensure_main("a", project["id"])
        def reject(*args, **kwargs):
            raise DomainError("invalid_input", "Context import rejected")
        monkeypatch.setattr(repo, "ingest_workspace_note", reject)
        with pytest.raises(DomainError):
            pages.save("a", page["id"], base64.b64encode(b"state").decode(), None, "Texte", "blocksuite-0.22.4", "father")
        assert pages.get("a", page["id"])["revision"] == 0
        assert pages.history("a", page["id"]) == []
    finally:
        repo.close()
