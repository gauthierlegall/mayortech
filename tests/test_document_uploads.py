import base64
from importlib import import_module
import io
from types import SimpleNamespace

import pytest

from travaux.documents import DocumentRepository
from travaux.domain import DomainError
from travaux.identity import IdentityStore
from travaux.jobs import JobQueue
from travaux.llm import DemoExtractor
from travaux.project_access import ProjectAccess
from travaux.repository import Repository
from travaux.retrieval import DossierRetrieval


@pytest.fixture
def upload_env(tmp_path):
    repo = Repository(tmp_path / 'uploads.sqlite3')
    queue = JobQueue(tmp_path / 'uploads.sqlite3')
    identities = repo.identity_store = IdentityStore(repo, 'town', None)
    alice = identities.provision('https://id.invalid', 'alice', 'Alice', 'editor')
    reader = identities.provision('https://id.invalid', 'reader', 'Reader', 'reader')
    projects = [repo.create_project('town', name, name) for name in ('ALPHA', 'BETA')]
    settings = SimpleNamespace(mode='staging', auth_mode='oidc', auth_required=True, llm='demo')
    repo.project_access = ProjectAccess(repo, settings)
    for member in (alice, reader):
        repo._db.execute('INSERT INTO project_grants VALUES(?,?,?,?,?)', ('town', member['actor_id'], projects[0]['id'], 'operator', 'now'))
    current = {'tenant_id': 'town', 'actor_id': alice['actor_id'], 'permissions': {'workspace': {'read': True, 'write': True}}}
    module = import_module('travaux.document_uploads')
    service = module.DocumentUploadService(repo, settings, queue=queue, extractor=DemoExtractor())
    yield repo, queue, settings, service, current, projects, reader
    repo.close()


def upload(env, content=b'Livraison : 2026-12-04', filename='note.txt', client_id='upload-one', **overrides):
    _, _, _, service, actor, (project, _), _ = env
    return service.upload('town', actor, project['id'], filename=filename, content_base64=base64.b64encode(content).decode(), client_id=client_id, **overrides)


