"""Tests for Sovereign BPMN 2.0 Workflow Engine (MayorFlow) - Pôles 3 & 5."""

import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings
from travaux.workflow_engine import BpmnXmlBuilder, WorkflowEngineRepository
from travaux.workflow_graph_validator import WorkflowGraphValidator
from travaux.workflow_prompt import PromptToBpmnEngine
from travaux.workflow_templates import MUNICIPAL_TEMPLATES
from travaux.workflow_token_machine import TokenEngine


@pytest.fixture
def test_app(tmp_path):
    db_file = tmp_path / "test_workflow.db"
    settings = Settings(
        mode="demo",
        db_path=db_file,
        tenant_id="mairie-plougastel",
        password_hash="test-hash",
        auth_mode="password",
    )
    app = create_app(settings)
    return app, settings


@pytest.fixture
def client(test_app):
    app, _ = test_app
    return TestClient(app)


def test_seed_templates_and_list_definitions(client):
    """Checks that the 10 municipal templates are automatically seeded and queryable."""
    res = client.get("/api/v1/workflows/definitions")
    assert res.status_code == 200
    defs = res.json()
    assert len(defs) >= 10
    keys = {d["key"] for d in defs}
    assert "urbanisme_ads" in keys
    assert "marches_cao" in keys
    assert "ccas_aide_sociale" in keys
    assert "seances_conseil" in keys


def test_get_definition_with_bpmn_xml(client):
    """Checks that a workflow definition includes both parsed JSON and standard BPMN 2.0 XML."""
    res = client.get("/api/v1/workflows/definitions")
    defs = res.json()
    ads_def = next(d for d in defs if d["key"] == "urbanisme_ads")

    res_detail = client.get(f"/api/v1/workflows/definitions/{ads_def['id']}")
    assert res_detail.status_code == 200
    data = res_detail.json()
    assert data["name"] == "Instruction Permis de Construire (ADS)"
    assert "version" in data
    assert "bpmn_xml" in data["version"]
    assert "<bpmn:definitions" in data["version"]["bpmn_xml"]
    assert "<bpmn:startEvent" in data["version"]["bpmn_xml"]
    assert "<bpmndi:BPMNDiagram" in data["version"]["bpmn_xml"]
    assert "nodes" in data["version"]["bpmn_json"]


def test_workflow_linear_and_service_execution(client):
    """Starts an ADS workflow instance, progresses through user tasks, triggers service task & seal."""
    # 1. Retrieve ADS definition ID
    defs = client.get("/api/v1/workflows/definitions").json()
    ads_def = next(d for d in defs if d["key"] == "urbanisme_ads")

    # 2. Start workflow instance
    headers = {"X-Requested-With": "Travaux"}
    start_payload = {
        "definition_id": ads_def["id"],
        "business_key": "PC-2026-042",
        "title": "Permis de Construire — Rénovation Maison Ty-Ar-Braz",
        "initial_variables": {
            "demandeur": "Jean-Pierre Le Gall",
            "pieces_completes": True,
            "surface_m2": 145,
        },
    }
    res_start = client.post("/api/v1/workflows/instances", json=start_payload, headers=headers)
    assert res_start.status_code == 200
    instance = res_start.json()
    assert instance["state"] == "running"
    assert instance["business_key"] == "PC-2026-042"

    # Active token should be at task_completude
    active_tokens = [t for t in instance["tokens"] if t["state"] == "active"]
    assert len(active_tokens) == 1
    t_completude = active_tokens[0]
    assert t_completude["node_id"] == "task_completude"

    # 3. Check inbox contains the task
    res_inbox = client.get("/api/v1/workflows/tasks/inbox?commission=urbanisme")
    assert res_inbox.status_code == 200
    inbox = res_inbox.json()
    assert any(task["id"] == t_completude["id"] for task in inbox)

    # 4. Claim the task
    res_claim = client.post(f"/api/v1/workflows/tasks/{t_completude['id']}/claim", headers=headers)
    assert res_claim.status_code == 200

    # 5. Complete task_completude with pieces_completes=True
    res_complete1 = client.post(
        f"/api/v1/workflows/tasks/{t_completude['id']}/complete",
        json={"form_data": {"pieces_completes": True, "observation": "Dossier CERFA conforme"}},
        headers=headers,
    )
    assert res_complete1.status_code == 200
    inst_state = res_complete1.json()

    # XOR Gateway should route to task_abf
    active_tokens2 = [t for t in inst_state["tokens"] if t["state"] == "active"]
    assert len(active_tokens2) == 1
    t_abf = active_tokens2[0]
    assert t_abf["node_id"] == "task_abf"

    # 6. Complete task_abf
    res_complete2 = client.post(
        f"/api/v1/workflows/tasks/{t_abf['id']}/complete",
        json={"form_data": {"avis_abf": "favorable_avec_prescriptions"}},
        headers=headers,
    )
    assert res_complete2.status_code == 200
    t_visa = [t for t in res_complete2.json()["tokens"] if t["state"] == "active"][0]
    assert t_visa["node_id"] == "task_visa_adjoint"

    # 7. Complete task_visa_adjoint -> triggers service tasks and reaches endEvent!
    res_complete3 = client.post(
        f"/api/v1/workflows/tasks/{t_visa['id']}/complete",
        json={"form_data": {"visa_adjoint": "accorde"}},
        headers=headers,
    )
    assert res_complete3.status_code == 200
    final_instance = res_complete3.json()
    assert final_instance["state"] == "completed"

    # Verify service tasks executed automatically
    vars_final = final_instance["variables"]
    assert vars_final.get("decision_pdf_generated") is True
    assert vars_final.get("decision_pdf_reference") == "DEC-PC-2026-042-2026"
    assert "integrity_seal_sha256" in vars_final

    # Verify immutable cryptographic audit log
    res_audit = client.get(f"/api/v1/workflows/instances/{final_instance['id']}/audit")
    assert res_audit.status_code == 200
    audit_trail = res_audit.json()
    assert len(audit_trail) >= 5
    assert all("sha256_hash" in entry for entry in audit_trail)


