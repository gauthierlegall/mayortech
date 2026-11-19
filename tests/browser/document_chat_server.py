"""Loopback-only QA: real API/SQLite/PDF parser/Yjs; deterministic fake LLM transport."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
for key in list(os.environ):
    if key.startswith("TRAVAUX_") or key in {"SSLKEYLOGFILE", "QUICLOGDIR"}:
        os.environ.pop(key, None)
import httpx
from travaux import api
from travaux.config import Settings
from travaux.llm import make_extractor

OUT = ROOT / "test-results" / "document-chat-integration"
OUT.mkdir(parents=True, exist_ok=True)
DATA = ROOT / ".local" / "document-chat-browser-qa"
DATA.mkdir(parents=True, exist_ok=True)
records = []


def provider(request):
    payload = json.loads(request.content)
    schema = payload["response_format"]["json_schema"]["name"]
    records.append({"model": payload["model"], "schema": schema})
    (OUT / "model-routing.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    context = json.loads(payload["messages"][1]["content"])
    if schema == "work_facts":
        quote = "Avancement : Terrassement termine RECETTE_RAG_1711"
        result = {
            "candidates": [
                {
                    "field": "Avancement",
                    "value": "Terrassement termine RECETTE_RAG_1711",
                    "kind": "text",
                    "quote": quote,
                }
            ]
            if quote in context["untrusted_source"]
            else [],
            "warnings": [],
        }
    elif schema == "dossier_passages":
        selected = [row for row in context["untrusted_passages"] if "RECETTE_RAG_1711" in row["quote"]]
        result = {"passages": selected[:2]}
    elif schema == "human_approved_change":
        question = context["request"]
        result = (
            {"operation": "action", "field": "", "value": question.split(":", 1)[1].strip()}
            if ":" in question
            else {"operation": "property", "field": "status", "value": "Terminé"}
        )
    else:
        raise AssertionError("Unexpected model schema")
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(result)}}]})


transport = httpx.MockTransport(provider)
api.make_extractor = lambda settings: make_extractor(settings, transport=transport)
settings = Settings(
    mode="demo",
    db_path=DATA / "workspace.sqlite3",
    tenant_id="browser-qa",
    allowed_hosts=("127.0.0.1",),
    llm="mistral",
    mistral_url="https://model.invalid/chat",
    mistral_key="fake-key-only",
    mistral_document_model="mistral-large-4-0",
    mistral_chat_model="zai-glm-5-3-flash",
    egress_approved=True,
)
app = api.create_app(settings)
app.state.assistant.transport = transport
app.state.conversations.retrieval.assistant.transport = transport
app.state.conversations.changes.transport = transport
project = (
    app.state.repo.find_project(settings.tenant_id, "QA-RAG-1711")
    if hasattr(app.state.repo, "find_project")
    else None
)
if not project:
    existing = [
        row for row in app.state.repo.list_projects(settings.tenant_id) if row["reference"] == "QA-RAG-1711"
    ]
    project = (
        existing[0]
        if existing
        else app.state.repo.create_project(
            settings.tenant_id, "QA-RAG-1711", "Recette documentaire et chatbot"
        )
    )
(OUT / "fixture.json").write_text(
    json.dumps(
        {
            "project_id": project["id"],
            "tenant": settings.tenant_id,
            "origin": "http://127.0.0.1:18806",
            "authentication": "local demo only; identity and MFA not exercised",
            "provider": "httpx.MockTransport; no external call",
            "database": str(settings.db_path),
        },
        indent=2,
    ),
    encoding="utf-8",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=18806, log_level="warning")
