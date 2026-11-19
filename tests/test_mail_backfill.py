from datetime import datetime, timezone
from threading import Event, Thread

import pytest

from travaux.config import Settings
from travaux.connection_hub import ConnectionHub, IntegrationPolicy
from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.mail_backfill import MailBackfillService
from travaux.integrations.exchange_backfill import HistoryItem, HistoryPage


ACTOR = {
    "actor_id": "operator",
    "tenant_id": "town",
    "permissions": {"organization": {"read": True, "write": True}},
}
NOW = datetime(2026, 11, 15, 10, tzinfo=timezone.utc).timestamp()
RAW = b"From: entreprise@example.invalid\r\nTo: travaux@example.invalid\r\nSubject: TRV-2026-042 - Livraison\r\nMessage-ID: <history@example.invalid>\r\nDate: Fri, 15 Jan 2027 09:00:00 +0100\r\n\r\nLivraison annoncee : 25 novembre 2025.\r\n"


class Reader:
    calls = []
    hook = None
    pages = {}

    def __init__(self, *args):
        pass

    def probe(self):
        return {
            "calendars": [],
            "mail_folders": [{"id": "inbox", "name": "Réception"}, {"id": "sent", "name": "Envoyés"}],
        }

    def read_history_page(self, folder_id, *, sync_state, start, end, page_size):
        assert page_size == 5
        type(self).calls.append((folder_id, sync_state, start, end))
        if type(self).hook:
            type(self).hook()
        return type(self).pages[(folder_id, sync_state)]

    def close(self):
        pass


def setup(tmp_path, mode="staging"):
    cfg = Settings(
        mode=mode,
        db_path=tmp_path / "backfill.sqlite3",
        tenant_id="town",
        password_hash="scrypt$x$x",
        public_origin="https://travaux.example.org",
        allowed_hosts=("travaux.example.org",),
    )
    repo = Repository(cfg.db_path)
    repo.create_project("town", "TRV-2026-042", "Portail")
    hub = ConnectionHub(
        repo, cfg, policy=IntegrationPolicy(True, ("ews.example.org",)), reader_factory=Reader
    )
    Reader.calls = []
    Reader.hook = None
    Reader.pages = {
        ("inbox", None): HistoryPage(
            (HistoryItem("mail", "r1", "c1", datetime(2025, 6, 1, tzinfo=timezone.utc), RAW),),
            "cursor-1",
            False,
        )
    }
    service = MailBackfillService(repo, cfg, hub=hub, clock=lambda: NOW)
    if mode == "public_demo":
        return service, repo, hub, None
    connection = hub.create(
        ACTOR,
        {
            "provider": "exchange",
            "label": "Mairie",
            "endpoint": "https://ews.example.org/EWS/Exchange.asmx",
            "mailbox": "agent@example.invalid",
            "username": "agent",
            "password": "synthetic-secret",
        },
    )
    connection = hub.probe(ACTOR, connection["id"], expected_revision=connection["revision"])
    connection = hub.select(
        ACTOR,
        connection["id"],
        calendar_ids=[],
        folder_ids=["inbox", "sent"],
        expected_revision=connection["revision"],
    )
    return service, repo, hub, connection


def plan(connection, **changes):
    return {
        "connection_id": connection["id"],
        "folder_ids": ["inbox"],
        "start": "2025-01-01",
        "end": "2025-12-31",
        "expected_connection_revision": connection["revision"],
        **changes,
    }


def test_preview_and_plan_are_local_scoped_and_have_no_invented_total(tmp_path):
    service, repo, hub, connection = setup(tmp_path)
    preview = service.preview(ACTOR, plan(connection))
    assert preview["start"] == "2025-01-01" and preview["end"] == "2025-12-31" and preview["end_inclusive"]
    assert preview["timezone"] == "Europe/Paris" and preview["scan_mode"] == "ews_initial_inventory"
    assert preview["total"] is None and preview["percent"] is None and preview["batch_size"] == 5
    assert preview["folders"] == [{"id": "inbox", "name": "Réception"}]
    assert Reader.calls == []
    job = service.create(ACTOR, plan(connection))
    assert job["status"] == "ready" and job["progress"]["scanned"] == 0 and job["revision"] == 0
    assert Reader.calls == [] and "cursor" not in str(job) and "synthetic-secret" not in str(job)
    with pytest.raises(DomainError):
        service.preview(ACTOR, plan(connection, folder_ids=["unapproved"]))
    with pytest.raises(DomainError):
        service.preview(ACTOR, plan(connection, expected_connection_revision=0))
    with pytest.raises(DomainError):
        service.preview(ACTOR, plan(connection, start="2025-02-30"))
    with pytest.raises(DomainError):
        service.preview(ACTOR, plan(connection, start="2026-01-01", end="2025-12-31"))


