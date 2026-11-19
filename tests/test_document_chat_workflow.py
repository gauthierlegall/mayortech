"""Actual HTTP upload -> document model -> RAG/chat model -> human confirmation.

All records and provider credentials are synthetic. Only MockTransport can run
the model requests; no browser, real identity provider or live model is called.
"""
import base64
import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from travaux.config import Settings
from travaux.llm import make_extractor

ORIGIN = 'https://workflow.invalid'


def text_pdf():
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject
    writer = PdfWriter(); page = writer.add_blank_page(width=300, height=200)
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    content = DecodedStreamObject(); content.set_data(b'BT /F1 12 Tf 20 100 Td (Avancement : Terrassement termine) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(content)
    output = io.BytesIO(); writer.write(output)
    return output.getvalue()


@pytest.fixture
def workflow(tmp_path, monkeypatch):
    from travaux import api
    for name in list(__import__('os').environ):
        if name.startswith('TRAVAUX_') or name in {'SSLKEYLOGFILE', 'QUICLOGDIR'}:
            monkeypatch.delenv(name, raising=False)
    configured = Settings(mode='pilot', auth_mode='oidc', db_path=tmp_path / 'workflow.sqlite3', tenant_id='workflow-town', public_origin=ORIGIN, allowed_hosts=('workflow.invalid',), llm='mistral', mistral_url='https://provider.invalid/chat', mistral_key='synthetic-only', mistral_document_model='mistral-large-4-0', mistral_chat_model='zai-glm-5-3-flash', egress_approved=True)
    requests, app_box = [], []
    def provider(request):
        payload = json.loads(request.content)
        requests.append({'model': payload['model'], 'schema': payload['response_format']['json_schema']['name'], 'body': payload, 'transaction_open': app_box[0].state.repo._db.in_transaction if app_box else False})
        if payload['model'] == 'mistral-large-4-0':
            result = {'candidates': [{'field': 'Avancement', 'value': 'Terrassement termine', 'kind': 'text', 'quote': 'Avancement : Terrassement termine'}], 'warnings': []}
        elif payload['response_format']['json_schema']['name'] == 'dossier_passages':
            context = json.loads(payload['messages'][1]['content'])
            result = {'passages': context['untrusted_passages'][:1]}
        else:
            result = {'operation': 'property', 'field': 'status', 'value': 'Terminé'}
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(result)}}]})
    transport = httpx.MockTransport(provider)
    monkeypatch.setattr(api, 'make_extractor', lambda settings: make_extractor(settings, transport=transport))
    app = api.create_app(configured); app_box.append(app)
    app.state.assistant.transport = transport
    app.state.conversations.retrieval.assistant.transport = transport
    app.state.conversations.changes.transport = transport
    member = app.state.identities.provision('https://identity.invalid', 'agent', 'Agent de recette', 'editor')
    repo = app.state.repo
    project = repo.create_project(configured.tenant_id, 'FLOW-A', 'Cour de recette')
    forbidden = repo.create_project(configured.tenant_id, 'FLOW-B', 'Dossier inaccessible')
    repo.ingest_source(configured.tenant_id, 'inaccessible', 'Secret', 'terrassement NEVER_SHARE_WITH_PROVIDER', project_ref='FLOW-B')
    repo._db.execute('INSERT INTO project_grants VALUES(?,?,?,?,?)', (configured.tenant_id, member['actor_id'], project['id'], 'test-operator', 'now'))
    token = app.state.sessions.issue(member['actor_id'], configured.tenant_id)
    with TestClient(app, base_url=ORIGIN, headers={'X-Requested-With': 'Travaux', 'Origin': ORIGIN}) as client:
        client.cookies.set('travaux_session', token)
        yield app, client, configured, member, project, forbidden, requests


def prepare_change(client, thread_id):
    response = client.post('/api/v1/conversations/'+thread_id+'/messages', json={'content': 'Mets le statut à Terminé', 'client_id': 'explicit-change', 'intent': 'change'})
    assert response.status_code == 200, response.text
    message = response.json()['messages'][1]
    assert message['mode'] == 'change_proposal'
    ident = message['context']['change_proposal_id']
    proposal = client.get('/api/v1/assistant-changes/'+ident)
    assert proposal.status_code == 200, proposal.text
    return proposal.json()


