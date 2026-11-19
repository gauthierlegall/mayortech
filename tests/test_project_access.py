from importlib import import_module
from importlib.util import find_spec
from types import SimpleNamespace

import pytest

from travaux.domain import DomainError
from travaux.repository import Repository


def test_access_module_is_available():
    assert find_spec('travaux.project_access') is not None, 'The dossier access boundary is missing'


@pytest.fixture
def access():
    repo = Repository()
    repo._db.execute('''CREATE TABLE identity_members(tenant_id TEXT,actor_id TEXT,issuer TEXT,subject TEXT,email TEXT,display_name TEXT,role TEXT,active INTEGER,revision INTEGER,PRIMARY KEY(tenant_id,actor_id))''')
    for tenant, actor, role in [('town', 'alice', 'editor'), ('town', 'bob', 'reader'), ('town', 'admin', 'admin'), ('other', 'alice', 'admin')]:
        repo._db.execute('INSERT INTO identity_members VALUES(?,?,?,?,?,?,?,?,?)', (tenant, actor, 'https://id.invalid', actor, actor+'@example.invalid', actor, role, 1, 1))
    projects = [repo.create_project('town', ref, ref) for ref in ('ALPHA', 'BETA')]
    service = import_module('travaux.project_access').ProjectAccess(repo, SimpleNamespace(auth_mode='oidc'))
    repo.project_access = service
    repo._db.execute("INSERT INTO project_grants(tenant_id,actor_id,project_id,granted_by,created_at) VALUES('town','alice',?,'admin','now')", (projects[0]['id'],))
    repo._db.execute("INSERT INTO project_grants(tenant_id,actor_id,project_id,granted_by,created_at) VALUES('town','bob',?,'admin','now')", (projects[1]['id'],))
    yield repo, service, projects
    repo.close()


def actor(name='alice', **claims):
    return {'tenant_id': 'town', 'actor_id': name, **claims}


def test_active_database_member_and_grant_are_authority(access):
    repo, service, (alpha, beta) = access
    scope = service.scope(actor(role='admin', email='admin@example.invalid', permissions={'workspace': {'write': True}}))
    assert scope.visible_project_ids == (alpha['id'],)
    scope.require_project(alpha['id'], write=True)
    with pytest.raises(DomainError): scope.require_project(beta['id'])
    assert set(service.scope(actor('admin')).visible_project_ids) == {alpha['id'], beta['id']}
    with pytest.raises(DomainError): service.scope(actor('missing')).require_project(alpha['id'])
    with pytest.raises(DomainError): service.scope(actor('bob')).require_project(beta['id'], write=True)
    repo._db.execute("UPDATE identity_members SET active=0 WHERE tenant_id='town' AND actor_id='alice'")
    with pytest.raises(DomainError): scope.require_project(alpha['id'])


def test_source_requires_every_link_and_no_link_requires_admin(access):
    repo, service, (alpha, beta) = access
    source = repo.ingest_source('town', 'shared', 'Shared', 'SECRET-BETA', project_ref='ALPHA')
    scope = service.scope(actor())
    scope.require_source(source['id'])
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', source['id'], beta['id'], 'admin', 'now'))
    with pytest.raises(DomainError): scope.require_source(source['id'])
    unknown = repo.ingest_source('town', 'unknown', 'Unassigned', 'private')
    with pytest.raises(DomainError): scope.require_source(unknown['id'])
    service.scope(actor('admin')).require_source(unknown['id'])


def test_sql_predicates_apply_before_count_and_limit_and_revoke_immediately(access):
    repo, service, (alpha, beta) = access
    scope = service.scope(actor())
    where, args = scope.project_clause('p.id')
    assert repo._db.execute('SELECT count(*) FROM projects p WHERE '+where, args).fetchone()[0] == 1
    source = repo.ingest_source('town', 'alpha', 'Alpha', 'visible', project_ref='ALPHA')
    repo.ingest_source('town', 'beta', 'Beta', 'invisible', project_ref='BETA')
    where, args = scope.source_clause('s.id')
    assert [row[0] for row in repo._db.execute('SELECT s.id FROM sources s WHERE '+where+' LIMIT 1', args)] == [source['id']]
    repo._db.execute("DELETE FROM project_grants WHERE tenant_id='town' AND actor_id='alice'")
    assert scope.visible_project_ids == ()
    where, args = scope.source_clause('s.id')
    assert repo._db.execute('SELECT count(*) FROM sources s WHERE '+where, args).fetchone()[0] == 0