def test_batches_filter_server_date_deduplicate_originals_and_keep_live_cursor_separate(tmp_path):
    service, repo, hub, connection = setup(tmp_path)
    Reader.pages = {
        ("inbox", None): HistoryPage(
            (
                HistoryItem("mail", "r1", "c1", datetime(2025, 6, 1, tzinfo=timezone.utc), RAW),
                HistoryItem("out_of_range", "outside", "c1", datetime(2024, 6, 1, tzinfo=timezone.utc), None),
                HistoryItem("mail", "duplicate", "c1", datetime(2025, 6, 1, tzinfo=timezone.utc), RAW),
            ),
            "history-cursor1",
            True,
        ),
        ("inbox", "history-cursor1"): HistoryPage(
            (HistoryItem("unavailable", "deleted", None, None, None),), "history-cursor2", False
        ),
    }
    job = service.create(ACTOR, plan(connection))
    first = service.run(ACTOR, job["id"], expected_revision=job["revision"])
    assert (
        first["status"] == "ready"
        and first["progress"]["imported"] == 1
        and first["progress"]["already_present"] == 1
        and first["progress"]["out_of_range"] == 1
    )
    second = service.run(ACTOR, job["id"], expected_revision=first["revision"])
    assert second["status"] == "completed" and second["has_warnings"]
    assert second["progress"]["scanned"] == 4 and second["progress"]["unavailable"] == 1
    assert len(repo.list_sources("town")) == 1
    assert repo._db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
    assert repo._db.execute("SELECT count(*) FROM candidates").fetchone()[0] == 0
    live = repo._db.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='ews_sync_checkpoints'"
    ).fetchone()[0]
    assert live == 0
    assert service.get(ACTOR, job["id"])["percent"] is None


@pytest.mark.parametrize("action,status", [("pause", "paused"), ("cancel", "cancelled")])
def test_pause_or_cancel_during_read_discards_inflight_batch_before_cursor_commit(tmp_path, action, status):
    service, repo, hub, connection = setup(tmp_path)
    entered = Event()
    release = Event()
    result = []
    Reader.hook = lambda: (entered.set(), release.wait(5))
    job = service.create(ACTOR, plan(connection))
    worker = Thread(
        target=lambda: result.append(service.run(ACTOR, job["id"], expected_revision=job["revision"]))
    )
    worker.start()
    assert entered.wait(5)
    running = service.get(ACTOR, job["id"])
    assert running["status"] == "running"
    stopped = service.control(ACTOR, job["id"], action, expected_revision=running["revision"])
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert stopped["status"] == status and result[0]["status"] == status
    assert repo.list_sources("town") == []
    assert service.get(ACTOR, job["id"])["progress"]["batches"] == 0
    Reader.hook = None
    if action == "pause":
        resumed = service.control(ACTOR, job["id"], "resume", expected_revision=stopped["revision"])
        done = service.run(ACTOR, job["id"], expected_revision=resumed["revision"])
        assert done["status"] == "completed" and done["progress"]["imported"] == 1
        assert Reader.calls[0][1] is None and Reader.calls[1][1] is None
    else:
        with pytest.raises(DomainError):
            service.control(ACTOR, job["id"], "resume", expected_revision=stopped["revision"])