def test_exclusive_gateway_xor_conditional_branching(client):
    """Verifies XOR gateway branches to task_pieces_manquantes when pieces_completes=False."""
    defs = client.get("/api/v1/workflows/definitions").json()
    ads_def = next(d for d in defs if d["key"] == "urbanisme_ads")
    headers = {"X-Requested-With": "Travaux"}

    res_start = client.post(
        "/api/v1/workflows/instances",
        json={
            "definition_id": ads_def["id"],
            "business_key": "PC-2026-099",
            "title": "Permis Incomplet",
            "initial_variables": {},
        },
        headers=headers,
    )
    inst = res_start.json()
    t_completude = [t for t in inst["tokens"] if t["state"] == "active"][0]

    # Submit with pieces_completes=False
    res_complete = client.post(
        f"/api/v1/workflows/tasks/{t_completude['id']}/complete",
        json={"form_data": {"pieces_completes": False, "motif": "Plan de masse manquant"}},
        headers=headers,
    )
    assert res_complete.status_code == 200
    inst_branched = res_complete.json()
    active_tok = [t for t in inst_branched["tokens"] if t["state"] == "active"][0]
    assert active_tok["node_id"] == "task_pieces_manquantes"


def test_dynamic_json_schema_form(client):
    """Tests saving and retrieving custom dynamic JSON Schema forms for user tasks."""
    defs = client.get("/api/v1/workflows/definitions").json()
    ads_def = defs[0]
    headers = {"X-Requested-With": "Travaux"}

    custom_schema = {
        "type": "object",
        "title": "Avis Technique ABF",
        "properties": {
            "avis": {"type": "string", "enum": ["favorable", "defavorable", "prescriptions"]},
            "prescriptions_texte": {"type": "string", "title": "Prescriptions patrimoniales"},
        },
        "required": ["avis"],
    }
    custom_ui = {
        "prescriptions_texte": {"ui:widget": "textarea"},
    }

    res_save = client.put(
        f"/api/v1/workflows/definitions/{ads_def['id']}/form/task_abf",
        json={"schema": custom_schema, "uischema": custom_ui},
        headers=headers,
    )
    assert res_save.status_code == 200
    saved = res_save.json()
    assert saved["schema"]["title"] == "Avis Technique ABF"

    # Get form
    res_get = client.get(f"/api/v1/workflows/definitions/{ads_def['id']}/form/task_abf")
    assert res_get.status_code == 200
    assert res_get.json()["schema"]["title"] == "Avis Technique ABF"


