"""Typed calendar evidence retrieved through CalendarService's visibility checks."""

from datetime import date, datetime, timedelta
import re
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .domain import DomainError, canonical_json, content_hash, normalized


def calendar_intent(query):
    return bool(
        re.search(
            r"agenda|rendez|reunion|visite|demain|aujourd|semaine|calendrier|planning", normalized(query)
        )
    )


def calendar_window(query):
    text = normalized(query)
    today = datetime.now(ZoneInfo("Europe/Paris")).date()
    first, last, direct = today - timedelta(days=90), today + timedelta(days=180), False
    if "apres-demain" in text or "apres demain" in text:
        first, last, direct = today + timedelta(days=2), today + timedelta(days=3), True
    elif "demain" in text:
        first, last, direct = today + timedelta(days=1), today + timedelta(days=2), True
    elif "aujourd" in text:
        first, last, direct = today, today + timedelta(days=1), True
    elif "semaine" in text:
        first = today - timedelta(days=today.weekday())
        if "prochaine" in text:
            first += timedelta(days=7)
        last, direct = first + timedelta(days=7), True
    else:
        exact = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        year = re.search(r"\b(20\d{2})\b", text)
        try:
            if exact and calendar_intent(query):
                first = date.fromisoformat(exact.group(1))
                last, direct = first + timedelta(days=1), True
            elif year and calendar_intent(query):
                first, last = date(int(year.group(1)), 1, 1), date(int(year.group(1)) + 1, 1, 1)
                direct = True
        except ValueError:
            raise DomainError("invalid_input", "La date demandée pour l’agenda est invalide.") from None
    return first.isoformat(), last.isoformat(), direct


def calendar_documents(service, tenant, current, query, *, project_id=None, projects=None):
    if (
        not isinstance(current, dict)
        or current.get("tenant_id") != tenant
        or service.settings.tenant_id != tenant
        or current.get("permissions", {}).get("workspace", {}).get("read") is not True
    ):
        raise DomainError("forbidden", "Ces agendas ne sont pas autorisés dans ce périmètre.")
    start, end, direct = calendar_window(query)
    # Never query the cache directly: deselected/disconnected calendars must
    # disappear from retrieval just as they disappear from the calendar UI.
    response = service.events(current, project_id=project_id, start=start, end=end)
    docs, versions = [], {}
    by_project = {item["id"]: item for item in projects or []}
    for event in response["items"][:500]:
        if event["project_id"] and event["project_id"] not in by_project:
            continue
        snapshot = {
            key: event.get(key)
            for key in (
                "id",
                "calendar_id",
                "calendar_name",
                "project_id",
                "revision",
                "source_kind",
                "title",
                "start",
                "end",
                "all_day",
                "timezone",
                "status",
                "description",
            )
        }
        digest = content_hash(canonical_json(snapshot))
        record = (
            f"Rendez-vous : {event['title']}\nDébut : {event['start']}\n"
            + f"Fin{' exclusive (journée entière)' if event['all_day'] else ''} : {event['end']}\n"
            + f"État dans l’agenda : {event['status']}\n{event.get('description', '')}"
        ).strip()
        project = by_project.get(event["project_id"], {})
        docs.append(
            {
                "kind": "calendar",
                "calendar_event_id": event["id"],
                "calendar_id": event["calendar_id"],
                "calendar_revision": event["revision"],
                "record_hash": digest,
                "quote": record[:1200],
                "title": event["title"],
                "project_id": event["project_id"],
                "project_name": project.get("name") or "Agenda — " + event["calendar_name"],
                "project_reference": project.get("reference", ""),
                "relations": [],
                "href": "#/agenda?" + urlencode({"event": event["id"], "date": event["start"][:10]}),
                "calendar_start": event["start"],
                "record_type": "calendar_event",
                "is_project_fact": False,
            }
        )
        versions[event["id"]] = {"revision": event["revision"], "record_hash": digest}
    return docs, versions, {"start": start, "end": end, "direct": direct}