def test_retrieval_never_indexes_an_ungranted_project(access):
    from travaux.retrieval import DossierRetrieval
    repo, _, (alpha, beta) = access
    repo.ingest_source('town', 'visible', 'Alpha', 'marker-public travaux', project_ref='ALPHA')
    repo.ingest_source('town', 'private', 'Beta', 'marker-secret travaux', project_ref='BETA')
    settings = SimpleNamespace(mode='pilot', llm='demo')
    result = DossierRetrieval(repo, settings).search('town', 'travaux', actor=actor())
    assert set(result['project_revisions']) == {alpha['id']}
    assert all(item['project_id'] == alpha['id'] for item in result['items'])
    with pytest.raises(DomainError): DossierRetrieval(repo, settings).search('town', 'secret', project_id=beta['id'], actor=actor())


def test_revoked_project_hides_stored_conversation_and_replay(access):
    from travaux.conversations import ConversationService
    repo, _, (alpha, _) = access
    current = actor(permissions={'workspace': {'read': True, 'write': True}})
    service = ConversationService(repo, SimpleNamespace(mode='pilot', llm='demo'))
    thread = service.create('town', current, 'private:alice', project_id=alpha['id'])
    repo._db.execute("DELETE FROM project_grants WHERE tenant_id='town' AND actor_id='alice'")
    assert service.list('town', current, 'private:alice') == []
    with pytest.raises(DomainError): service.get('town', current, 'private:alice', thread['id'])


def test_mailbox_counts_and_direct_reads_respect_grants(access):
    from travaux.mailbox import MailboxRepository
    repo, _, _ = access
    repo.ingest_source('town', 'mail-a', 'Alpha', 'visible', project_ref='ALPHA')
    secret = repo.ingest_source('town', 'mail-b', 'Beta', 'secret', project_ref='BETA')
    mailbox = MailboxRepository(repo)
    result = mailbox.list_messages('town', 'alice', limit=1)
    assert result['total'] == 1 and result['items'][0]['subject'] == 'Alpha'
    assert mailbox.folders('town', 'alice')[0]['total'] == 1
    with pytest.raises(DomainError): mailbox.get_message('town', 'alice', secret['id'])


def test_original_documents_reject_ungranted_id_before_returning_bytes(access):
    from travaux.documents import DocumentRepository
    repo, _, (_, beta) = access
    source = repo.ingest_source('town', 'pdf-b', 'Beta', 'secret', project_ref='BETA')
    documents = DocumentRepository(repo)
    document = documents.store('town', source['id'], b'secret bytes', 'piece.pdf', 'application/pdf')
    with pytest.raises(DomainError): documents.download('town', document['id'], actor=actor())
    with pytest.raises(DomainError): documents.list_project('town', beta['id'], actor=actor())


def test_field_report_list_count_and_direct_read_respect_grants(access):
    from travaux.field_reports import FieldReportService
    repo, _, (alpha, beta) = access
    service = FieldReportService(repo)
    admin = actor('admin', permissions={'workspace': {'read': True, 'write': True}})
    records = [service.create('town', admin, {'client_id': 'client-'+project['reference'], 'project_id': project['id'], 'kind': 'Visite', 'date': '2026-11-17', 'title': project['name'], 'detail': 'Private observation', 'author': 'Operator'}) for project in (alpha, beta)]
    current = actor(permissions={'workspace': {'read': True, 'write': True}})
    result = service.list('town', current)
    assert result['total'] == 1 and result['items'][0]['id'] == records[0]['id']
    with pytest.raises(DomainError): service.get('town', records[1]['id'], current)


def test_revocation_removes_stored_notifications_and_unread_count(access):
    from travaux.notifications import NotificationService
    repo, _, (alpha, beta) = access
    service = NotificationService(repo, SimpleNamespace())
    current = actor(permissions={'workspace': {'read': True}})
    with repo._transaction() as db:
        for project in (alpha, beta): service._enqueue(db, 'town', 'alice', 'private:alice', project['id'], project['id'], None, 'pending', project['name'], 'private')
    result = service.list('town', current, 'private:alice', refresh=False)
    assert result['unread'] == 1 and [item['project_id'] for item in result['items']] == [alpha['id']]
    repo._db.execute("DELETE FROM project_grants WHERE tenant_id='town' AND actor_id='alice'")
    assert service.list('town', current, 'private:alice', refresh=False)['items'] == []


