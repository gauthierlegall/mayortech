"""Durable checkpoint and replay tests; no Exchange connection is made."""
from dataclasses import replace

import pytest

from travaux.integrations.appflowy import IntegrationUnavailable
from travaux.integrations.exchange import EWSSettings
from travaux.integrations.exchange_sync import (
    ChangePage, DurableReceipt, EWSIncrementalCollector,
    SQLiteSyncCheckpointStore, SyncChange,
)


def settings():
    return EWSSettings(enabled=True, endpoint="https://exchange.example.test/EWS/Exchange.asmx",
                       mailbox="agent@example.test", allowed_folder_ids=("folder-1",))


class Source:
    def __init__(self, page):
        self.page = page
        self.calls = []

    def read_page(self, folder_id, *, sync_state, page_size):
        self.calls.append((folder_id, sync_state, page_size))
        return self.page


def collector(tmp_path, page):
    source = Source(page)
    store = SQLiteSyncCheckpointStore(tmp_path / "checkpoints.sqlite")
    runner = EWSIncrementalCollector(tenant_id="town", connection_id="connection-1", settings=settings(), source=source, checkpoints=store)
    return runner, source, store


def test_checkpoint_is_advanced_after_durable_ingestion_and_flags_are_not_actions(tmp_path):
    page = ChangePage(changes=(SyncChange("create", "item-1", "v1", b"Synthetic MIME"),
                              SyncChange("delete", "item-2", None, None)),
                      next_sync_state="token-1", has_more=True, ignored_read_flags=2)
    runner, source, store = collector(tmp_path, page)
    received = []

    def sink(event):
        assert store.load(runner.scope_key("folder-1")).sync_state is None
        received.append(event)
        return DurableReceipt(event.idempotency_key, durable=True)

    report = runner.collect_once("folder-1", sink=sink)
    assert report.accepted == 2 and report.ignored_read_flags == 2 and report.has_more
    assert store.load(runner.scope_key("folder-1")).sync_state == "token-1"
    assert received[0].mime == b"Synthetic MIME"
    assert received[1].kind == "delete" and received[1].review_required
    assert received[1].mime is None  # Delete is metadata/review; no archive purge.
    assert source.calls == [("folder-1", None, 5)]


def test_crash_before_checkpoint_replays_same_idempotency_key_after_restart(tmp_path):
    page = ChangePage((SyncChange("create", "item-1", "v1", b"Synthetic MIME"),), "token-1", False)
    runner, _, store = collector(tmp_path, page)
    keys = []

    def crash_after_ingestion(event):
        keys.append(event.idempotency_key)
        raise RuntimeError("Simulated process failure after DB commit")

    with pytest.raises(RuntimeError):
        runner.collect_once("folder-1", sink=crash_after_ingestion)
    assert store.load(runner.scope_key("folder-1")).sync_state is None
    restarted, source, restarted_store = collector(tmp_path, page)

    def already_ingested(event):
        keys.append(event.idempotency_key)
        return DurableReceipt(event.idempotency_key, durable=True)

    restarted.collect_once("folder-1", sink=already_ingested)
    assert keys[0] == keys[1]
    assert source.calls[0][1] is None
    assert restarted_store.load(restarted.scope_key("folder-1")).sync_state == "token-1"


@pytest.mark.parametrize("receipt", [DurableReceipt("wrong-key", True), None, False])
def test_missing_or_wrong_ack_does_not_advance_checkpoint(tmp_path, receipt):
    runner, _, store = collector(tmp_path, ChangePage((SyncChange("update", "item", "v2", b"Synthetic"),), "next", False))
    with pytest.raises(IntegrationUnavailable, match="durable_ingestion_ack_required"):
        runner.collect_once("folder-1", sink=lambda event: receipt)
    assert store.load(runner.scope_key("folder-1")).sync_state is None


def test_scope_and_invalid_cursor_fail_before_sink(tmp_path):
    runner, source, store = collector(tmp_path, ChangePage((), "", False))
    with pytest.raises(IntegrationUnavailable, match="folder_out_of_scope"):
        runner.collect_once("not-allowed", sink=lambda event: None)
    assert source.calls == []
    with pytest.raises(IntegrationUnavailable, match="invalid_sync_state"):
        runner.collect_once("folder-1", sink=lambda event: None)
    assert store.load(runner.scope_key("folder-1")).sync_state is None


