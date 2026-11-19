import pytest

from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.workspace import WorkspaceRepository
from travaux.field_reports import FieldReportService

ACTOR = {
    "actor_id": "operator",
    "tenant_id": "town",
    "permissions": {"workspace": {"read": True, "write": True}},
}


def setup(tmp_path):
    repo = Repository(tmp_path / "reports.sqlite3")
    project = repo.create_project("town", "TRV-QA-FIELD", "Dossier fictif")
    pages = WorkspaceRepository(repo)
    return FieldReportService(repo), repo, project["id"], pages


def values(pid, **changes):
    return {
        "client_id": "field-report-client-1",
        "project_id": pid,
        "kind": "Anomalie",
        "date": "2026-11-15",
        "title": "Constat fictif",
        "detail": "Compte rendu fictif\nDeuxième ligne.",
        "author": "Équipe fictive",
        **changes,
    }


def test_human_report_is_persisted_sourced_and_creation_replay_is_idempotent(tmp_path):
    service, repo, pid, pages = setup(tmp_path)
    report = service.create("town", ACTOR, values(pid))
    assert report["status"] == "À traiter" and report["revision"] == 0
    source = repo.get_source("town", report["source_id"])
    assert source["metadata"]["origin"] == "human_field_report"
    assert "Deuxième ligne." in source["body"] and source["project_ids"] == [pid]
    assert repo.get_memory("town", pid)["facts"] == [] and repo.list_candidates("town", pid) == []
    before = repo.get_project("town", pid)["revision"]
    assert service.create("town", ACTOR, values(pid))["id"] == report["id"]
    assert repo.get_project("town", pid)["revision"] == before
    assert len(repo.get_memory("town", pid)["notes"]) == 1
    with pytest.raises(DomainError) as failure:
        service.create("town", ACTOR, values(pid, title="Autre titre"))
    assert failure.value.code == "conflict"
    assert service.list("town", ACTOR, project_id=pid)["items"][0]["id"] == report["id"]


def test_status_uses_cas_and_current_report_links_to_the_immutable_original(tmp_path):
    service, repo, pid, pages = setup(tmp_path)
    report = service.create("town", ACTOR, values(pid))
    lifted = service.update("town", report["id"], ACTOR, expected_revision=0, status="Levée")
    assert (
        lifted["status"] == "Levée" and lifted["revision"] == 1 and lifted["source_id"] == report["source_id"]
    )
    assert service.list("town", ACTOR, status="À traiter")["items"] == []
    with pytest.raises(DomainError) as failure:
        service.update("town", report["id"], ACTOR, expected_revision=0, status="À traiter")
    assert failure.value.code == "stale_revision"
    assert service.update("town", report["id"], ACTOR, expected_revision=1, status="Levée")["revision"] == 1
    assert (
        service.update("town", report["id"], ACTOR, expected_revision=1, status="À traiter")["revision"] == 2
    )
    assert repo.list_candidates("town", pid) == []


def test_native_action_link_checks_page_scope_is_idempotent_and_never_stores_a_second_action(tmp_path):
    service, repo, pid, pages = setup(tmp_path)
    report = service.create("town", ACTOR, values(pid))
    page = pages.ensure_main("town", pid)
    link = {"page_id": page["id"], "database_id": "database-1", "row_id": "row-1"}
    saved = service.link_action("town", report["id"], ACTOR, expected_revision=0, **link)
    assert saved["action_link"] == {**link, "source_key": "field-report:" + report["id"]}
    assert service.link_action("town", report["id"], ACTOR, expected_revision=0, **link)["revision"] == 1
    with pytest.raises(DomainError):
        service.link_action(
            "town", report["id"], ACTOR, expected_revision=1, **{**link, "row_id": "other-row"}
        )
    another = repo.create_project("town", "TRV-QA-OTHER", "Autre dossier fictif")
    other_page = pages.ensure_main("town", another["id"])
    second = service.create("town", ACTOR, values(pid, client_id="field-report-client-2"))
    with pytest.raises(DomainError):
        service.link_action(
            "town", second["id"], ACTOR, expected_revision=0, **{**link, "page_id": other_page["id"]}
        )
    assert service.get("town", second["id"], ACTOR)["action_link"] is None
    assert repo.list_candidates("town", pid) == []


@pytest.mark.parametrize(
    "change",
    [
        {"date": "2026-02-30"},
        {"date": "tomorrow"},
        {"title": "x" * 161},
        {"detail": "x" * 20001},
        {"kind": "Autre"},
        {"author": ""},
        {"project_id": []},
        {"title": "\n"},
        {"client_id": True},
    ],
)
def test_bad_input_does_not_create_sources_or_events(tmp_path, change):
    service, repo, pid, pages = setup(tmp_path)
    with pytest.raises(DomainError):
        service.create("town", ACTOR, values(pid, **change))
    assert service.list("town", ACTOR)["total"] == 0
    assert repo.get_memory("town", pid)["notes"] == []


def test_tenant_permissions_and_rollback_are_enforced(tmp_path, monkeypatch):
    service, repo, pid, pages = setup(tmp_path)
    readonly = {**ACTOR, "permissions": {"workspace": {"read": True, "write": False}}}
    with pytest.raises(DomainError):
        service.create("town", readonly, values(pid))
    with pytest.raises(DomainError):
        service.list("other", ACTOR)
    with pytest.raises(DomainError):
        service.list("town", {**ACTOR, "tenant_id": "other"})

    def fail(*args):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(repo, "_audit", fail)
    with pytest.raises(RuntimeError):
        service.create("town", ACTOR, values(pid))
    assert service.list("town", ACTOR)["total"] == 0 and repo.get_memory("town", pid)["notes"] == []
    assert repo.list_events("town", pid) == []


def test_revision_types_are_strict_and_long_details_are_preserved(tmp_path):
    service, repo, pid, pages = setup(tmp_path)
    detail = ("Constat fictif\n" * 1400)[:20000]
    report = service.create("town", ACTOR, values(pid, detail=detail))
    assert report["detail"] == detail
    for bad in [True, "0", -1]:
        with pytest.raises(DomainError):
            service.update("town", report["id"], ACTOR, expected_revision=bad, status="Levée")
