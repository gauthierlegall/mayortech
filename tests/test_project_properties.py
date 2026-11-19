import json

import pytest

from travaux.domain import DomainError
from travaux.documents import DocumentRepository
from travaux.project_properties import FIELDS, ProjectProfileService
from travaux.repository import Repository


ACTOR = {
    "actor_id": "operator",
    "tenant_id": "commune",
    "permissions": {"workspace": {"read": True, "write": True}},
}


def setup(tmp_path):
    repo = Repository(tmp_path / "properties.sqlite3")
    project = repo.create_project("commune", "TRV-FICTIF-1", "Dossier fictif")
    return ProjectProfileService(repo), repo, project["id"]


def patch(service, project_id, changes, **overrides):
    previous = service.get("commune", project_id, ACTOR)
    return service.update(
        "commune",
        project_id,
        ACTOR,
        changes=changes,
        expected_revision=previous["revision"],
        expected_project_revision=overrides.get("expected_project_revision", previous["project_revision"]),
    )


def test_fifteen_photo_labels_exist_without_fabricating_values(tmp_path):
    service, repo, ident = setup(tmp_path)
    labels = {field["label"] for field in FIELDS}
    assert labels == {
        "Dossier",
        "Catégorie",
        "Coût estimé",
        "Coût réel",
        "Date demande",
        "Demandeur",
        "Entreprise",
        "Lieu",
        "Notes",
        "Observation",
        "Pièces jointes",
        "Priorité",
        "Service / Responsable",
        "Statut",
        "Échéance",
    }
    snapshot = service.get("commune", ident, ACTOR)
    assert snapshot["values"]["name"] == "Dossier fictif"
    assert snapshot["values"]["estimated_cost"] == "" and snapshot["values"]["actual_cost"] == ""
    assert snapshot["values"]["request_date"] == "" and snapshot["values"]["deadline"] == ""
    assert snapshot["documents"] == [] and snapshot["can_edit"]
    assert snapshot["origins"]["name"]["kind"] == "project"


def test_manual_properties_preserve_separate_notes_costs_and_no_candidate_acceptance(tmp_path):
    service, repo, ident = setup(tmp_path)
    long_note = "Texte fictif\n" * 1200
    saved = patch(
        service,
        ident,
        {
            "name": "Dossier renommé",
            "estimated_cost": "1 234,50",
            "actual_cost": "0",
            "request_date": "2026-10-05",
            "deadline": "2026-12-05",
            "notes": long_note,
            "observation": "Observation indépendante",
            "priority": "Urgente",
            "service_owner": "Service fictif",
            "status": "En attente",
        },
    )
    assert saved["values"]["estimated_cost"] == "1234.50"
    assert saved["values"]["actual_cost"] == "0.00"
    assert saved["values"]["notes"] == long_note
    assert saved["values"]["observation"] == "Observation indépendante"
    assert repo.get_project("commune", ident)["name"] == "Dossier renommé"
    assert repo.get_project("commune", ident)["status"] == "on_hold"
    assert repo.list_candidates("commune", ident) == []
    origin = saved["origins"]["estimated_cost"]
    assert origin["kind"] == "human_property" and origin["actor_id"] == "operator"
    source = repo.get_source("commune", origin["source_id"])
    assert "Coût estimé : 1234.50" in source["body"] and source["project_ids"] == [ident]
    assert service.get("commune", ident, ACTOR)["values"] == saved["values"]
    audit = repo._db.execute(
        "SELECT payload FROM audit_events WHERE action='project.properties.updated'"
    ).fetchone()
    assert "estimated_cost" in json.loads(audit[0])["fields"]


