from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from travaux.connection_hub import IntegrationPolicy
from travaux.domain import DomainError
from travaux.integrations.calendar_readers import CalDAVReader, GuardedDAVSession


class Response:
    def __init__(self, body=b"<xml/>", status=207):
        self.body, self.status_code = body, status
        self.headers = {}
        self.closed = False

    def iter_content(self, chunk_size):
        yield self.body

    def close(self):
        self.closed = True


class Session:
    trust_env = True

    def __init__(self, response=None):
        self.calls = []
        self.response = response or Response()

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response

    def close(self):
        pass


def policy(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("1.1.1.1", 443))])
    monkeypatch.delenv("SSLKEYLOGFILE", raising=False)
    monkeypatch.delenv("QUICLOGDIR", raising=False)
    return IntegrationPolicy(True, ("cal.example.org",))


def test_caldav_session_guards_every_hop_blocks_writes_and_bounds_bytes(monkeypatch):
    original = Session()
    session = GuardedDAVSession(original, policy(monkeypatch), "cal.example.org")
    response = session.request("PROPFIND", "https://cal.example.org/dav", auth="kept", allow_redirects=True)
    assert response._content == b"<xml/>"
    assert original.calls[0][2]["allow_redirects"] is False and original.calls[0][2]["verify"] is True
    assert original.trust_env is False
    for method, url in [
        ("PUT", "https://cal.example.org/dav"),
        ("PROPFIND", "https://evil.example.org/dav"),
        ("GET", "http://cal.example.org/dav"),
    ]:
        with pytest.raises(DomainError):
            session.request(method, url)
    assert len(original.calls) == 1
    large = GuardedDAVSession(Session(Response(b"x" * 4_000_001)), policy(monkeypatch), "cal.example.org")
    with pytest.raises(DomainError):
        large.request("REPORT", "https://cal.example.org/dav")


def test_private_host_requires_explicit_server_allowlist_and_metadata_is_never_allowed(monkeypatch):
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("10.2.3.4", 443))])
    with pytest.raises(DomainError):
        IntegrationPolicy(True, ("exchange.example.org",)).endpoint(
            "https://exchange.example.org/EWS/Exchange.asmx", resolve=True
        )
    IntegrationPolicy(True, ("exchange.example.org",), ("exchange.example.org",)).endpoint(
        "https://exchange.example.org/EWS/Exchange.asmx", resolve=True
    )
    monkeypatch.setattr("socket.getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("169.254.169.254", 443))])
    with pytest.raises(DomainError):
        IntegrationPolicy(True, ("exchange.example.org",), ("exchange.example.org",)).endpoint(
            "https://exchange.example.org/EWS/Exchange.asmx", resolve=True
        )


def test_real_caldav_api_is_used_read_only_with_server_side_recurrence_expansion(monkeypatch):
    wire = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//T//FR\r\nBEGIN:VEVENT\r\nUID:v1\r\nDTSTART:20261120T080000Z\r\nDTEND:20261120T090000Z\r\nSUMMARY:Visite\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    calls = []
    cal = SimpleNamespace(
        url="https://cal.example.org/dav/work/",
        name="Travaux",
        search=lambda **kwargs: calls.append(kwargs) or [SimpleNamespace(data=wire)],
    )
    client = SimpleNamespace(
        session=Session(), principal=lambda: SimpleNamespace(calendars=lambda: [cal]), close=lambda: None
    )

    def factory(**kwargs):
        assert kwargs["ssl_verify_cert"] is True and kwargs["enable_rfc6764"] is False
        return client

    reader = CalDAVReader(
        {"endpoint": "https://cal.example.org/dav", "username": "a"},
        {"password": "not-logged"},
        policy(monkeypatch),
        sdk=SimpleNamespace(DAVClient=factory),
    )
    assert reader.probe() == {"calendars": [{"id": str(cal.url), "name": "Travaux"}], "mail_folders": []}
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    end = datetime(2026, 12, 1, tzinfo=timezone.utc)
    result = reader.calendar_events([str(cal.url)], start, end)
    assert result[str(cal.url)][0]["title"] == "Visite"
    assert calls[0]["server_expand"] is True and calls[0]["post_filter"] is False
    assert calls[0]["expand"] is False and calls[0]["split_expanded"] is False


def test_installed_caldav_sdk_never_expands_hostile_secondly_rule_locally(monkeypatch):
    import caldav
    import recurring_ical_events

    server_policy = policy(monkeypatch)
    client = caldav.DAVClient(url="https://cal.example.org/dav", enable_rfc6764=False)
    calendar = caldav.Calendar(client=client, url="https://cal.example.org/dav/work/")
    wire = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//FR\r\nBEGIN:VEVENT\r\nUID:hostile\r\nDTSTART:20261120T080000Z\r\nDTEND:20261120T080001Z\r\nRRULE:FREQ=SECONDLY\r\nSUMMARY:Unexpanded server rule\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    resource = caldav.Event(client=client, url="https://cal.example.org/dav/work/item.ics", data=wire)
    monkeypatch.setattr(client, "principal", lambda: SimpleNamespace(calendars=lambda: [calendar]))
    reports = []

    def report(xml, *args, **kwargs):
        reports.append(xml.xmlelement() if hasattr(xml, "xmlelement") else xml)
        return None, [resource]

    monkeypatch.setattr(calendar, "_request_report_build_resultlist", report)
    expansions = []

    def never_expand(*args, **kwargs):
        expansions.append(True)
        raise AssertionError("Client-side recurrence expansion is forbidden")

    monkeypatch.setattr(recurring_ical_events, "of", never_expand)
    reader = CalDAVReader(
        {"endpoint": "https://cal.example.org/dav", "username": "agent"},
        {"password": "synthetic"},
        server_policy,
        sdk=SimpleNamespace(DAVClient=lambda **kwargs: client),
    )
    with pytest.raises(DomainError, match="récurrence"):
        reader.calendar_events(
            [str(calendar.url)],
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 1, tzinfo=timezone.utc),
        )
    assert expansions == []
    assert len(reports) == 1 and reports[0].find(".//{urn:ietf:params:xml:ns:caldav}expand") is not None
    reader.close()


