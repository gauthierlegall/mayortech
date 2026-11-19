"""Session opaque révocable, hachage scrypt, aucune identité depuis le navigateur."""
import hashlib
from contextlib import contextmanager
import hmac
import secrets
import sqlite3
import time
from pathlib import Path


def hash_password(password: str) -> str:
    if len(password) < 16:
        raise ValueError("Utiliser une phrase de passe d'au moins 16 caractères")
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, expected = encoded.split("$")
        if algorithm != "scrypt" or len(password) > 1024:
            return False
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class SessionStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (digest TEXT PRIMARY KEY,actor_id TEXT NOT NULL,tenant_id TEXT NOT NULL,expires REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS attempts (client TEXT PRIMARY KEY,count INTEGER NOT NULL,reset REAL NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def issue(self, actor_id: str, tenant_id: str, ttl=8 * 3600):
        token = secrets.token_urlsafe(48)
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (self.digest(token), actor_id, tenant_id, time.time() + ttl))
        return token

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def resolve(self, token):
        if not token or len(token) > 256:
            return None
        with self.connect() as db:
            row = db.execute("SELECT actor_id,tenant_id FROM sessions WHERE digest=? AND expires>?", (self.digest(token), time.time())).fetchone()
        return dict(row) if row else None

    def revoke(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE digest=?", (self.digest(token),))

    def revoke_actor(self, actor_id, tenant_id):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE actor_id=? AND tenant_id=?", (actor_id, tenant_id))

    def allow_attempt(self, client):
        # Persistent, serialized limit. Proxy must not forward an arbitrary client IP.
        now = time.time()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT count,reset FROM attempts WHERE client=?", (client,)).fetchone()
            count, reset = (row["count"], row["reset"]) if row and row["reset"] > now else (0, now + 300)
            if count >= 10:
                return False
            db.execute("INSERT INTO attempts VALUES(?,?,?) ON CONFLICT(client) DO UPDATE SET count=excluded.count,reset=excluded.reset", (client, count + 1, reset))
        return True