def pdf_bytes(text=None):
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=200)
    if text:
        font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject(); stream.set_data(b'BT /F1 12 Tf 20 100 Td ('+text.encode('ascii')+b') Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
    result = io.BytesIO(); writer.write(result)
    return result.getvalue()


def test_real_pdf_upload_persists_original_and_only_pending_proposals(upload_env):
    repo, queue, _, _, actor, (project, _), _ = upload_env
    original = pdf_bytes('Livraison : 2026-12-04')
    result = upload(upload_env, original, 'devis.pdf')
    assert result['status'] == 'needs_review' and result['extraction_status'] == 'extracted'
    assert queue.get('town', result['job_id'])['status'] == 'done'
    document, stored = DocumentRepository(repo).download('town', result['document_id'], actor=actor)
    assert stored == original and document['kind'] == 'attachment'
    memory = repo.get_memory('town', project['id'])
    assert memory['facts'] == [] and memory['pending'][0]['value'] == '2026-12-04'
    assert memory['pending'][0]['evidence'][0]['source_id'] == result['source_id']


def test_upload_replay_and_new_version_never_overwrite_originals(upload_env):
    repo, _, _, _, actor, _, _ = upload_env
    first = upload(upload_env)
    replay = upload(upload_env)
    assert replay['source_id'] == first['source_id'] and replay['document_id'] == first['document_id'] and replay['job_id'] == first['job_id']
    with pytest.raises(DomainError): upload(upload_env, b'Changed contents')
    with pytest.raises(DomainError): upload(upload_env, filename='other.txt')
    second = upload(upload_env, b'Livraison : 2026-12-11', client_id='upload-two')
    assert second['document_id'] != first['document_id'] and second['source_id'] != first['source_id']
    assert DocumentRepository(repo).download('town', first['document_id'], actor=actor)[1] == b'Livraison : 2026-12-04'
    assert DocumentRepository(repo).download('town', second['document_id'], actor=actor)[1] == b'Livraison : 2026-12-11'
    assert repo._db.execute('SELECT count(*) FROM original_documents').fetchone()[0] == 2


@pytest.mark.parametrize(('filename', 'content'), [('program.exe', b'opaque'), ('../note.txt', b'plain'), ('note.txt', b'x'*5_000_001)], ids=['unsafe-extension', 'path-filename', 'oversized'])
def test_unsafe_or_oversized_uploads_leave_no_document(upload_env, filename, content):
    repo, _, _, _, _, _, _ = upload_env
    with pytest.raises(DomainError): upload(upload_env, content, filename)
    assert repo._db.execute('SELECT count(*) FROM original_documents').fetchone()[0] == 0


def test_uploads_respect_actor_tenant_readonly_and_grants(upload_env):
    repo, _, _, service, actor, (project, other), reader = upload_env
    body = {'filename': 'note.txt', 'content_base64': base64.b64encode(b'plain').decode(), 'client_id': 'forbidden'}
    with pytest.raises(DomainError): service.upload('town', actor, other['id'], **body)
    with pytest.raises(DomainError): service.upload('foreign', actor, project['id'], **body)
    readonly = {**actor, 'actor_id': reader['actor_id']}
    with pytest.raises(DomainError): service.upload('town', readonly, project['id'], **body)
    repo._db.execute('DELETE FROM project_grants WHERE actor_id=?', (actor['actor_id'],))
    with pytest.raises(DomainError): service.upload('town', actor, project['id'], **body)
    assert repo._db.execute('SELECT count(*) FROM original_documents').fetchone()[0] == 0


def test_uploaded_text_enters_dynamic_retrieval_and_shared_source_disappears(upload_env):
    repo, _, settings, _, actor, (project, other), _ = upload_env
    retrieval = DossierRetrieval(repo, settings)
    assert retrieval.search('town', 'terrassement', actor=actor)['items'] == []
    result = upload(upload_env, b'Terrassement termine dans la cour.', 'rapport.md')
    found = retrieval.search('town', 'terrassement', actor=actor)
    assert found['items'][0]['source_id'] == result['source_id']
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', result['source_id'], other['id'], 'operator', 'now'))
    assert retrieval.search('town', 'terrassement', actor=actor)['items'] == []
    with pytest.raises(DomainError): upload(upload_env, b'Terrassement termine dans la cour.', 'rapport.md')


@pytest.mark.parametrize(('original', 'expected'), [(pdf_bytes(), 'ocr_required'), (b'%PDF-1.4\nbroken', 'failed')], ids=['scanned-pdf', 'corrupt-pdf'])
def test_scan_or_failed_extraction_keeps_original_without_fact_or_fake_text(upload_env, original, expected):
    repo, _, _, _, actor, (project, _), _ = upload_env
    result = upload(upload_env, original, 'scan.pdf')
    assert result['extraction_status'] == expected and result['warnings']
    assert DocumentRepository(repo).download('town', result['document_id'], actor=actor)[1] == original
    source = repo.get_source('town', result['source_id'])
    assert source['body'] == ''
    assert repo.get_memory('town', project['id'])['facts'] == []
    assert repo.list_candidates('town', project['id']) == []


def test_crash_after_atomic_commit_replays_the_queued_analysis(upload_env, monkeypatch):
    repo, queue, _, service, _, _, _ = upload_env
    original = service._analyze
    def interrupted(*args, **kwargs): raise RuntimeError('simulated process interruption')
    monkeypatch.setattr(service, '_analyze', interrupted)
    with pytest.raises(RuntimeError): upload(upload_env)
    assert repo._db.execute('SELECT count(*) FROM original_documents').fetchone()[0] == 1
    assert queue.list('town')[0]['status'] == 'queued'
    monkeypatch.setattr(service, '_analyze', original)
    result = upload(upload_env)
    assert result['replayed'] and result['job_status'] == 'done'
    assert repo._db.execute('SELECT count(*) FROM original_documents').fetchone()[0] == 1


def test_job_enqueue_failure_rolls_back_source_original_and_receipt(upload_env, monkeypatch):
    module = import_module('travaux.document_uploads')
    repo, _, _, _, _, _, _ = upload_env
    def fail(*args): raise RuntimeError('synthetic queue failure')
    monkeypatch.setattr(module, '_enqueue_extract_in_transaction', fail)
    with pytest.raises(RuntimeError): upload(upload_env)
    for table in ['sources', 'original_documents', 'document_uploads', 'jobs']:
        assert repo._db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0


def test_revocation_after_parser_prevents_any_upload_commit(upload_env, monkeypatch):
    module = import_module('travaux.document_uploads')
    repo, _, _, _, actor, _, _ = upload_env
    original = module.extract_document
    def revoke(filename, raw):
        result = original(filename, raw)
        repo._db.execute('DELETE FROM project_grants WHERE actor_id=?', (actor['actor_id'],))
        return result
    monkeypatch.setattr(module, 'extract_document', revoke)
    with pytest.raises(DomainError): upload(upload_env)
    assert repo._db.execute('SELECT count(*) FROM original_documents').fetchone()[0] == 0


def test_model_failure_preserves_original_and_never_returns_provider_details(upload_env):
    import json
    _, _, _, service, _, _, _ = upload_env
    class FailingExtractor:
        def extract(self, text): raise ValueError('SYNTHETIC_PRIVATE_PROVIDER_DETAIL')
    service.extractor = FailingExtractor()
    result = upload(upload_env)
    assert result['status'] == 'needs_review' and result['job_status'] == 'failed' and result['warnings']
    assert 'SYNTHETIC_PRIVATE_PROVIDER_DETAIL' not in json.dumps(result)
    assert upload(upload_env)['document_id'] == result['document_id']


def test_large4_payload_runs_outside_transaction_and_commits_pending_evidence(upload_env, monkeypatch):
    import json
    import httpx
    from travaux.config import Settings
    from travaux.llm import make_extractor
    monkeypatch.delenv('SSLKEYLOGFILE', raising=False); monkeypatch.delenv('QUICLOGDIR', raising=False)
    repo, queue, _, _, actor, (project, _), _ = upload_env
    configured = Settings(mode='staging', auth_mode='oidc', public_origin='https://uploads.invalid', allowed_hosts=('uploads.invalid',), llm='mistral', mistral_url='https://provider.invalid/chat', mistral_key='only-synthetic', mistral_document_model='mistral-large-4-0', mistral_chat_model='zai-glm-5-3-flash', egress_approved=True)
    observed = []
    def provider(request):
        observed.append((json.loads(request.content)['model'], repo._db.in_transaction))
        payload = {'candidates': [{'field': 'Livraison', 'value': '2026-12-04', 'kind': 'date', 'quote': 'Livraison : 2026-12-04'}], 'warnings': []}
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(payload)}}]})
    service = import_module('travaux.document_uploads').DocumentUploadService(repo, configured, queue=queue, extractor=make_extractor(configured, transport=httpx.MockTransport(provider)))
    result = service.upload('town', actor, project['id'], filename='note.txt', content_base64=base64.b64encode(b'Livraison : 2026-12-04').decode(), client_id='large4')
    assert observed == [('mistral-large-4-0', False)]
    assert result['candidate_count'] == 1 and repo.get_memory('town', project['id'])['facts'] == []


def test_http_rejects_extra_actor_metadata_and_public_demo_uploads(upload_env):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient
    module = import_module('travaux.document_uploads')
    repo, queue, settings, _, actor, (project, _), _ = upload_env
    app = FastAPI()
    @app.exception_handler(DomainError)
    def denied(_, error): return JSONResponse({'error': {'code': error.code}}, status_code=403)
    module.register_document_upload_routes(app, repo, 'town', lambda: actor, settings, queue=queue, extractor=DemoExtractor())
    body = {'filename': 'note.txt', 'content_base64': base64.b64encode(b'plain').decode(), 'client_id': 'http'}
    with TestClient(app) as client:
        assert client.post('/api/v1/projects/'+project['id']+'/documents/upload', json={**body, 'actor_id': 'forged'}).status_code == 422
        assert client.post('/api/v1/projects/'+project['id']+'/documents/upload', json=body).status_code == 201
    public = module.DocumentUploadService(repo, SimpleNamespace(mode='public_demo'), queue=queue, extractor=DemoExtractor())
    with pytest.raises(DomainError): public.upload('town', actor, project['id'], **body)
