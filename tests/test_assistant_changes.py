"""The assistant proposes; a version-bound human confirmation commits once."""
import importlib

import pytest

from travaux.config import Settings
from travaux.domain import DomainError
from travaux.project_properties import ProjectProfileService
from travaux.repository import Repository

ACTOR = {"actor_id": "agent-a", "tenant_id": "town-a", "permissions": {"workspace": {"read": True, "write": True}}}


@pytest.fixture
def changes(tmp_path):
    repo = Repository(tmp_path / "changes.sqlite3")
    project = repo.create_project("town-a", "TEST-A", "Dossier de recette")
    cls = importlib.import_module("travaux.assistant_changes").AssistantChanges
    service = cls(repo, Settings(db_path=tmp_path / "changes.sqlite3", tenant_id="town-a"))
    yield service, repo, project["id"]
    repo.close()


def prepare(service, project, command="Mets le statut à Terminé", key="change-1"):
    return service.prepare("town-a", ACTOR, project, command, client_id=key, conversation_id="thread-a")


def test_proposal_changes_nothing_until_explicit_human_confirmation(changes):
    service, repo, project = changes
    before = repo.get_project("town-a", project)
    proposal = prepare(service, project)
    assert proposal["plan"] == {"operation": "property", "field": "status", "value": "Terminé"}
    assert repo.get_project("town-a", project) == before
    result = service.confirm("town-a", ACTOR, proposal["id"], expected_plan_hash=proposal["plan_hash"])
    assert result["status"] == "applied"
    assert repo.get_project("town-a", project)["status"] == "completed"
    assert ProjectProfileService(repo).get("town-a", project, ACTOR)["values"]["status"] == "Terminé"
    count = len(repo.list_events("town-a", project))
    assert service.confirm("town-a", ACTOR, proposal["id"], expected_plan_hash=proposal["plan_hash"]) == result
    assert len(repo.list_events("town-a", project)) == count


def test_changed_project_or_plan_cannot_be_silently_overwritten(changes):
    service, repo, project = changes
    proposal = prepare(service, project)
    with pytest.raises(DomainError):
        service.confirm("town-a", ACTOR, proposal["id"], expected_plan_hash="forged")
    repo.add_note("town-a", project, "Une autre personne a modifié ce dossier", actor_id="agent-b")
    with pytest.raises(DomainError) as failure:
        service.confirm("town-a", ACTOR, proposal["id"], expected_plan_hash=proposal["plan_hash"])
    assert failure.value.code == "stale_revision"
    assert repo.get_project("town-a", project)["status"] == "active"


def test_read_only_actor_and_other_actor_cannot_apply_the_proposal(changes):
    service, _, project = changes
    proposal = prepare(service, project)
    for actor in [{**ACTOR, "actor_id": "other"}, {**ACTOR, "permissions": {"workspace": {"read": True, "write": False}}}]:
        with pytest.raises(DomainError):
            service.confirm("town-a", actor, proposal["id"], expected_plan_hash=proposal["plan_hash"])


def test_confirmed_action_is_a_durable_fact_once_and_preserves_its_source(changes):
    service, repo, project = changes
    proposal = prepare(service, project, "Crée une action : Appeler le maître d’œuvre")
    result = service.confirm("town-a", ACTOR, proposal["id"], expected_plan_hash=proposal["plan_hash"])
    candidate = repo.get_candidate("town-a", result["result"]["candidate_id"])
    assert candidate["status"] == "accepted" and candidate["field"].startswith("action.")
    assert candidate["value"] == "Appeler le maître d’œuvre"
    assert candidate["evidence"][0]["quote"] in repo.get_source("town-a", candidate["source_id"])["body"]
    replay = prepare(service, project, "Crée une action : Appeler le maître d’œuvre")
    assert replay["id"] == proposal["id"] and replay["status"] == "applied"
    with pytest.raises(DomainError):
        prepare(service, project, "Crée une action : Autre contenu")
