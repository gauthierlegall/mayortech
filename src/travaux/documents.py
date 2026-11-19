"""Extraction bornée, sans réseau ni rendu actif. Aucun OCR implicite."""
from html.parser import HTMLParser
import io
import json
import os
from pathlib import PurePath
import subprocess
import sys
import hashlib
import re
import unicodedata
from urllib.parse import quote
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

from .domain import DomainError, require_text, utc_now
from .project_access import access_scope


DOCUMENT_SCHEMA = """CREATE TABLE IF NOT EXISTS original_documents (
 id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, source_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('email','attachment')),
 original_filename TEXT NOT NULL, filename TEXT NOT NULL, media_type TEXT NOT NULL,
 sha256 TEXT NOT NULL, size INTEGER NOT NULL, content BLOB NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(tenant_id,source_id,sha256), UNIQUE(tenant_id,id),
 FOREIGN KEY(tenant_id,source_id) REFERENCES sources(tenant_id,id))"""


def safe_download_filename(filename: str) -> str:
    """Display/download leaf only; the declared original stays separate metadata."""
    leaf = filename.replace("\\", "/").split("/")[-1]
    leaf = "".join(c for c in leaf if c.isprintable() and c not in '\x00:\"')
    leaf = leaf.strip().strip(".")[:200]
    return leaf if leaf not in {"", ".", ".."} else "document"


