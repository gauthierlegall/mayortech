"""Import de la source et des textes de pièces : chacune garde sa propre preuve."""
import hashlib
import json
from pathlib import Path
import time
from uuid import uuid4

from .documents import DocumentRepository, extract_document
from .integrations.mail import parse_eml


def _enqueue_extract_in_transaction(db, tenant, source_id):
    """Same JobQueue schema/idempotency contract, using the active SQLite UoW."""
    payload = json.dumps({"source_id": source_id}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    db.execute("INSERT OR IGNORE INTO jobs(id,tenant_id,kind,payload,idempotency_key,created_at) VALUES(?,?,?,?,?,?)",
               (str(uuid4()), tenant, "extract", payload, source_id, time.time()))
    row = db.execute("SELECT id,payload FROM jobs WHERE tenant_id=? AND kind='extract' AND idempotency_key=?", (tenant, source_id)).fetchone()
    if row["payload"] != payload:
        raise ValueError("idempotency_payload_mismatch")
    return row["id"]


def import_mail(repo, queue, tenant, raw: bytes, *, external_id=None, metadata=None):
    parsed = parse_eml(raw, max_bytes=10_000_000)
    documents = [extract_document(item.filename, item.content) for item in parsed.attachments]
    descriptors = [{"filename": item.filename, "sha256": item.sha256, "status": document["status"], "warnings": document["warnings"]} for item, document in zip(parsed.attachments, documents)]
    originals = DocumentRepository(repo)
    extract_ids = []
    jobs = []
    shared_queue = repo.path != ":memory:" and getattr(queue, "path", None) is not None and Path(queue.path).resolve() == Path(repo.path).resolve()
    # Sources, immutable evidence, original bytes and their audit share one UoW.
    # In the standard single-DB pilot, jobs commit with those bytes. A separately
    # configured queue is fed after commit and an exact import replay repairs it.
    with repo._transaction() as db:
        source = repo.ingest_source(tenant, external_id or parsed.message_id or hashlib.sha256(raw).hexdigest(), parsed.subject or "Sans objet", parsed.text or "(Message sans texte exploitable)", thread_id=parsed.thread_id, sender=parsed.sender, received_at=parsed.received_at.isoformat() if parsed.received_at else None, metadata={**(metadata or {}), "raw_sha256": parsed.sha256, "warnings": list(parsed.warnings), "attachments": descriptors})
        originals.store(tenant, source["id"], raw, (metadata or {}).get("filename") or "courrier.eml", "message/rfc822", kind="email")
        sources = [source]
        extract_ids.append(source["id"])
        reference = repo.get_project(tenant, source["project_id"])["reference"] if source.get("project_id") else None
        for part, document in zip(parsed.attachments, documents):
            child = repo.ingest_source(tenant, f"attachment:{source['id']}:{part.sha256}", f"Pièce jointe : {part.filename}", document["text"] or "(Aucun texte extrait pour cette pièce ; consulter son original.)", project_ref=reference, sender=parsed.sender, received_at=parsed.received_at.isoformat() if parsed.received_at else None, metadata={"parent_source_id": source["id"], "filename": part.filename, "raw_sha256": part.sha256, "extraction_status": document["status"], "warnings": document["warnings"], "pages": document["pages"]})
            originals.store(tenant, child["id"], part.content, part.filename, part.content_type, kind="attachment")
            sources.append(child)
            if document["text"]:
                extract_ids.append(child["id"])
        if shared_queue:
            jobs = [_enqueue_extract_in_transaction(db, tenant, source_id) for source_id in extract_ids]
    if not shared_queue:
        jobs = [queue.enqueue(tenant, "extract", {"source_id": source_id}, source_id) for source_id in extract_ids]
    return {"source": source, "related_sources": sources[1:], "job_id": jobs[0], "job_ids": jobs}
