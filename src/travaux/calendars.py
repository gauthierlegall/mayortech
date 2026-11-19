"""Calendar cache and explicit project links, using the real BSD icalendar parser.

Imported events are not confirmed project facts. Remote calendars remain read-only.
All-day DTEND stays exclusive, as required by RFC 5545.
"""

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from icalendar import Calendar, Event

from .domain import DomainError, canonical_json, content_hash, require_text, utc_now
from .project_access import access_scope


MAX_ICS_BYTES = 2_000_000
MAX_EVENTS = 1000


def _instant(value, default_timezone="Europe/Paris"):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            zone = ZoneInfo(default_timezone)
            localized = value.replace(tzinfo=zone)
            if localized.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != value:
                raise ValueError("nonexistent_local_time")
            return localized
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), ZoneInfo(default_timezone))
    raw = str(value)
    return _instant(
        datetime.fromisoformat(raw.replace("Z", "+00:00")) if "T" in raw else date.fromisoformat(raw),
        default_timezone,
    )


def date_range(start=None, end=None):
    today = datetime.now(timezone.utc).date()
    try:
        lower = _instant(start or (today - timedelta(days=90)).isoformat())
        upper = _instant(end or (today + timedelta(days=180)).isoformat())
        if upper <= lower or upper - lower > timedelta(days=367):
            raise ValueError("range")
    except (ValueError, TypeError, OverflowError, ZoneInfoNotFoundError):
        raise DomainError(
            "invalid_input", "Une période chronologique de 366 jours au maximum est attendue."
        ) from None
    return lower, upper


def parse_ics(content, *, default_timezone="Europe/Paris"):
    if (
        not isinstance(content, (str, bytes))
        or len(content.encode("utf8") if isinstance(content, str) else content) > MAX_ICS_BYTES
    ):
        raise DomainError("invalid_input", "Le fichier calendrier dépasse la limite de deux mégaoctets.")
    try:
        ZoneInfo(default_timezone)
        wire = content.encode("utf8") if isinstance(content, str) else content
        upper_wire = wire.upper()
        if (
            not upper_wire.lstrip(b"\xef\xbb\xbf\r\n ").startswith(b"BEGIN:VCALENDAR")
            or upper_wire.count(b"BEGIN:VEVENT") > MAX_EVENTS
            or upper_wire.count(b"BEGIN:") > 5000
        ):
            raise ValueError("calendar_expected")
        calendar = Calendar.from_ical(wire)
        events = []
        warnings = []
        identities = set()
        for component in calendar.walk("VEVENT"):
            if len(events) >= MAX_EVENTS:
                raise ValueError("event_limit")
            uid = str(component.get("UID", "")).strip()
            if not uid or len(uid) > 1000 or "DTSTART" not in component:
                raise ValueError("event_identity_or_start_missing")
            begin = component.decoded("DTSTART")
            finish = component.decoded("DTEND") if "DTEND" in component else None
            all_day = isinstance(begin, date) and not isinstance(begin, datetime)
            if finish is None:
                duration = (
                    component.decoded("DURATION")
                    if "DURATION" in component
                    else timedelta(days=1)
                    if all_day
                    else timedelta(0)
                )
                finish = begin + duration
            if (
                all_day != (isinstance(finish, date) and not isinstance(finish, datetime))
                or _instant(finish, default_timezone) < _instant(begin, default_timezone)
                or (all_day and finish == begin)
            ):
                raise ValueError("invalid_event_end")
            if isinstance(begin, datetime) and begin.tzinfo is None:
                begin = _instant(begin, default_timezone)
                finish = _instant(finish, default_timezone)
                warnings.append(f"Fuseau {default_timezone} appliqué aux heures flottantes du fichier.")
            recurrence = (
                component.decoded("RECURRENCE-ID").isoformat() if "RECURRENCE-ID" in component else ""
            )
            recurrence_timezone = (
                str(component["RECURRENCE-ID"].params.get("TZID") or "") if recurrence else ""
            )
            sequence = component.decoded("SEQUENCE") if "SEQUENCE" in component else 0
            if (
                isinstance(sequence, bool)
                or not isinstance(sequence, int)
                or not 0 <= sequence <= 2_147_483_647
            ):
                raise ValueError("invalid_sequence")
            stamp = component.decoded("DTSTAMP") if "DTSTAMP" in component else None
            if stamp is not None:
                if not isinstance(stamp, datetime) or stamp.tzinfo is None:
                    raise ValueError("utc_dtstamp_required")
                stamp = stamp.astimezone(timezone.utc).isoformat()
            identity = (uid, recurrence)
            if identity in identities:
                raise ValueError("duplicate_event_identity")
            identities.add(identity)
            if component.get("RRULE"):
                warnings.append(
                    "La récurrence est conservée dans le fichier original ; seules les occurrences présentes dans ce fichier sont affichées."
                )
            title = str(component.get("SUMMARY") or "Sans titre")[:500]
            link = str(component.get("URL") or "")
            parsed = urlsplit(link)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                link = ""
            zone = str(
                component["DTSTART"].params.get("TZID")
                or getattr(getattr(begin, "tzinfo", None), "key", "")
                or ("UTC" if not all_day and begin.utcoffset() == timedelta(0) else default_timezone)
            )
            events.append(
                {
                    "remote_uid": uid,
                    "recurrence_id": recurrence,
                    "recurrence_timezone": recurrence_timezone,
                    "sequence": sequence,
                    "dtstamp": stamp,
                    "title": title,
                    "start": begin.isoformat(),
                    "end": finish.isoformat(),
                    "all_day": all_day,
                    "timezone": zone,
                    "status": str(component.get("STATUS") or "CONFIRMED").lower(),
                    "description": str(component.get("DESCRIPTION") or "")[:10000],
                    "source_url": link,
                }
            )
        return events, list(dict.fromkeys(warnings))
    except DomainError:
        raise
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError, ZoneInfoNotFoundError):
        raise DomainError(
            "invalid_input", "Ce calendrier est invalide, trop volumineux ou contient des dates incohérentes."
        ) from None


