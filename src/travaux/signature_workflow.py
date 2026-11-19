"""A versioned approval circuit for a single immutable original PDF."""

from functools import lru_cache
from importlib.resources import files
import re
from typing import Literal

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError
from .project_access import access_scope


@lru_cache
def _spec():
    from SpiffWorkflow.bpmn.parser import BpmnParser

    parser = BpmnParser()
    parser.add_bpmn_str(files("travaux").joinpath("document_approval.bpmn").read_bytes())
    return parser.get_spec("document_approval_v1")


def _serializer():
    from SpiffWorkflow.bpmn.serializer import BpmnWorkflowSerializer

    return BpmnWorkflowSerializer()


def _ready_task(workflow, name):
    from SpiffWorkflow.task import TaskState

    return next((task for task in workflow.get_tasks(state=TaskState.READY) if task.task_spec.name == name), None)


def create_circuit(document_sha256):
    from SpiffWorkflow.bpmn.workflow import BpmnWorkflow

    if not isinstance(document_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", document_sha256):
        raise DomainError("invalid_input", "L’empreinte du PDF original est requise.")
    workflow = BpmnWorkflow(_spec())
    workflow.set_data(document_sha256=document_sha256)
    workflow.do_engine_steps()
    return _serializer().serialize_json(workflow)


def describe_circuit(snapshot):
    workflow = _serializer().deserialize_json(snapshot)
    state = "review"
    if workflow.is_completed():
        state = "rejected"
    elif _ready_task(workflow, "signature") is not None:
        state = "awaiting_signature"
    return {"status": state, "document_sha256": workflow.data["document_sha256"]}


def advance_circuit(snapshot, decision):
    serializer = _serializer()
    workflow = serializer.deserialize_json(snapshot)
    review = _ready_task(workflow, "review")
    if review is None or decision not in {"approve", "reject"}:
        raise DomainError("conflict", "Cette décision n’est pas disponible à cette étape.")
    review.set_data(approved=decision == "approve")
    review.run()
    workflow.do_engine_steps()
    return serializer.serialize_json(workflow)


class SubmitCircuit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReviewCircuit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]
    revision: int = Field(ge=1, strict=True)


def register_signature_workflow(app, repo, tenant, actor, documents):
    # Fail during opt-in startup if the dependency or packaged definition is missing.
    _spec()
    path = "/api/v1/projects/{project_id}/documents/{document_id}/signature-circuit"
    with repo._transaction() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS signature_circuits (
            tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, document_id TEXT NOT NULL,
            submitted_by TEXT NOT NULL, snapshot TEXT NOT NULL, revision INTEGER NOT NULL,
            PRIMARY KEY(tenant_id, project_id, document_id),
            FOREIGN KEY(tenant_id, project_id) REFERENCES projects(tenant_id,id),
            FOREIGN KEY(tenant_id, document_id) REFERENCES original_documents(tenant_id,id))""")

    def original(project_id, document_id, current, *, write=False):
        scope = access_scope(repo, current)
        scope.require_project_contents(project_id, write=write)
        scope.require_object("document", document_id, write=write)
        metadata, content = documents.download(tenant, document_id, actor=current)
        if project_id not in metadata["project_ids"]:
            raise DomainError("not_found", "Ce document n’appartient pas à ce dossier.")
        if metadata["media_type"] != "application/pdf" or not content.startswith(b"%PDF-"):
            raise DomainError("invalid_input", "Choisissez un PDF original pour ouvrir un circuit.")
        return metadata["sha256"]

    def get_row(db, project_id, document_id):
        return db.execute("""SELECT * FROM signature_circuits
            WHERE tenant_id=? AND project_id=? AND document_id=?""", (tenant, project_id, document_id)).fetchone()

    def present(row, digest, current, project_id):
        scope = access_scope(repo, current)
        writable = (scope.project_capabilities(project_id)["can_edit"]
                    and current["permissions"]["workspace"]["write"])
        if row is None:
            return {"status": "not_started", "document_sha256": digest, "can_submit": writable, "can_decide": False}
        state = describe_circuit(row["snapshot"])
        if state["document_sha256"] != digest:
            raise DomainError("conflict", "Le PDF ne correspond plus à celui présenté pour validation.")
        return {**state, "revision": row["revision"], "can_submit": False,
                "can_decide": writable and state["status"] == "review" and row["submitted_by"] != current["actor_id"]}

    @app.get(path)
    def read(project_id: str, document_id: str, current=Depends(actor)):
        with repo._lock:
            digest = original(project_id, document_id, current)
            return present(get_row(repo._db, project_id, document_id), digest, current, project_id)

    @app.post(path, status_code=201)
    def submit(project_id: str, document_id: str, body: SubmitCircuit, current=Depends(actor)):
        with repo._transaction() as db:
            digest = original(project_id, document_id, current, write=True)
            if body.document_sha256 != digest:
                raise DomainError("conflict", "Rouvrez le PDF avant de le soumettre.")
            if get_row(db, project_id, document_id) is None:
                db.execute("INSERT INTO signature_circuits VALUES(?,?,?,?,?,1)",
                           (tenant, project_id, document_id, current["actor_id"], create_circuit(digest)))
                repo._audit(db, tenant, project_id, "signature_circuit.submitted", current["actor_id"], document_id,
                            {"document_sha256": digest})
            return present(get_row(db, project_id, document_id), digest, current, project_id)

    @app.patch(path)
    def review(project_id: str, document_id: str, body: ReviewCircuit, current=Depends(actor)):
        with repo._transaction() as db:
            digest = original(project_id, document_id, current, write=True)
            row = get_row(db, project_id, document_id)
            if row is None or row["revision"] != body.revision:
                raise DomainError("conflict", "Le circuit a changé. Rechargez le document avant de décider.")
            state = present(row, digest, current, project_id)
            if not state["can_decide"]:
                raise DomainError("forbidden", "La relecture doit être effectuée par un autre membre habilité.")
            snapshot = advance_circuit(row["snapshot"], body.decision)
            db.execute("""UPDATE signature_circuits SET snapshot=?, revision=revision+1
                WHERE tenant_id=? AND project_id=? AND document_id=?""", (snapshot, tenant, project_id, document_id))
            repo._audit(db, tenant, project_id, "signature_circuit.reviewed", current["actor_id"], document_id,
                        {"document_sha256": digest, "decision": body.decision})
            return present(get_row(db, project_id, document_id), digest, current, project_id)
