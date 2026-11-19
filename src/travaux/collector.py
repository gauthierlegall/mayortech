"""Collecte EWS sortante, avec accusé de persistance avant tout checkpoint."""
import json
import os
from email.parser import BytesHeaderParser
from email import policy
from pathlib import Path

from .importing import import_mail
from .integrations.exchange import EWSReadOnlyCollector, EWSSettings
from .integrations.mail import MailParseError
from .integrations.exchange_sync import DurableReceipt, EWSIncrementalCollector, ExchangelibChangeSource, SQLiteSyncCheckpointStore
from .jobs import JobQueue
from .repository import Repository


def collect_exchange(settings, config_path: Path):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("tenant_id") != settings.tenant_id or config.get("egress_approved") is not True:
        raise ValueError("exchange_scope_not_approved")
    connection_id = config.get("connection_id", "")
    if not isinstance(connection_id, str) or not connection_id or len(connection_id) > 100:
        raise ValueError("exchange_connection_id_required")
    ews = EWSSettings.model_validate_json(json.dumps(config["settings"]))
    reader = EWSReadOnlyCollector.connect(ews, username=os.getenv("TRAVAUX_EWS_USERNAME", ""), password=os.getenv("TRAVAUX_EWS_PASSWORD", ""))
    repo = Repository(settings.db_path)
    queue = JobQueue(settings.db_path)
    collector = EWSIncrementalCollector(tenant_id=settings.tenant_id, connection_id=connection_id, settings=ews, source=ExchangelibChangeSource(reader), checkpoints=SQLiteSyncCheckpointStore(settings.db_path))

    def persist(event):
        metadata = {"connection_id": connection_id, "folder_id": event.folder_id, "remote_id": event.remote_id, "change_key": event.change_key, "event_kind": event.kind}
        if event.kind in {"create", "update"} and event.mime:
            try:
                import_mail(repo, queue, settings.tenant_id, event.mime, external_id=f"ews:{connection_id}:{event.remote_id}", metadata=metadata)
            except MailParseError:
                # A poison MIME must not block all subsequent mail forever. Persist
                # a reviewable, visibly unread source retaining its server locator.
                header = BytesHeaderParser(policy=policy.default).parsebytes(event.mime[:65536].split(b"\r\n\r\n", 1)[0])
                subject = str(header.get("Subject", "Message Exchange non analysé"))[:1000]
                repo.ingest_source(settings.tenant_id, f"ews-quarantine:{event.idempotency_key}", subject, "Message non analysé : limite MIME dépassée ou structure invalide. Le message original reste dans la messagerie. Réimporter une source autorisée ou examiner manuellement.", metadata={**metadata, "raw_sha256": event.sha256, "warnings": ["mail_quarantined_review_required"], "review_required": True})
        else:
            # Preserve evidence of deletion/unavailability for an archivist's review.
            # An EWS deletion can be a move and is never treated as an erasure order.
            repo.ingest_source(settings.tenant_id, f"ews-event:{event.idempotency_key}", "Événement Exchange à vérifier", "Source supprimée, déplacée ou devenue indisponible. Vérification de son périmètre et des archives requise.", metadata={**metadata, "warnings": ["review_required"], "review_required": True})
        return DurableReceipt(event.idempotency_key, True)

    reports, remaining = [], []
    try:
        for folder_id in ews.allowed_folder_ids:
            for _ in range(10):
                report = collector.collect_once(folder_id, sink=persist)
                reports.append({"accepted": report.accepted, "ignored_read_flags": report.ignored_read_flags, "has_more": report.has_more, "checkpoint_revision": report.checkpoint_revision})
                if not report.has_more:
                    break
            remaining.append(report.has_more)
    finally:
        repo.close()
        reader._account.protocol.close()
    return {"status": "collected", "batches": reports, "more_available": any(remaining)}