def export_ics(events):
    calendar = Calendar()
    calendar.add("prodid", "-//Travaux//Agenda de chantier//FR")
    calendar.add("version", "2.0")
    for item in events:
        event = Event()
        event.add("uid", item.get("remote_uid") or item["id"])
        event.add("summary", item["title"])
        event.add(
            "dtstart",
            date.fromisoformat(item["start"])
            if item["all_day"]
            else datetime.fromisoformat(item["start"].replace("Z", "+00:00")),
        )
        if item["end"] != item["start"]:
            event.add(
                "dtend",
                date.fromisoformat(item["end"])
                if item["all_day"]
                else datetime.fromisoformat(item["end"].replace("Z", "+00:00")),
            )
        event.add("status", str(item.get("status") or "confirmed").upper())
        event.add("description", item.get("description") or "")
        event.add("sequence", item.get("sequence", 0))
        if item.get("dtstamp"):
            event.add("dtstamp", datetime.fromisoformat(item["dtstamp"].replace("Z", "+00:00")))
        if item.get("recurrence_id"):
            raw = item["recurrence_id"]
            if "T" not in raw:
                recurrence_value = date.fromisoformat(raw)
            else:
                recurrence_value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if recurrence_value.tzinfo is not None and recurrence_value.utcoffset() != timedelta(0):
                    try:
                        recurrence_value = recurrence_value.astimezone(
                            ZoneInfo(item.get("recurrence_timezone") or item.get("timezone", "Europe/Paris"))
                        )
                    except ZoneInfoNotFoundError:
                        raise DomainError(
                            "invalid_input",
                            "Le fuseau personnalisé de cet identifiant de récurrence exige le fichier calendrier original.",
                        ) from None
            event.add("recurrence-id", recurrence_value)
        calendar.add_component(event)
    return calendar.to_ical()