def test_read_flag_only_page_can_advance_without_creating_a_source(tmp_path):
    runner, _, store = collector(tmp_path, ChangePage((), "flags-token", False, ignored_read_flags=3))
    report = runner.collect_once("folder-1", sink=lambda event: pytest.fail("No content event expected"))
    assert report.accepted == 0 and report.ignored_read_flags == 3
    assert store.load(runner.scope_key("folder-1")).sync_state == "flags-token"


def test_concurrent_checkpoint_change_is_detected_not_overwritten(tmp_path):
    page = ChangePage((SyncChange("create", "item", "v1", b"Synthetic"),), "next", False)
    runner, _, store = collector(tmp_path, page)

    def sink(event):
        store.advance(runner.scope_key("folder-1"), expected_revision=0, next_sync_state="other-worker-token")
        return DurableReceipt(event.idempotency_key, True)

    with pytest.raises(IntegrationUnavailable, match="checkpoint_conflict"):
        runner.collect_once("folder-1", sink=sink)
    assert store.load(runner.scope_key("folder-1")).sync_state == "other-worker-token"


def test_updated_mime_gets_new_event_but_same_replay_is_stable(tmp_path):
    page = ChangePage((SyncChange("update", "item", "v1", b"one"),), "cursor-1", False)
    runner, source, _ = collector(tmp_path, page)
    keys = []

    def sink(event):
        keys.append(event.idempotency_key)
        return DurableReceipt(event.idempotency_key, True)

    runner.collect_once("folder-1", sink=sink)
    source.page = replace(page, changes=(SyncChange("update", "item", "v2", b"two"),), next_sync_state="cursor-2")
    runner.collect_once("folder-1", sink=sink)
    assert keys[0] != keys[1]
    assert source.calls[1][1] == "cursor-1"


def test_sdk_sync_page_reads_mime_and_uses_fetched_revision_without_mutation(monkeypatch):
    import exchangelib
    from exchangelib.services import SyncFolderItems
    from lxml import etree
    from travaux.integrations.exchange import EWSReadOnlyCollector
    from travaux.integrations.exchange_sync import ExchangelibChangeSource

    configuration = exchangelib.Configuration(
        service_endpoint=settings().endpoint,
        credentials=exchangelib.Credentials("fake", "fake"), auth_type=exchangelib.NTLM,
        version=exchangelib.Version(build=exchangelib.Build(15, 2, 1, 1)),
    )
    account = exchangelib.Account(primary_smtp_address=settings().mailbox, config=configuration,
                                 autodiscover=False, access_type=exchangelib.DELEGATE)
    namespace = "http://schemas.microsoft.com/exchange/services/2006/types"

    def local_response(service, payload):
        request = etree.tostring(payload).decode()
        assert "SyncFolderItems" in request and "IdOnly" in request and "NormalItems" in request
        assert "old-cursor" in request
        assert "UpdateItem" not in request
        service.sync_state = "new-cursor"
        service.includes_last_item_in_range = True
        for xml in (
            f'<t:Create xmlns:t="{namespace}"><t:Message><t:ItemId Id="item-1" ChangeKey="sync-revision"/></t:Message></t:Create>',
            f'<t:ReadFlagChange xmlns:t="{namespace}"><t:ItemId Id="item-1"/><t:IsRead>true</t:IsRead></t:ReadFlagChange>',
            f'<t:Delete xmlns:t="{namespace}"><t:ItemId Id="item-2"/></t:Delete>',
        ):
            yield etree.fromstring(xml.encode())

    def local_fetch(self, *, ids, only_fields, chunk_size):
        assert ids == [("item-1", "sync-revision")]
        assert only_fields == ["mime_content"] and chunk_size == 1
        yield exchangelib.Message(id="item-1", changekey="fetched-revision", mime_content=b"Synthetic MIME")

    monkeypatch.setattr(SyncFolderItems, "_get_elements", local_response)
    monkeypatch.setattr(exchangelib.Account, "fetch", local_fetch)
    reader = EWSReadOnlyCollector(settings(), account=account, sdk=exchangelib)
    page = ExchangelibChangeSource(reader).read_page("folder-1", sync_state="old-cursor", page_size=5)
    assert page.next_sync_state == "new-cursor" and not page.has_more
    assert page.ignored_read_flags == 1
    assert page.changes[0].mime == b"Synthetic MIME"
    assert page.changes[0].change_key == "fetched-revision"
    assert page.changes[1].kind == "delete" and page.changes[1].mime is None
