from datetime import date, datetime

import pytest
from icalendar import Calendar

from travaux.calendars import CalendarService, parse_ics, export_ics
from travaux.connection_hub import ConnectionHub, IntegrationPolicy
from travaux.config import Settings
from travaux.domain import DomainError
from travaux.repository import Repository


ICS = """BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//FR\r\nBEGIN:VEVENT\r\nUID:visite-1\r\nDTSTART;TZID=Europe/Paris:20261120T090000\r\nDTEND;TZID=Europe/Paris:20261120T100000\r\nSUMMARY:Visite du portail\r\nDESCRIPTION:Accès à confirmer\r\nSTATUS:TENTATIVE\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nUID:journee-1\r\nDTSTART;VALUE=DATE:20261123\r\nDTEND;VALUE=DATE:20261125\r\nSUMMARY:Intervention voirie\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"""
ACTOR = {
    "actor_id": "operator",
    "tenant_id": "commune",
    "permissions": {"organization": {"write": True}, "workspace": {"read": True, "write": True}},
}


def service(tmp_path, mode="demo"):
    cfg = (
        Settings(db_path=tmp_path / "calendars.sqlite3", tenant_id="commune")
        if mode == "demo"
        else Settings(
            mode=mode,
            db_path=tmp_path / "calendars.sqlite3",
            tenant_id="commune",
            password_hash="scrypt$x$x",
            public_origin="https://travaux.example.org",
            allowed_hosts=("travaux.example.org",),
        )
    )
    repo = Repository(cfg.db_path)
    hub = ConnectionHub(repo, cfg, policy=IntegrationPolicy())
    return CalendarService(repo, cfg, hub=hub), repo


def test_real_icalendar_parser_preserves_dst_all_day_and_exclusive_end():
    events, warnings = parse_ics(ICS)
    assert len(events) == 2
    timed = events[0]
    assert timed["start"] == "2026-11-20T09:00:00+01:00" and timed["timezone"] == "Europe/Paris"
    assert timed["status"] == "tentative" and not timed["all_day"]
    assert events[1]["start"] == "2026-11-23" and events[1]["end"] == "2026-11-25" and events[1]["all_day"]
    again, _ = parse_ics(export_ics(events).decode("utf8"))
    assert [(x["start"], x["end"], x["title"], x["status"]) for x in again] == [
        (x["start"], x["end"], x["title"], x["status"]) for x in events
    ]
    assert warnings == []


def test_event_link_resolves_outside_current_month_and_rechecks_visibility(tmp_path):
    calendar, repo = service(tmp_path)
    calendar.import_ics(ACTOR, content=ICS, name="Agenda")
    event = calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"][0]
    assert calendar.events(ACTOR, start="2027-01-01", end="2027-02-01")["items"] == []
    assert calendar.event(ACTOR, event["id"])["start"] == event["start"]
    with pytest.raises(DomainError):
        calendar.event({**ACTOR, "tenant_id": "other"}, event["id"])
    with repo._transaction() as db:
        db.execute("UPDATE calendar_events SET deleted=1 WHERE id=?", (event["id"],))
    with pytest.raises(DomainError) as missing:
        calendar.event(ACTOR, event["id"])
    assert missing.value.code == "not_found"


@pytest.mark.parametrize(
    "uid,recurrence,is_date",
    [
        ("journee-1", "RECURRENCE-ID;VALUE=DATE:20261120", True),
        ("visite-1", "RECURRENCE-ID;TZID=Europe/Paris:20261118T090000", False),
        ("visite-1", "RECURRENCE-ID:20261118T090000", False),
    ],
)
def test_recurrence_identity_roundtrip_preserves_original_date_or_datetime_type(uid, recurrence, is_date):
    source = ICS.replace(f"UID:{uid}\r\n", f"UID:{uid}\r\n{recurrence}\r\n")
    imported, _ = parse_ics(source)
    identity = next(item["recurrence_id"] for item in imported if item["remote_uid"] == uid)
    wire = export_ics(imported)
    exported = next(item for item in Calendar.from_ical(wire).walk("VEVENT") if str(item["UID"]) == uid)
    value = exported.decoded("RECURRENCE-ID")
    assert (isinstance(value, date) and not isinstance(value, datetime)) is is_date
    restored, _ = parse_ics(wire)
    assert next(item["recurrence_id"] for item in restored if item["remote_uid"] == uid) == identity


def test_parser_never_follows_calendar_urls_or_expands_unbounded_recurrence():
    recurring = ICS.replace(
        "SUMMARY:Visite du portail",
        "SUMMARY:Visite du portail\r\nRRULE:FREQ=SECONDLY\r\nURL:javascript:alert(1)",
    )
    events, warnings = parse_ics(recurring)
    assert len(events) == 2 and events[0]["source_url"] == ""
    assert any("récurrence" in item.lower() for item in warnings)
    with pytest.raises(DomainError):
        parse_ics("BEGIN:VCALENDAR\n" + "x" * 2_000_001)
    with pytest.raises(DomainError):
        parse_ics(ICS.replace("20261120T100000", "20261120T080000"))
    no_end = ICS.replace("DTEND;TZID=Europe/Paris:20261120T100000\r\n", "")
    instant, _ = parse_ics(no_end)
    assert instant[0]["end"] == instant[0]["start"]
    with pytest.raises(DomainError):
        parse_ics(
            "BEGIN:VCALENDAR\r\n"
            + ("BEGIN:VEVENT\r\nUID:a\r\nDTSTART;VALUE=DATE:20261120\r\nEND:VEVENT\r\n" * 1001)
            + "END:VCALENDAR"
        )