def test_calendar_events_collections_and_export_exclude_ungranted_and_unassigned(access):
    from travaux.calendars import CalendarService
    repo, _, (alpha, beta) = access
    service = CalendarService(repo, SimpleNamespace(tenant_id='town'), hub=SimpleNamespace(_actor=lambda value: None))
    with repo._transaction() as db:
        for project in (alpha, beta):
            calendar = 'cal-'+project['reference']
            db.execute('INSERT INTO calendar_collections VALUES(?,?,?,?,?,?,?)', (calendar, 'town', None, project['name'], calendar, 'ics', 'now'))
            value = {'remote_uid': calendar, 'recurrence_id': '', 'title': project['name'], 'start': '2026-11-17', 'end': '2026-11-18', 'all_day': True, 'timezone': 'Europe/Paris', 'status': 'confirmed', 'description': 'private', 'source_url': ''}
            service._store(db, 'town', calendar, [value], 'admin', project_id=project['id'])
        service._store(db, 'town', 'cal-ALPHA', [{**value, 'remote_uid': 'unassigned', 'title': 'UNASSIGNED'}], 'admin')
    current = actor(permissions={'workspace': {'read': True}})
    result = service.events(current, start='2026-11-16', end='2026-11-19')
    assert result['total'] == 1 and result['items'][0]['title'] == 'ALPHA'
    assert service.collections(current)['total'] == 1
    assert b'BETA' not in service.export(current, start='2026-11-16', end='2026-11-19')
    hidden = repo._db.execute("SELECT id FROM calendar_events WHERE project_id IS NULL").fetchone()[0]
    with pytest.raises(DomainError): service.event(current, hidden)