def test_existing_facts_are_labelled_and_can_be_overridden_without_mutation(tmp_path):
    service, repo, ident = setup(tmp_path)
    note = repo.add_note("commune", ident, "Lieu : Atelier fictif. Livraison : 2026-12-18. Budget : 500 €.")
    for field, value, quote, kind in [
        ("location", "Atelier fictif", "Atelier fictif", "text"),
        ("delivery_date", "2026-12-18", "2026-12-18", "date"),
        ("budget_raw", "500 €", "500 €", "text"),
    ]:
        candidate = repo.add_candidate(
            "commune", ident, note["source_id"], field, value, quote=quote, kind=kind
        )
        repo.review_candidate("commune", candidate["id"], "accept")
    snapshot = service.get("commune", ident, ACTOR)
    assert (
        snapshot["values"]["location"] == "Atelier fictif"
        and snapshot["origins"]["location"]["kind"] == "confirmed_fact"
    )
    # A livraison or a generic budget is not an unobserved Notion deadline/estimate.
    assert snapshot["values"]["deadline"] == "" and snapshot["values"]["estimated_cost"] == ""
    previous = repo.get_memory("commune", ident)["facts"]
    saved = patch(service, ident, {"location": "Autre lieu fictif", "contractor": ""})
    assert saved["values"]["location"] == "Autre lieu fictif"
    assert repo.get_memory("commune", ident)["facts"] == previous
    cleared = patch(service, ident, {"location": ""})
    assert cleared["values"]["location"] == "" and cleared["origins"]["location"]["kind"] == "human_property"


def test_revision_conflicts_are_atomic_and_other_project_updates_require_reload(tmp_path):
    service, repo, ident = setup(tmp_path)
    initial = service.get("commune", ident, ACTOR)
    patch(service, ident, {"requester": "Service fictif"})
    with pytest.raises(DomainError) as conflict:
        service.update(
            "commune",
            ident,
            ACTOR,
            expected_revision=initial["revision"],
            expected_project_revision=initial["project_revision"],
            changes={"requester": "Écrasement interdit"},
        )
    assert conflict.value.code == "stale_revision"
    assert service.get("commune", ident, ACTOR)["values"]["requester"] == "Service fictif"
    latest = service.get("commune", ident, ACTOR)
    repo.add_note("commune", ident, "Autre modification concurrente")
    with pytest.raises(DomainError):
        service.update(
            "commune",
            ident,
            ACTOR,
            expected_revision=latest["revision"],
            expected_project_revision=latest["project_revision"],
            changes={"name": "Conflit"},
        )
    assert repo.get_project("commune", ident)["name"] == "Dossier fictif"


@pytest.mark.parametrize(
    "changes",
    [
        {"estimated_cost": "NaN"},
        {"actual_cost": "-2"},
        {"actual_cost": "1.001"},
        {"estimated_cost": 1.2},
        {"request_date": "2026-02-30"},
        {"deadline": "tomorrow"},
        {"priority": "inconnue"},
        {"status": "inconnu"},
        {"not_a_field": "x"},
        {"name": "  "},
    ],
)
def test_invalid_changes_fail_without_mutation(tmp_path, changes):
    service, repo, ident = setup(tmp_path)
    with pytest.raises(DomainError):
        patch(service, ident, changes)
    assert service.get("commune", ident, ACTOR)["revision"] == 0
    assert repo.get_memory("commune", ident)["notes"] == []


def test_tenant_rbac_and_real_attachment_links(tmp_path):
    service, repo, ident = setup(tmp_path)
    source = repo.ingest_source(
        "commune",
        "attachment-fictif",
        "Pièce fictive",
        "Texte fictif",
        project_ref="TRV-FICTIF-1",
        metadata={"filename": "note.txt", "kind": "attachment"},
    )
    document = DocumentRepository(repo).store(
        "commune", source["id"], b"Texte fictif", "note.txt", "text/plain"
    )
    snapshot = service.get("commune", ident, ACTOR)
    assert snapshot["documents"][0]["id"] == document["id"] and snapshot["documents"][0][
        "download_url"
    ].endswith("/download")
    read_only = {**ACTOR, "permissions": {"workspace": {"read": True, "write": False}}}
    assert service.get("commune", ident, read_only)["can_edit"] is False
    for who, tenant in [
        ({**ACTOR, "tenant_id": "other"}, "commune"),
        (ACTOR, "other"),
        ({**ACTOR, "permissions": {}}, "commune"),
    ]:
        with pytest.raises(DomainError):
            service.get(tenant, ident, who)
    with pytest.raises(DomainError):
        service.update(
            "commune",
            ident,
            read_only,
            changes={"name": "Refus"},
            expected_revision=0,
            expected_project_revision=0,
        )
