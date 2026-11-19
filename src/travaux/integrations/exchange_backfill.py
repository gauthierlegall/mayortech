"""One bounded EWS inventory page, with server-date filtering before MIME fetch.

The caller owns a historical SyncFolderItems cursor, separate from live sync.
Microsoft EWS initial-sync semantics and the existing exchangelib service are
reused; no fragile offset pagination or guessed date ordering is introduced.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib

from ..domain import DomainError


def find_existing_exchange_original(db, tenant, connection_id, digest):
    """Call within the ingestion transaction; metadata differences are irrelevant."""
    return db.execute(
        """SELECT s.id FROM sources s JOIN original_documents d ON d.tenant_id=s.tenant_id AND d.source_id=s.id
        WHERE s.tenant_id=? AND d.kind='email' AND d.sha256=? AND json_extract(s.metadata,'$.connection_id')=? ORDER BY s.created_at,s.id LIMIT 1""",
        (tenant, digest, connection_id),
    ).fetchone()


@dataclass(frozen=True)
class HistoryItem:
    kind: str
    remote_id: str
    change_key: str | None
    received_at: datetime | None
    mime: bytes | None = field(repr=False)
    reason: str = ""


@dataclass(frozen=True)
class HistoryPage:
    items: tuple[HistoryItem, ...]
    next_sync_state: str = field(repr=False)
    has_more: bool


class ExchangeHistorySource:
    def __init__(self, reader, *, service_class=None, errors=None):
        self.reader = reader
        self.service_class = service_class or importlib.import_module("exchangelib.services").SyncFolderItems
        self.errors = errors or importlib.import_module("exchangelib.errors")

    @staticmethod
    def _date(value):
        return (
            value.astimezone(timezone.utc)
            if isinstance(value, datetime) and value.tzinfo is not None
            else None
        )

    def read_page(self, folder_id, *, sync_state, start, end, page_size=5):
        if folder_id not in self.reader.settings.allowed_folder_ids or not 1 <= page_size <= 5:
            raise DomainError("forbidden", "Ce dossier ou cette taille de lot ne sont pas autorisés.")
        root = self.reader._folders.Root(account=self.reader._account)
        folder = self.reader._folders.Folder(root=root, id=folder_id)
        service = self.service_class(account=self.reader._account)
        result = []
        try:
            iterator = service.call(
                folder=folder,
                shape="IdOnly",
                additional_fields=(),
                sync_state=sync_state,
                ignore=(),
                max_changes_returned=page_size,
                sync_scope="NormalItems",
            )
            for index, entry in enumerate(iterator):
                if index >= page_size or isinstance(entry, Exception):
                    raise ValueError("invalid_inventory_page")
                kind, item = entry
                if kind == "read_flag_change":
                    result.append(HistoryItem("read_flag", "", None, None, None))
                    continue
                if kind == "delete":
                    result.append(
                        HistoryItem("unavailable", item.id, item.changekey, None, None, "remote_deleted")
                    )
                    continue
                if kind not in {"create", "update"}:
                    raise ValueError("unknown_inventory_change")
                metadata = list(
                    self.reader._account.fetch(
                        ids=[(item.id, item.changekey)],
                        only_fields=["datetime_received", "size"],
                        chunk_size=1,
                    )
                )
                if len(metadata) != 1:
                    raise ValueError("metadata_count")
                detail = metadata[0]
                if isinstance(detail, (self.errors.ErrorItemNotFound, self.errors.ErrorAccessDenied)):
                    result.append(
                        HistoryItem(
                            "unavailable", item.id, item.changekey, None, None, "metadata_unavailable"
                        )
                    )
                    continue
                if isinstance(detail, Exception):
                    raise ValueError("metadata_read_failed")
                received = self._date(getattr(detail, "datetime_received", None))
                if detail.id != item.id or received is None:
                    result.append(
                        HistoryItem(
                            "unavailable", item.id, item.changekey, None, None, "server_date_unavailable"
                        )
                    )
                    continue
                if not start <= received < end:
                    result.append(HistoryItem("out_of_range", item.id, detail.changekey, received, None))
                    continue
                size = getattr(detail, "size", None)
                if isinstance(size, int) and size > self.reader.settings.max_mime_bytes:
                    result.append(
                        HistoryItem(
                            "unavailable", item.id, detail.changekey, received, None, "mime_too_large"
                        )
                    )
                    continue
                originals = list(
                    self.reader._account.fetch(
                        ids=[(detail.id, detail.changekey)],
                        only_fields=["mime_content", "datetime_received"],
                        chunk_size=1,
                    )
                )
                if len(originals) != 1:
                    raise ValueError("mime_count")
                original = originals[0]
                if isinstance(original, (self.errors.ErrorItemNotFound, self.errors.ErrorAccessDenied)):
                    result.append(
                        HistoryItem(
                            "unavailable", item.id, detail.changekey, received, None, "mime_unavailable"
                        )
                    )
                    continue
                if isinstance(original, Exception):
                    raise ValueError("mime_read_failed")
                actual_received = self._date(getattr(original, "datetime_received", None))
                if original.id != item.id or actual_received is None:
                    result.append(
                        HistoryItem("unavailable", item.id, detail.changekey, received, None, "item_changed")
                    )
                    continue
                if not start <= actual_received < end:
                    result.append(
                        HistoryItem("out_of_range", item.id, original.changekey, actual_received, None)
                    )
                    continue
                mime = original.mime_content
                if not isinstance(mime, bytes) or len(mime) > self.reader.settings.max_mime_bytes:
                    result.append(
                        HistoryItem(
                            "unavailable",
                            item.id,
                            original.changekey,
                            actual_received,
                            None,
                            "mime_too_large",
                        )
                    )
                    continue
                result.append(HistoryItem("mail", original.id, original.changekey, actual_received, mime))
        except self.errors.ErrorInvalidSyncStateData:
            raise DomainError(
                "backfill_cursor_invalid",
                "Le curseur Exchange historique n’est plus valide. Créez une nouvelle reprise ; les messages déjà enregistrés seront dédupliqués.",
            ) from None
        except DomainError:
            raise
        except Exception:
            raise DomainError(
                "backfill_read_failed",
                "Le lot Exchange historique n’a pas pu être lu. Aucun curseur de ce lot n’a été avancé.",
            ) from None
        next_state = service.sync_state
        if (
            not isinstance(next_state, str)
            or not next_state
            or len(next_state) > 100_000
            or type(service.includes_last_item_in_range) is not bool
        ):
            raise DomainError(
                "backfill_read_failed",
                "La réponse Exchange est incomplète. Le curseur précédent est conservé.",
            )
        more = not service.includes_last_item_in_range
        if more and next_state == sync_state:
            raise DomainError(
                "backfill_read_failed",
                "Le curseur Exchange n’a pas progressé. Le lot a été arrêté sans modification.",
            )
        return HistoryPage(tuple(result), next_state, more)