def ingest_and_ask(workflow):
    app, client, configured, _, project, _, requests = workflow
    original = text_pdf()
    uploaded = client.post('/api/v1/projects/'+project['id']+'/documents/upload', json={'filename': 'terrain.pdf', 'content_base64': base64.b64encode(original).decode(), 'client_id': 'document-workflow'})
    assert uploaded.status_code == 201, uploaded.text
    receipt = uploaded.json()
    assert receipt['status'] == 'needs_review' and receipt['job_status'] == 'done' and receipt['candidate_count'] == 1
    assert app.state.repo.get_memory(configured.tenant_id, project['id'])['facts'] == []
    assert client.get('/api/v1/documents/'+receipt['document_id']+'/download').content == original
    conversation = client.post('/api/v1/conversations', json={'project_id': project['id'], 'title': 'Revue documentaire'})
    assert conversation.status_code == 201, conversation.text
    thread_id = conversation.json()['id']
    answer = client.post('/api/v1/conversations/'+thread_id+'/messages', json={'content': 'Quels travaux concernent le terrassement ?', 'client_id': 'document-question'})
    assert answer.status_code == 200, answer.text
    result = answer.json()['messages'][1]
    assert result['mode'] == 'mistral_extraits'
    assert result['citations'][0]['source_id'] == receipt['source_id']
    assert 'Terrassement termine' in result['content']
    assert 'NEVER_SHARE_WITH_PROVIDER' not in json.dumps(requests)
    return receipt, thread_id


def test_document_large4_then_chat_glm_requires_confirmation_before_database_change(workflow):
    app, client, configured, _, project, _, requests = workflow
    receipt, thread_id = ingest_and_ask(workflow)
    proposal = prepare_change(client, thread_id)
    assert proposal['plan'] == {'operation': 'property', 'field': 'status', 'value': 'Terminé'}
    assert proposal['status'] == 'pending'
    assert client.get('/api/v1/projects/'+project['id']).json()['status'] == 'active'
    confirm = client.post('/api/v1/assistant-changes/'+proposal['id']+'/confirm', json={'expected_plan_hash': proposal['plan_hash']})
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()['status'] == 'applied'
    assert app.state.repo.get_project(configured.tenant_id, project['id'])['status'] == 'completed'
    replay = client.post('/api/v1/assistant-changes/'+proposal['id']+'/confirm', json={'expected_plan_hash': proposal['plan_hash']})
    assert replay.status_code == 200 and replay.json() == confirm.json()
    assert [item['model'] for item in requests] == ['mistral-large-4-0', 'zai-glm-5-3-flash', 'zai-glm-5-3-flash']
    assert not any(item['transaction_open'] for item in requests)
    assert app.state.repo.get_source(configured.tenant_id, receipt['source_id'])['project_ids'] == [project['id']]


def test_revocation_blocks_document_rag_history_and_pending_confirmation_before_provider_call(workflow):
    app, client, configured, member, project, _, requests = workflow
    receipt, thread_id = ingest_and_ask(workflow)
    proposal = prepare_change(client, thread_id)
    count = len(requests)
    with app.state.repo._transaction() as db:
        db.execute('DELETE FROM project_grants WHERE tenant_id=? AND actor_id=?', (configured.tenant_id, member['actor_id']))
    assert client.get('/api/v1/documents/'+receipt['document_id']+'/download').status_code == 404
    assert client.get('/api/v1/projects/'+project['id']+'/retrieval', params={'q': 'terrassement'}).status_code == 404
    assert client.get('/api/v1/conversations/'+thread_id).status_code == 404
    assert client.get('/api/v1/conversations').json()['items'] == []
    assert client.post('/api/v1/assistant-changes/'+proposal['id']+'/confirm', json={'expected_plan_hash': proposal['plan_hash']}).status_code == 404
    assert app.state.repo.get_project(configured.tenant_id, project['id'])['status'] == 'active'
    assert len(requests) == count
