"""Human document decisions, scoped to one immutable original and one project."""

import json
import sqlite3
from uuid import uuid4

from .documents import DocumentRepository
from .domain import DomainError, evidence_span, require_text
from .storyline import MANIFEST_SHA256, STORYLINE_ID
from .project_access import access_scope

LABELS = {"approved": "Validé", "under_review": "En examen", "unknown": "Non renseigné"}


class DocumentReviewService:
    def __init__(self, repo):
        self.repo = repo
        self.documents = DocumentRepository(repo)
        with repo._lock:
            repo._db.execute("""CREATE TABLE IF NOT EXISTS document_review_decisions(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT NOT NULL UNIQUE,
                tenant_id TEXT NOT NULL,project_id TEXT NOT NULL,document_id TEXT NOT NULL,
                document_sha256 TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('approved','under_review')),
                reviewer TEXT NOT NULL,note_id TEXT NOT NULL,source_id TEXT NOT NULL,
                evidence_quote TEXT NOT NULL,reason TEXT NOT NULL,project_revision INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(tenant_id,document_id) REFERENCES original_documents(tenant_id,id))""")
            repo._db.execute(
                "CREATE INDEX IF NOT EXISTS document_review_latest ON document_review_decisions(tenant_id,project_id,document_id,sequence DESC)"
            )

    @staticmethod
    def _actor(tenant, actor, action):
        if not isinstance(actor, dict) or actor.get("tenant_id") != tenant:
            raise DomainError("forbidden", "Cette décision n’est pas autorisée dans ce périmètre.")
        if actor.get("permissions", {}).get("workspace", {}).get(action) is not True:
            raise DomainError("forbidden", "Votre accès ne permet pas cette opération sur le dossier.")
        return require_text(actor.get("actor_id"), "actor_id", maximum=1000)

    def _document(self, tenant, document_id):
        row = self.repo._db.execute(
            "SELECT id,source_id,kind,filename,sha256 FROM original_documents WHERE tenant_id=? AND id=?",
            (tenant, document_id),
        ).fetchone()
        if row is None:
            raise DomainError("not_found", "Cette pièce n’est pas disponible dans votre espace.")
        if row["kind"] != "attachment":
            raise DomainError(
                "invalid_input",
                "Seule une pièce jointe du dossier peut recevoir cette décision documentaire.",
            )
        source = self.repo.get_source(tenant, row["source_id"])
        return dict(row), source

    def _baseline(self, tenant, project_id, document, source):
        # Metadata is not an authority by itself: this baseline must be the exact
        # operator-pinned fixture ledger, bound to the original and its proofs.
        try:
            ledger = self.repo._db.execute(
                "SELECT result_json FROM demo_storylines WHERE tenant_id=? AND storyline_id=? AND manifest_sha256=?",
                (tenant, STORYLINE_ID, MANIFEST_SHA256),
            ).fetchone()
        except sqlite3.OperationalError:
            ledger = None
        if not ledger:
            return None
        result = json.loads(ledger["result_json"])
        catalog_id = result.get("catalog_source_id")
        if not catalog_id:
            return None
        try:
            catalog_source = self.repo.get_source(tenant, catalog_id)
        except DomainError:
            return None
        metadata = catalog_source["metadata"]
        rows = result.get("document_catalog", [])
        if (
            project_id not in catalog_source["project_ids"]
            or metadata.get("document_catalog") != rows
            or metadata.get("origin") != "demo_fixture_catalog"
        ):
            return None
        row = next(
            (
                item
                for item in rows
                if item.get("document_id") == document["id"]
                and item.get("source_id") == source["id"]
                and item.get("sha256") == document["sha256"]
                and item.get("mail_source_id") == source["metadata"].get("parent_source_id")
            ),
            None,
        )
        if not row or row.get("status") not in {"validated", "under_review"}:
            return None
        proofs = {}
        try:
            for name in ("status", "version", "amount"):
                declared = row["evidence"][name]
                proof_source = self.repo.get_source(tenant, declared["source_id"])
                if project_id not in proof_source["project_ids"]:
                    return None
                proofs[name] = evidence_span(proof_source, declared["quote"])
        except (DomainError, KeyError, TypeError):
            return None
        status = "approved" if row["status"] == "validated" else "under_review"
        return {
            "status": status,
            "status_label": LABELS[status],
            "origin": "fixture_catalogue",
            "source_id": proofs["status"]["source_id"],
            "reviewer": None,
            "created_at": self.repo.get_source(tenant, proofs["status"]["source_id"])["received_at"],
            "recorded_project_revision": None,
            "evidence": proofs,
        }

    def _entry(self, tenant, project_id, document, source, actor):
        project = self.repo.get_project(tenant, project_id)
        recorded = self.repo._db.execute(
            "SELECT * FROM document_review_decisions WHERE tenant_id=? AND project_id=? AND document_id=? AND document_sha256=? ORDER BY sequence DESC LIMIT 1",
            (tenant, project_id, document["id"], document["sha256"]),
        ).fetchone()
        if recorded:
            note_source = self.repo.get_source(tenant, recorded["source_id"])
            if project_id not in note_source["project_ids"]:
                raise DomainError(
                    "invalid_state", "La preuve de la décision doit être réconciliée avant lecture."
                )
            status = recorded["status"]
            state = {
                "status": status,
                "status_label": LABELS[status],
                "origin": "human_decision",
                "source_id": recorded["source_id"],
                "reviewer": recorded["reviewer"],
                "created_at": recorded["created_at"],
                "recorded_project_revision": recorded["project_revision"],
                "evidence": {"status": evidence_span(note_source, recorded["evidence_quote"])},
            }
        else:
            state = self._baseline(tenant, project_id, document, source) or {
                "status": "unknown",
                "status_label": LABELS["unknown"],
                "origin": "none",
                "source_id": None,
                "reviewer": None,
                "created_at": None,
                "recorded_project_revision": None,
                "evidence": {},
            }
        return {
            "project_id": project_id,
            "project_revision": project["revision"],
            "document_id": document["id"],
            "document_source_id": source["id"],
            "sha256": document["sha256"],
            **state,
            "can_review": actor.get("permissions", {}).get("workspace", {}).get("write") is True
            and source["project_ids"] == [project_id],
        }

    def list_project(self, tenant, project_id, *, actor):
        self._actor(tenant, actor, "read")
        access_scope(self.repo, actor).require_project(project_id)
        with self.repo._lock:
            project = self.repo.get_project(tenant, project_id)
            items = []
            for item in self.documents.list_project(tenant, project_id, actor=actor):
                if item["kind"] != "attachment" or not item["id"]:
                    continue
                document, source = self._document(tenant, item["id"])
                items.append(self._entry(tenant, project_id, document, source, actor))
            return {"project_id": project_id, "project_revision": project["revision"], "items": items}

    def decide(self, tenant, document_id, *, decision, expected_project_revision, actor, reason=""):
        reviewer = self._actor(tenant, actor, "write")
        scope = access_scope(self.repo, actor)
        scope.require_object('document', document_id, write=True)
        if decision not in {"approve", "under_review"}:
            raise DomainError("invalid_input", "Une décision Valider ou En examen est attendue.")
        if type(expected_project_revision) is not int or expected_project_revision < 0:
            raise DomainError("invalid_input", "La révision exacte du dossier relu est attendue.")
        reason = require_text(reason, "reason", maximum=2000, empty=True).strip()
        status = "approved" if decision == "approve" else "under_review"
        with self.repo._transaction() as db:
            scope.require_object('document', document_id, write=True)
            document, source = self._document(tenant, document_id)
            if len(source["project_ids"]) != 1:
                raise DomainError(
                    "conflict", "Rattachez cette pièce à un seul dossier avant de décider de son statut."
                )
            project_id = source["project_ids"][0]
            scope.require_project(project_id, write=True)
            project = self.repo.get_project(tenant, project_id)
            if project["revision"] != expected_project_revision:
                raise DomainError(
                    "stale_revision",
                    "Le dossier a changé. Relisez sa situation avant de confirmer votre décision.",
                )
            quote = (
                f"Décision enregistrée : « {LABELS[status]} » pour le document « {document['filename']} »."
            )
            body = quote + ("\nMotif : " + reason if reason else "")
            note = self.repo.add_note(tenant, project_id, body, actor_id=reviewer, origin="human")
            revision = self.repo.get_project(tenant, project_id)["revision"]
            db.execute(
                """INSERT INTO document_review_decisions(id,tenant_id,project_id,document_id,document_sha256,
                        status,reviewer,note_id,source_id,evidence_quote,reason,project_revision,created_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid4()),
                    tenant,
                    project_id,
                    document_id,
                    document["sha256"],
                    status,
                    reviewer,
                    note["id"],
                    note["source_id"],
                    quote,
                    reason,
                    revision,
                    note["created_at"],
                ),
            )
            return self._entry(tenant, project_id, document, source, actor)


def register_document_review_routes(app, repo, tenant, actor):
    from fastapi import Depends
    from pydantic import BaseModel, ConfigDict, Field

    class Decision(BaseModel):
        model_config = ConfigDict(extra="forbid")
        decision: str = Field(pattern="^(approve|under_review)$")
        expected_project_revision: int = Field(ge=0, strict=True)
        reason: str = Field(default="", max_length=2000)

    service = DocumentReviewService(repo)

    @app.get("/api/v1/projects/{project_id}/document-reviews")
    def list_reviews(project_id: str, current=Depends(actor)):
        return service.list_project(tenant, project_id, actor=current)

    @app.post("/api/v1/documents/{document_id}/decision")
    def decide(document_id: str, body: Decision, current=Depends(actor)):
        return service.decide(
            tenant,
            document_id,
            decision=body.decision,
            expected_project_revision=body.expected_project_revision,
            reason=body.reason,
            actor=current,
        )

    return service
