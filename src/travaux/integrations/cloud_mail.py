"""Bounded, GET-only Graph/Gmail readers with durable import-before-cursor.

The cloud cursor is encrypted with the same tenant-bound vault as tokens. A
remote removal records a review event; it never deletes a local original.
"""
import base64
from dataclasses import dataclass
import hashlib
import json
import time
from urllib.parse import quote, unquote, urlencode, urlsplit

from ..domain import DomainError, canonical_json

PAGE_SIZE = 5
MAX_FOLDERS = 100
MAX_MIME = 10_000_000
MAX_PAGES_PER_RUN = 5


def _invalid():
    return DomainError("integration_unavailable", "La réponse de la messagerie est incomplète ou dépasse le périmètre autorisé.")


def _ident(value):
    if not isinstance(value, str) or not value or len(value) > 2000 or not value.isprintable():
        raise _invalid()
    return value


@dataclass(frozen=True)
class CloudChange:
    remote_id: str
    revision: str
    kind: str
    mime: bytes | None = None


@dataclass(frozen=True)
class CloudPage:
    changes: tuple[CloudChange, ...]
    cursor: dict
    has_more: bool


class CloudMailReader:
    def __init__(self, row, service):
        self.row, self.service = dict(row), service
        self.config = service._configuration(row["provider"])
        if row["endpoint"] != self.config.api_base:
            raise _invalid()
        self.base = self.config.api_base
        self.host = urlsplit(self.base).hostname
        self._deadline, self._requests = time.monotonic() + 120, 0

    def _safe_url(self, url):
        parsed = urlsplit(url)
        base_path = urlsplit(self.base).path
        expected = base_path + ("/users/me/" if self.row["provider"] == "google" else "/me/")
        decoded = unquote(parsed.path)
        if (parsed.scheme != "https" or parsed.hostname != self.host or parsed.port not in {None, 443}
                or parsed.username is not None or parsed.password is not None or parsed.fragment
                or not parsed.path.startswith(expected) or "\\" in decoded
                or any(segment in {".", ".."} for segment in decoded.split("/"))
                or len(url) > 100_000):
            raise _invalid()
        return url

    def _get(self, url, *, raw=False):
        self._safe_url(url)
        self._requests += 1
        if self._requests > 80 or time.monotonic() > self._deadline:
            raise DomainError("integration_busy", "Cette lecture atteint sa limite. Les messages et repères déjà enregistrés sont conservés.")
        token = self.service.access_token(self.row["id"])
        return self.service._request("GET", url, token=token, expected_host=self.host, max_bytes=MAX_MIME if raw else 14_000_000, raw=raw)

    def probe(self):
        if self.row["provider"] == "google":
            body = self._get(self.base + "/users/me/labels")
            values = body.get("labels", [])
            if not isinstance(values, list) or len(values) > MAX_FOLDERS:
                raise _invalid()
            folders = [{"id": _ident(item.get("id")), "name": _ident(item.get("name"))[:500]} for item in values]
        else:
            folders, visited, queue = [], set(), [(self.base + "/me/mailFolders?" + urlencode({"$top": 100, "includeHiddenFolders": "false", "$select": "id,displayName,childFolderCount"}), "", 0)]
            while queue:
                url, parent, depth = queue.pop(0)
                if depth > 8 or url in visited or len(visited) >= 100:
                    raise _invalid()
                visited.add(url)
                body = self._get(url)
                values = body.get("value")
                if not isinstance(values, list) or len(values) > MAX_FOLDERS:
                    raise _invalid()
                for item in values:
                    ident, title = _ident(item.get("id")), _ident(item.get("displayName"))
                    title = (parent + " / " + title if parent else title)[:500]
                    folders.append({"id": ident, "name": title})
                    children = item.get("childFolderCount", 0)
                    if type(children) is not int or not 0 <= children <= MAX_FOLDERS:
                        raise _invalid()
                    if children:
                        queue.append((self.base + "/me/mailFolders/" + quote(ident, safe="") + "/childFolders?" + urlencode({"$top": 100, "includeHiddenFolders": "false", "$select": "id,displayName,childFolderCount"}), title, depth + 1))
                if body.get("@odata.nextLink"):
                    queue.append((self._safe_url(_ident(body["@odata.nextLink"])), parent, depth))
                if len(folders) > MAX_FOLDERS:
                    raise _invalid()
        if len({item["id"] for item in folders}) != len(folders):
            raise _invalid()
        return {"calendars": [], "mail_folders": folders}

    def _graph_page(self, folder, cursor):
        root = self.base + "/me/mailFolders/" + quote(folder, safe="") + "/messages"
        url = cursor.get("url") if cursor else root + "/delta?" + urlencode({"$top": PAGE_SIZE, "$select": "id,changeKey"})
        # A provider nextLink stays within this exact selected folder's delta.
        if not isinstance(url, str) or urlsplit(url).path != urlsplit(root + "/delta").path:
            raise _invalid()
        body = self._get(url)
        values = body.get("value")
        if not isinstance(values, list) or len(values) > PAGE_SIZE:
            raise _invalid()
        changes = []
        for item in values:
            ident = _ident(item.get("id"))
            revision = str(item.get("changeKey", ""))[:2000]
            if "@removed" in item:
                changes.append(CloudChange(ident, revision or hashlib.sha256(url.encode()).hexdigest(), "delete"))
            else:
                try:
                    mime = self._get(root + "/" + quote(ident, safe="") + "/$value", raw=True)
                except DomainError as failure:
                    if failure.code != "mail_cursor_expired":
                        raise
                    changes.append(CloudChange(ident, revision, "unavailable"))
                else:
                    changes.append(CloudChange(ident, revision, "mail", mime))
        next_url = body.get("@odata.nextLink") or body.get("@odata.deltaLink")
        if not next_url or not isinstance(next_url, str):
            raise _invalid()
        self._safe_url(next_url)
        if urlsplit(next_url).path != urlsplit(root + "/delta").path:
            raise _invalid()
        more = bool(body.get("@odata.nextLink"))
        if more and next_url == url:
            raise _invalid()
        return CloudPage(tuple(changes), {"url": next_url}, more)

    def _gmail_mime(self, ident, folder, revision):
        try:
            value = self._get(self.base + "/users/me/messages/" + quote(ident, safe="") + "?format=raw")
        except DomainError as failure:
            if failure.code == "mail_cursor_expired":
                return CloudChange(ident, revision, "unavailable")
            raise
        if value.get("id") != ident or not isinstance(value.get("labelIds"), list):
            raise _invalid()
        if folder not in value["labelIds"]:
            return CloudChange(ident, revision, "unavailable")
        encoded = value.get("raw")
        if not isinstance(encoded, str) or len(encoded) > 13_333_340:
            raise _invalid()
        try:
            mime = base64.b64decode(encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
        except (ValueError, TypeError):
            raise _invalid() from None
        if not mime or len(mime) > MAX_MIME:
            raise _invalid()
        return CloudChange(ident, str(value.get("historyId") or revision), "mail", mime)

    def _gmail_page(self, folder, cursor):
        state = dict(cursor or {})
        if not state:
            profile = self._get(self.base + "/users/me/profile")
            state = {"phase": "bootstrap", "anchor": _ident(profile.get("historyId")), "page_token": ""}
        if state.get("phase") == "bootstrap":
            params = {"labelIds": folder, "maxResults": PAGE_SIZE, "includeSpamTrash": "false"}
            if state.get("page_token"):
                params["pageToken"] = state["page_token"]
            body = self._get(self.base + "/users/me/messages?" + urlencode(params))
            messages = body.get("messages", [])
            if not isinstance(messages, list) or len(messages) > PAGE_SIZE:
                raise _invalid()
            changes = tuple(self._gmail_mime(_ident(item.get("id")), folder, state["anchor"]) for item in messages)
            next_token = body.get("nextPageToken")
            if next_token:
                _ident(next_token)
                if next_token == state.get("page_token"):
                    raise _invalid()
                next_state = {**state, "page_token": next_token}
            else:
                next_state = {"phase": "history", "history_id": state["anchor"]}
            return CloudPage(changes, next_state, True)  # The first history pass closes the bootstrap race.
        if state.get("phase") != "history" or not isinstance(state.get("history_id"), str):
            raise _invalid()
        if state.get("pending"):
            pending = state["pending"]
            if not isinstance(pending, list) or len(pending) > 1000:
                raise _invalid()
            take, remaining = pending[:PAGE_SIZE], pending[PAGE_SIZE:]
            changes = tuple(CloudChange(_ident(item["id"]), _ident(item["revision"]), "delete") if item["kind"] == "delete" else self._gmail_mime(_ident(item["id"]), folder, _ident(item["revision"])) for item in take)
            next_state = {**state, "pending": remaining} if remaining else dict(state["after_pending"])
            return CloudPage(changes, next_state, bool(remaining) or bool(next_state.get("page_token")))
        params = {"labelId": folder, "startHistoryId": state["history_id"], "maxResults": PAGE_SIZE}
        if state.get("page_token"):
            params["pageToken"] = state["page_token"]
        body = self._get(self.base + "/users/me/history?" + urlencode(params))
        histories = body.get("history", [])
        if not isinstance(histories, list) or len(histories) > PAGE_SIZE:
            raise _invalid()
        pending = []
        for record in histories:
            revision = _ident(record.get("id"))
            for key, kind in (("messagesAdded", "mail"), ("labelsAdded", "mail"), ("messagesDeleted", "delete"), ("labelsRemoved", "delete")):
                entries = record.get(key, [])
                if not isinstance(entries, list) or len(entries) > 1000:
                    raise _invalid()
                for entry in entries:
                    if key in {"labelsAdded", "labelsRemoved"} and folder not in entry.get("labelIds", []):
                        continue
                    ident = _ident(entry.get("message", {}).get("id"))
                    pending.append({"id": ident, "revision": revision, "kind": kind})
                    if len(pending) > 1000:
                        raise _invalid()
        # One message can occur in several history changes. Reading its latest
        # MIME is safe; removals remain explicit review events.
        pending = list({(item["id"], item["revision"], item["kind"]): item for item in pending}.values())
        next_token = body.get("nextPageToken")
        if next_token:
            next_token = _ident(next_token)
            if next_token == state.get("page_token"):
                raise _invalid()
            next_state = {"phase": "history", "history_id": state["history_id"], "page_token": next_token}
        else:
            next_state = {"phase": "history", "history_id": _ident(body.get("historyId"))}
        if not pending:
            return CloudPage((), next_state, bool(next_token))
        temporary = {**state, "pending": pending, "after_pending": next_state}
        return self._gmail_page(folder, temporary)

    def _scope(self, folder):
        return hashlib.sha256(canonical_json([self.row["provider"], self.row["endpoint"], self.row["mailbox"].lower(), folder]).encode()).hexdigest()

    def _persist(self, repo, queue, tenant, folder, change):
        from ..documents import DocumentRepository
        from ..importing import import_mail
        from .mail import MailParseError
        from .exchange_backfill import find_existing_exchange_original

        metadata = {"connection_id": self.row["id"], "folder_id": folder, "remote_id": change.remote_id, "change_key": change.revision, "event_kind": change.kind, "provider": self.row["provider"]}
        if change.kind == "mail":
            if not isinstance(change.mime, bytes) or not change.mime or len(change.mime) > MAX_MIME:
                raise _invalid()
            digest = hashlib.sha256(change.mime).hexdigest()
            if find_existing_exchange_original(repo._db, tenant, self.row["id"], digest):
                return
            try:
                import_mail(repo, queue, tenant, change.mime, external_id=f"{self.row['provider']}:{self.row['id']}:{change.remote_id}", metadata=metadata)
            except MailParseError:
                source = repo.ingest_source(tenant, f"cloud-quarantine:{self.row['id']}:{digest}", "Courriel à vérifier", "Message non analysé. Consulter l’original avant toute synthèse.", metadata={**metadata, "raw_sha256": digest, "warnings": ["mail_quarantined_review_required"], "review_required": True})
                DocumentRepository(repo).store(tenant, source["id"], change.mime, "courrier.eml", "message/rfc822", kind="email")
        elif change.kind in {"delete", "unavailable"}:
            key = hashlib.sha256(canonical_json([self.row["id"], folder, change.remote_id, change.revision, change.kind]).encode()).hexdigest()
            repo.ingest_source(tenant, "cloud-event:" + key, "Événement de messagerie à vérifier", "Message retiré du dossier ou devenu indisponible sur le serveur. Cet événement n’efface aucune preuve locale.", metadata={**metadata, "warnings": ["review_required"], "review_required": True})
        else:
            raise _invalid()

    def collect_mail(self, repo, tenant, connection_id, *, guard):
        from pathlib import Path
        from ..documents import DocumentRepository
        from ..jobs import JobQueue

        if tenant != self.service.settings.tenant_id or connection_id != self.row["id"] or repo.path == ":memory:":
            raise DomainError("forbidden", "Cette lecture exige le stockage durable de votre espace.")
        folders = json.loads(self.row["selected_folders"])
        known = {item["id"] for item in json.loads(self.row["folder_choices"])}
        if not folders or len(folders) > MAX_FOLDERS or any(folder not in known for folder in folders):
            raise DomainError("forbidden", "Choisissez uniquement les dossiers vérifiés de cette connexion.")
        queue = JobQueue(Path(repo.path))
        DocumentRepository(repo)
        with repo._transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS cloud_mail_checkpoints(
                tenant_id TEXT NOT NULL,connection_id TEXT NOT NULL,folder_id TEXT NOT NULL,
                scope_hash TEXT NOT NULL,cursor_ciphertext TEXT NOT NULL,revision INTEGER NOT NULL,updated REAL NOT NULL,
                PRIMARY KEY(tenant_id,connection_id,folder_id))""")
            checkpoints = {row["folder_id"]: dict(row) for row in db.execute("SELECT * FROM cloud_mail_checkpoints WHERE tenant_id=? AND connection_id=?", (tenant, connection_id))}
        # Oldest first means large folder sets do not starve later selections.
        ordered = sorted(folders, key=lambda folder: checkpoints.get(folder, {}).get("updated", 0))
        reports = []
        for folder in ordered[:MAX_PAGES_PER_RUN]:
            guard()
            previous = checkpoints.get(folder)
            scope = self._scope(folder)
            if previous and previous["scope_hash"] != scope:
                raise DomainError("mail_cursor_expired", "Le périmètre de ce compte a changé. Vérifiez sa reprise de lecture.")
            cursor = self.service.hub.vault.decrypt(previous["cursor_ciphertext"]) if previous else None
            page = self._gmail_page(folder, cursor) if self.row["provider"] == "google" else self._graph_page(folder, cursor)
            if len(page.changes) > PAGE_SIZE or len(canonical_json(page.cursor)) > 100_000:
                raise _invalid()
            sealed = self.service.hub.vault.encrypt(page.cursor)
            expected_revision = previous["revision"] if previous else 0
            with repo._transaction() as db:
                guard()
                current = db.execute("SELECT revision FROM cloud_mail_checkpoints WHERE tenant_id=? AND connection_id=? AND folder_id=?", (tenant, connection_id, folder)).fetchone()
                if (current["revision"] if current else 0) != expected_revision:
                    raise DomainError("stale_revision", "Une autre lecture a avancé. Actualisez avant de reprendre.")
                for change in page.changes:
                    self._persist(repo, queue, tenant, folder, change)
                guard()
                db.execute("INSERT INTO cloud_mail_checkpoints VALUES(?,?,?,?,?,?,?) ON CONFLICT(tenant_id,connection_id,folder_id) DO UPDATE SET scope_hash=excluded.scope_hash,cursor_ciphertext=excluded.cursor_ciphertext,revision=excluded.revision,updated=excluded.updated", (tenant, connection_id, folder, scope, sealed, expected_revision + 1, time.time()))
            reports.append({"folder_id": folder, "accepted": len(page.changes), "has_more": page.has_more, "checkpoint_revision": expected_revision + 1})
        return {"accepted": sum(item["accepted"] for item in reports), "batches": reports, "more_available": len(ordered) > MAX_PAGES_PER_RUN or any(item["has_more"] for item in reports), "remote_write_enabled": False}

    def close(self):
        pass  # Service-created httpx clients close after every bounded request.
