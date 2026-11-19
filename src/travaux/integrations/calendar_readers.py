"""Read-only wrappers around python-caldav 3.7 and exchangelib 5.x.

API/source references and license choices: docs/CONNECTEURS_AGENDAS_2026.md.
Discovery, REPORT and EWS calendarView are delegated to the maintained clients.
"""

import importlib
import json
import logging
import os
import time
from pathlib import Path

from ..calendars import MAX_EVENTS, parse_ics
from ..domain import DomainError


def _safe_environment():
    if os.getenv("SSLKEYLOGFILE") or os.getenv("QUICLOGDIR") or os.getenv("PYTHON_CALDAV_COMMDUMP"):
        raise DomainError(
            "integration_unavailable",
            "Désactivez les journaux de débogage TLS et CalDAV avant une connexion institutionnelle.",
        )


def _suppress_sensitive_sdk_logs(namespace):
    # SDK repair/HTTP diagnostics can contain an entire ICS/SOAP document or
    # authorization header. Keep only our explicitly sanitized API failures.
    logger = logging.getLogger(namespace)
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False


class GuardedDAVSession:
    """Keep the SDK protocol, guard each actual request (including redirects)."""

    def __init__(self, session, policy, hostname):
        self._session, self.policy, self.hostname = session, policy, hostname
        self._session.trust_env = False
        self._deadline = time.monotonic() + 60
        self._requests = 0

    def __getattr__(self, name):
        return getattr(self._session, name)

    def request(self, method, url, **kwargs):
        _safe_environment()
        if method.upper() not in {"GET", "HEAD", "OPTIONS", "PROPFIND", "REPORT"}:
            raise DomainError("forbidden", "Le connecteur agenda fonctionne uniquement en lecture.")
        self.policy.endpoint(str(url), resolve=True, same_host=self.hostname)
        remaining = self._deadline - time.monotonic()
        self._requests += 1
        if remaining <= 0 or self._requests > 50:
            raise DomainError(
                "integration_unavailable",
                "La lecture de cet agenda dépasse la limite de cette synchronisation.",
            )
        kwargs.update(allow_redirects=False, verify=True, timeout=min(15, remaining), stream=True)
        response = self._session.request(method, url, **kwargs)
        content = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > 4_000_000:
                    raise DomainError(
                        "integration_unavailable", "La réponse de cet agenda est trop volumineuse."
                    )
            # requests and niquests both expose the buffered response to DAVResponse.
            response._content = bytes(content)
            response._content_consumed = True
        finally:
            response.close()
        return response

    def close(self):
        return self._session.close()


class CalDAVReader:
    def __init__(self, profile, secrets, policy, *, sdk=None):
        _safe_environment()
        _suppress_sensitive_sdk_logs("caldav")
        self.profile, self.policy = profile, policy
        self.hostname = policy.endpoint(profile["endpoint"], resolve=True)
        sdk = sdk or importlib.import_module("caldav")
        self.client = sdk.DAVClient(
            url=profile["endpoint"],
            username=profile["username"],
            password=secrets["password"],
            ssl_verify_cert=True,
            require_tls=True,
            enable_rfc6764=False,
            timeout=15,
            huge_tree=False,
            rate_limit_handle=False,
        )
        self.client.session = GuardedDAVSession(self.client.session, policy, self.hostname)
        self._calendars = None

    def _choices(self):
        if self._calendars is None:
            calendars = self.client.principal().calendars()
            if len(calendars) > 100:
                raise ValueError("calendar_limit")
            self._calendars = {}
            for calendar in calendars:
                ident = str(calendar.url)
                self.policy.endpoint(ident, same_host=self.hostname)
                if ident in self._calendars:
                    raise ValueError("duplicate_calendar")
                self._calendars[ident] = calendar
        return self._calendars

    def probe(self):
        return {
            "calendars": [
                {"id": ident, "name": str(calendar.name or ident)[:500]}
                for ident, calendar in self._choices().items()
            ],
            "mail_folders": [],
        }

    def calendar_events(self, selected, start, end):
        choices = self._choices()
        if any(ident not in choices for ident in selected):
            raise ValueError("calendar_out_of_scope")
        result = {}
        total = 0
        wire_bytes = 0
        for ident in selected:
            result[ident] = []
            # SDK 3.7 still expands locally with expand=True, even when
            # server_expand=True. These false flags bypass that processing;
            # server_expand still emits CALDAV:expand in the bounded REPORT.
            values = choices[ident].search(
                event=True,
                start=start,
                end=end,
                expand=False,
                server_expand=True,
                split_expanded=False,
                post_filter=False,
                compatibility_workarounds=False,
            )
            for value in values:
                wire = value.data
                wire_bytes += len(wire.encode("utf8") if isinstance(wire, str) else wire)
                if wire_bytes > 5_000_000:
                    raise ValueError("calendar_payload_limit")
                events, warnings = parse_ics(wire)
                if any("récurrence" in warning.lower() for warning in warnings):
                    raise DomainError(
                        "integration_unavailable",
                        "Le serveur n’a pas développé cette récurrence. La synchronisation est arrêtée ; les rendez-vous précédents sont conservés.",
                    )
                total += len(events)
                if total > MAX_EVENTS:
                    raise ValueError("calendar_event_limit")
                result[ident].extend(events)
        return result

    def close(self):
        self.client.close()


