"""Immutable dossier uploads and human-review proposals; no automatic acceptance.

The existing bounded parser runs before the unit of work. Source, original,
receipt and extraction job commit together. Model work runs after that commit;
its cached output is validated and written under a fresh authorization check.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
from pathlib import Path, PurePosixPath
import re
import secrets
import time
from uuid import uuid4

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from .documents import DocumentRepository, extract_document
from .domain import DomainError, canonical_json, require_text, utc_now
from .importing import _enqueue_extract_in_transaction
from .pipeline import extract_source
from .project_access import access_scope

MAX_FILE_BYTES = 5_000_000
MAX_BASE64_LENGTH = 4 * ((MAX_FILE_BYTES + 2) // 3)
MEDIA_TYPES = {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.txt': 'text/plain', '.md': 'text/markdown', '.csv': 'text/csv'}


class _CachedExtraction:
    """A precomputed result, with no provider or I/O reachable under the UoW."""
    def __init__(self, result): self.result = result
    def extract(self, _text): return self.result


class DocumentUploadService:
    def __init__(self, repo, settings, *, queue, extractor):
        self.repo, self.settings, self.queue, self.extractor = repo, settings, queue, extractor
        self.documents = DocumentRepository(repo)
        with repo._transaction() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS document_uploads(
                id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,client_id TEXT NOT NULL,
                project_id TEXT NOT NULL,filename TEXT NOT NULL,payload_hash TEXT NOT NULL,
                source_id TEXT NOT NULL,document_id TEXT NOT NULL,job_id TEXT NOT NULL,created_at TEXT NOT NULL,
                UNIQUE(tenant_id,actor_id,client_id),
                FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id),
                FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id),
                FOREIGN KEY(tenant_id,document_id) REFERENCES original_documents(tenant_id,id))''')

    def _guard(self, tenant, actor, project_id):
        if self.settings.mode == 'public_demo':
            raise DomainError('forbidden', 'La démonstration publique accepte uniquement ses documents fictifs préparés.')
        if not isinstance(actor, dict) or actor.get('tenant_id') != tenant or actor.get('permissions', {}).get('workspace', {}).get('write') is not True:
            raise DomainError('forbidden', 'Votre accès ne permet pas d’importer une pièce dans ce dossier.')
        identity = require_text(actor.get('actor_id'), 'actor_id', maximum=200)
        access_scope(self.repo, actor).require_project_contents(project_id, write=True)
        return identity, self.repo.get_project(tenant, project_id)

    def _queue_boundary(self):
        if self.repo.path == ':memory:' or getattr(self.queue, 'path', None) is None or Path(self.queue.path).resolve() != Path(self.repo.path).resolve():
            raise DomainError('integration_unavailable', 'Le dépôt de documents et la file de traitement doivent partager le stockage transactionnel.')

    @staticmethod
    def _input(filename, content_base64, client_id, project_id):
        filename = require_text(filename, 'filename', maximum=180).strip()
        suffix = PurePosixPath(filename).suffix.lower()
        if suffix not in MEDIA_TYPES or any(character in filename for character in ('/', '\\', ':')) or not filename.isprintable():
            raise DomainError('invalid_input', 'Choisissez un fichier PDF, DOCX, TXT, MD ou CSV, avec un nom de fichier simple.')
        if not isinstance(client_id, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', client_id):
            raise DomainError('invalid_input', 'L’identifiant de cet import est invalide.')
        try:
            if not isinstance(content_base64, str) or len(content_base64) > MAX_BASE64_LENGTH:
                raise ValueError()
            raw = base64.b64decode(content_base64, validate=True)
            if not raw or len(raw) > MAX_FILE_BYTES:
                raise ValueError()
        except (ValueError, binascii.Error):
            raise DomainError('invalid_input', 'Le fichier doit contenir au maximum 5 Mo et un encodage valide.') from None
        digest = hashlib.sha256(raw).hexdigest()
        fingerprint = hashlib.sha256(canonical_json({'project_id': project_id, 'filename': filename, 'sha256': digest}).encode()).hexdigest()
        return filename, raw, suffix, digest, fingerprint

    def _receipt(self, tenant, identity, client_id):
        return self.repo._db.execute('SELECT * FROM document_uploads WHERE tenant_id=? AND actor_id=? AND client_id=?', (tenant, identity, client_id)).fetchone()

    def _reply(self, tenant, actor, receipt, *, replayed):
        with self.repo._lock:
            self._guard(tenant, actor, receipt['project_id'])
            scope = access_scope(self.repo, actor)
            scope.require_source(receipt['source_id'])
            source = self.repo.get_source(tenant, receipt['source_id'])
            document = self.documents.get(tenant, receipt['document_id'], actor=actor)
        job = self.queue.get(tenant, receipt['job_id'])
        warnings = list(source['metadata'].get('warnings', []))
        result = job.get('result') if job else None
        if isinstance(result, dict): warnings.extend(result.get('warnings', []))
        if job and job['status'] == 'failed': warnings.append('L’analyse automatique n’a pas abouti. L’original reste conservé ; une revue humaine est nécessaire.')
        return {'status': 'needs_review', 'project_id': receipt['project_id'], 'source_id': receipt['source_id'], 'document_id': receipt['document_id'], 'job_id': receipt['job_id'], 'job_status': job['status'] if job else 'unavailable', 'extraction_status': source['metadata']['extraction_status'], 'candidate_count': result.get('candidates', 0) if isinstance(result, dict) else 0, 'document': document, 'warnings': list(dict.fromkeys(warnings)), 'replayed': replayed}

    def _analyze(self, tenant, actor, project_id, source_id, job_id):
        token, now = secrets.token_hex(24), time.time()
        with self.repo._transaction() as db:
            self._guard(tenant, actor, project_id)
            access_scope(self.repo, actor).require_source(source_id)
            claimed = db.execute("UPDATE jobs SET status='running',lease_token=?,lease_until=?,worker='document-upload',attempts=attempts+1 WHERE tenant_id=? AND id=? AND (status='queued' OR (status='running' AND lease_until<?))", (token, now+120, tenant, job_id, now)).rowcount
            source = self.repo.get_source(tenant, source_id)
        if not claimed: return
        try:
            if not source['body'].strip():
                result = {'status': 'needs_review', 'candidates': 0, 'warnings': ['Aucun texte exploitable : consultez l’original ou fournissez une version avec texte.']}
            elif self.extractor is None:
                raise ValueError('document_extractor_unavailable')
            else:
                # Provider work occurs outside any transaction. Only the cached
                # result goes through the normal evidence pipeline under the UoW.
                extracted = self.extractor.extract(source['body'])
                with self.repo._transaction():
                    self._guard(tenant, actor, project_id)
                    access_scope(self.repo, actor).require_source(source_id)
                    result = extract_source(self.repo, tenant, source_id, _CachedExtraction(extracted))
            self.queue.complete(job_id, token, result)
        except DomainError as failure:
            self.queue.fail(job_id, token, 'document_analysis_failed_review_required')
            if failure.code in {'forbidden', 'not_found', 'unauthenticated'}: raise
        except Exception:
            # No provider exception, parser output, credential or document body
            # is copied into the durable error code or response.
            self.queue.fail(job_id, token, 'document_analysis_failed_review_required')

    def upload(self, tenant, actor, project_id, *, filename, content_base64, client_id):
        with self.repo._lock:
            identity, project = self._guard(tenant, actor, project_id)
        self._queue_boundary()
        filename, raw, suffix, digest, fingerprint = self._input(filename, content_base64, client_id, project_id)
        with self.repo._lock:
            old = self._receipt(tenant, identity, client_id)
            if old:
                if old['payload_hash'] != fingerprint:
                    raise DomainError('idempotency_conflict', 'Cet identifiant appartient déjà à un autre import. Rechargez le dossier avant de recommencer.')
        if old:
            self._analyze(tenant, actor, project_id, old['source_id'], old['job_id'])
            return self._reply(tenant, actor, old, replayed=True)
        parsed = extract_document(filename, raw)
        text = parsed.get('text', '') if parsed.get('status') in {'extracted', 'partial'} else ''
        warnings = list(parsed.get('warnings', []))
        if not text.strip(): warnings.append('Aucun texte exploitable ; une revue manuelle de cette pièce est requise.')
        with self.repo._transaction() as db:
            identity, project = self._guard(tenant, actor, project_id)
            old = self._receipt(tenant, identity, client_id)
            if old:
                if old['payload_hash'] != fingerprint: raise DomainError('idempotency_conflict', 'Cet identifiant appartient déjà à un autre import.')
                receipt, replayed = old, True
            else:
                upload_id = str(uuid4())
                family = hashlib.sha256(filename.casefold().encode()).hexdigest()
                source = self.repo.ingest_source(tenant, 'upload:'+project_id+':'+family, 'Pièce déposée : '+filename, text, project_ref=project['reference'], metadata={'source_kind': 'uploaded_document', 'origin': 'human_document_upload', 'filename': filename, 'raw_sha256': digest, 'extraction_status': parsed.get('status', 'failed'), 'warnings': warnings, 'pages': parsed.get('pages', []), 'upload_id': upload_id, 'uploaded_by': identity})
                if source['project_ids'] != [project_id]:
                    raise DomainError('invalid_state', 'Le document doit appartenir uniquement au dossier choisi.')
                document = self.documents.store(tenant, source['id'], raw, filename, MEDIA_TYPES[suffix], kind='attachment')
                job_id = _enqueue_extract_in_transaction(db, tenant, source['id'])
                db.execute('INSERT INTO document_uploads VALUES(?,?,?,?,?,?,?,?,?,?,?)', (upload_id, tenant, identity, client_id, project_id, filename, fingerprint, source['id'], document['id'], job_id, utc_now()))
                self.repo._audit(db, tenant, project_id, 'document.uploaded', identity, document['id'], {'source_id': source['id'], 'document_id': document['id'], 'sha256': digest, 'size': len(raw)})
                receipt, replayed = self._receipt(tenant, identity, client_id), False
        self._analyze(tenant, actor, project_id, receipt['source_id'], receipt['job_id'])
        return self._reply(tenant, actor, receipt, replayed=replayed)


class DocumentUploadBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filename: str = Field(min_length=1, max_length=180, strict=True)
    content_base64: str = Field(min_length=1, max_length=MAX_BASE64_LENGTH, strict=True)
    client_id: str = Field(min_length=1, max_length=100, strict=True)


def register_document_upload_routes(app, repo, tenant, actor, settings, *, queue, extractor):
    service = DocumentUploadService(repo, settings, queue=queue, extractor=extractor)

    @app.post('/api/v1/projects/{project_id}/documents/upload', status_code=201)
    def upload(project_id: str, body: DocumentUploadBody, current=Depends(actor)):
        return service.upload(tenant, current, project_id, **body.model_dump())

    return service
