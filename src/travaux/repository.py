"""Durable SQLite pilot. All object reads/writes are scoped by tenant.

This is an executable local demonstration, not a Postgres concurrency or
production-security qualification. HTTP authentication is owned by the server.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import re
import sqlite3
import threading
from uuid import uuid4

from .domain import (DomainError, canonical_json, content_hash, evidence_span,
                     normalize_value, normalized, payload_hash, require_text,
                     utc_now, validate_field)
from .summary_format import summary_field_label


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS projects (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, reference TEXT NOT NULL COLLATE NOCASE,
 name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active',
 revision INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
 UNIQUE(tenant_id,reference), UNIQUE(tenant_id,id));
CREATE TABLE IF NOT EXISTS sources (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, external_id TEXT NOT NULL, version INTEGER NOT NULL,
 subject TEXT NOT NULL, body TEXT NOT NULL, body_hash TEXT NOT NULL, payload_hash TEXT NOT NULL,
 thread_id TEXT, project_ref TEXT, sender TEXT NOT NULL, received_at TEXT NOT NULL,
 metadata TEXT NOT NULL, match_status TEXT NOT NULL, match_candidates TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ready', created_at TEXT NOT NULL,
 UNIQUE(tenant_id,external_id,payload_hash), UNIQUE(tenant_id,id));
CREATE TABLE IF NOT EXISTS source_links (
 tenant_id TEXT NOT NULL, source_id TEXT NOT NULL, project_id TEXT NOT NULL,
 actor_id TEXT NOT NULL, created_at TEXT NOT NULL,
 PRIMARY KEY(tenant_id,source_id,project_id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id));
CREATE TABLE IF NOT EXISTS candidates (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, source_id TEXT NOT NULL,
 field TEXT NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL, dedup_key TEXT NOT NULL,
 origin TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', reviewed_by TEXT,
 reviewed_at TEXT, created_at TEXT NOT NULL, UNIQUE(tenant_id,project_id,dedup_key),
 UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id));
CREATE TABLE IF NOT EXISTS evidence (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
 source_id TEXT NOT NULL, source_hash TEXT NOT NULL, start INTEGER NOT NULL,
 end INTEGER NOT NULL, quote TEXT NOT NULL,
 UNIQUE(tenant_id,candidate_id,source_id,start,end),
 FOREIGN KEY(tenant_id,candidate_id) REFERENCES candidates(tenant_id,id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id));
CREATE TABLE IF NOT EXISTS notes (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, source_id TEXT NOT NULL,
 content TEXT NOT NULL, actor_id TEXT NOT NULL, origin TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id));
CREATE TABLE IF NOT EXISTS summaries (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, version INTEGER NOT NULL,
 snapshot_revision INTEGER NOT NULL, snapshot TEXT NOT NULL, snapshot_hash TEXT NOT NULL,
 content TEXT NOT NULL, content_hash TEXT NOT NULL, citations TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'draft', stale INTEGER NOT NULL DEFAULT 0,
 model TEXT NOT NULL DEFAULT 'deterministic-local', created_by TEXT NOT NULL, created_at TEXT NOT NULL,
 approved_by TEXT, approved_at TEXT, cancelled_by TEXT, cancelled_at TEXT, cancellation_reason TEXT,
 parent_summary_id TEXT, native_revision TEXT,
 coverage TEXT NOT NULL DEFAULT 'partial', warnings TEXT NOT NULL DEFAULT '[]',
 source_context_hash TEXT NOT NULL DEFAULT '', UNIQUE(tenant_id,project_id,version),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id));
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, revision INTEGER NOT NULL,
 event_type TEXT NOT NULL, actor_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(tenant_id,project_id,revision),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id));
CREATE TABLE IF NOT EXISTS outbox (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES events(id));
CREATE TABLE IF NOT EXISTS audit_events (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
 action TEXT NOT NULL, actor_id TEXT NOT NULL, object_id TEXT NOT NULL,
 payload TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id));
CREATE TABLE IF NOT EXISTS workspace_note_bindings (
 tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, remote_id TEXT NOT NULL,
 note_id TEXT NOT NULL, source_id TEXT NOT NULL, body_hash TEXT NOT NULL,
 remote_revision TEXT, observed_at TEXT NOT NULL,
 PRIMARY KEY(tenant_id,project_id,remote_id),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id));
CREATE INDEX IF NOT EXISTS idx_sources_thread ON sources(tenant_id,thread_id);
CREATE INDEX IF NOT EXISTS idx_candidates_project ON candidates(tenant_id,project_id,status);
CREATE INDEX IF NOT EXISTS idx_summaries_project ON summaries(tenant_id,project_id,version);
"""