def test_provider_payload_is_scoped_before_any_model_call(access):
    import json
    import httpx
    from travaux.assistant_dossier import DossierAssistant
    from travaux.retrieval import DossierRetrieval
    repo, _, _ = access
    repo.ingest_source('town', 'public', 'Alpha', 'travaux marker-public', project_ref='ALPHA')
    repo.ingest_source('town', 'secret', 'Beta', 'travaux marker-secret', project_ref='BETA')
    observed = []
    def provider(request):
        observed.append(json.loads(request.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"passages":[]}'}}]})
    settings = SimpleNamespace(mode='pilot', llm='mistral', egress_approved=True, mistral_url='https://llm.invalid/chat', mistral_model='test', chat_model='test', mistral_key='synthetic')
    assistant = DossierAssistant(repo, settings, transport=httpx.MockTransport(provider))
    answer = DossierRetrieval(repo, settings, assistant=assistant).answer('town', 'travaux', actor=actor())
    assert len(observed) == 1
    assert 'marker-public' in json.dumps(observed) and 'marker-secret' not in json.dumps(observed)
    assert 'marker-secret' not in json.dumps(answer)


def test_global_conversation_historical_reply_cannot_replay_after_revocation(access):
    from travaux.conversations import ConversationService
    repo, _, (alpha, _) = access
    repo.ingest_source('town', 'past', 'Alpha', 'travaux remembered-secret', project_ref='ALPHA')
    current = actor(permissions={'workspace': {'read': True, 'write': True}})
    service = ConversationService(repo, SimpleNamespace(mode='pilot', llm='demo'))
    thread = service.create('town', current, 'private:alice')
    result = service.send('town', current, 'private:alice', thread['id'], 'travaux', 'message-1')
    assert 'remembered-secret' in result['messages'][1]['content']
    repo._db.execute("DELETE FROM project_grants WHERE tenant_id='town' AND actor_id='alice'")
    assert service.list('town', current, 'private:alice') == []
    with pytest.raises(DomainError): service.send('town', current, 'private:alice', thread['id'], 'travaux', 'message-1')


def test_notification_refresh_never_enqueues_an_ungranted_project(access):
    from travaux.notifications import NotificationService
    repo, _, (alpha, beta) = access
    for project in (alpha, beta):
        source = repo.ingest_source('town', 'pending-'+project['id'], project['name'], 'Retard annoncé', project_ref=project['reference'])
        repo.add_candidate('town', project['id'], source['id'], 'progress', 'Retard', quote='Retard annoncé')
    service = NotificationService(repo, SimpleNamespace())
    current = actor(permissions={'workspace': {'read': True}})
    result = service.list('town', current, 'private:alice')
    assert result['unread'] == 1 and result['items'][0]['project_id'] == alpha['id']
    assert repo._db.execute("SELECT count(*) FROM user_notifications WHERE project_id=?", (beta['id'],)).fetchone()[0] == 0


def test_summary_and_native_page_require_access_to_shared_source_content(access):
    from travaux.workspace import WorkspaceRepository
    repo, service, (alpha, beta) = access
    source = repo.ingest_source('town', 'shared-summary', 'Alpha', 'shared secret', project_ref='ALPHA')
    summary = repo.create_summary('town', alpha['id'], actor_id='admin')
    page = WorkspaceRepository(repo).ensure_main('town', alpha['id'])
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', source['id'], beta['id'], 'admin', 'now'))
    scope = service.scope(actor())
    with pytest.raises(DomainError): scope.require_object('summary', summary['id'])
    with pytest.raises(DomainError): scope.require_object('page', page['id'])


def test_non_oidc_modes_keep_legacy_service_behavior():
    from travaux.project_access import ProjectAccess
    repo = Repository()
    try:
        scope = ProjectAccess(repo, SimpleNamespace(auth_mode='password')).scope(None)
        assert scope.all_projects and not scope.restricted
        assert scope.project_clause('project_id') == ('1=1', [])
    finally: repo.close()


def test_review_candidate_shared_source_is_denied_and_client_claims_cannot_write(access):
    repo, service, (alpha, beta) = access
    source = repo.ingest_source('town', 'candidate-shared', 'Alpha', 'annonce', project_ref='ALPHA')
    candidate = repo.add_candidate('town', alpha['id'], source['id'], 'progress', 'Travaux', quote='annonce')
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', source['id'], beta['id'], 'admin', 'now'))
    with pytest.raises(DomainError): service.scope(actor(role='admin')).require_object('candidate', candidate['id'])


def test_stored_notification_with_now_forbidden_shared_source_is_hidden(access):
    from travaux.notifications import NotificationService
    repo, _, (alpha, beta) = access
    source = repo.ingest_source('town', 'notify-shared', 'Alpha', 'annonce', project_ref='ALPHA')
    candidate = repo.add_candidate('town', alpha['id'], source['id'], 'progress', 'Travaux', quote='annonce')
    service = NotificationService(repo, SimpleNamespace())
    with repo._transaction() as db:
        service._enqueue(db, 'town', 'alice', 'private:alice', 'candidate', alpha['id'], candidate['id'], 'pending', 'Secret', 'annonce')
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', source['id'], beta['id'], 'admin', 'now'))
    current = actor(permissions={'workspace': {'read': True}})
    assert service.list('town', current, 'private:alice', refresh=False)['items'] == []


def test_oidc_governance_filters_audit_before_totals_and_exposes_real_capabilities(access):
    from travaux.identity import IdentityStore
    from travaux.governance import GovernanceService
    repo, _, (alpha, beta) = access
    repo.identity_store = IdentityStore(repo, 'town', None)
    service = GovernanceService(repo, 'town', SimpleNamespace(mode='pilot', auth_mode='oidc', fixture_mode=False))
    with repo._transaction() as db:
        repo._audit(db, 'town', alpha['id'], 'visible', 'alice', 'a', {})
        repo._audit(db, 'town', beta['id'], 'hidden', 'bob', 'b', {})
    result = service.audit(actor(), limit=1)
    assert result['total'] == 1 and result['items'][0]['action'] == 'visible'
    assert result['items'][0]['actor_label'] == 'alice'
    capabilities = service.roles(actor('admin'))
    assert capabilities['capabilities'] == {'identity_provider': True, 'member_management': True, 'invitations': False}
    assert all(item['assignable'] for item in capabilities['items'])
    assert not any(item['assignable'] for item in service.roles(actor())['items'])


def test_oidc_audit_excludes_shared_source_rows_before_count(access):
    from travaux.identity import IdentityStore
    from travaux.governance import GovernanceService
    repo, _, (alpha, beta) = access
    repo.identity_store = IdentityStore(repo, 'town', None)
    source = repo.ingest_source('town', 'audit-secret', 'SECRET-AUDIT', 'secret', project_ref='ALPHA')
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', source['id'], beta['id'], 'admin', 'now'))
    with repo._transaction() as db:
        repo._audit(db, 'town', alpha['id'], 'private.proof', 'admin', source['id'], {'source_id': source['id']})
    service = GovernanceService(repo, 'town', SimpleNamespace(mode='pilot', auth_mode='oidc', fixture_mode=False))
    result = service.audit(actor())
    assert result['total'] == 0 and result['items'] == []


def test_object_write_guard_uses_database_role_even_for_documents(access):
    from travaux.documents import DocumentRepository
    repo, service, _ = access
    source = repo.ingest_source('town', 'reader-document', 'Beta', 'secret', project_ref='BETA')
    document = DocumentRepository(repo).store('town', source['id'], b'private', 'piece.pdf', 'application/pdf')
    with pytest.raises(DomainError): service.scope(actor('bob', role='admin')).require_object('document', document['id'], write=True)


def test_field_report_write_rechecks_grant_inside_the_mutation_transaction(access, monkeypatch):
    from contextlib import contextmanager
    from travaux.field_reports import FieldReportService
    repo, _, (alpha, _) = access
    service = FieldReportService(repo)
    current = actor(permissions={'workspace': {'read': True, 'write': True}})
    record = service.create('town', current, {'client_id': 'transaction-report', 'project_id': alpha['id'], 'kind': 'Visite', 'date': '2026-11-17', 'title': 'Observation', 'detail': 'Initial', 'author': 'Alice'})
    original = repo._transaction
    @contextmanager
    def revoke_then_begin():
        with original() as db:
            db.execute("DELETE FROM project_grants WHERE tenant_id='town' AND actor_id='alice'")
            yield db
    monkeypatch.setattr(repo, '_transaction', revoke_then_begin)
    with pytest.raises(DomainError): service.update('town', record['id'], current, expected_revision=record['revision'], status='Levée')
