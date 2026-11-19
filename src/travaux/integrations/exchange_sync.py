"""One-page EWS synchronization with a durable ACK-before-checkpoint boundary.

The sink must commit the source/event, dedup key and its extraction outbox in one
transaction before returning DurableReceipt. A crash then causes safe replay,
not a lost message. The transport never advances the cursor in memory only.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Protocol

from .appflowy import IntegrationUnavailable
from .exchange import EWSReadOnlyCollector, EWSSettings


@dataclass(frozen=True)
class SyncChange:
    kind: Literal["create", "update", "delete", "unavailable"]
    remote_id: str
    change_key: str | None
    mime: bytes | None = field(repr=False)


@dataclass(frozen=True)
class ChangePage:
    changes: tuple[SyncChange, ...]
    next_sync_state: str = field(repr=False)
    has_more: bool
    ignored_read_flags: int = 0


@dataclass(frozen=True)
class MailSyncEvent:
    tenant_id: str
    connection_id: str
    folder_id: str
    remote_id: str
    change_key: str | None
    kind: str
    mime: bytes | None = field(repr=False)
    sha256: str | None
    idempotency_key: str
    review_required: bool


@dataclass(frozen=True)
class DurableReceipt:
    idempotency_key: str
    durable: bool


@dataclass(frozen=True)
class SyncCheckpoint:
    sync_state: str | None = field(default=None, repr=False)
    revision: int = 0


@dataclass(frozen=True)
class CollectionReport:
    accepted: int
    ignored_read_flags: int
    has_more: bool
    checkpoint_revision: int


class ChangePageSource(Protocol):
    def read_page(self, folder_id: str, *, sync_state: str | None, page_size: int) -> ChangePage: ...


class SQLiteSyncCheckpointStore:
    def __init__(self, path: str | Path):
        if str(path) == ":memory:":
            raise ValueError("durable_checkpoint_required")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                connection.execute("CREATE TABLE IF NOT EXISTS ews_sync_checkpoints (scope TEXT PRIMARY KEY, sync_state TEXT NOT NULL, revision INTEGER NOT NULL)")
        finally:
            connection.close()

    def load(self, scope: str) -> SyncCheckpoint:
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            row = connection.execute("SELECT sync_state, revision FROM ews_sync_checkpoints WHERE scope=?", (scope,)).fetchone()
            return SyncCheckpoint(*row) if row else SyncCheckpoint()
        finally:
            connection.close()

    def advance(self, scope: str, *, expected_revision: int, next_sync_state: str) -> SyncCheckpoint:
        if not next_sync_state or len(next_sync_state) > 100_000:
            raise IntegrationUnavailable("invalid_sync_state")
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute("SELECT revision FROM ews_sync_checkpoints WHERE scope=?", (scope,)).fetchone()
                if (row[0] if row else 0) != expected_revision:
                    raise IntegrationUnavailable("checkpoint_conflict")
                revision = expected_revision + 1
                connection.execute("INSERT INTO ews_sync_checkpoints VALUES (?, ?, ?) ON CONFLICT(scope) DO UPDATE SET sync_state=excluded.sync_state, revision=excluded.revision",
                                   (scope, next_sync_state, revision))
                return SyncCheckpoint(next_sync_state, revision)
        finally:
            connection.close()


class EWSIncrementalCollector:
    def __init__(self, *, tenant_id: str, connection_id: str, settings: EWSSettings,
                 source: ChangePageSource, checkpoints: SQLiteSyncCheckpointStore):
        if not settings.enabled:
            raise IntegrationUnavailable("exchange_disabled")
        self.tenant_id = tenant_id
        self.connection_id = connection_id
        self.settings = settings
        self.source = source
        self.checkpoints = checkpoints

    def scope_key(self, folder_id: str) -> str:
        # A changed endpoint/mailbox/tenant never reuses another mailbox's cursor.
        values = (self.tenant_id, self.connection_id, self.settings.endpoint,
                  self.settings.mailbox.casefold(), folder_id, "NormalItems")
        return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode("utf-8")).hexdigest()

    def collect_once(self, folder_id: str, *, sink: Callable[[MailSyncEvent], DurableReceipt]) -> CollectionReport:
        if folder_id not in self.settings.allowed_folder_ids:
            raise IntegrationUnavailable("folder_out_of_scope")
        scope = self.scope_key(folder_id)
        checkpoint = self.checkpoints.load(scope)
        # Five MIME messages/page bounds memory; MaxChangesReturned is a page size,
        # not an offset. Subsequent calls use the server's new opaque SyncState.
        page = self.source.read_page(folder_id, sync_state=checkpoint.sync_state, page_size=min(self.settings.max_batch, 5))
        if not page.next_sync_state or len(page.next_sync_state) > 100_000:
            raise IntegrationUnavailable("invalid_sync_state")
        if page.has_more and page.next_sync_state == checkpoint.sync_state:
            raise IntegrationUnavailable("stalled_sync_state")
        if len(page.changes) + page.ignored_read_flags > min(self.settings.max_batch, 5):
            raise IntegrationUnavailable("exchange_page_limit")
        for change in page.changes:
            if change.kind not in {"create", "update", "delete", "unavailable"} or not change.remote_id:
                raise IntegrationUnavailable("invalid_sync_change")
            if change.kind in {"create", "update"} and not isinstance(change.mime, bytes):
                raise IntegrationUnavailable("sync_mime_required")
            if change.mime is not None and len(change.mime) > self.settings.max_mime_bytes:
                raise IntegrationUnavailable("exchange_mime_limit")
            digest = hashlib.sha256(change.mime).hexdigest() if change.mime is not None else None
            identity = (scope, change.kind, change.remote_id, change.change_key, digest)
            event_key = "ews-" + hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode("utf-8")).hexdigest()
            event = MailSyncEvent(self.tenant_id, self.connection_id, folder_id, change.remote_id,
                                  change.change_key, change.kind, change.mime, digest, event_key,
                                  review_required=change.kind in {"delete", "unavailable"})
            receipt = sink(event)
            if (not isinstance(receipt, DurableReceipt) or receipt.durable is not True
                    or receipt.idempotency_key != event.idempotency_key):
                raise IntegrationUnavailable("durable_ingestion_ack_required")
        advanced = self.checkpoints.advance(scope, expected_revision=checkpoint.revision,
                                           next_sync_state=page.next_sync_state)
        return CollectionReport(len(page.changes), page.ignored_read_flags, page.has_more, advanced.revision)


class ExchangelibChangeSource:
    """Uses the actual SDK's single-page SyncFolderItems service.

    Folder.sync_items() consumes all pages before exposing item_sync_state; using
    the service's public call()/sync_state lets us ACK one bounded page at a time.
    """
    def __init__(self, reader: EWSReadOnlyCollector):
        self.reader = reader
        self._service = importlib.import_module("exchangelib.services").SyncFolderItems
        self._errors = importlib.import_module("exchangelib.errors")

    def read_page(self, folder_id: str, *, sync_state: str | None, page_size: int) -> ChangePage:
        if folder_id not in self.reader.settings.allowed_folder_ids:
            raise IntegrationUnavailable("folder_out_of_scope")
        if not 1 <= page_size <= min(self.reader.settings.max_batch, 5):
            raise ValueError("invalid_sync_page_size")
        root = self.reader._folders.Root(account=self.reader._account)
        folder = self.reader._folders.Folder(root=root, id=folder_id)
        service = self._service(account=self.reader._account)
        changes: list[SyncChange] = []
        ignored = 0
        try:
            iterator = service.call(folder=folder, shape="IdOnly", additional_fields=(),
                                    sync_state=sync_state, ignore=(), max_changes_returned=page_size,
                                    sync_scope="NormalItems")
            for index, entry in enumerate(iterator):
                if index >= page_size:
                    raise IntegrationUnavailable("exchange_page_limit")
                if isinstance(entry, Exception):
                    raise IntegrationUnavailable("exchange_sync_failed")
                kind, item = entry
                if kind == "read_flag_change":
                    ignored += 1
                    continue
                if kind == "delete":
                    changes.append(SyncChange("delete", item.id, item.changekey, None))
                    continue
                if kind not in {"create", "update"}:
                    raise IntegrationUnavailable("unknown_exchange_change")
                values = list(self.reader._account.fetch(ids=[(item.id, item.changekey)],
                                                        only_fields=["mime_content"], chunk_size=1))
                if len(values) != 1:
                    raise IntegrationUnavailable("exchange_item_read_failed")
                fetched = values[0]
                if isinstance(fetched, (self._errors.ErrorItemNotFound, self._errors.ErrorAccessDenied)):
                    changes.append(SyncChange("unavailable", item.id, item.changekey, None))
                    continue
                if isinstance(fetched, Exception):
                    raise IntegrationUnavailable("exchange_item_read_failed")
                if fetched.id != item.id:
                    raise IntegrationUnavailable("exchange_item_identity_mismatch")
                mime = fetched.mime_content
                if not isinstance(mime, bytes) or len(mime) > self.reader.settings.max_mime_bytes:
                    raise IntegrationUnavailable("exchange_mime_limit")
                # A message may have changed between SyncFolderItems and GetItem.
                # Attribute the retrieved MIME to its actual GetItem revision.
                changes.append(SyncChange(kind, fetched.id, fetched.changekey, mime))
        except self._errors.ErrorInvalidSyncStateData:
            # A reset can replay or omit data; an operator must reconcile it.
            raise IntegrationUnavailable("exchange_cursor_invalid_requires_review") from None
        except IntegrationUnavailable:
            raise
        except Exception:
            raise IntegrationUnavailable("exchange_sync_failed") from None
        if type(service.includes_last_item_in_range) is not bool or not service.sync_state:
            raise IntegrationUnavailable("incomplete_sync_response")
        return ChangePage(tuple(changes), service.sync_state, not service.includes_last_item_in_range, ignored)
