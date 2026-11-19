"""Document extraction and RAG use distinct explicit Mistral model IDs."""
import json

import httpx
import pytest

from travaux.auth import hash_password
from travaux.config import Settings
from travaux.repository import Repository


def test_environment_routes_documents_to_large4_and_chat_to_glm(monkeypatch):
    for name in list(__import__("os").environ):
        if name.startswith("TRAVAUX_"):
            monkeypatch.delenv(name)
    for name, value in {"LLM": "mistral", "MISTRAL_URL": "https://api.eu.mistral.ai/v1/chat/completions", "MISTRAL_KEY": "only-fake", "LLM_EGRESS_APPROVED": "true"}.items():
        monkeypatch.setenv("TRAVAUX_"+name, value)
    configured = Settings.from_env()
    assert configured.document_model == "mistral-large-4-0"
    assert configured.chat_model == "zai-glm-5-3-flash"


def test_actual_extraction_and_rag_requests_have_their_own_model(tmp_path, monkeypatch):
    monkeypatch.delenv("SSLKEYLOGFILE", raising=False)
    monkeypatch.delenv("QUICLOGDIR", raising=False)
    from travaux.llm import make_extractor
    from travaux.assistant_dossier import DossierAssistant
    configured = Settings(mode="staging", db_path=tmp_path / "models.sqlite3", password_hash=hash_password("a fake password for model routing"), public_origin="https://travaux.example", allowed_hosts=("travaux.example",), llm="mistral", mistral_url="https://api.eu.mistral.ai/v1/chat/completions", mistral_document_model="mistral-large-4-0", mistral_chat_model="zai-glm-5-3-flash", mistral_key="only-fake", egress_approved=True)
    models = []
    def provider(request):
        payload = json.loads(request.content)
        models.append(payload["model"])
        result = {"candidates": [], "warnings": []} if payload["model"] == "mistral-large-4-0" else {"passages": []}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(result)}}]})
    transport = httpx.MockTransport(provider)
    make_extractor(configured, transport=transport).extract("Document de recette fictif")
    repo = Repository(configured.db_path)
    try:
        DossierAssistant(repo, configured, transport=transport)._select("Question fictive", [], {})
    finally:
        repo.close()
    assert models == ["mistral-large-4-0", "zai-glm-5-3-flash"]
@pytest.mark.parametrize('variable', ['SSLKEYLOGFILE', 'QUICLOGDIR'])
def test_rag_refuses_tls_diagnostics_before_sending_sources(tmp_path, monkeypatch, variable):
    from travaux.assistant_dossier import DossierAssistant
    from travaux.domain import DomainError
    from travaux.repository import Repository
    monkeypatch.setenv(variable, 'synthetic-diagnostic-path')
    calls = []
    def provider(request):
        calls.append(request)
        raise AssertionError('No data may leave before TLS diagnostic refusal')
    repo = Repository(tmp_path / 'diagnostic.sqlite3')
    settings = Settings(llm='mistral', mistral_url='https://model.invalid/chat', mistral_key='fake', mistral_chat_model='zai-glm-5-3-flash', egress_approved=True)
    service = DossierAssistant(repo, settings, transport=httpx.MockTransport(provider))
    try:
        with pytest.raises(DomainError, match='TLS'):
            service._select('Question', [{'source_id': 'private', 'quote': 'Private document'}], {})
        assert calls == []
    finally:
        repo.close()