class DocumentRepository:
    """Bounded immutable original bytes in the pilot's existing SQLite transaction.

    No inference of a document's legal/version relationship from its filename.
    Text sources created before this table remain explicitly unavailable originals.
    """

    def __init__(self, repository):
        self.repo = repository
        with self.repo._lock:
            # execute, not executescript: do not implicitly commit an outer UoW.
            self.repo._db.execute(DOCUMENT_SCHEMA)

    @staticmethod
    def _text_info(source, kind):
        metadata = source["metadata"]
        status = metadata.get("extraction_status", "extracted" if source["body"].strip() else "empty")
        available = bool(source["body"].strip()) and status in {"extracted", "partial"}
        if kind == "email" and source["body"].startswith("(Message sans texte exploitable)"):
            available = False
        return status, available

    def _public(self, row, source):
        result = {key: row[key] for key in (
            "id", "source_id", "kind", "original_filename", "filename", "media_type", "sha256", "size", "created_at")}
        status, text_available = self._text_info(source, row["kind"])
        return {**result, "available": True, "download_url": f"/api/v1/documents/{row['id']}/download",
                "parent_source_id": source["metadata"].get("parent_source_id"),
                "project_ids": source["project_ids"], "extraction_status": status,
                "text_available": text_available, "preview_source_id": source["id"] if text_available else None,
                "warnings": source["metadata"].get("warnings", [])}

    def store(self, tenant_id, source_id, content: bytes, filename: str, media_type: str, *, kind="attachment"):
        require_text(filename, "filename", maximum=1000)
        if not isinstance(content, bytes) or len(content) > 10_000_000 or kind not in {"email", "attachment"}:
            raise DomainError("invalid_input", "Original invalide ou trop volumineux.")
        if not isinstance(media_type, str) or not re.fullmatch(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+", media_type):
            media_type = "application/octet-stream"
        digest = hashlib.sha256(content).hexdigest()
        with self.repo._transaction() as db:
            source = self.repo.get_source(tenant_id, source_id)
            recorded_hash = source["metadata"].get("raw_sha256")
            if recorded_hash and recorded_hash != digest:
                raise DomainError("invalid_evidence", "Ces octets ne correspondent pas à l'empreinte originale de la source.")
            row = db.execute("SELECT * FROM original_documents WHERE tenant_id=? AND source_id=? AND sha256=?",
                             (tenant_id, source_id, digest)).fetchone()
            if row is None:
                doc_id = str(uuid4())
                db.execute("INSERT INTO original_documents VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (doc_id, tenant_id, source_id, kind, filename, safe_download_filename(filename),
                            media_type.lower(), digest, len(content), content, utc_now()))
                row = db.execute("SELECT * FROM original_documents WHERE tenant_id=? AND id=?", (tenant_id, doc_id)).fetchone()
                for project_id in source["project_ids"]:
                    self.repo._audit(db, tenant_id, project_id, "document.stored", "import-worker", doc_id,
                                     {"source_id": source_id, "sha256": digest, "size": len(content), "kind": kind})
            return self._public(row, source)

    def get(self, tenant_id, document_id, *, actor=None):
        return self.download(tenant_id, document_id, actor=actor)[0]

    def download(self, tenant_id, document_id, *, actor=None):
        scope = access_scope(self.repo, actor)
        scope.require_object('document', document_id)
        with self.repo._lock:
            row = self.repo._db.execute("SELECT * FROM original_documents WHERE tenant_id=? AND id=?", (tenant_id, document_id)).fetchone()
            if row is None:
                raise DomainError("not_found", "Document introuvable dans le périmètre autorisé.")
            source = self.repo.get_source(tenant_id, row["source_id"])
            content = bytes(row["content"])
            if len(content) != row["size"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise DomainError("invalid_state", "L'intégrité de cet original ne peut pas être vérifiée. Contactez l'exploitant.")
            return self._public(row, source), content

    def list_project(self, tenant_id, project_id, *, actor=None):
        scope = access_scope(self.repo, actor)
        scope.require_project(project_id)
        self.repo.get_project(tenant_id, project_id)
        with self.repo._lock:
            clause, args = scope.source_clause('s.id')
            ids = self.repo._db.execute('SELECT s.id FROM sources s JOIN source_links l ON l.tenant_id=s.tenant_id AND l.source_id=s.id WHERE l.tenant_id=? AND l.project_id=? AND '+clause, [tenant_id, project_id, *args]).fetchall()
            sources = [scope.sanitize_source(self.repo.get_source(tenant_id, row[0])) for row in ids]
            sources = [s for s in sources if not s["metadata"].get("note_id")]
            children = [s for s in sources if s["metadata"].get("parent_source_id")]
            result = []
            for source in sources:
                rows = self.repo._db.execute("SELECT id,source_id,kind,original_filename,filename,media_type,sha256,size,created_at FROM original_documents WHERE tenant_id=? AND source_id=? ORDER BY created_at,id",
                                            (tenant_id, source["id"])).fetchall()
                metadata = source["metadata"]
                kind = "attachment" if metadata.get("parent_source_id") else "email"
                status, text_available = self._text_info(source, kind)
                filename = metadata.get("filename") or f"courrier-{source['id']}.eml"
                if rows:
                    result.extend(self._public(row, source) for row in rows)
                else:
                    filename = filename if isinstance(filename, str) else "Document"
                    result.append({"id": None, "source_id": source["id"], "parent_source_id": metadata.get("parent_source_id"),
                                   "kind": kind, "original_filename": filename, "filename": safe_download_filename(filename),
                                   "media_type": "message/rfc822" if kind == "email" else "application/octet-stream",
                                   "sha256": metadata.get("raw_sha256"), "size": None, "created_at": source["created_at"],
                                   "available": False, "download_url": None, "project_ids": source["project_ids"],
                                   "text_available": text_available, "preview_source_id": source["id"] if text_available else None,
                                   "extraction_status": status, "warnings": ["Original non conservé lors de cet ancien import."]})
                # Old opaque parts had a descriptor but no child text source.
                # Show unavailability; never manufacture a download from text.
                if kind == "email":
                    descriptors = metadata.get("attachments", [])
                    for descriptor in descriptors if isinstance(descriptors, list) else []:
                        if not isinstance(descriptor, dict):
                            continue
                        matching_child = any(child["metadata"].get("parent_source_id") == source["id"]
                                             and child["metadata"].get("filename") == descriptor.get("filename")
                                             and (not descriptor.get("sha256") or not child["metadata"].get("raw_sha256")
                                                  or child["metadata"].get("raw_sha256") == descriptor["sha256"])
                                             for child in children)
                        if matching_child:
                            continue
                        filename = descriptor.get("filename") or "Pièce jointe"
                        filename = filename if isinstance(filename, str) else "Pièce jointe"
                        result.append({"id": None, "source_id": source["id"], "parent_source_id": source["id"],
                                       "kind": "attachment", "original_filename": filename, "filename": safe_download_filename(filename),
                                       "media_type": "application/octet-stream", "sha256": descriptor.get("sha256"), "size": None,
                                       "created_at": source["created_at"], "available": False, "download_url": None,
                                       "project_ids": source["project_ids"], "text_available": False, "preview_source_id": None,
                                       "extraction_status": descriptor.get("status", "unknown"),
                                       "warnings": ["Original non conservé lors de cet ancien import."]})
            return result


def register_document_routes(app, repo, tenant, actor):
    from fastapi import Depends
    from fastapi.responses import Response
    documents = DocumentRepository(repo)

    @app.get("/api/v1/projects/{project_id}/documents")
    def project_documents(project_id: str, current=Depends(actor)):
        items = documents.list_project(tenant, project_id, actor=current)
        return {"items": items, "total": len(items)}

    @app.get("/api/v1/documents/{document_id}/download")
    def download_document(document_id: str, current=Depends(actor)):
        metadata, content = documents.download(tenant, document_id, actor=current)
        ascii_name = unicodedata.normalize("NFKD", metadata["filename"]).encode("ascii", "ignore").decode()
        ascii_name = safe_download_filename(ascii_name)
        disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(metadata["filename"], safe="")}'
        return Response(content, media_type="application/octet-stream", headers={
            "Content-Disposition": disposition, "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
            "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'none'",
        })

    @app.get("/api/v1/documents/{document_id}/preview")
    def preview_document(document_id: str, current=Depends(actor)):
        metadata, content = documents.download(tenant, document_id, actor=current)
        if metadata["media_type"] != "application/pdf" or not content.startswith(b"%PDF-"):
            raise DomainError("invalid_input", "L’aperçu intégré est disponible pour les fichiers PDF. Téléchargez cet original pour le consulter.")
        return Response(content, media_type="application/pdf", headers={
            "Content-Disposition": "inline", "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
            "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'self'",
        })

    return documents


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object"}:
            self.hidden += 1
        if tag in {"p", "br", "div", "li", "tr"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def extract_document(filename: str, data: bytes):
    if PurePath(filename).suffix.lower() not in {".pdf", ".docx"} or len(data) > 5_000_000:
        return _extract_document(filename, data)
    # Parse complex binaries in a disposable process with no application secrets
    # in its environment. Linux deployment additionally enforces memory/CPU limits.
    import base64
    environment = {key: os.environ[key] for key in ("SystemRoot", "TEMP", "TMP") if key in os.environ}
    environment.update(PYTHONUTF8="1", PYTHONNOUSERSITE="1")
    payload = json.dumps({"filename": PurePath(filename).name, "data": base64.b64encode(data).decode()})
    try:
        process = subprocess.run([sys.executable, "-m", "travaux.document_worker"], input=payload, capture_output=True, text=True, encoding="utf-8", timeout=10, env=environment, check=False)
        if process.returncode != 0 or len(process.stdout) > 500_000:
            raise ValueError("document_worker_failed")
        result = json.loads(process.stdout)
        if not isinstance(result, dict) or len(result.get("text", "")) > 60000:
            raise ValueError("document_worker_invalid")
        return result
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return {"filename": PurePath(filename).name, "status": "failed", "text": "", "pages": [], "warnings": ["Extraction interrompue par la limite de ressources : revue manuelle requise."]}


def _extract_document(filename: str, data: bytes):
    result = {"filename": PurePath(filename).name[:180], "status": "unsupported", "text": "", "pages": [], "warnings": []}
    if len(data) > 5_000_000:
        return {**result, "status": "too_large", "warnings": ["Pièce supérieure à 5 Mo : revue manuelle requise."]}
    ext = PurePath(filename).suffix.lower()
    try:
        if ext in {".txt", ".csv", ".md", ".html", ".htm"}:
            text = data.decode("utf-8", errors="replace")
            if ext in {".html", ".htm"}:
                parser = PlainHTML()
                parser.feed(text)
                text = "".join(parser.parts)
            result.update(status="extracted", text=text[:60000])
            if len(text) > 60000:
                result.update(status="partial", warnings=["Extraction limitée à 60 000 caractères; couverture partielle."])
        elif ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                return {**result, "status": "encrypted", "warnings": ["PDF chiffré : aucune tentative de déchiffrement."]}
            text_size = 0
            for index, page in enumerate(reader.pages[:30]):
                text = page.extract_text() or ""
                text_size += len(text)
                if text_size > 60000:
                    break
                result["pages"].append({"page": index + 1, "text": text})
            result["text"] = "\n".join(p["text"] for p in result["pages"])
            result["status"] = "extracted" if result["text"].strip() else "ocr_required"
            if len(reader.pages) > len(result["pages"]):
                result.update(status="partial", warnings=["PDF limité à 30 pages / 60 000 caractères."])
        elif ext == ".docx":
            with ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 20_000_000:
                    return {**result, "status": "too_large", "warnings": ["Archive décompressée trop volumineuse."]}
            from docx import Document
            document = Document(io.BytesIO(data))
            text = "\n".join(p.text for p in document.paragraphs)
            table_text = [" | ".join(cell.text for cell in row.cells) for table in document.tables for row in table.rows]
            text += "\n" + "\n".join(table_text)
            result.update(status="extracted" if len(text) <= 60000 else "partial", text=text[:60000])
        else:
            result["warnings"] = ["Format non interprété. Le résumé doit signaler cette pièce non couverte."]
    except ImportError:
        result.update(status="dependency_missing", warnings=["Installer l'option documents pour ce format."])
    except (ValueError, OSError, BadZipFile, KeyError):
        result.update(status="failed", warnings=["Document illisible : aucune extraction utilisable."])
    return result
