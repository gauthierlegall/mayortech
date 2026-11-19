from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from travaux.calendars import CalendarService
from travaux.config import Settings
from travaux.connection_hub import ConnectionHub
from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.retrieval import DossierRetrieval


ACTOR = {
    "tenant_id": "town",
    "actor_id": "alice",
    "permissions": {"workspace": {"read": True, "write": True}, "organization": {"write": True}},
}


def ics(title, day, sequence=0):
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//FR\r\nBEGIN:VEVENT\r\nUID:meeting-1\r\n"
        + f"DTSTART;VALUE=DATE:{day:%Y%m%d}\r\nDTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}\r\n"
        + f"SUMMARY:{title}\r\nSEQUENCE:{sequence}\r\nDESCRIPTION:Événement agenda distinct des faits confirmés\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )


def test_calendar_rag_uses_visible_typed_records_and_current_assignments(tmp_path):
    cfg = Settings(db_path=tmp_path / "calendar-rag.sqlite3", tenant_id="town")
    repo = Repository(cfg.db_path)
    hub = ConnectionHub(repo, cfg)
    calendar = CalendarService(repo, cfg, hub=hub)
    project = repo.create_project("town", "TRV-042", "Portail")
    tomorrow = datetime.now(ZoneInfo("Europe/Paris")).date() + timedelta(days=1)
    imported = calendar.import_ics(
        ACTOR, content=ics("Visite thermolaquage", tomorrow), name="Agenda technique"
    )
    event = calendar.events(ACTOR)["items"][0]
    assigned = calendar.assign(
        ACTOR, event["id"], project_id=project["id"], expected_revision=event["revision"]
    )
    retrieval = DossierRetrieval(repo, cfg, calendars=calendar)
    revision = repo.get_project("town", project["id"])["revision"]
    answer = retrieval.answer("town", "Quels rendez-vous demain ?", project_id=project["id"], actor=ACTOR)
    assert "Visite thermolaquage" in answer["content"]
    citation = next(item for item in answer["citations"] if item.get("kind") == "calendar")
    assert citation["calendar_event_id"] == event["id"] and "source_id" not in citation
    assert citation["href"].startswith("#/agenda?event=")
    assert citation["record_hash"] and citation["calendar_revision"] == assigned["revision"]
    assert answer["context"]["calendar_revisions"][event["id"]]["record_hash"] == citation["record_hash"]
    assert repo.get_project("town", project["id"])["revision"] == revision
    assert repo.get_memory("town", project["id"])["facts"] == []
    changed = calendar.import_ics(
        ACTOR,
        content=ics("Visite thermolaquage reportée", tomorrow, sequence=1),
        name="Agenda technique",
        calendar_id=imported["calendar_id"],
    )
    assert changed["updated"] == 1
    fresh = retrieval.answer("town", "Quels rendez-vous demain ?", project_id=project["id"], actor=ACTOR)
    assert "reportée" in fresh["content"]
    assert fresh["context"]["calendar_revisions"][event["id"]]["record_hash"] != citation["record_hash"]
    current = calendar.events(ACTOR)["items"][0]
    calendar.assign(ACTOR, event["id"], project_id=None, expected_revision=current["revision"])
    detached = retrieval.answer("town", "Quels rendez-vous demain ?", project_id=project["id"], actor=ACTOR)
    assert not any(item.get("kind") == "calendar" for item in detached["citations"])
    assert event["id"] not in detached["context"]["calendar_revisions"]
    global_answer = retrieval.answer("town", "Quels rendez-vous demain ?", actor=ACTOR)
    assert any(
        item.get("kind") == "calendar" and item["project_id"] is None for item in global_answer["citations"]
    )
    repo.close()


def test_calendar_rag_rejects_mismatched_tenant_provider_and_unauthorized_actor(tmp_path):
    cfg = Settings(db_path=tmp_path / "calendar-rag.sqlite3", tenant_id="town")
    repo = Repository(cfg.db_path)
    calendar = CalendarService(repo, cfg, hub=ConnectionHub(repo, cfg))
    tomorrow = datetime.now(ZoneInfo("Europe/Paris")).date() + timedelta(days=1)
    calendar.import_ics(ACTOR, content=ics("RENDEZVOUS-PRIVE-TOWN", tomorrow), name="Privé")
    retrieval = DossierRetrieval(repo, cfg, calendars=calendar)
    with pytest.raises(DomainError):
        retrieval.search("other", "demain", actor={**ACTOR, "tenant_id": "other"})
    with pytest.raises(DomainError):
        retrieval.search("town", "demain", actor={**ACTOR, "permissions": {}})
    with pytest.raises(DomainError):
        retrieval.search("town", "demain")
    repo.close()


def test_calendar_reminder_resolves_when_synced_event_moves_outside_window(tmp_path):
    from travaux.notifications import NotificationService

    cfg = Settings(db_path=tmp_path / "calendar-reminder.sqlite3", tenant_id="town")
    repo = Repository(cfg.db_path)
    calendar = CalendarService(repo, cfg, hub=ConnectionHub(repo, cfg))
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    imported = calendar.import_ics(
        ACTOR, content=ics("Visite demain", today + timedelta(days=1)), name="Travaux"
    )
    notifications = NotificationService(repo, cfg, calendars=calendar)
    first = notifications.list("town", ACTOR, "private:alice")
    reminder = next(item for item in first["items"] if item["kind"] == "calendar")
    assert reminder["href"].startswith("#/agenda?event=") and reminder["resolved_at"] is None
    calendar.import_ics(
        ACTOR,
        content=ics("Visite reportée", today + timedelta(days=5), sequence=1),
        name="Travaux",
        calendar_id=imported["calendar_id"],
    )
    after = notifications.list("town", ACTOR, "private:alice")
    assert next(item for item in after["items"] if item["id"] == reminder["id"])["resolved_at"]
    assert after["unread"] == 0
    repo.close()
