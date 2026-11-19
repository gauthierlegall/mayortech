"""Exercise the EWS boundary without opening a socket or using credentials."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from travaux.domain import DomainError
from travaux.integrations.exchange import EWSSettings
from travaux.integrations.exchange_backfill import ExchangeHistorySource


START = datetime(2025, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 1, 1, tzinfo=timezone.utc)
INSIDE = datetime(2025, 6, 1, tzinfo=timezone.utc)
OUTSIDE = datetime(2024, 6, 1, tzinfo=timezone.utc)


def build_source(entries, metadata, originals=None, *, cursor="history-next", more=False, failure=None):
    calls = []

    class ItemNotFound(Exception):
        pass

    class AccessDenied(Exception):
        pass

    class InvalidSyncState(Exception):
        pass

    class Account:
        def fetch(self, *, ids, only_fields, chunk_size):
            assert chunk_size == 1
            calls.append((ids, only_fields))
            values = metadata if only_fields == ["datetime_received", "size"] else originals
            return iter([values[ids[0][0]]])

    class SyncService:
        def __init__(self, *, account):
            self.sync_state = cursor
            self.includes_last_item_in_range = not more

        def call(self, **kwargs):
            calls.append(kwargs)
            if failure == "invalid_cursor":
                raise InvalidSyncState("synthetic token must not escape")
            return iter(entries)

    account = Account()
    reader = SimpleNamespace(
        settings=EWSSettings(
            enabled=True,
            endpoint="https://ews.example.invalid/EWS/Exchange.asmx",
            mailbox="agent@example.invalid",
            allowed_folder_ids=("inbox",),
        ),
        _account=account,
        _folders=SimpleNamespace(Root=lambda **kwargs: kwargs, Folder=lambda **kwargs: kwargs),
    )
    errors = SimpleNamespace(
        ErrorItemNotFound=ItemNotFound,
        ErrorAccessDenied=AccessDenied,
        ErrorInvalidSyncStateData=InvalidSyncState,
    )
    return ExchangeHistorySource(reader, service_class=SyncService, errors=errors), calls


def item(ident, received=INSIDE, **values):
    return SimpleNamespace(id=ident, changekey="c1", datetime_received=received, **values)


def test_metadata_is_bounded_and_outside_period_never_fetches_body():
    source, calls = build_source(
        [("create", item("old")), ("create", item("wanted"))],
        {"old": item("old", OUTSIDE, size=12), "wanted": item("wanted", size=12)},
        {"wanted": item("wanted", mime_content=b"original MIME")},
        more=True,
    )
    page = source.read_page("inbox", sync_state=None, start=START, end=END, page_size=5)
    assert [entry.kind for entry in page.items] == ["out_of_range", "mail"]
    assert page.items[0].mime is None and page.items[1].mime == b"original MIME"
    assert page.next_sync_state == "history-next" and page.has_more
    assert calls[0] == {
        "folder": {"root": {"account": source.reader._account}, "id": "inbox"},
        "shape": "IdOnly",
        "additional_fields": (),
        "sync_state": None,
        "ignore": (),
        "max_changes_returned": 5,
        "sync_scope": "NormalItems",
    }
    assert calls[1:] == [
        ([("old", "c1")], ["datetime_received", "size"]),
        ([("wanted", "c1")], ["datetime_received", "size"]),
        ([("wanted", "c1")], ["mime_content", "datetime_received"]),
    ]


def test_missing_date_and_oversized_metadata_skip_mime_fetch_and_date_race_is_discarded():
    source, calls = build_source(
        [("create", item(ident)) for ident in ("undated", "huge", "moved")],
        {
            "undated": item("undated", None, size=12),
            "huge": item("huge", size=10_000_001),
            "moved": item("moved", size=12),
        },
        {"moved": item("moved", OUTSIDE, mime_content=b"discarded")},
    )
    page = source.read_page("inbox", sync_state=None, start=START, end=END)
    assert [(entry.kind, entry.reason) for entry in page.items] == [
        ("unavailable", "server_date_unavailable"),
        ("unavailable", "mime_too_large"),
        ("out_of_range", ""),
    ]
    assert all(entry.mime is None for entry in page.items)
    body_calls = [call for call in calls if isinstance(call, tuple) and "mime_content" in call[1]]
    assert body_calls == [([("moved", "c1")], ["mime_content", "datetime_received"])]


@pytest.mark.parametrize(
    "case,code",
    [
        ("invalid_cursor", "backfill_cursor_invalid"),
        ("stalled", "backfill_read_failed"),
        ("too_many", "backfill_read_failed"),
    ],
)
def test_bad_inventory_fails_without_secret_or_cursor_echo(case, code):
    source, _ = build_source(
        [("read_flag_change", None)] * (6 if case == "too_many" else 0),
        {},
        cursor="synthetic-private-cursor",
        more=True,
        failure="invalid_cursor" if case == "invalid_cursor" else None,
    )
    with pytest.raises(DomainError) as raised:
        source.read_page("inbox", sync_state="synthetic-private-cursor", start=START, end=END)
    assert raised.value.code == code
    assert "synthetic" not in str(raised.value)


def test_unapproved_folder_and_batch_limit_fail_before_ews_call():
    source, calls = build_source([], {})
    for folder, size in (("other", 5), ("inbox", 6), ("inbox", 0)):
        with pytest.raises(DomainError):
            source.read_page(folder, sync_state=None, start=START, end=END, page_size=size)
    assert calls == []
