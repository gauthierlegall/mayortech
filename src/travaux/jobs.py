"""File durable mono-hôte : réservation atomique, bail et jeton de clôture."""
import json
from contextlib import contextmanager
from pathlib import Path
import secrets
import sqlite3
import time
from uuid import uuid4


class JobQueue:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'queued',attempts INTEGER NOT NULL DEFAULT 0,
                lease_token TEXT,lease_until REAL,worker TEXT,result TEXT,error TEXT,created_at REAL NOT NULL,
                UNIQUE(tenant_id,kind,idempotency_key))""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(self, tenant_id, kind, payload, key):
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO jobs(id,tenant_id,kind,payload,idempotency_key,created_at) VALUES(?,?,?,?,?,?)", (str(uuid4()), tenant_id, kind, canonical, key, time.time()))
            existing = db.execute("SELECT id,payload FROM jobs WHERE tenant_id=? AND kind=? AND idempotency_key=?", (tenant_id, kind, key)).fetchone()
            if json.loads(existing["payload"]) != payload:
                raise ValueError("idempotency_payload_mismatch")
            return existing["id"]

    def claim(self, worker, lease_seconds=120):
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE status='queued' OR (status='running' AND lease_until<?) ORDER BY created_at LIMIT 1", (now,)).fetchone()
            if not row:
                return None
            token = secrets.token_hex(24)
            db.execute("UPDATE jobs SET status='running',lease_token=?,lease_until=?,worker=?,attempts=attempts+1 WHERE id=?", (token, now + lease_seconds, worker, row["id"]))
            result = dict(row)
            result.update(lease_token=token, payload=json.loads(row["payload"]))
            return result

    def complete(self, job_id, token, result):
        with self.connect() as db:
            cursor = db.execute("UPDATE jobs SET status='done',result=?,lease_token=NULL WHERE id=? AND lease_token=? AND status='running' AND lease_until>?", (json.dumps(result), job_id, token, time.time()))
            return cursor.rowcount == 1

    def fail(self, job_id, token, code):
        with self.connect() as db:
            return db.execute("UPDATE jobs SET status='failed',error=?,lease_token=NULL WHERE id=? AND lease_token=? AND status='running' AND lease_until>?", (code, job_id, token, time.time())).rowcount == 1

    def retry(self, tenant_id, job_id):
        with self.connect() as db:
            return db.execute("UPDATE jobs SET status='queued',error=NULL WHERE tenant_id=? AND id=? AND status='failed'", (tenant_id, job_id)).rowcount == 1

    def get(self, tenant_id, job_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE tenant_id=? AND id=?", (tenant_id, job_id)).fetchone()
        return self._public(row) if row else None

    def list(self, tenant_id):
        with self.connect() as db:
            return [self._public(row) for row in db.execute("SELECT * FROM jobs WHERE tenant_id=? ORDER BY created_at DESC LIMIT 100", (tenant_id,))]

    @staticmethod
    def _public(row):
        return {**{key: row[key] for key in ("id", "kind", "status", "attempts", "error", "created_at")}, "result": json.loads(row["result"]) if row["result"] else None}
