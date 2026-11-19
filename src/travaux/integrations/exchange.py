"""Optional EWS reader. No Graph assumption, autodiscover, or write operation.

Read-only here describes exposed operations, not server-granted permissions.
The DSI must separately restrict the account and approve its authentication.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .appflowy import IntegrationUnavailable


class EWSSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    enabled: bool = False
    endpoint: str
    mailbox: str = Field(min_length=3, max_length=320)
    allowed_folder_ids: tuple[str, ...] = Field(min_length=1, max_length=20)
    auth_mode: Literal["ntlm", "gssapi", "sspi"] = "ntlm"
    max_batch: int = Field(default=100, ge=1, le=100)
    max_mime_bytes: int = Field(default=10_000_000, ge=1024, le=25_000_000)

    @field_validator("endpoint")
    @classmethod
    def tls_endpoint(cls, value):
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path.lower() != "/ews/exchange.asmx"):
            raise ValueError("https_ews_endpoint_required")
        return value

    @field_validator("allowed_folder_ids")
    @classmethod
    def explicit_folders(cls, values):
        if len(set(values)) != len(values) or any(not item or len(item) > 1024 for item in values):
            raise ValueError("explicit_unique_folder_ids_required")
        return values


@dataclass(frozen=True)
class EWSMessage:
    folder_id: str
    remote_id: str
    change_key: str | None
    mime: bytes = field(repr=False)


class EWSReadOnlyCollector:
    def __init__(self, settings: EWSSettings, *, account, sdk):
        if not settings.enabled:
            raise IntegrationUnavailable("exchange_disabled")
        self.settings = settings
        self._account = account
        self._sdk = sdk
        self._folders = importlib.import_module("exchangelib.folders")

    @classmethod
    def connect(cls, settings: EWSSettings, *, username: str, password: str):
        if not settings.enabled:
            raise IntegrationUnavailable("exchange_disabled")
        try:
            sdk = importlib.import_module("exchangelib")
            protocol = importlib.import_module("exchangelib.protocol")
        except ImportError as exc:
            raise IntegrationUnavailable("exchangelib_not_installed") from exc
        if issubclass(protocol.BaseProtocol.HTTP_ADAPTER_CLS, protocol.NoVerifyHTTPAdapter):
            raise IntegrationUnavailable("insecure_exchange_tls_adapter")
        authentication = {"ntlm": sdk.NTLM, "gssapi": sdk.GSSAPI, "sspi": sdk.SSPI}[settings.auth_mode]
        # TLS checks stay enabled. No NoVerify adapter, Basic auth, or impersonation.
        configuration = sdk.Configuration(
            service_endpoint=settings.endpoint, credentials=sdk.Credentials(username=username, password=password),
            auth_type=authentication, max_connections=1,
        )
        account = sdk.Account(primary_smtp_address=settings.mailbox, config=configuration,
                              autodiscover=False, access_type=sdk.DELEGATE)
        return cls(settings, account=account, sdk=sdk)

    def read_folder_snapshot(self, folder_id: str, *, offset: int = 0, limit: int = 100) -> tuple[EWSMessage, ...]:
        """Bounded snapshot, NOT an incremental sync cursor or durable checkpoint.

        A changing mailbox can reorder offset pages. Repeat/deduplicate snapshots;
        a separately qualified EWS SyncFolderItems implementation is needed for a
        reliable change stream. No mark-as-read or mutation method is called.
        """
        if folder_id not in self.settings.allowed_folder_ids:
            raise IntegrationUnavailable("folder_out_of_scope")
        if offset < 0 or not 1 <= limit <= self.settings.max_batch:
            raise ValueError("invalid_batch_bounds")
        root = self._folders.Root(account=self._account)
        folder = self._folders.Folder(root=root, id=folder_id)
        query = folder.all().only("id", "changekey", "mime_content").order_by("datetime_received")
        query.page_size = min(limit, 25)
        query.chunk_size = 5
        messages = []
        for item in query[offset:offset + limit]:
            if isinstance(item, Exception):
                raise IntegrationUnavailable("exchange_item_read_failed")
            mime = item.mime_content
            if not isinstance(mime, bytes) or len(mime) > self.settings.max_mime_bytes:
                raise IntegrationUnavailable("exchange_mime_limit")
            messages.append(EWSMessage(folder_id=folder_id, remote_id=item.id, change_key=item.changekey, mime=mime))
        return tuple(messages)