def test_failed_persistence_rolls_back_sources_jobs_and_cursor_then_resumes_after_restart(
    tmp_path, monkeypatch
):
    import travaux.mail_backfill as module

    service, repo, hub, connection = setup(tmp_path)
    job = service.create(ACTOR, plan(connection))
    original = module.import_mail

    def crash_after_write(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("synthetic storage failure, do not expose")

    monkeypatch.setattr(module, "import_mail", crash_after_write)
    failed = service.run(ACTOR, job["id"], expected_revision=job["revision"])
    assert failed["status"] == "failed" and failed["last_error"]["code"] == "batch_failed"
    assert "synthetic storage" not in str(failed)
    assert (
        repo.list_sources("town") == [] and repo._db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0
    )
    monkeypatch.setattr(module, "import_mail", original)
    restarted = MailBackfillService(repo, service.settings, hub=hub, clock=lambda: NOW)
    resumed = restarted.control(ACTOR, job["id"], "resume", expected_revision=failed["revision"])
    done = restarted.run(ACTOR, job["id"], expected_revision=resumed["revision"])
    assert done["status"] == "completed" and done["progress"]["imported"] == 1
    assert Reader.calls[1][1] is None


def test_public_writes_and_cross_tenant_reads_are_refused(tmp_path):
    service, repo, hub, connection = setup(tmp_path, "public_demo")
    assert service.list(ACTOR)["can_manage"] is False
    with pytest.raises(DomainError):
        service.preview(
            ACTOR,
            {
                "connection_id": "fake",
                "folder_ids": ["inbox"],
                "start": "2025-01-01",
                "end": "2025-12-31",
                "expected_connection_revision": 0,
            },
        )
    with pytest.raises(DomainError):
        service.list({**ACTOR, "tenant_id": "other"})


def test_historical_then_live_sync_reuses_same_original_without_new_source_or_job(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from travaux.integrations.calendar_readers import ExchangeCalendarReader
    from travaux.integrations.exchange import EWSSettings
    from travaux.integrations.exchange_sync import ChangePage, SyncChange

    service, repo, hub, connection = setup(tmp_path)
    job = service.create(ACTOR, plan(connection))
    assert service.run(ACTOR, job["id"], expected_revision=0)["progress"]["imported"] == 1

    class Source:
        def __init__(self, *args):
            pass

        def read_page(self, folder_id, *, sync_state, page_size):
            return ChangePage((SyncChange("create", "r1", "live-key", RAW),), "live-cursor", False)

    monkeypatch.setattr("travaux.integrations.exchange_sync.ExchangelibChangeSource", Source)
    live = ExchangeCalendarReader.__new__(ExchangeCalendarReader)
    live.reader = SimpleNamespace(
        settings=EWSSettings(
            enabled=True,
            endpoint=connection["endpoint"],
            mailbox=connection["mailbox"],
            allowed_folder_ids=("inbox",),
            max_batch=5,
        )
    )
    report = live.collect_mail(repo, "town", connection["id"], guard=lambda: None)
    assert report["accepted"] == 1
    assert len(repo.list_sources("town")) == 1
    assert repo._db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
    assert repo._db.execute("SELECT revision FROM ews_sync_checkpoints").fetchone()[0] == 1


def test_end_date_is_inclusive_in_paris_including_daylight_saving(tmp_path):
    service, repo, hub, connection = setup(tmp_path)
    preview = service.preview(ACTOR, plan(connection, start="2025-03-30", end="2025-03-30"))
    assert preview["start_at"] == "2025-03-29T23:00:00+00:00"
    assert preview["end_at"] == "2025-03-30T22:00:00+00:00"
    with pytest.raises(DomainError):
        service.preview(ACTOR, plan(connection, end="2027-01-01"))


def test_scope_revoked_during_read_prevents_any_commit_and_can_resume_after_restoration(tmp_path):
    service, repo, hub, connection = setup(tmp_path)
    entered = Event()
    release = Event()
    result = []
    Reader.hook = lambda: (entered.set(), release.wait(5))
    job = service.create(ACTOR, plan(connection))
    worker = Thread(target=lambda: result.append(service.run(ACTOR, job["id"], expected_revision=0)))
    worker.start()
    assert entered.wait(5)
    changed = hub.select(
        ACTOR,
        connection["id"],
        calendar_ids=[],
        folder_ids=["sent"],
        expected_revision=connection["revision"],
    )
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert result[0]["status"] == "failed" and result[0]["last_error"]["code"] == "connection_scope_changed"
    assert result[0]["progress"]["batches"] == 0 and repo.list_sources("town") == []
    hub.select(
        ACTOR,
        connection["id"],
        calendar_ids=[],
        folder_ids=["inbox", "sent"],
        expected_revision=changed["revision"],
    )
    Reader.hook = None
    resumed = service.control(ACTOR, job["id"], "resume", expected_revision=result[0]["revision"])
    done = service.run(ACTOR, job["id"], expected_revision=resumed["revision"])
    assert done["status"] == "completed" and done["progress"]["imported"] == 1
    assert Reader.calls[0][1] is None and Reader.calls[1][1] is None


def test_expired_lease_takeover_ignores_old_worker_without_duplicate_import(tmp_path):
    service, repo, hub, connection = setup(tmp_path)
    now = [NOW]
    service.clock = lambda: now[0]
    entered = Event()
    release = Event()
    old_result = []

    def hold_first_read():
        if len(Reader.calls) == 1:
            entered.set()
            release.wait(5)

    Reader.hook = hold_first_read
    job = service.create(ACTOR, plan(connection))
    worker = Thread(target=lambda: old_result.append(service.run(ACTOR, job["id"], expected_revision=0)))
    worker.start()
    assert entered.wait(5)
    now[0] += 361
    interrupted = service.get(ACTOR, job["id"])
    assert interrupted["interrupted"]
    current = service.run(ACTOR, job["id"], expected_revision=interrupted["revision"])
    assert current["status"] == "completed"
    release.set()
    worker.join(5)
    assert not worker.is_alive()
    assert old_result[0]["status"] == "completed"
    assert service.get(ACTOR, job["id"])["progress"]["batches"] == 1
    assert len(repo.list_sources("town")) == 1
    assert repo._db.execute("SELECT count(*) FROM jobs").fetchone()[0] == 1