def test_import_is_idempotent_and_project_assignment_is_explicit_revision_checked(tmp_path):
    calendar, repo = service(tmp_path)
    project = repo.create_project("commune", "TRV-042", "Portail")
    first = calendar.import_ics(ACTOR, content=ICS, name="Agenda travaux")
    assert first["imported"] == 2
    items = calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]
    assert all(x["project_id"] is None for x in items)
    event = items[0]
    assigned = calendar.assign(
        ACTOR, event["id"], project_id=project["id"], expected_revision=event["revision"]
    )
    assert assigned["project_id"] == project["id"]
    with pytest.raises(DomainError):
        calendar.assign(ACTOR, event["id"], project_id=None, expected_revision=event["revision"])
    second = calendar.import_ics(ACTOR, content=ICS, name="Agenda travaux", calendar_id=first["calendar_id"])
    assert second["imported"] == 0 and second["unchanged"] == 2
    same = calendar.events(ACTOR, project_id=project["id"], start="2026-11-01", end="2026-12-01")["items"]
    assert [x["id"] for x in same] == [event["id"]]
    assert same[0]["revision"] == assigned["revision"]
    assert len(calendar.events(ACTOR, start="2026-11-24", end="2026-11-25")["items"]) == 1
    assert "BEGIN:VEVENT" in calendar.export(ACTOR, project_id=project["id"]).decode("utf8")


def test_public_import_refused_and_fixture_seed_requires_fictitious_project(tmp_path):
    calendar, repo = service(tmp_path, "public_demo")
    with pytest.raises(DomainError):
        calendar.import_ics(ACTOR, content=ICS, name="Données privées")
    assert calendar.seed_demo("commune")["created"] == 0
    project = repo.create_project("commune", "TRV-2026-042", "Portail")
    source = repo.ingest_source(
        "commune",
        "demo-source",
        "Exemple",
        "Texte",
        project_ref="TRV-2026-042",
        metadata={"fictitious": True},
    )
    assert source["project_id"] == project["id"]
    result = calendar.seed_demo("commune")
    assert result["created"] == 1
    assert calendar.seed_demo("commune")["created"] == 0
    item = calendar.events(ACTOR, project_id=project["id"], start="2026-11-01", end="2026-12-01")["items"][0]
    assert item["source_kind"] == "demo_calendar" and item["status"] == "tentative"


def test_tenant_and_write_permissions_are_enforced_and_headers_never_become_html(tmp_path):
    calendar, _ = service(tmp_path)
    with pytest.raises(DomainError):
        calendar.events({**ACTOR, "tenant_id": "elsewhere"})
    with pytest.raises(DomainError):
        calendar.import_ics(
            {**ACTOR, "permissions": {"workspace": {"write": False}}}, content=ICS, name="Agenda"
        )
    calendar.import_ics(
        ACTOR,
        content=ICS.replace("SUMMARY:Visite du portail", "SUMMARY:<script>alert(1)</script>"),
        name="Agenda",
    )
    items = calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]
    assert any(item["title"] == "<script>alert(1)</script>" for item in items)
    with pytest.raises(DomainError):
        calendar.events(ACTOR, start="2026-12-01", end="2026-11-01")
    with pytest.raises(DomainError):
        calendar.events(ACTOR, start="2026-01-01", end="2028-01-01")