def test_connector_never_emits_sdk_ics_repairs_or_http_tokens_to_logs(monkeypatch, caplog):
    import logging
    import caldav
    from caldav.lib import vcal

    server_policy = policy(monkeypatch)
    secret = "FAKE_CALENDAR_TOKEN_DO_NOT_LOG"
    client = caldav.DAVClient(url="https://cal.example.org/dav", enable_rfc6764=False)
    reader = CalDAVReader(
        {"endpoint": "https://cal.example.org/dav", "username": "agent"},
        {"password": secret},
        server_policy,
        sdk=SimpleNamespace(DAVClient=lambda **kwargs: client),
    )
    monkeypatch.setattr(vcal, "fixup_error_loggings", 0)
    with caplog.at_level(logging.DEBUG):
        # Missing DTSTAMP causes the actual installed SDK to repair the ICS and
        # normally log its full source diff at WARNING.
        resource = caldav.Event(
            client=client,
            url="https://cal.example.org/dav/item.ics",
            data="BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//FR\r\nBEGIN:VEVENT\r\nUID:log\r\nDTSTART:20261120T080000Z\r\nSUMMARY:"
            + secret
            + "\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n",
        )
        assert secret in resource.data
        logging.getLogger("caldav").warning("Authorization: Bearer %s", secret)
        logging.getLogger("travaux.calendar").warning("safe_connector_diagnostic")
    assert secret not in caplog.text and "Ical data was modified" not in caplog.text
    assert "safe_connector_diagnostic" in caplog.text
    reader.close()
    monkeypatch.setenv("PYTHON_CALDAV_COMMDUMP", "1")
    with pytest.raises(DomainError):
        CalDAVReader(
            {"endpoint": "https://cal.example.org/dav", "username": "agent"},
            {"password": secret},
            server_policy,
        )


def test_exchange_mail_reuses_durable_ingestion_before_checkpoint_and_replay_dedup(tmp_path, monkeypatch):
    from travaux.integrations.calendar_readers import ExchangeCalendarReader
    from travaux.integrations.exchange import EWSSettings
    from travaux.integrations.exchange_sync import ChangePage, SyncChange
    from travaux.repository import Repository

    repo = Repository(tmp_path / "ews.sqlite3")
    repo.create_project("commune", "TRV-2026-042", "Portail")
    raw = b"From: entreprise@example.invalid\r\nTo: travaux@example.invalid\r\nSubject: TRV-2026-042 - Acces\r\nMessage-ID: <mail-1@example.invalid>\r\nDate: Fri, 20 Nov 2026 08:00:00 +0100\r\n\r\nAcces annonce pour la visite.\r\n"
    config = EWSSettings(
        enabled=True,
        endpoint="https://ews.example.org/EWS/Exchange.asmx",
        mailbox="travaux@example.invalid",
        allowed_folder_ids=("inbox",),
        max_batch=5,
    )

    class Source:
        def __init__(self, *args):
            pass

        def read_page(self, folder_id, *, sync_state, page_size):
            return ChangePage(
                (SyncChange("create", "remote-1", "change-1", raw),) if sync_state is None else (),
                "cursor-1" if sync_state is None else "cursor-2",
                False,
            )

    monkeypatch.setattr("travaux.integrations.exchange_sync.ExchangelibChangeSource", Source)
    reader = ExchangeCalendarReader.__new__(ExchangeCalendarReader)
    reader.reader = SimpleNamespace(settings=config)

    def reject():
        raise DomainError("stale_revision", "Périmètre modifié")

    with pytest.raises(DomainError):
        reader.collect_mail(repo, "commune", "connection-1", guard=reject)
    assert repo.list_sources("commune") == []
    assert repo._db.execute("SELECT count(*) FROM ews_sync_checkpoints").fetchone()[0] == 0
    accepted = reader.collect_mail(repo, "commune", "connection-1", guard=lambda: None)
    assert accepted["accepted"] == 1
    sources = repo.list_sources("commune")
    assert len(sources) == 1 and sources[0]["body"].strip() == "Acces annonce pour la visite."
    assert sources[0]["external_id"] == "ews:connection-1:remote-1"
    assert repo._db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
    assert repo._db.execute("SELECT revision FROM ews_sync_checkpoints").fetchone()[0] == 1
    replay = reader.collect_mail(repo, "commune", "connection-1", guard=lambda: None)
    assert replay["accepted"] == 0 and len(repo.list_sources("commune")) == 1
    assert repo._db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