def test_prompt_to_bpmn_generation(client):
    """Tests Stieges Prompt-to-Logic-Core extraction and Sugiyama auto-layout."""
    headers = {"X-Requested-With": "Travaux"}
    prompt_text = (
        "Créer un workflow d'instruction pour une demande d'aide sociale CCAS. "
        "D'abord entretien avec l'assistante sociale, si urgence alors bon d'urgence DGS, "
        "ensuite commission permanente et mandatement trésorier avec scellement."
    )
    res_prompt = client.post(
        "/api/v1/workflows/prompt/generate",
        json={"prompt": prompt_text, "category_hint": "ccas"},
        headers=headers,
    )
    assert res_prompt.status_code == 200
    generated = res_prompt.json()
    assert generated["category"] == "ccas"
    assert "<bpmn:definitions" in generated["bpmn_xml"]
    assert len(generated["bpmn_json"]["nodes"]) >= 4

    # Verify Sugiyama coordinates were calculated
    for node in generated["bpmn_json"]["nodes"]:
        assert "x" in node and node["x"] > 0
        assert "y" in node and node["y"] > 0


def test_graph_validator_and_auto_repair():
    """Checks that disconnected graphs are safely repaired with valid start/end nodes."""
    broken_nodes = [
        {"id": "task_1", "type": "userTask", "name": "Étape isolée"},
    ]
    broken_edges = []

    is_valid, errors = WorkflowGraphValidator.validate(broken_nodes, broken_edges)
    assert is_valid is False
    assert len(errors) > 0

    repaired_nodes, repaired_edges = WorkflowGraphValidator.auto_repair(broken_nodes, broken_edges)
    has_start = any(n["type"] == "startEvent" for n in repaired_nodes)
    has_end = any(n["type"] == "endEvent" for n in repaired_nodes)
    assert has_start is True
    assert has_end is True


def test_supervision_metrics_and_heatmap(client):
    """Tests BAM supervision metrics and thermal node heatmap."""
    res_metrics = client.get("/api/v1/workflows/watch/metrics")
    assert res_metrics.status_code == 200
    metrics = res_metrics.json()
    assert "active_instances" in metrics
    assert "completed_instances" in metrics
    assert "node_heatmap" in metrics
    assert isinstance(metrics["node_heatmap"], list)


def test_sla_timer_escalation_to_dgs(test_app, client):
    """Verifies that expired timers escalate assigned tasks to DGS."""
    app, settings = test_app
    workflow_repo: WorkflowEngineRepository = app.state.workflow_engine
    headers = {"X-Requested-With": "Travaux"}

    defs = client.get("/api/v1/workflows/definitions").json()
    ads_def = defs[0]

    # Start instance
    res_start = client.post(
        "/api/v1/workflows/instances",
        json={"definition_id": ads_def["id"], "business_key": "SLA-TEST-01", "title": "Test Échéance SLA"},
        headers=headers,
    )
    inst = res_start.json()
    token = [t for t in inst["tokens"] if t["state"] == "active"][0]

    # Force a timer with timestamp in the past
    past_iso = "2020-01-01T00:00:00Z"
    workflow_repo.register_timer(
        instance_id=inst["id"],
        token_id=token["id"],
        node_id=token["node_id"],
        trigger_at=past_iso,
        sla_action="escalate_dgs",
    )

    # Trigger timer check
    res_check = client.post("/api/v1/workflows/timers/check", headers=headers)
    assert res_check.status_code == 200
    data = res_check.json()
    assert data["escalated_count"] >= 1

    # Verify token reassigned to DGS
    updated_tok = workflow_repo.get_token(token["id"])
    assert updated_tok["assigned_role"] == "dgs"


def test_publish_new_version(client):
    """Verifies publishing a new BPMN version increments version number."""
    defs = client.get("/api/v1/workflows/definitions").json()
    target_def = defs[0]
    headers = {"X-Requested-With": "Travaux"}

    res_pub = client.post(
        f"/api/v1/workflows/definitions/{target_def['id']}/versions",
        json={
            "bpmn_xml": "<bpmn:definitions version='2'></bpmn:definitions>",
            "bpmn_json": {"nodes": [], "edges": []},
        },
        headers=headers,
    )
    assert res_pub.status_code == 200
    updated = res_pub.json()
    assert updated["current_version"] == 2