def test_sync_is_scoped_atomic_and_preserves_human_links_while_archiving_missing_events(tmp_path):
    calendar, repo = service(tmp_path, "staging")
    calendar.hub.policy = IntegrationPolicy(True, ("cal.example.org",))
    first_events, _ = parse_ics(ICS)

    class Reader:
        values = {"remote-calendar": first_events}

        def __init__(self, *args):
            pass

        def probe(self):
            return {"calendars": [{"id": "remote-calendar", "name": "Service travaux"}], "mail_folders": []}

        def calendar_events(self, *args):
            return type(self).values

        def close(self):
            pass

    calendar.hub.reader_factory = Reader
    connection = calendar.hub.create(
        ACTOR,
        {
            "provider": "caldav",
            "label": "Mairie",
            "endpoint": "https://cal.example.org/dav",
            "username": "agent",
            "password": "fixture-password",
        },
    )
    connection = calendar.hub.probe(ACTOR, connection["id"], expected_revision=0)
    connection = calendar.hub.select(
        ACTOR,
        connection["id"],
        calendar_ids=["remote-calendar"],
        folder_ids=[],
        expected_revision=connection["revision"],
    )
    result = calendar.sync(
        ACTOR,
        connection["id"],
        expected_revision=connection["revision"],
        start="2026-11-01",
        end="2026-12-01",
    )
    assert result["imported"] == 2 and result["connection"]["last_calendar_sync_at"]
    assert result["connection"]["last_mail_sync_at"] is None
    event = next(
        item
        for item in calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]
        if item["remote_uid"] == "visite-1"
    )
    project = repo.create_project("commune", "TRV-1", "Portail")
    assigned = calendar.assign(
        ACTOR, event["id"], project_id=project["id"], expected_revision=event["revision"]
    )
    Reader.values = {"outside-scope": first_events}
    with pytest.raises(DomainError):
        calendar.sync(
            ACTOR,
            connection["id"],
            expected_revision=result["connection"]["revision"],
            start="2026-11-01",
            end="2026-12-01",
        )
    assert len(calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]) == 2
    Reader.values = {"remote-calendar": [{**first_events[0], "title": "Visite déplacée"}]}
    updated = calendar.sync(
        ACTOR,
        connection["id"],
        expected_revision=result["connection"]["revision"],
        start="2026-11-01",
        end="2026-12-01",
    )
    assert updated["updated"] == 1 and updated["cancelled"] == 1
    kept = calendar.events(ACTOR, project_id=project["id"], start="2026-11-01", end="2026-12-01")["items"][0]
    assert (
        kept["id"] == event["id"]
        and kept["project_id"] == project["id"]
        and kept["revision"] > assigned["revision"]
    )
    assert repo._db.execute("SELECT count(*) FROM calendar_events WHERE deleted=1").fetchone()[0] == 1
    calendar.hub.select(
        ACTOR,
        connection["id"],
        calendar_ids=[],
        folder_ids=[],
        expected_revision=updated["connection"]["revision"],
    )
    assert calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"] == []


@pytest.mark.parametrize(
    "sequence,stamp",
    [
        (1, "20261119T100000Z"),
        (2, "20261117T100000Z"),
        (2, "20261118T100000Z"),
    ],
)
def test_ics_replay_cannot_resurrect_cancelled_event_or_overwrite_equal_revision(tmp_path, sequence, stamp):
    calendar, repo = service(tmp_path)
    cancelled = ICS.replace(
        "UID:visite-1\r\n", "UID:visite-1\r\nSEQUENCE:2\r\nDTSTAMP:20261118T100000Z\r\n"
    ).replace("STATUS:TENTATIVE", "STATUS:CANCELLED")
    first = calendar.import_ics(ACTOR, content=cancelled, name="Suivi")
    event = next(
        item
        for item in calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]
        if item["remote_uid"] == "visite-1"
    )
    stale = ICS.replace(
        "UID:visite-1\r\n", f"UID:visite-1\r\nSEQUENCE:{sequence}\r\nDTSTAMP:{stamp}\r\n"
    ).replace("STATUS:TENTATIVE", "STATUS:CONFIRMED")
    with pytest.raises(DomainError, match="version"):
        calendar.import_ics(ACTOR, content=stale, name="Ancien fichier", calendar_id=first["calendar_id"])
    kept = next(
        item
        for item in calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]
        if item["remote_uid"] == "visite-1"
    )
    assert (
        kept["id"] == event["id"] and kept["revision"] == event["revision"] and kept["status"] == "cancelled"
    )
    assert repo._db.execute("SELECT count(*) FROM calendar_import_originals").fetchone()[0] == 1
    assert (
        calendar.import_ics(ACTOR, content=cancelled, name="Identique", calendar_id=first["calendar_id"])[
            "unchanged"
        ]
        == 2
    )


def test_newer_ics_sequence_or_stamp_updates_and_roundtrips_source_version(tmp_path):
    calendar, _ = service(tmp_path)
    initial = ICS.replace("UID:visite-1\r\n", "UID:visite-1\r\nSEQUENCE:2\r\nDTSTAMP:20261118T100000Z\r\n")
    first = calendar.import_ics(ACTOR, content=initial, name="Suivi")
    newer_stamp = initial.replace("20261118T100000Z", "20261119T100000Z").replace(
        "SUMMARY:Visite du portail", "SUMMARY:Visite à relire"
    )
    assert (
        calendar.import_ics(ACTOR, content=newer_stamp, name="Suivi", calendar_id=first["calendar_id"])[
            "updated"
        ]
        == 1
    )
    newer_sequence = (
        newer_stamp.replace("SEQUENCE:2", "SEQUENCE:3")
        .replace("20261119T100000Z", "20261117T100000Z")
        .replace("SUMMARY:Visite à relire", "SUMMARY:Nouveau planning")
    )
    assert (
        calendar.import_ics(ACTOR, content=newer_sequence, name="Suivi", calendar_id=first["calendar_id"])[
            "updated"
        ]
        == 1
    )
    event = next(
        item
        for item in calendar.events(ACTOR, start="2026-11-01", end="2026-12-01")["items"]
        if item["remote_uid"] == "visite-1"
    )
    assert event["sequence"] == 3 and event["dtstamp"] == "2026-11-17T10:00:00+00:00"
    roundtrip, _ = parse_ics(export_ics([event]))
    assert roundtrip[0]["sequence"] == event["sequence"] and roundtrip[0]["dtstamp"] == event["dtstamp"]