class CalendarService:
    def __init__(self, repo, settings, *, hub):
        self.repo, self.settings, self.hub = repo, settings, hub
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS calendar_collections(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
                connection_id TEXT,name TEXT NOT NULL,remote_id TEXT NOT NULL,source_kind TEXT NOT NULL,
                created_at TEXT NOT NULL,UNIQUE(tenant_id,id),UNIQUE(tenant_id,connection_id,remote_id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS calendar_events(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
                calendar_id TEXT NOT NULL,remote_uid TEXT NOT NULL,recurrence_id TEXT NOT NULL,data TEXT NOT NULL,data_hash TEXT NOT NULL,
                project_id TEXT,revision INTEGER NOT NULL DEFAULT 0,deleted INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,
                UNIQUE(tenant_id,id),UNIQUE(tenant_id,calendar_id,remote_uid,recurrence_id),
                FOREIGN KEY(tenant_id,calendar_id) REFERENCES calendar_collections(tenant_id,id),
                FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id))""")
            db.execute("""CREATE TABLE IF NOT EXISTS calendar_event_history(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
                event_id TEXT NOT NULL,action TEXT NOT NULL,data TEXT NOT NULL,actor_id TEXT NOT NULL,created_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS calendar_import_originals(id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
                calendar_id TEXT NOT NULL,sha256 TEXT NOT NULL,content BLOB NOT NULL,created_at TEXT NOT NULL,
                UNIQUE(tenant_id,calendar_id,sha256))""")

    def _actor(self, actor, *, write=False):
        self.hub._actor(actor)
        if actor.get("permissions", {}).get("workspace", {}).get("write" if write else "read") is not True:
            raise DomainError("forbidden", "Vous ne disposez pas des droits nécessaires sur cet agenda.")

    def collections(self, actor):
        self._actor(actor)
        scope = access_scope(self.repo, actor)
        clause, args = ('1=1', []) if scope.all_projects else scope.project_clause('e.project_id')
        with self.repo._lock:
            rows = self.repo._db.execute(
                "SELECT * FROM calendar_collections c WHERE c.tenant_id=? AND "+('1=1' if scope.all_projects else 'EXISTS (SELECT 1 FROM calendar_events e WHERE e.tenant_id=c.tenant_id AND e.calendar_id=c.id AND e.deleted=0 AND '+clause+')')+" ORDER BY c.name,c.id",
                (self.settings.tenant_id, *args),
            ).fetchall()
            items = [
                {key: row[key] for key in ("id", "name", "connection_id", "source_kind")}
                for row in rows
                if self._visible_collection(dict(row))
            ]
        return {"items": items, "total": len(items), "remote_write_enabled": False}

    def _visible_collection(self, collection):
        if not collection["connection_id"]:
            return True
        connection = self.repo._db.execute(
            "SELECT status,selected_calendars FROM connector_connections WHERE tenant_id=? AND id=?",
            (collection["tenant_id"], collection["connection_id"]),
        ).fetchone()
        return bool(
            connection
            and connection["status"] in {"verified", "synced"}
            and collection["remote_id"] in json.loads(connection["selected_calendars"])
        )

    def _collection(self, tenant, calendar_id):
        row = self.repo._db.execute(
            "SELECT * FROM calendar_collections WHERE tenant_id=? AND id=?", (tenant, calendar_id)
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Cet agenda n’existe pas dans votre espace.")
        return dict(row)

    def _dto(self, row):
        collection = self._collection(row["tenant_id"], row["calendar_id"])
        return {
            **json.loads(row["data"]),
            "id": row["id"],
            "calendar_id": row["calendar_id"],
            "calendar_name": collection["name"],
            "project_id": row["project_id"],
            "revision": row["revision"],
            "source_kind": collection["source_kind"],
            "origin": collection["source_kind"],
            "editable": False,
            "assignment_editable": True,
        }

    def event(self, actor, ident):
        self._actor(actor)
        access_scope(self.repo, actor).require_object('calendar_event', ident)
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM calendar_events WHERE tenant_id=? AND id=? AND deleted=0",
                (self.settings.tenant_id, ident),
            ).fetchone()
            if row is None or not self._visible_collection(
                self._collection(row["tenant_id"], row["calendar_id"])
            ):
                raise DomainError(
                    "not_found", "Ce rendez-vous n’est plus disponible dans vos agendas autorisés."
                )
            return self._dto(dict(row))

    def events(self, actor, *, project_id=None, start=None, end=None):
        self._actor(actor)
        scope = access_scope(self.repo, actor)
        if project_id: scope.require_project(project_id)
        clause, args = ('1=1', []) if scope.all_projects else scope.project_clause('project_id')
        lower, upper = date_range(start, end)
        with self.repo._lock:
            if project_id:
                self.repo.get_project(self.settings.tenant_id, project_id)
            rows = self.repo._db.execute(
                "SELECT * FROM calendar_events WHERE tenant_id=? AND deleted=0"
                + (" AND project_id=?" if project_id else "") + ' AND '+clause,
                ((self.settings.tenant_id, project_id) if project_id else (self.settings.tenant_id,)) + tuple(args),
            ).fetchall()
            items = []
            for row in rows:
                if not self._visible_collection(self._collection(row["tenant_id"], row["calendar_id"])):
                    continue
                value = self._dto(dict(row))
                if (
                    _instant(value["start"], value["timezone"]) < upper
                    and _instant(value["end"], value["timezone"]) > lower
                ):
                    items.append(value)
        items.sort(key=lambda item: (item["start"], item["title"], item["id"]))
        return {
            "items": items,
            "total": len(items),
            "start": lower.isoformat(),
            "end": upper.isoformat(),
            "remote_write_enabled": False,
        }

    def _store(
        self, db, tenant, calendar_id, items, actor_id, *, project_id=None, enforce_ics_revision=False
    ):
        counts = {"imported": 0, "updated": 0, "unchanged": 0}
        for value in items:
            identity = (tenant, calendar_id, value["remote_uid"], value.get("recurrence_id", ""))
            previous = db.execute(
                "SELECT * FROM calendar_events WHERE tenant_id=? AND calendar_id=? AND remote_uid=? AND recurrence_id=?",
                identity,
            ).fetchone()
            digest = content_hash(canonical_json(value))
            previous_data = json.loads(previous["data"]) if previous else None
            if previous_data is not None:
                for key, default in [("sequence", 0), ("dtstamp", None), ("recurrence_timezone", "")]:
                    previous_data.setdefault(key, default)
            identical = previous_data is not None and canonical_json(previous_data) == canonical_json(value)
            if previous and (previous["data_hash"] == digest or identical) and not previous["deleted"]:
                counts["unchanged"] += 1
                continue
            if previous and enforce_ics_revision:
                old_sequence = previous_data.get("sequence", 0)
                new_sequence = value.get("sequence", 0)
                old_stamp = previous_data.get("dtstamp")
                new_stamp = value.get("dtstamp")
                newer_stamp = (
                    old_stamp is not None
                    and new_stamp is not None
                    and _instant(new_stamp) > _instant(old_stamp)
                )
                if new_sequence < old_sequence or (new_sequence == old_sequence and not newer_stamp):
                    raise DomainError(
                        "stale_calendar_version",
                        "La version de ce rendez-vous est plus ancienne ou en conflit avec celle déjà conservée. Aucun changement de ce fichier n’a été appliqué.",
                    )
            ident = previous["id"] if previous else str(uuid4())
            if previous:
                db.execute(
                    "UPDATE calendar_events SET data=?,data_hash=?,revision=revision+1,deleted=0,updated_at=? WHERE tenant_id=? AND id=?",
                    (canonical_json(value), digest, utc_now(), tenant, ident),
                )
                counts["updated"] += 1
            else:
                db.execute(
                    "INSERT INTO calendar_events VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        ident,
                        tenant,
                        calendar_id,
                        value["remote_uid"],
                        value.get("recurrence_id", ""),
                        canonical_json(value),
                        digest,
                        project_id,
                        0,
                        0,
                        utc_now(),
                    ),
                )
                counts["imported"] += 1
            db.execute(
                "INSERT INTO calendar_event_history VALUES(?,?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    tenant,
                    ident,
                    "remote.updated" if previous else "imported",
                    canonical_json(value),
                    actor_id,
                    utc_now(),
                ),
            )
        return counts

    def import_ics(self, actor, *, content, name, calendar_id=None, default_timezone="Europe/Paris"):
        scope = access_scope(self.repo, actor)
        if not scope.all_projects:
            raise DomainError('forbidden', 'Un administrateur doit importer les agendas non rattachés.')
        self._actor(actor, write=True)
        if self.settings.mode == "public_demo":
            raise DomainError(
                "forbidden",
                "Les fichiers privés ne peuvent pas être importés dans la démonstration publique.",
            )
        title = require_text(name, "name", maximum=200).strip()
        values, warnings = parse_ics(content, default_timezone=default_timezone)
        wire = content.encode("utf8") if isinstance(content, str) else content
        with self.repo._transaction() as db:
            if calendar_id:
                collection = self._collection(self.settings.tenant_id, calendar_id)
                if collection["source_kind"] != "ics_import":
                    raise DomainError(
                        "forbidden", "Cet agenda distant ne peut pas être remplacé par un import."
                    )
            else:
                calendar_id = str(uuid4())
                db.execute(
                    "INSERT INTO calendar_collections VALUES(?,?,?,?,?,?,?)",
                    (calendar_id, self.settings.tenant_id, None, title, calendar_id, "ics_import", utc_now()),
                )
            counts = self._store(
                db, self.settings.tenant_id, calendar_id, values, actor["actor_id"], enforce_ics_revision=True
            )
            db.execute(
                "INSERT OR IGNORE INTO calendar_import_originals VALUES(?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    self.settings.tenant_id,
                    calendar_id,
                    hashlib.sha256(wire).hexdigest(),
                    wire,
                    utc_now(),
                ),
            )
        return {**counts, "calendar_id": calendar_id, "warnings": warnings, "events": len(values)}

    def assign(self, actor, ident, *, project_id, expected_revision):
        scope = access_scope(self.repo, actor)
        scope.require_object('calendar_event', ident, write=True)
        if project_id: scope.require_project(project_id, write=True)
        elif not scope.all_projects:
            raise DomainError('forbidden', 'Un administrateur doit retirer le rattachement de cet agenda.')
        self._actor(actor, write=True)
        with self.repo._transaction() as db:
            scope.require_object('calendar_event', ident, write=True)
            if project_id: scope.require_project(project_id, write=True)
            row = db.execute(
                "SELECT * FROM calendar_events WHERE tenant_id=? AND id=? AND deleted=0",
                (self.settings.tenant_id, ident),
            ).fetchone()
            if row is None:
                raise DomainError("not_found", "Ce rendez-vous n’existe pas dans votre espace.")
            self.hub._revision(dict(row), expected_revision)
            if project_id:
                self.repo.get_project(self.settings.tenant_id, project_id)
            if (
                self.settings.mode == "public_demo"
                and self._collection(self.settings.tenant_id, row["calendar_id"])["source_kind"]
                != "demo_calendar"
            ):
                raise DomainError(
                    "forbidden",
                    "Seuls les rendez-vous fictifs peuvent être utilisés dans cette démonstration.",
                )
            if row["project_id"] != project_id:
                db.execute(
                    "UPDATE calendar_events SET project_id=?,revision=revision+1,updated_at=? WHERE tenant_id=? AND id=?",
                    (project_id, utc_now(), self.settings.tenant_id, ident),
                )
                db.execute(
                    "INSERT INTO calendar_event_history VALUES(?,?,?,?,?,?,?)",
                    (
                        str(uuid4()),
                        self.settings.tenant_id,
                        ident,
                        "project.assigned",
                        canonical_json({"before": row["project_id"], "after": project_id}),
                        actor["actor_id"],
                        utc_now(),
                    ),
                )
            saved = db.execute(
                "SELECT * FROM calendar_events WHERE tenant_id=? AND id=?", (self.settings.tenant_id, ident)
            ).fetchone()
            return self._dto(dict(saved))

    def export(self, actor, *, project_id=None, start=None, end=None):
        return export_ics(self.events(actor, project_id=project_id, start=start, end=end)["items"])

    def sync(self, actor, ident, *, expected_revision, start=None, end=None):
        self.hub._actor(actor, manage=True, external=True)
        lower, upper = date_range(start, end)
        with self.repo._lock:
            row = self.hub._row(self.settings.tenant_id, ident)
            self.hub._revision(row, expected_revision)
            selected = json.loads(row["selected_calendars"])
            if row["status"] not in {"verified", "synced"} or not selected:
                raise DomainError(
                    "invalid_state", "Choisissez au moins un agenda vérifié avant la synchronisation."
                )
        reader = None
        try:
            reader = self.hub.reader(row)
            result = reader.calendar_events(selected, lower, upper)
            if set(result) != set(selected) or sum(len(items) for items in result.values()) > MAX_EVENTS:
                raise ValueError("scope_or_limit")
        except DomainError:
            raise
        except Exception:
            raise DomainError(
                "integration_unavailable",
                "Les agendas n’ont pas pu être synchronisés. Les rendez-vous précédents sont conservés.",
            ) from None
        finally:
            if reader is not None:
                reader.close()
        totals = {"imported": 0, "updated": 0, "unchanged": 0, "cancelled": 0}
        with self.repo._transaction() as db:
            current = self.hub._row(self.settings.tenant_id, ident)
            self.hub._revision(current, expected_revision)
            choices = {item["id"]: item["name"] for item in json.loads(row["calendar_choices"])}
            for remote_id, items in result.items():
                for item in items:
                    if (
                        not isinstance(item, dict)
                        or not item.get("remote_uid")
                        or _instant(item["end"], item.get("timezone", "Europe/Paris"))
                        < _instant(item["start"], item.get("timezone", "Europe/Paris"))
                    ):
                        raise DomainError("invalid_input", "Un rendez-vous distant est invalide.")
                found = db.execute(
                    "SELECT id FROM calendar_collections WHERE tenant_id=? AND connection_id=? AND remote_id=?",
                    (self.settings.tenant_id, ident, remote_id),
                ).fetchone()
                calendar_id = found["id"] if found else str(uuid4())
                if not found:
                    db.execute(
                        "INSERT INTO calendar_collections VALUES(?,?,?,?,?,?,?)",
                        (
                            calendar_id,
                            self.settings.tenant_id,
                            ident,
                            choices[remote_id],
                            remote_id,
                            row["provider"],
                            utc_now(),
                        ),
                    )
                counts = self._store(db, self.settings.tenant_id, calendar_id, items, actor["actor_id"])
                for key, value in counts.items():
                    totals[key] += value
                seen = {(item["remote_uid"], item.get("recurrence_id", "")) for item in items}
                previous = db.execute(
                    "SELECT * FROM calendar_events WHERE tenant_id=? AND calendar_id=? AND deleted=0",
                    (self.settings.tenant_id, calendar_id),
                ).fetchall()
                for event in previous:
                    data = json.loads(event["data"])
                    if (
                        (event["remote_uid"], event["recurrence_id"]) not in seen
                        and _instant(data["start"], data["timezone"]) < upper
                        and _instant(data["end"], data["timezone"]) > lower
                    ):
                        db.execute(
                            "UPDATE calendar_events SET deleted=1,revision=revision+1,updated_at=? WHERE tenant_id=? AND id=?",
                            (utc_now(), self.settings.tenant_id, event["id"]),
                        )
                        db.execute(
                            "INSERT INTO calendar_event_history VALUES(?,?,?,?,?,?,?)",
                            (
                                str(uuid4()),
                                self.settings.tenant_id,
                                event["id"],
                                "remote.unavailable",
                                event["data"],
                                actor["actor_id"],
                                utc_now(),
                            ),
                        )
                        totals["cancelled"] += 1
            db.execute(
                "UPDATE connector_connections SET status=?,revision=revision+1,last_sync_at=?,last_calendar_sync_at=?,last_error=?,updated_at=? WHERE tenant_id=? AND id=?",
                ("synced", utc_now(), utc_now(), "", utc_now(), self.settings.tenant_id, ident),
            )
        return {
            **totals,
            "connection": self.hub._dto(self.hub._row(self.settings.tenant_id, ident)),
            "remote_write_enabled": False,
        }

    def seed_demo(self, tenant):
        if tenant != self.settings.tenant_id or not self.settings.fixture_mode:
            raise DomainError("forbidden", "Ce corpus est réservé à la démonstration.")
        created = 0
        for reference, title, day in [
            ("TRV-2026-042", "Visite préparatoire du portail — exemple", "2026-11-20"),
            ("TRV-2026-038", "Point de chantier voirie — exemple", "2026-11-23"),
        ]:
            project = next(
                (item for item in self.repo.list_projects(tenant) if item["reference"] == reference), None
            )
            if not project:
                continue
            memory = self.repo.get_memory(tenant, project["id"])
            if not any(source["metadata"].get("fictitious") is True for source in memory["sources"]):
                continue
            calendar_id = "calendar-demo-travaux"
            value = {
                "remote_uid": "demo:" + reference,
                "recurrence_id": "",
                "title": title,
                "start": day,
                "end": (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
                "all_day": True,
                "timezone": "Europe/Paris",
                "status": "tentative",
                "description": "Rendez-vous fictif du scénario de démonstration. Il ne confirme aucune information reçue par mail.",
                "source_url": "",
            }
            with self.repo._transaction() as db:
                db.execute(
                    "INSERT OR IGNORE INTO calendar_collections VALUES(?,?,?,?,?,?,?)",
                    (
                        calendar_id,
                        tenant,
                        None,
                        "Service travaux · exemple",
                        calendar_id,
                        "demo_calendar",
                        utc_now(),
                    ),
                )
                exists = db.execute(
                    "SELECT 1 FROM calendar_events WHERE tenant_id=? AND calendar_id=? AND remote_uid=?",
                    (tenant, calendar_id, value["remote_uid"]),
                ).fetchone()
                if not exists:
                    created += self._store(
                        db, tenant, calendar_id, [value], "operator-demo", project_id=project["id"]
                    )["imported"]
        return {"created": created, "fictitious": True}


def register_calendar_routes(app, repo, tenant, actor, settings, *, hub):
    from fastapi import Depends
    from fastapi.responses import Response
    from pydantic import BaseModel, ConfigDict, Field

    class Import(BaseModel):
        model_config = ConfigDict(extra="forbid")
        content: str = Field(min_length=1, max_length=MAX_ICS_BYTES)
        name: str = Field(default="Agenda importé", min_length=1, max_length=200)
        calendar_id: str | None = Field(default=None, max_length=200)
        timezone: str = Field(default="Europe/Paris", max_length=100)

    class Assignment(BaseModel):
        model_config = ConfigDict(extra="forbid")
        project_id: str | None = Field(default=None, max_length=200)
        expected_revision: int = Field(ge=0, strict=True)

    class Sync(BaseModel):
        model_config = ConfigDict(extra="forbid")
        expected_revision: int = Field(ge=0, strict=True)
        start: str | None = Field(default=None, max_length=50)
        end: str | None = Field(default=None, max_length=50)

    service = CalendarService(repo, settings, hub=hub)

    @app.get("/api/v1/calendars")
    def calendars(current=Depends(actor)):
        return service.collections(current)

    @app.get("/api/v1/calendars/events")
    def events(
        project_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        current=Depends(actor),
    ):
        return service.events(current, project_id=project_id, start=start, end=end)

    @app.get("/api/v1/calendars/events/{ident}")
    def event(ident: str, current=Depends(actor)):
        return service.event(current, ident)

    @app.post("/api/v1/calendars/import-ics", status_code=201)
    def import_calendar(body: Import, current=Depends(actor)):
        return service.import_ics(
            current,
            content=body.content,
            name=body.name,
            calendar_id=body.calendar_id,
            default_timezone=body.timezone,
        )

    @app.patch("/api/v1/calendars/events/{ident}/assignment")
    def assignment(ident: str, body: Assignment, current=Depends(actor)):
        return service.assign(
            current, ident, project_id=body.project_id, expected_revision=body.expected_revision
        )

    @app.post("/api/v1/integrations/connections/{ident}/sync")
    def sync(ident: str, body: Sync, current=Depends(actor)):
        return service.sync(
            current, ident, expected_revision=body.expected_revision, start=body.start, end=body.end
        )

    @app.get("/api/v1/calendars/export.ics")
    def export(
        project_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
        current=Depends(actor),
    ):
        return Response(
            service.export(current, project_id=project_id, start=start, end=end),
            media_type="text/calendar; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="agenda-travaux.ics"'},
        )

    return service