class ExchangeCalendarReader:
    def __init__(self, profile, secrets, policy):
        _safe_environment()
        _suppress_sensitive_sdk_logs("exchangelib")
        self.profile, self.policy = profile, policy
        policy.endpoint(profile["endpoint"], resolve=True)
        from .exchange import EWSReadOnlyCollector, EWSSettings

        folders = tuple(json.loads(profile.get("selected_folders", "[]"))) or ("discovery-only",)
        config = EWSSettings(
            enabled=True,
            endpoint=profile["endpoint"],
            mailbox=profile["mailbox"],
            allowed_folder_ids=folders,
            max_batch=5,
        )
        self.reader = EWSReadOnlyCollector.connect(
            config, username=profile["username"], password=secrets["password"]
        )
        self.account, self.sdk = self.reader._account, self.reader._sdk
        # The municipal workspace uses Europe/Paris; request each event's own
        # timezone as well so all-day values are converted before taking .date().
        self.account.default_timezone = self.sdk.EWSTimeZone("Europe/Paris")
        self.account.protocol.TIMEOUT = 15

    def probe(self):
        calendar = self.account.calendar
        inbox = self.account.inbox
        return {
            "calendars": [{"id": calendar.id, "name": str(calendar.name or "Calendrier Exchange")}],
            "mail_folders": [{"id": inbox.id, "name": str(inbox.name or "Boîte de réception")}],
        }

    def calendar_events(self, selected, start, end):
        calendar = self.account.calendar
        if selected != [calendar.id]:
            raise ValueError("calendar_out_of_scope")
        query = calendar.view(
            start=self.sdk.EWSDateTime.from_datetime(start), end=self.sdk.EWSDateTime.from_datetime(end)
        )
        query = query.only(
            "subject",
            "uid",
            "start",
            "end",
            "original_start",
            "start_timezone",
            "is_all_day",
            "location",
            "is_cancelled",
            "type",
        )
        query.page_size = 50
        items = []
        for index, item in enumerate(query[: MAX_EVENTS + 1]):
            if index >= MAX_EVENTS or isinstance(item, Exception):
                raise ValueError("exchange_calendar_limit_or_failure")
            begin, finish = item.start, item.end
            all_day = bool(item.is_all_day)
            if all_day:
                zone = getattr(item, "start_timezone", None) or self.account.default_timezone
                begin, finish = begin.astimezone(zone).date(), finish.astimezone(zone).date()
            recurring = getattr(item, "type", "Single") in {"Occurrence", "Exception"}
            original = getattr(item, "original_start", None)
            recurrence = (original or item.start).isoformat() if recurring else ""
            items.append(
                {
                    "remote_uid": str(item.uid or item.id),
                    "recurrence_id": recurrence,
                    "title": str(item.subject or "Sans titre")[:500],
                    "start": begin.isoformat(),
                    "end": finish.isoformat(),
                    "all_day": all_day,
                    "timezone": str(self.account.default_timezone.key),
                    "status": "cancelled" if item.is_cancelled else "confirmed",
                    "description": str(item.location or "")[:10000],
                    "source_url": "",
                }
            )
        return {calendar.id: items}

    def collect_mail(self, repo, tenant, connection_id, *, guard):
        from email import policy as email_policy
        from email.parser import BytesHeaderParser
        from .exchange_sync import (
            DurableReceipt,
            EWSIncrementalCollector,
            ExchangelibChangeSource,
            SQLiteSyncCheckpointStore,
        )
        from .mail import MailParseError
        from ..documents import DocumentRepository
        from ..importing import import_mail
        from ..jobs import JobQueue
        from .exchange_backfill import find_existing_exchange_original

        queue = JobQueue(Path(repo.path))
        originals = DocumentRepository(repo)
        collector = EWSIncrementalCollector(
            tenant_id=tenant,
            connection_id=connection_id,
            settings=self.reader.settings,
            source=ExchangelibChangeSource(self.reader),
            checkpoints=SQLiteSyncCheckpointStore(repo.path),
        )

        def persist(event):
            metadata = {
                "connection_id": connection_id,
                "folder_id": event.folder_id,
                "remote_id": event.remote_id,
                "change_key": event.change_key,
                "event_kind": event.kind,
            }
            with repo._transaction():
                guard()
                if event.kind in {"create", "update"} and event.mime:
                    if find_existing_exchange_original(repo._db, tenant, connection_id, event.sha256):
                        return DurableReceipt(event.idempotency_key, True)
                    try:
                        import_mail(
                            repo,
                            queue,
                            tenant,
                            event.mime,
                            external_id=f"ews:{connection_id}:{event.remote_id}",
                            metadata=metadata,
                        )
                    except MailParseError:
                        header = BytesHeaderParser(policy=email_policy.default).parsebytes(
                            event.mime[:65536].split(b"\r\n\r\n", 1)[0]
                        )
                        source = repo.ingest_source(
                            tenant,
                            f"ews-quarantine:{event.idempotency_key}",
                            str(header.get("Subject", "Message Exchange non analysé"))[:1000],
                            "Message non analysé. Consulter son original et vérifier son rattachement avant toute synthèse.",
                            metadata={
                                **metadata,
                                "raw_sha256": event.sha256,
                                "warnings": ["mail_quarantined_review_required"],
                                "review_required": True,
                            },
                        )
                        originals.store(
                            tenant, source["id"], event.mime, "courrier.eml", "message/rfc822", kind="email"
                        )
                else:
                    repo.ingest_source(
                        tenant,
                        f"ews-event:{event.idempotency_key}",
                        "Événement Exchange à vérifier",
                        "Message déplacé, supprimé ou devenu indisponible dans le serveur. Cet événement n’efface aucune preuve du dossier.",
                        metadata={**metadata, "warnings": ["review_required"], "review_required": True},
                    )
            return DurableReceipt(event.idempotency_key, True)

        reports = []
        remaining = []
        for folder_id in self.reader.settings.allowed_folder_ids:
            for _ in range(3):
                guard()
                report = collector.collect_once(folder_id, sink=persist)
                reports.append(
                    {
                        "folder_id": folder_id,
                        "accepted": report.accepted,
                        "has_more": report.has_more,
                        "checkpoint_revision": report.checkpoint_revision,
                    }
                )
                if not report.has_more:
                    break
            remaining.append(report.has_more)
        return {
            "accepted": sum(item["accepted"] for item in reports),
            "batches": reports,
            "more_available": any(remaining),
            "remote_write_enabled": False,
        }

    def read_history_page(self, folder_id, *, sync_state, start, end, page_size=5):
        from .exchange_backfill import ExchangeHistorySource

        return ExchangeHistorySource(self.reader).read_page(
            folder_id, sync_state=sync_state, start=start, end=end, page_size=page_size
        )

    def close(self):
        self.account.protocol.close()


def open_reader(profile, secrets, policy):
    if profile["provider"] == "caldav":
        return CalDAVReader(profile, secrets, policy)
    if profile["provider"] == "exchange":
        return ExchangeCalendarReader(profile, secrets, policy)
    raise DomainError("integration_unavailable", "Ce fournisseur n’est pas raccordé au serveur.")
