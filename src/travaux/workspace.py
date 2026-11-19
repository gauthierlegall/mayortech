"""Native AFFiNE documents: versioned state and human context in one transaction."""
import base64
import binascii
import hashlib
from uuid import uuid4

from .domain import DomainError, require_text, utc_now


SCHEMA = """
CREATE TABLE IF NOT EXISTS native_pages (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL,
 kind TEXT NOT NULL DEFAULT 'main', title TEXT NOT NULL, state BLOB,
 text TEXT NOT NULL DEFAULT '', revision_hash TEXT, revision INTEGER NOT NULL DEFAULT 0,
 editor_version TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,project_id) REFERENCES projects(tenant_id,id));
CREATE UNIQUE INDEX IF NOT EXISTS idx_native_main ON native_pages(tenant_id,project_id) WHERE kind='main';
CREATE TABLE IF NOT EXISTS native_page_versions (
 tenant_id TEXT NOT NULL,page_id TEXT NOT NULL,revision INTEGER NOT NULL,
 state BLOB NOT NULL,text TEXT NOT NULL,revision_hash TEXT NOT NULL,
 editor_version TEXT NOT NULL,actor_id TEXT NOT NULL,created_at TEXT NOT NULL,
 PRIMARY KEY(tenant_id,page_id,revision),
 FOREIGN KEY(tenant_id,page_id) REFERENCES native_pages(tenant_id,id));
"""


class WorkspaceRepository:
    def __init__(self, repository):
        self.repo = repository
        with self.repo._lock:
            self.repo._db.executescript(SCHEMA)

    @staticmethod
    def _page(db, tenant, page_id):
        row = db.execute("SELECT * FROM native_pages WHERE tenant_id=? AND id=?", (tenant, page_id)).fetchone()
        if row is None:
            raise DomainError("not_found", "Page introuvable dans cet espace.")
        result = dict(row)
        state = result.pop("state")
        result["state_base64"] = base64.b64encode(state).decode() if state is not None else None
        return result

    def ensure_main(self, tenant, project_id):
        with self.repo._transaction() as db:
            project = self.repo._one(db, "projects", tenant, project_id)
            existing = db.execute("SELECT id FROM native_pages WHERE tenant_id=? AND project_id=? AND kind='main'", (tenant, project_id)).fetchone()
            if existing:
                return self._page(db, tenant, existing["id"])
            page_id, now = str(uuid4()), utc_now()
            db.execute("INSERT INTO native_pages(id,tenant_id,project_id,title,created_at,updated_at) VALUES(?,?,?,?,?,?)", (page_id, tenant, project_id, project["name"], now, now))
            return self._page(db, tenant, page_id)

    def get(self, tenant, page_id):
        with self.repo._lock:
            return self._page(self.repo._db, tenant, page_id)

    def list(self, tenant, project_id=None):
        with self.repo._lock:
            if project_id:
                self.repo._one(self.repo._db, "projects", tenant, project_id)
            query = "SELECT id FROM native_pages WHERE tenant_id=?" + (" AND project_id=?" if project_id else "") + " ORDER BY updated_at DESC"
            args = (tenant, project_id) if project_id else (tenant,)
            return [self._page(self.repo._db, tenant, r["id"]) for r in self.repo._db.execute(query, args)]

    def save(self, tenant, page_id, state_base64, expected_revision_hash, text, editor_version, actor_id):
        require_text(text, "text", maximum=100000, empty=True)
        if editor_version != "blocksuite-0.22.4":
            raise DomainError("invalid_input", "Version d'éditeur non prise en charge.")
        try:
            if not isinstance(state_base64, str) or len(state_base64) > 2_800_000:
                raise ValueError()
            state = base64.b64decode(state_base64, validate=True)
            if not state or len(state) > 2_000_000:
                raise ValueError()
        except (ValueError, binascii.Error):
            raise DomainError("invalid_input", "État de page invalide ou trop volumineux.") from None
        fingerprint = hashlib.sha256(state + b"\x00" + text.encode() + b"\x00" + editor_version.encode()).hexdigest()
        with self.repo._transaction() as db:
            page = self._page(db, tenant, page_id)
            if page["revision_hash"] == fingerprint:
                return page
            if page["revision_hash"] != expected_revision_hash:
                raise DomainError("stale_revision", "Une autre version de cette page a été enregistrée. Conservez votre texte et rechargez-la avant de remplacer son contenu.")
            revision, now = page["revision"] + 1, utc_now()
            db.execute("INSERT INTO native_page_versions VALUES(?,?,?,?,?,?,?,?,?)", (tenant, page_id, revision, state, text, fingerprint, editor_version, actor_id, now))
            db.execute("UPDATE native_pages SET state=?,text=?,revision_hash=?,revision=?,editor_version=?,updated_at=? WHERE tenant_id=? AND id=?", (state, text, fingerprint, revision, editor_version, now, tenant, page_id))
            self.repo.ingest_workspace_note(tenant, page["project_id"], "affine:" + page_id, text.strip() or "(Page de chantier vide : aucun contenu saisi.)", remote_revision=fingerprint, actor_id=actor_id, origin="manual_affine", actor_verified=True)
            return self._page(db, tenant, page_id)

    def history(self, tenant, page_id):
        with self.repo._lock:
            self._page(self.repo._db, tenant, page_id)
            return [dict(r) for r in self.repo._db.execute("SELECT revision,revision_hash,editor_version,actor_id,created_at FROM native_page_versions WHERE tenant_id=? AND page_id=? ORDER BY revision DESC", (tenant, page_id))]