class Repository:
    def __init__(self, db_path: str | Path = ':memory:'):
        if str(db_path) != ':memory:':
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(db_path)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None, timeout=15)
        self._db.row_factory = sqlite3.Row
        self._db.execute('PRAGMA foreign_keys=ON')
        self._db.execute('PRAGMA journal_mode=WAL')
        self._db.execute('PRAGMA busy_timeout=15000')
        self._db.executescript(SCHEMA)
        if 'native_revision' not in {r[1] for r in self._db.execute('PRAGMA table_info(summaries)')}:
            self._db.execute('ALTER TABLE summaries ADD COLUMN native_revision TEXT')
        existing_columns = {r[1] for r in self._db.execute('PRAGMA table_info(summaries)')}
        for column, declaration in (
            ('coverage', "TEXT NOT NULL DEFAULT 'partial'"),
            ('warnings', "TEXT NOT NULL DEFAULT '[]'"),
            ('source_context_hash', "TEXT NOT NULL DEFAULT ''"),
        ):
            if column not in existing_columns:
                self._db.execute(f'ALTER TABLE summaries ADD COLUMN {column} {declaration}')

    def close(self):
        with self._lock:
            self._db.close()

    @contextmanager
    def _transaction(self):
        with self._lock:
            nested = self._db.in_transaction
            savepoint = 'batch_' + uuid4().hex if nested else None
            self._db.execute('SAVEPOINT ' + savepoint if nested else 'BEGIN IMMEDIATE')
            try:
                yield self._db
                self._db.execute('RELEASE SAVEPOINT ' + savepoint if nested else 'COMMIT')
            except BaseException:
                if nested:
                    self._db.execute('ROLLBACK TO SAVEPOINT ' + savepoint)
                    self._db.execute('RELEASE SAVEPOINT ' + savepoint)
                else:
                    self._db.execute('ROLLBACK')
                raise

    @staticmethod
    def _one(db, table, tenant_id, object_id):
        if table not in ('projects', 'sources', 'candidates', 'summaries'):
            raise ValueError('Internal table not allowed')
        row = db.execute(f'SELECT * FROM {table} WHERE tenant_id=? AND id=?', (tenant_id, object_id)).fetchone()
        if row is None:
            raise DomainError('not_found', 'Objet introuvable dans le périmètre autorisé.')
        return dict(row)

    def _project(self, db, tenant, project_id):
        result = self._one(db, 'projects', tenant, project_id)
        counts = {}
        for key, query in {
            'sources': 'SELECT count(*) FROM source_links WHERE tenant_id=? AND project_id=?',
            'candidates': 'SELECT count(*) FROM candidates WHERE tenant_id=? AND project_id=?',
            'pending': "SELECT count(*) FROM candidates WHERE tenant_id=? AND project_id=? AND status='pending'",
            'accepted': "SELECT count(*) FROM candidates WHERE tenant_id=? AND project_id=? AND status='accepted'",
            'notes': 'SELECT count(*) FROM notes WHERE tenant_id=? AND project_id=?',
            'summaries': 'SELECT count(*) FROM summaries WHERE tenant_id=? AND project_id=?',
        }.items():
            counts[key] = db.execute(query, (tenant, project_id)).fetchone()[0]
        result['stats'] = counts
        return result

    def create_project(self, tenant_id, reference, name, project_id=None, description='', status='active'):
        require_text(tenant_id, 'tenant_id', maximum=100)
        require_text(reference, 'reference', maximum=100)
        require_text(name, 'name', maximum=300)
        require_text(description, 'description', maximum=10000, empty=True)
        project_id = project_id or str(uuid4())
        with self._transaction() as db:
            existing = db.execute('SELECT id FROM projects WHERE tenant_id=? AND reference=? COLLATE NOCASE',
                                  (tenant_id, reference.strip())).fetchone()
            if existing:
                return self._project(db, tenant_id, existing['id'])
            try:
                db.execute('INSERT INTO projects(id,tenant_id,reference,name,description,status,created_at) VALUES(?,?,?,?,?,?,?)',
                           (project_id, tenant_id, reference.strip(), name.strip(), description, status, utc_now()))
            except sqlite3.IntegrityError:
                raise DomainError('conflict', 'Identifiant de chantier déjà utilisé.') from None
            return self._project(db, tenant_id, project_id)

    def get_project(self, tenant_id, project_id):
        with self._lock:
            return self._project(self._db, tenant_id, project_id)

    def list_projects(self, tenant_id):
        with self._lock:
            return [self._project(self._db, tenant_id, row['id']) for row in
                    self._db.execute('SELECT id FROM projects WHERE tenant_id=? ORDER BY reference', (tenant_id,)).fetchall()]

    def _match(self, db, tenant, subject, thread_id, project_ref):
        projects = [dict(r) for r in db.execute('SELECT id,reference,name FROM projects WHERE tenant_id=?', (tenant,))]
        exact = set()
        for project in projects:
            if project_ref and normalized(project_ref) == normalized(project['reference']):
                exact.add(project['id'])
            elif not project_ref and re.search(r'(?<![\w-])' + re.escape(project['reference']) + r'(?![\w-])', subject, re.I):
                exact.add(project['id'])
        threads = set()
        if thread_id:
            threads = {r[0] for r in db.execute('SELECT DISTINCT l.project_id FROM source_links l JOIN sources s '
                       'ON s.tenant_id=l.tenant_id AND s.id=l.source_id WHERE s.tenant_id=? AND s.thread_id=?', (tenant, thread_id))}
        candidates = exact | threads
        if len(candidates) == 1:
            return 'matched', sorted(candidates)
        if len(candidates) > 1:
            return 'ambiguous', sorted(candidates)
        names = [p['id'] for p in projects if normalized(p['name']) and normalized(p['name']) in normalized(subject)]
        return ('ambiguous' if names else 'unmatched'), sorted(names)

    def _source(self, db, tenant, source_id):
        row = self._one(db, 'sources', tenant, source_id)
        row['metadata'] = json.loads(row['metadata'])
        row['candidate_project_ids'] = json.loads(row.pop('match_candidates'))
        row['project_ids'] = [r[0] for r in db.execute('SELECT project_id FROM source_links WHERE tenant_id=? AND source_id=? ORDER BY project_id',
                                                     (tenant, source_id))]
        row['project_id'] = row['project_ids'][0] if len(row['project_ids']) == 1 else None
        return row

    def ingest_source(self, tenant_id, external_id, subject, body, thread_id=None, project_ref=None,
                      sender='', received_at=None, metadata=None):
        require_text(external_id, 'external_id', maximum=1000)
        require_text(subject, 'subject', maximum=10000, empty=True)
        require_text(body, 'body', maximum=2_000_000, empty=True)
        metadata = metadata or {}
        serialized_metadata = canonical_json(metadata)
        if not isinstance(metadata, dict) or len(serialized_metadata) > 300000:
            raise DomainError('invalid_input', 'Métadonnées structurées trop volumineuses.')
        fingerprint = payload_hash([subject, body, thread_id, project_ref, sender, received_at, metadata])
        with self._transaction() as db:
            existing = db.execute('SELECT id FROM sources WHERE tenant_id=? AND external_id=? AND payload_hash=?',
                                  (tenant_id, external_id, fingerprint)).fetchone()
            if existing:
                return self._source(db, tenant_id, existing['id'])
            version = db.execute('SELECT coalesce(max(version),0)+1 FROM sources WHERE tenant_id=? AND external_id=?',
                                 (tenant_id, external_id)).fetchone()[0]
            match_status, candidates = self._match(db, tenant_id, subject, thread_id, project_ref)
            source_id = str(uuid4())
            now = utc_now()
            db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (source_id, tenant_id, external_id, version, subject, body, content_hash(body), fingerprint,
                        thread_id, project_ref, sender, received_at or now, serialized_metadata,
                        match_status, canonical_json(candidates), 'ready' if match_status == 'matched' else 'needs_match', now))
            if match_status == 'matched':
                db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', (tenant_id, source_id, candidates[0], 'matching-rule', now))
                self._stale_source_context(db, tenant_id, candidates[0])
            return self._source(db, tenant_id, source_id)

    def assign_source(self, tenant_id, source_id, project_id, actor_id='demo'):
        with self._transaction() as db:
            self._one(db, 'sources', tenant_id, source_id)
            self._one(db, 'projects', tenant_id, project_id)
            existing = db.execute('SELECT project_id FROM source_links WHERE tenant_id=? AND source_id=?', (tenant_id, source_id)).fetchall()
            if existing and project_id not in {r[0] for r in existing}:
                raise DomainError('conflict', 'La source est déjà rattachée ; une réaffectation doit être réconciliée explicitement.')
            db.execute('INSERT OR IGNORE INTO source_links VALUES(?,?,?,?,?)', (tenant_id, source_id, project_id, actor_id, utc_now()))
            db.execute("UPDATE sources SET match_status='matched',match_candidates=?,status='ready' WHERE tenant_id=? AND id=?",
                       (canonical_json([project_id]), tenant_id, source_id))
            if not existing:
                self._stale_source_context(db, tenant_id, project_id)
            return self._source(db, tenant_id, source_id)

    def get_source(self, tenant_id, source_id):
        with self._lock:
            return self._source(self._db, tenant_id, source_id)

    def list_sources(self, tenant_id, project_id=None):
        with self._lock:
            if project_id is not None:
                self._one(self._db, 'projects', tenant_id, project_id)
                ids = self._db.execute('SELECT source_id FROM source_links WHERE tenant_id=? AND project_id=? ORDER BY created_at',
                                       (tenant_id, project_id)).fetchall()
            else:
                ids = self._db.execute('SELECT id FROM sources WHERE tenant_id=? ORDER BY created_at', (tenant_id,)).fetchall()
            return [self._source(self._db, tenant_id, row[0]) for row in ids]

    def _candidate(self, db, tenant, candidate_id):
        row = self._one(db, 'candidates', tenant, candidate_id)
        row['value'] = json.loads(row['value'])
        row['evidence'] = [dict(r) for r in db.execute('SELECT source_id,source_hash,start,end,quote FROM evidence '
                          'WHERE tenant_id=? AND candidate_id=? ORDER BY rowid', (tenant, candidate_id))]
        comparable = list(db.execute("SELECT id,kind,value FROM candidates WHERE tenant_id=? AND project_id=? "
            "AND field=? AND status='accepted' AND id<>? AND value<>? ORDER BY created_at", 
            (tenant, row['project_id'], row['field'], candidate_id, canonical_json(row['value']))))
        row['conflict_with'] = [r['id'] for r in comparable if not (
            row['kind'] == 'money' and r['kind'] == 'money'
            and row['value']['basis'] != json.loads(r['value'])['basis'])]
        return row

    def add_candidate(self, tenant_id, project_id, source_id, field, value, *, quote, kind='text', origin='mail',
                      evidence_start=None, evidence_end=None, source_hash=None):
        field = validate_field(field)
        value = normalize_value(kind, value)
        with self._transaction() as db:
            self._one(db, 'projects', tenant_id, project_id)
            source = self._source(db, tenant_id, source_id)
            if project_id not in source['project_ids']:
                raise DomainError('unmatched_source', 'Rattacher et valider le chantier avant extraction.')
            span = evidence_span(source, quote, evidence_start, evidence_end, source_hash)
            key = payload_hash([field, kind, value])
            existing = db.execute('SELECT id FROM candidates WHERE tenant_id=? AND project_id=? AND dedup_key=?',
                                  (tenant_id, project_id, key)).fetchone()
            if existing is None:
                # Replaying an old source must retain its old decision; a genuinely
                # new announcement may propose a previously superseded value again.
                existing = db.execute('SELECT c.id FROM candidates c JOIN evidence e ON '
                    'e.tenant_id=c.tenant_id AND e.candidate_id=c.id WHERE c.tenant_id=? AND c.project_id=? '
                    'AND c.field=? AND c.kind=? AND c.value=? AND e.source_id=? ORDER BY c.created_at DESC LIMIT 1',
                    (tenant_id, project_id, field, kind, canonical_json(value), source_id)).fetchone()
            candidate_id = existing[0] if existing else str(uuid4())
            if not existing:
                db.execute('INSERT INTO candidates(id,tenant_id,project_id,source_id,field,kind,value,dedup_key,origin,created_at) '
                           'VALUES(?,?,?,?,?,?,?,?,?,?)', (candidate_id, tenant_id, project_id, source_id,
                            field, kind, canonical_json(value), key, origin, utc_now()))
                self._stale_source_context(db, tenant_id, project_id)
            db.execute('INSERT OR IGNORE INTO evidence VALUES(?,?,?,?,?,?,?,?)', (str(uuid4()), tenant_id, candidate_id,
                       source_id, span['source_hash'], span['start'], span['end'], span['quote']))
            db.execute("UPDATE sources SET status='extracted' WHERE tenant_id=? AND id=?", (tenant_id, source_id))
            return self._candidate(db, tenant_id, candidate_id)

    def get_candidate(self, tenant_id, candidate_id):
        with self._lock:
            return self._candidate(self._db, tenant_id, candidate_id)

    def add_candidates(self, tenant_id, project_id, source_id, candidates):
        """Commit a complete extraction batch, including evidence and coverage, or none."""
        if not isinstance(candidates, list) or len(candidates) > 40:
            raise DomainError('invalid_input', 'Un lot borné à 40 propositions est attendu.')
        allowed = {'field', 'value', 'quote', 'kind', 'origin', 'evidence_start', 'evidence_end', 'source_hash'}
        with self._transaction() as db:
            self._one(db, 'projects', tenant_id, project_id)
            source = self._source(db, tenant_id, source_id)
            if project_id not in source['project_ids']:
                raise DomainError('unmatched_source', 'Rattacher le chantier avant extraction.')
            result = []
            for item in candidates:
                if not isinstance(item, dict) or set(item) - allowed or not {'field', 'value', 'quote'} <= set(item):
                    raise DomainError('invalid_input', 'Contrat de proposition invalide.')
                result.append(self.add_candidate(tenant_id, project_id, source_id, **item))
            if source['status'] != 'extracted':
                db.execute("UPDATE sources SET status='extracted' WHERE tenant_id=? AND id=?", (tenant_id, source_id))
                self._stale_source_context(db, tenant_id, project_id)
            return result

    def list_candidates(self, tenant_id, project_id=None):
        with self._lock:
            params = [tenant_id]
            sql = 'SELECT id FROM candidates WHERE tenant_id=?'
            if project_id is not None:
                self._one(self._db, 'projects', tenant_id, project_id)
                sql += ' AND project_id=?'
                params.append(project_id)
            return [self._candidate(self._db, tenant_id, r[0]) for r in self._db.execute(sql + ' ORDER BY created_at', params).fetchall()]

    def _event(self, db, tenant, project_id, actor_id, event_type, payload):
        db.execute('UPDATE projects SET revision=revision+1 WHERE tenant_id=? AND id=?', (tenant, project_id))
        revision = self._one(db, 'projects', tenant, project_id)['revision']
        now, event_id = utc_now(), str(uuid4())
        db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?)', (event_id, tenant, project_id, revision,
                   event_type, actor_id, canonical_json(payload), now))
        db.execute('INSERT INTO outbox(id,tenant_id,event_id,created_at) VALUES(?,?,?,?)', (str(uuid4()), tenant, event_id, now))
        db.execute("UPDATE summaries SET stale=1,status=CASE WHEN status IN ('draft','needs_review') THEN 'stale' ELSE status END "
                   'WHERE tenant_id=? AND project_id=? AND snapshot_revision<?', (tenant, project_id, revision))
        return revision

    @staticmethod
    def _stale_source_context(db, tenant, project_id):
        # Observations invalidate a draft without falsely claiming a human has
        # accepted a new fact or incrementing the validated-memory revision.
        db.execute("UPDATE summaries SET stale=1,status=CASE WHEN status IN ('draft','needs_review') THEN 'stale' ELSE status END "
                   'WHERE tenant_id=? AND project_id=?', (tenant, project_id))

    def review_candidate(self, tenant_id, candidate_id, decision, actor_id='demo', expected_revision=None):
        if decision not in ('accept', 'reject', 'replace'):
            raise DomainError('invalid_input', 'Décision accept, reject ou replace attendue.')
        with self._transaction() as db:
            candidate = self._candidate(db, tenant_id, candidate_id)
            project = self._one(db, 'projects', tenant_id, candidate['project_id'])
            desired = 'rejected' if decision == 'reject' else 'accepted'
            if candidate['status'] == desired:
                return candidate
            if expected_revision is not None and project['revision'] != expected_revision:
                raise DomainError('stale_revision', 'Le chantier a changé ; relire avant de décider.')
            if candidate['status'] != 'pending':
                raise DomainError('invalid_state', 'Cette proposition a déjà fait l’objet d’une décision.')
            if desired == 'accepted' and candidate['value'] is None:
                raise DomainError('invalid_state', 'Une valeur inconnue ne devient pas un engagement confirmé.')
            if desired == 'accepted' and candidate['conflict_with'] and decision != 'replace':
                raise DomainError('unresolved_conflict', 'Comparer et remplacer explicitement les valeurs contradictoires.')
            now = utc_now()
            if decision == 'replace':
                for conflict_id in candidate['conflict_with']:
                    db.execute("UPDATE candidates SET status='superseded',dedup_key=dedup_key||':superseded:'||id "
                               'WHERE tenant_id=? AND id=?', (tenant_id, conflict_id))
            db.execute('UPDATE candidates SET status=?,reviewed_by=?,reviewed_at=? WHERE tenant_id=? AND id=?',
                       (desired, actor_id, now, tenant_id, candidate_id))
            self._event(db, tenant_id, candidate['project_id'], actor_id, 'candidate.' + desired,
                        {'candidate_id': candidate_id, 'decision': decision, 'supersedes': candidate['conflict_with'] if decision == 'replace' else []})
            return self._candidate(db, tenant_id, candidate_id)

    def add_note(self, tenant_id, project_id, content, actor_id='demo', origin='human'):
        require_text(content, 'content', maximum=100000)
        with self._transaction() as db:
            self._one(db, 'projects', tenant_id, project_id)
            note = self._insert_note(db, tenant_id, project_id, content, actor_id, origin)
            self._event(db, tenant_id, project_id, actor_id, 'note.added', {'note_id': note['id'], 'source_id': note['source_id']})
            return note

    def _insert_note(self, db, tenant_id, project_id, content, actor_id, origin):
        note_id, source_id, now = str(uuid4()), str(uuid4()), utc_now()
        metadata = {'origin': origin, 'actor_id': actor_id, 'note_id': note_id}
        db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (source_id, tenant_id, 'note:' + note_id, 1, 'Note humaine', content, content_hash(content),
             payload_hash(metadata), None, None, actor_id, now, canonical_json(metadata), 'matched',
             canonical_json([project_id]), 'manual', now))
        db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', (tenant_id, source_id, project_id, actor_id, now))
        db.execute('INSERT INTO notes VALUES(?,?,?,?,?,?,?,?)', (note_id, tenant_id, project_id, source_id, content, actor_id, origin, now))
        return dict(db.execute('SELECT * FROM notes WHERE tenant_id=? AND id=?', (tenant_id, note_id)).fetchone())

    def ingest_workspace_note(self, tenant_id, project_id, remote_id, content, remote_revision=None,
                              actor_id='appflowy:actor_unverified', origin='manual_appflowy', actor_verified=False):
        """Read-only native import; current note moves to a new immutable source version.

        The caller must map remote_id to project_id server-side before calling.
        A content fingerprint is an observation, never a CAS or verified author.
        """
        require_text(remote_id, 'remote_id', maximum=1000)
        require_text(content, 'content', maximum=100000)
        with self._transaction() as db:
            self._one(db, 'projects', tenant_id, project_id)
            binding = db.execute('SELECT * FROM workspace_note_bindings WHERE tenant_id=? AND project_id=? AND remote_id=?',
                                 (tenant_id, project_id, remote_id)).fetchone()
            body_hash = content_hash(content)
            revision_json = canonical_json(remote_revision) if remote_revision is not None else None
            now = utc_now()
            if binding and binding['body_hash'] == body_hash:
                db.execute('UPDATE workspace_note_bindings SET remote_revision=?,observed_at=? WHERE tenant_id=? AND project_id=? AND remote_id=?',
                           (revision_json, now, tenant_id, project_id, remote_id))
                return dict(db.execute('SELECT * FROM notes WHERE tenant_id=? AND id=?', (tenant_id, binding['note_id'])).fetchone())
            if origin not in ('manual_appflowy', 'manual_affine') or type(actor_verified) is not bool:
                raise DomainError('invalid_input', 'Origine de note native invalide.')
            external_id = ('appflowy-note:' if origin == 'manual_appflowy' else 'affine-note:') + payload_hash([remote_id, project_id])
            if binding is None:
                note = self._insert_note(db, tenant_id, project_id, content, actor_id, origin)
                note_id, source_id, version = note['id'], note['source_id'], 1
                metadata = {'origin': origin, 'note_id': note_id, 'remote_id': remote_id,
                            'remote_revision': remote_revision, 'actor_id': actor_id, 'actor_verified': actor_verified}
                # The object has not yet been exposed; finish its immutable initial
                # version inside this same transaction before its first commit.
                db.execute('UPDATE sources SET external_id=?,metadata=?,payload_hash=? WHERE tenant_id=? AND id=?',
                           (external_id, canonical_json(metadata), payload_hash([body_hash, remote_revision, version]), tenant_id, source_id))
                db.execute('INSERT INTO workspace_note_bindings VALUES(?,?,?,?,?,?,?,?)',
                           (tenant_id, project_id, remote_id, note_id, source_id, body_hash, revision_json, now))
            else:
                note_id, source_id = binding['note_id'], str(uuid4())
                version = db.execute('SELECT max(version)+1 FROM sources WHERE tenant_id=? AND external_id=?',
                                     (tenant_id, external_id)).fetchone()[0]
                metadata = {'origin': origin, 'note_id': note_id, 'remote_id': remote_id,
                            'remote_revision': remote_revision, 'actor_id': actor_id, 'actor_verified': actor_verified}
                db.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (source_id, tenant_id, external_id, version, 'Page native du chantier', content, body_hash,
                     payload_hash([body_hash, remote_revision, version]), None, None, actor_id, now, canonical_json(metadata),
                     'matched', canonical_json([project_id]), 'manual', now))
                db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', (tenant_id, source_id, project_id, actor_id, now))
                db.execute('UPDATE notes SET source_id=?,content=?,actor_id=? WHERE tenant_id=? AND id=?',
                           (source_id, content, actor_id, tenant_id, note_id))
                db.execute('UPDATE workspace_note_bindings SET source_id=?,body_hash=?,remote_revision=?,observed_at=? '
                           'WHERE tenant_id=? AND project_id=? AND remote_id=?',
                           (source_id, body_hash, revision_json, now, tenant_id, project_id, remote_id))
            payload = {'note_id': note_id, 'source_id': source_id, 'source_version': version,
                       'remote_id': remote_id, 'body_hash': body_hash, 'actor_verified': actor_verified}
            self._event(db, tenant_id, project_id, actor_id, 'workspace.note_imported', payload)
            self._audit(db, tenant_id, project_id, 'workspace.note_imported', actor_id, note_id, payload)
            return dict(db.execute('SELECT * FROM notes WHERE tenant_id=? AND id=?', (tenant_id, note_id)).fetchone())

    def correct_candidate(self, tenant_id, candidate_id, value, reason, actor_id='demo', expected_revision=None):
        """An authenticated human assertion gets its own source, never a false mail quote."""
        require_text(value, 'corrected_value', maximum=10000)
        require_text(reason, 'reason', maximum=2000)
        with self._transaction() as db:
            original = self._candidate(db, tenant_id, candidate_id)
            project = self._one(db, 'projects', tenant_id, original['project_id'])
            if expected_revision is not None and project['revision'] != expected_revision:
                raise DomainError('stale_revision', 'Le chantier a changé ; relire avant de corriger.')
            if original['status'] not in ('pending', 'accepted'):
                raise DomainError('invalid_state', 'Cette proposition a déjà fait l’objet d’une décision.')
            kind = original['kind']
            raw_value = value
            if kind == 'money':
                raw_value = {**original['value'], 'amount': value}
            elif kind not in ('text', 'status', 'date'):
                raise DomainError('invalid_input', 'Ce type exige une correction structurée dédiée.')
            corrected_value = normalize_value(kind, raw_value)
            project_id = original['project_id']
            key = payload_hash([original['field'], kind, corrected_value])
            now, new_id = utc_now(), str(uuid4())
            rendered = canonical_json(corrected_value) if isinstance(corrected_value, dict) else str(corrected_value)
            quote = f"{original['field']} : {rendered}"
            note_content = f"Correction humaine — {quote}\nMotif : {reason}\nProposition initiale : {candidate_id}."
            note = self._insert_note(db, tenant_id, project_id, note_content, actor_id, 'human_assertion')
            superseded = []
            active = db.execute("SELECT id,kind,value FROM candidates WHERE tenant_id=? AND project_id=? AND field=? AND status='accepted'",
                                (tenant_id, project_id, original['field'])).fetchall()
            for fact in active:
                if kind == 'money' and fact['kind'] == 'money' and corrected_value['basis'] != json.loads(fact['value'])['basis']:
                    continue
                db.execute("UPDATE candidates SET status='superseded',dedup_key=dedup_key||':superseded:'||id WHERE tenant_id=? AND id=?",
                           (tenant_id, fact['id']))
                superseded.append(fact['id'])
            if original['status'] == 'pending':
                db.execute("UPDATE candidates SET status='rejected',reviewed_by=?,reviewed_at=? WHERE tenant_id=? AND id=?",
                           (actor_id, now, tenant_id, candidate_id))
            # The human may explicitly correct to a value previously rejected or
            # already proposed; retain that history while releasing its active key.
            db.execute("UPDATE candidates SET dedup_key=dedup_key||':historical:'||id,"
                       "status=CASE WHEN status='pending' THEN 'superseded' ELSE status END "
                       'WHERE tenant_id=? AND project_id=? AND dedup_key=?', (tenant_id, project_id, key))
            db.execute('INSERT INTO candidates(id,tenant_id,project_id,source_id,field,kind,value,dedup_key,origin,status,reviewed_by,reviewed_at,created_at) '
                       'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (new_id, tenant_id, project_id, note['source_id'], original['field'], kind,
                       canonical_json(corrected_value), key, 'human_assertion', 'accepted', actor_id, now, now))
            source = self._source(db, tenant_id, note['source_id'])
            span = evidence_span(source, quote)
            db.execute('INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?)', (str(uuid4()), tenant_id, new_id,
                       note['source_id'], span['source_hash'], span['start'], span['end'], span['quote']))
            payload = {'original_candidate_id': candidate_id, 'corrected_candidate_id': new_id,
                       'source_id': note['source_id'], 'reason': reason, 'supersedes': superseded}
            self._event(db, tenant_id, project_id, actor_id, 'candidate.corrected', payload)
            self._audit(db, tenant_id, project_id, 'candidate.corrected', actor_id, new_id, payload)
            return self._candidate(db, tenant_id, new_id)

    def _memory(self, db, tenant, project_id):
        project = self._project(db, tenant, project_id)
        candidates = [self._candidate(db, tenant, r[0]) for r in db.execute('SELECT id FROM candidates WHERE tenant_id=? AND project_id=? ORDER BY created_at',
                                                                       (tenant, project_id)).fetchall()]
        notes = [dict(r) for r in db.execute('SELECT * FROM notes WHERE tenant_id=? AND project_id=? ORDER BY created_at', (tenant, project_id))]
        sources = [self._source(db, tenant, r[0]) for r in db.execute('SELECT source_id FROM source_links WHERE tenant_id=? AND project_id=? ORDER BY created_at',
                                                                  (tenant, project_id)).fetchall()]
        return {'project': project, 'project_id': project_id, 'revision': project['revision'],
                'facts': [c for c in candidates if c['status'] == 'accepted'],
                'pending': [c for c in candidates if c['status'] == 'pending'],
                'conflicts': [c for c in candidates if c['status'] == 'pending' and c['conflict_with']],
                'notes': notes, 'sources': sources}

    def get_memory(self, tenant_id, project_id):
        with self._lock:
            return self._memory(self._db, tenant_id, project_id)

    def _citations(self, db, tenant, project_id, citations):
        if not isinstance(citations, list) or len(citations) > 500:
            raise DomainError('invalid_evidence', 'Liste bornée de citations attendue.')
        result = []
        for citation in citations:
            if not isinstance(citation, dict) or not citation.get('source_id'):
                raise DomainError('invalid_evidence', 'Une citation exige une source et un passage exact.')
            source = self._source(db, tenant, citation['source_id'])
            if project_id not in source['project_ids']:
                raise DomainError('invalid_evidence', 'Source hors du chantier du récapitulatif.')
            span = evidence_span(source, citation.get('quote', ''), citation.get('start'), citation.get('end'), citation.get('source_hash'))
            span['origin'] = 'human' if source['metadata'].get('note_id') else 'mail'
            result.append(span)
        return result

    @staticmethod
    def _render(memory):
        lines = [f"# {memory['project']['name']}", f"Référence : {memory['project']['reference']}", '', '## État confirmé']
        citations = []
        if not memory['facts']:
            lines.append('Aucun fait confirmé à ce stade.')
        for fact in memory['facts']:
            value = fact['value']
            if isinstance(value, dict) and 'amount' in value:
                label = f"{value['amount']} {value['currency']} {value['basis']}"
            else:
                label = str(value)
            lines.append(f"- {summary_field_label(fact['field'])} : {label}")
            citations.extend(fact['evidence'])
        if memory['notes']:
            lines.extend(['', '## Notes humaines'])
            for note in memory['notes']:
                lines.append(f"- Note humaine ({note['actor_id']}) : {note['content']}")
                citations.append({'source_id': note['source_id'], 'quote': note['content']})
        if memory['pending']:
            lines.extend(['', f"## À vérifier : {len(memory['pending'])} proposition(s)"])
            if memory['conflicts']:
                lines.append(f"{len(memory['conflicts'])} contradiction(s) exigent un arbitrage.")
        return '\n'.join(lines), citations

    def _summary(self, db, tenant, summary_id):
        row = self._one(db, 'summaries', tenant, summary_id)
        row['citations'] = json.loads(row['citations'])
        row['snapshot'] = json.loads(row['snapshot'])
        row['stale'] = bool(row['stale'])
        row['project_revision'] = row['snapshot_revision']
        row['native_revision'] = json.loads(row['native_revision']) if row['native_revision'] is not None else None
        row['warnings'] = json.loads(row['warnings'])
        row['coverage_stale'] = row['source_context_hash'] != self._source_context_hash(db, tenant, row['project_id'])
        row['stale'] = row['stale'] or row['coverage_stale']
        if not row['source_context_hash']:
            row['warnings'].append('Ancienne version : couverture des sources non enregistrée.')
            row['coverage'] = 'partial'
        return row

    @staticmethod
    def _source_context_hash(db, tenant, project_id):
        sources = [dict(r) for r in db.execute('SELECT s.id,s.body_hash,s.status,s.metadata FROM sources s JOIN source_links l '
            'ON l.tenant_id=s.tenant_id AND l.source_id=s.id WHERE l.tenant_id=? AND l.project_id=? ORDER BY s.id',
            (tenant, project_id))]
        candidates = [dict(r) for r in db.execute('SELECT id,status FROM candidates WHERE tenant_id=? AND project_id=? ORDER BY id',
                                                 (tenant, project_id))]
        return payload_hash({'sources': sources, 'candidates': candidates})

    @staticmethod
    def _coverage(memory):
        warnings = []
        if not memory['sources']:
            warnings.append('Aucune source rattachée à ce chantier.')
        for source in memory['sources']:
            if source['status'] not in ('extracted', 'manual'):
                warnings.append(f"Source non entièrement analysée : {source['subject']}.")
            metadata = source['metadata']
            for attachment in metadata.get('attachments', []):
                if not isinstance(attachment, dict):
                    warnings.append('Pièce jointe dont la couverture est inconnue.')
                elif attachment.get('status') not in ('extracted', 'covered'):
                    warnings.append(f"Pièce non couverte : {attachment.get('filename', 'sans nom')} ({attachment.get('status', 'unknown')}).")
            for warning in metadata.get('warnings', []):
                warnings.append(f"Avertissement source : {warning}.")
        if memory['pending']:
            warnings.append(f"{len(memory['pending'])} proposition(s) restent à confirmer.")
        warnings = list(dict.fromkeys(warnings))
        return ('partial' if warnings else 'complete'), warnings

    def _audit(self, db, tenant, project_id, action, actor_id, object_id, payload):
        db.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)',
                   (str(uuid4()), tenant, project_id, action, actor_id, object_id, canonical_json(payload), utc_now()))

    def _save_summary(self, db, tenant, project_id, memory, content, citations, actor_id, model, parent=None, snapshot=None, native_revision=None):
        require_text(content, 'content', maximum=500000)
        citations = self._citations(db, tenant, project_id, citations)
        version = db.execute('SELECT coalesce(max(version),0)+1 FROM summaries WHERE tenant_id=? AND project_id=?', (tenant, project_id)).fetchone()[0]
        coverage, warnings = self._coverage(memory)
        context_hash = self._source_context_hash(db, tenant, project_id)
        snapshot = snapshot or {'project_id': project_id, 'revision': memory['revision'],
                    'facts': memory['facts'], 'notes': memory['notes'],
                    'pending_ids': [c['id'] for c in memory['pending']],
                    'source_versions': [{'id': s['id'], 'body_hash': s['body_hash']} for s in memory['sources']],
                    'source_context_hash': context_hash, 'coverage': coverage, 'warnings': warnings}
        context_hash = snapshot.get('source_context_hash', context_hash)
        coverage, warnings = snapshot.get('coverage', coverage), snapshot.get('warnings', warnings)
        summary_id = str(uuid4())
        db.execute('INSERT INTO summaries(id,tenant_id,project_id,version,snapshot_revision,snapshot,snapshot_hash,content,content_hash,citations,model,created_by,created_at,parent_summary_id,native_revision,coverage,warnings,source_context_hash) '
                   'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (summary_id, tenant, project_id, version, snapshot['revision'], canonical_json(snapshot),
                   payload_hash(snapshot), content, content_hash(content), canonical_json(citations), model, actor_id, utc_now(), parent,
                   canonical_json(native_revision) if native_revision is not None else None, coverage, canonical_json(warnings), context_hash))
        self._audit(db, tenant, project_id, 'summary.created', actor_id, summary_id,
                    {'version': version, 'content_hash': content_hash(content), 'snapshot_hash': payload_hash(snapshot), 'parent_summary_id': parent})
        return self._summary(db, tenant, summary_id)

    def create_summary(self, tenant_id, project_id, content=None, citations=None, actor_id='demo', model='deterministic-local'):
        with self._transaction() as db:
            memory = self._memory(db, tenant_id, project_id)
            if content is None:
                content, default_citations = self._render(memory)
                citations = default_citations if citations is None else citations
            return self._save_summary(db, tenant_id, project_id, memory, content, citations or [], actor_id, model)

    def edit_summary(self, tenant_id, summary_id, content, *, expected_content_hash, citations=None, actor_id='demo', native_revision=None):
        with self._transaction() as db:
            original = self._summary(db, tenant_id, summary_id)
            if original['status'] not in ('draft', 'needs_review') or original['stale']:
                raise DomainError('invalid_state', 'Seul un brouillon courant peut être corrigé.')
            if original['content_hash'] != expected_content_hash:
                raise DomainError('content_mismatch', 'Le texte a changé ; relire la version actuelle.')
            memory = self._memory(db, tenant_id, original['project_id'])
            result = self._save_summary(db, tenant_id, original['project_id'], memory, content,
                original['citations'] if citations is None else citations, actor_id, 'human-edited', summary_id,
                original['snapshot'], native_revision)
            db.execute("UPDATE summaries SET status='superseded' WHERE tenant_id=? AND id=?", (tenant_id, summary_id))
            return result

    def approve_summary(self, tenant_id, summary_id, *, expected_content_hash, expected_snapshot_hash,
                        expected_project_revision, actor_id='demo', expected_remote_revision=None):
        with self._transaction() as db:
            summary = self._summary(db, tenant_id, summary_id)
            project = self._one(db, 'projects', tenant_id, summary['project_id'])
            if summary['content_hash'] != expected_content_hash:
                raise DomainError('content_mismatch', 'Le contenu à approuver ne correspond pas au texte relu.')
            if summary['snapshot_hash'] != expected_snapshot_hash:
                raise DomainError('snapshot_mismatch', 'La mémoire du récapitulatif ne correspond pas.')
            if summary['native_revision'] != expected_remote_revision:
                raise DomainError('remote_revision_mismatch', 'La révision native observée ne correspond pas au texte importé.')
            if summary['snapshot_revision'] != expected_project_revision or project['revision'] != expected_project_revision:
                raise DomainError('stale_revision', 'La mémoire a changé ; préparer ou relire un nouveau récapitulatif.')
            if summary['coverage_stale']:
                raise DomainError('stale_source_context', 'De nouvelles sources ou propositions sont arrivées ; préparer un nouveau récapitulatif.')
            if summary['stale']:
                raise DomainError('stale_revision', 'La mémoire a changé ; préparer ou relire un nouveau récapitulatif.')
            if summary['status'] == 'approved':
                return summary
            if summary['status'] not in ('draft', 'needs_review'):
                raise DomainError('invalid_state', 'Cette version ne peut pas être validée.')
            self._citations(db, tenant_id, summary['project_id'], summary['citations'])
            db.execute("UPDATE summaries SET status='approved',approved_by=?,approved_at=? WHERE tenant_id=? AND id=?",
                       (actor_id, utc_now(), tenant_id, summary_id))
            self._audit(db, tenant_id, summary['project_id'], 'summary.approved', actor_id, summary_id,
                        {'version': summary['version'], 'content_hash': summary['content_hash'], 'snapshot_hash': summary['snapshot_hash']})
            return self._summary(db, tenant_id, summary_id)

    def cancel_summary(self, tenant_id, summary_id, *, reason, actor_id='demo'):
        require_text(reason, 'reason', maximum=10000)
        with self._transaction() as db:
            summary = self._summary(db, tenant_id, summary_id)
            if summary['status'] == 'cancelled':
                return summary
            db.execute("UPDATE summaries SET status='cancelled',cancelled_by=?,cancelled_at=?,cancellation_reason=? WHERE tenant_id=? AND id=?",
                       (actor_id, utc_now(), reason, tenant_id, summary_id))
            self._audit(db, tenant_id, summary['project_id'], 'summary.cancelled', actor_id, summary_id,
                        {'reason': reason, 'content_hash': summary['content_hash']})
            return self._summary(db, tenant_id, summary_id)

    def get_summary(self, tenant_id, summary_id):
        with self._lock:
            return self._summary(self._db, tenant_id, summary_id)

    def list_summaries(self, tenant_id, project_id=None):
        with self._lock:
            params = [tenant_id]
            sql = 'SELECT id FROM summaries WHERE tenant_id=?'
            if project_id is not None:
                self._one(self._db, 'projects', tenant_id, project_id)
                sql += ' AND project_id=?'
                params.append(project_id)
            return [self._summary(self._db, tenant_id, r[0]) for r in self._db.execute(sql + ' ORDER BY created_at DESC', params).fetchall()]

    def list_events(self, tenant_id, project_id):
        with self._lock:
            self._one(self._db, 'projects', tenant_id, project_id)
            events = [dict(r) for r in self._db.execute('SELECT * FROM events WHERE tenant_id=? AND project_id=? ORDER BY revision', (tenant_id, project_id))]
            for event in events:
                event['payload'] = json.loads(event['payload'])
            return events

    def list_audit(self, tenant_id, project_id):
        with self._lock:
            self._one(self._db, 'projects', tenant_id, project_id)
            rows = [dict(r) for r in self._db.execute('SELECT * FROM audit_events WHERE tenant_id=? AND project_id=? ORDER BY created_at',
                                                     (tenant_id, project_id))]
            for row in rows:
                row['payload'] = json.loads(row['payload'])
            return rows
