"""REST API Routes for Sovereign BPMN 2.0 Workflows (MayorFlow)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from .domain import DomainError
from .workflow_engine import WorkflowEngineRepository
from .workflow_token_machine import TokenEngine
from .workflow_prompt import PromptToBpmnEngine
from .workflow_templates import MUNICIPAL_TEMPLATES, seed_municipal_templates, seed_demo_workflow_instances


class CreateDefinitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=128)
    category: str = Field(min_length=2, max_length=32)
    commission_id: Optional[str] = None
    description: Optional[str] = None
    bpmn_xml: Optional[str] = ""
    bpmn_json: Optional[Dict[str, Any]] = None


class UpdateDefinitionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    description: Optional[str] = None
    commission_id: Optional[str] = None


class PublishVersionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bpmn_xml: str
    bpmn_json: Dict[str, Any]


class StartInstancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    definition_id: str
    business_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=256)
    initial_variables: Optional[Dict[str, Any]] = None


class CompleteTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    form_data: Dict[str, Any]


class SaveFormPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_dict: Dict[str, Any] = Field(alias="schema")
    uischema: Optional[Dict[str, Any]] = None


class PromptWorkflowPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=5, max_length=4000)
    category_hint: Optional[str] = None
    base_workflow_id: Optional[str] = None


def register_workflow_routes(app: Any, repo: Any, tenant: str, actor: Any, workflow_repo: WorkflowEngineRepository) -> None:
    token_engine = TokenEngine(workflow_repo)

    # Automatically seed 10 municipal templates
    seed_municipal_templates(workflow_repo, tenant)
    seed_demo_workflow_instances(token_engine, workflow_repo, tenant)

    # ----------------- Definitions Endpoints -----------------

    @app.get("/api/v1/workflows/definitions")
    def list_definitions(category: Optional[str] = None, current=Depends(actor)):
        return workflow_repo.list_definitions(tenant, category=category)

    @app.post("/api/v1/workflows/definitions")
    def create_definition(payload: CreateDefinitionPayload, current=Depends(actor)):
        return workflow_repo.create_definition(
            tenant_id=tenant,
            key=payload.key,
            name=payload.name,
            category=payload.category,
            commission_id=payload.commission_id,
            description=payload.description,
            bpmn_xml=payload.bpmn_xml or "",
            bpmn_json=payload.bpmn_json,
        )

    @app.get("/api/v1/workflows/definitions/{definition_id}")
    def get_definition(definition_id: str, current=Depends(actor)):
        return workflow_repo.get_definition(definition_id)

    @app.patch("/api/v1/workflows/definitions/{definition_id}")
    def update_definition(definition_id: str, payload: UpdateDefinitionPayload, current=Depends(actor)):
        return workflow_repo.update_definition(
            definition_id=definition_id,
            name=payload.name,
            description=payload.description,
            commission_id=payload.commission_id,
        )

    @app.post("/api/v1/workflows/definitions/{definition_id}/versions")
    def publish_version(definition_id: str, payload: PublishVersionPayload, current=Depends(actor)):
        return workflow_repo.publish_new_version(
            definition_id=definition_id,
            bpmn_xml=payload.bpmn_xml,
            bpmn_json=payload.bpmn_json,
        )

    # ----------------- Dynamic Forms (JSON Schema) -----------------

    @app.get("/api/v1/workflows/definitions/{definition_id}/form/{node_id}")
    def get_task_form(definition_id: str, node_id: str, current=Depends(actor)):
        return workflow_repo.get_task_form(definition_id, node_id)

    @app.put("/api/v1/workflows/definitions/{definition_id}/form/{node_id}")
    def save_task_form(definition_id: str, node_id: str, payload: SaveFormPayload, current=Depends(actor)):
        return workflow_repo.save_task_form(
            definition_id=definition_id,
            node_id=node_id,
            schema=payload.schema_dict,
            uischema=payload.uischema,
        )

    # ----------------- Instances & Execution Endpoints -----------------

    @app.get("/api/v1/workflows/instances")
    def list_instances(
        state: Optional[str] = None,
        initiator_id: Optional[str] = None,
        definition_id: Optional[str] = None,
        current=Depends(actor),
    ):
        return workflow_repo.list_instances(
            tenant_id=tenant,
            state=state,
            initiator_id=initiator_id,
            definition_id=definition_id,
        )

    @app.post("/api/v1/workflows/instances")
    def start_instance(payload: StartInstancePayload, current=Depends(actor)):
        initiator_id = current.get("sub", current.get("email", "anonymous_agent"))
        initiator_name = current.get("name", current.get("email", "Agent Municipal"))
        return token_engine.start_instance(
            tenant_id=tenant,
            definition_id=payload.definition_id,
            business_key=payload.business_key,
            title=payload.title,
            initiator_id=initiator_id,
            initiator_name=initiator_name,
            initial_variables=payload.initial_variables or {},
        )

    @app.get("/api/v1/workflows/instances/{instance_id}")
    def get_instance(instance_id: str, current=Depends(actor)):
        return workflow_repo.get_instance(instance_id)

    @app.post("/api/v1/workflows/instances/{instance_id}/terminate")
    def terminate_instance(instance_id: str, current=Depends(actor)):
        return workflow_repo.update_instance_state(instance_id, state="terminated")

    @app.get("/api/v1/workflows/instances/{instance_id}/audit")
    def get_instance_audit(instance_id: str, current=Depends(actor)):
        return workflow_repo.get_instance_audit_trail(instance_id)

    # ----------------- Inbox & Task Handling (MayorFlow Play) -----------------

    @app.get("/api/v1/workflows/tasks/inbox")
    def get_tasks_inbox(
        commission: Optional[str] = None,
        role: Optional[str] = None,
        current=Depends(actor),
    ):
        user_id = current.get("sub", current.get("email", ""))
        return workflow_repo.list_inbox_tasks(
            tenant_id=tenant,
            user_id=user_id,
            commission=commission,
            role=role,
        )

    @app.post("/api/v1/workflows/tasks/{token_id}/claim")
    def claim_task(token_id: str, current=Depends(actor)):
        user_id = current.get("sub", current.get("email", "current_user"))
        return workflow_repo.claim_token(token_id, user_id=user_id)

    @app.post("/api/v1/workflows/tasks/{token_id}/complete")
    def complete_task(token_id: str, payload: CompleteTaskPayload, current=Depends(actor)):
        actor_id = current.get("sub", current.get("email", "current_user"))
        return token_engine.advance_user_task(
            token_id=token_id,
            actor_id=actor_id,
            form_data=payload.form_data,
        )

    # ----------------- Templates Endpoints -----------------

    @app.get("/api/v1/workflows/templates")
    def list_templates(current=Depends(actor)):
        return MUNICIPAL_TEMPLATES

    @app.post("/api/v1/workflows/templates/{key}/instantiate")
    def instantiate_template(key: str, current=Depends(actor)):
        tmpl = next((t for t in MUNICIPAL_TEMPLATES if t["key"] == key), None)
        if not tmpl:
            raise DomainError("not_found", f"Template '{key}' introuvable.")

        instantiated_key = f"{key}_{TokenEngine(workflow_repo).repo.repo.utc_now() if hasattr(workflow_repo.repo, 'utc_now') else 'inst'}"
        import uuid
        instantiated_key = f"{key}_{uuid.uuid4().hex[:6]}"

        from .workflow_engine import BpmnXmlBuilder
        bpmn_xml = BpmnXmlBuilder.to_xml(
            process_id=instantiated_key,
            process_name=tmpl["name"],
            nodes=tmpl["nodes"],
            edges=tmpl["edges"],
        )
        return workflow_repo.create_definition(
            tenant_id=tenant,
            key=instantiated_key,
            name=tmpl["name"],
            category=tmpl["category"],
            commission_id=tmpl.get("commission_id"),
            description=tmpl.get("description"),
            bpmn_xml=bpmn_xml,
            bpmn_json={"nodes": tmpl["nodes"], "edges": tmpl["edges"]},
        )

    # ----------------- Prompt-to-BPMN Studio -----------------

    @app.post("/api/v1/workflows/prompt/generate")
    def prompt_generate_workflow(payload: PromptWorkflowPayload, current=Depends(actor)):
        base_workflow = None
        if payload.base_workflow_id:
            base_workflow = workflow_repo.get_definition(payload.base_workflow_id)

        parsed = PromptToBpmnEngine.parse_prompt(
            prompt=payload.prompt,
            category_hint=payload.category_hint,
            base_workflow=base_workflow,
        )
        return parsed

    # ----------------- Watch & BAM Supervision Heatmap -----------------

    @app.get("/api/v1/workflows/watch/metrics")
    def get_watch_metrics(current=Depends(actor)):
        return workflow_repo.get_supervision_metrics(tenant)

    @app.post("/api/v1/workflows/timers/check")
    def check_timers(current=Depends(actor)):
        escalated = token_engine.run_sla_escalations()
        return {"escalated_count": len(escalated), "details": escalated}
