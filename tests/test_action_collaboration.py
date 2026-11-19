from importlib import import_module
from types import SimpleNamespace

import pytest

from travaux.domain import DomainError
from travaux.identity import IdentityStore
from travaux.project_access import ProjectAccess
from travaux.repository import Repository
from travaux.workspace import WorkspaceRepository


@pytest.fixture
def collab():
    repo = Repository()
    members = repo.identity_store = IdentityStore(repo, 'town', None)
    alice = members.provision('https://id.invalid', 'alice', 'Alice', 'editor', email='private-alice@example.invalid')
    bob = members.provision('https://id.invalid', 'bob', 'Bob', 'reader', email='private-bob@example.invalid')
    admin = members.provision('https://id.invalid', 'admin', 'Admin', 'admin')
    other = members.provision('https://id.invalid', 'other', 'Other', 'editor')
    projects = [repo.create_project('town', name, name) for name in ('ALPHA', 'BETA')]
    settings = SimpleNamespace(auth_mode='oidc', auth_required=True, mode='pilot')
    repo.project_access = ProjectAccess(repo, settings)
    for member, project in [(alice, projects[0]), (bob, projects[0]), (other, projects[1])]:
        repo._db.execute('INSERT INTO project_grants VALUES(?,?,?,?,?)', ('town', member['actor_id'], project['id'], admin['actor_id'], 'now'))
    page = WorkspaceRepository(repo).ensure_main('town', projects[0]['id'])
    actor = {'tenant_id': 'town', 'actor_id': alice['actor_id'], 'permissions': {'workspace': {'read': True, 'write': True}}}
    service = import_module('travaux.action_collaboration').ActionCollaboration(repo, settings)
    yield repo, service, actor, projects, page, bob
    repo.close()


def test_participants_expose_only_active_authorized_identity_fields(collab):
    repo, service, actor, (project, _), _, bob = collab
    result = service.participants('town', actor, project['id'], limit=1, offset=0)
    assert result['total'] == 3 and len(result['items']) == 1
    assert set(result['items'][0]) == {'id', 'display_name', 'role'}
    assert result['items'][0]['display_name'] == 'Admin'
    repo._db.execute('UPDATE identity_members SET active=0 WHERE actor_id=?', (bob['actor_id'],))
    assert service.participants('town', actor, project['id'])['total'] == 2


def test_checklist_and_assignment_use_cas_and_never_store_an_action_title(collab):
    repo, service, actor, (project, _), page, bob = collab
    ref = {'page_id': page['id'], 'action_id': 'native-action'}
    state = service.get('town', actor, project['id'], **ref)
    assert state['revision'] == 0 and state['checklist'] == []
    changed = service.patch('town', actor, project['id'], **ref, expected_revision=0, changes={'assignee_id': bob['actor_id'], 'checklist': [{'id': 'step-1', 'text': 'Contrôler les accès', 'checked': False}]})
    assert changed['revision'] == 1 and changed['assignee']['display_name'] == 'Bob'
    with pytest.raises(DomainError): service.patch('town', actor, project['id'], **ref, expected_revision=0, changes={'checklist': []})
    with pytest.raises(DomainError): service.patch('town', actor, project['id'], **ref, expected_revision=1, changes={'title': 'Cannot duplicate the canonical action'})
    columns = {row[1] for row in repo._db.execute('PRAGMA table_info(action_collaboration)')}
    assert not columns.intersection({'title', 'status', 'start_date', 'due_date'})


def test_assignment_rejects_deactivated_or_ungranted_member(collab):
    repo, service, actor, (project, _), page, bob = collab
    repo._db.execute('DELETE FROM project_grants WHERE actor_id=?', (bob['actor_id'],))
    with pytest.raises(DomainError): service.patch('town', actor, project['id'], page_id=page['id'], action_id='action', expected_revision=0, changes={'assignee_id': bob['actor_id']})
    repo._db.execute('UPDATE identity_members SET active=0 WHERE actor_id=?', (bob['actor_id'],))
    with pytest.raises(DomainError): service.patch('town', actor, project['id'], page_id=page['id'], action_id='action', expected_revision=0, changes={'assignee_id': bob['actor_id']})


def test_comments_are_authoritative_idempotent_and_paginated(collab):
    _, service, actor, (project, _), page, _ = collab
    ref = {'page_id': page['id'], 'action_id': 'action'}
    first = service.add_comment('town', actor, project['id'], **ref, client_id='comment-one', body='Observation humaine')
    replay = service.add_comment('town', actor, project['id'], **ref, client_id='comment-one', body='Observation humaine')
    assert replay['id'] == first['id'] and first['author']['id'] == actor['actor_id']
    assert first['author']['display_name'] == 'Alice'
    with pytest.raises(DomainError): service.add_comment('town', actor, project['id'], **ref, client_id='comment-one', body='Changed replay')
    service.add_comment('town', actor, project['id'], **ref, client_id='comment-two', body='Deuxième commentaire')
    result = service.list_comments('town', actor, project['id'], **ref, limit=1, offset=1)
    assert result['total'] == 2 and len(result['items']) == 1
    assert result['items'][0]['body'] == 'Deuxième commentaire'


def test_collaboration_denies_cross_project_and_revoked_actor(collab):
    repo, service, actor, (project, other), page, _ = collab
    with pytest.raises(DomainError): service.get('town', actor, other['id'], page_id=page['id'], action_id='action')
    with pytest.raises(DomainError): service.get('other', actor, project['id'], page_id=page['id'], action_id='action')
    repo._db.execute('DELETE FROM project_grants WHERE actor_id=?', (actor['actor_id'],))
    with pytest.raises(DomainError): service.list_comments('town', actor, project['id'], page_id=page['id'], action_id='action')


def test_checklist_limits_and_booleans_are_strict(collab):
    _, service, actor, (project, _), page, _ = collab
    for checklist in [[{'id': 'one', 'text': 'Check', 'checked': 'false'}], [{'id': str(number), 'text': 'Check', 'checked': False} for number in range(101)]]:
        with pytest.raises(DomainError): service.patch('town', actor, project['id'], page_id=page['id'], action_id='action', expected_revision=0, changes={'checklist': checklist})
    with pytest.raises(DomainError): service.add_comment('town', actor, project['id'], page_id=page['id'], action_id='action', client_id='long', body='x'*4001)


def rule_values(**changes):
    return {'unit': 'month', 'interval': 1, 'anchor_start': '2026-01-31', 'span_days': 2, 'month_end': False, 'active': True, **changes}


def save_rule(collab, **changes):
    _, service, actor, (project, _), page, _ = collab
    return service.set_rule('town', actor, project['id'], page_id=page['id'], action_id='template-action', expected_revision=0, rule=rule_values(**changes))


def test_recurrence_month_end_uses_original_anchor_without_clamp_drift(collab):
    _, service, actor, (project, _), _, _ = collab
    rule = save_rule(collab)
    first = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)
    second = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=2, expected_rule_revision=1)
    assert first['plan'] == {'startDate': '2026-02-28', 'dueDate': '2026-03-02'}
    assert second['plan'] == {'startDate': '2026-03-31', 'dueDate': '2026-04-02'}
    assert first['source_key'] == 'recurrence:'+first['operation_id']


@pytest.mark.parametrize(('values', 'expected'), [
    ({'unit': 'week', 'interval': 2, 'anchor_start': '2026-03-22', 'span_days': 0}, '2026-04-05'),
    ({'unit': 'year', 'anchor_start': '2024-02-29', 'span_days': 0}, '2025-02-28'),
    ({'unit': 'month', 'anchor_start': '2026-02-28', 'month_end': True, 'span_days': 0}, '2026-03-31'),
])
def test_recurrence_week_leap_year_and_explicit_month_end_are_civil_dates(collab, values, expected):
    _, service, actor, (project, _), _, _ = collab
    rule = save_rule(collab, **values)
    operation = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)
    assert operation['plan']['startDate'] == expected and operation['plan']['dueDate'] == expected


def test_prepare_replays_after_interruption_and_rule_cas_preserves_existing_plans(collab):
    _, service, actor, (project, _), page, _ = collab
    rule = save_rule(collab)
    first = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)
    replay = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)
    assert replay == first
    with pytest.raises(DomainError): service.set_rule('town', actor, project['id'], page_id=page['id'], action_id='template-action', expected_revision=0, rule=rule_values(interval=2))
    changed = service.set_rule('town', actor, project['id'], page_id=page['id'], action_id='template-action', expected_revision=1, rule=rule_values(interval=2))
    assert changed['revision'] == 2
    replay = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=2)
    assert replay == first
    assert service.list_occurrences('town', actor, project['id'], rule_id=rule['id'], limit=1)['total'] == 1


def test_confirmation_requires_saved_page_and_is_an_immutable_client_receipt(collab):
    import base64
    repo, service, actor, (project, _), page, _ = collab
    rule = save_rule(collab)
    operation = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)
    with pytest.raises(DomainError): service.confirm_occurrence('town', actor, project['id'], operation['operation_id'], page_id=page['id'], row_id='new-action', page_revision_hash='0'*64)
    saved = WorkspaceRepository(repo).save('town', page['id'], base64.b64encode(b'\x00\x00').decode(), None, 'Native state receipt', 'blocksuite-0.22.4', actor['actor_id'])
    args = {'page_id': page['id'], 'row_id': 'new-action', 'page_revision_hash': saved['revision_hash']}
    confirmed = service.confirm_occurrence('town', actor, project['id'], operation['operation_id'], **args)
    assert confirmed['phase'] == 'confirmed' and confirmed['confirmation']['verification'] == 'client_receipt_for_saved_page'
    assert service.confirm_occurrence('town', actor, project['id'], operation['operation_id'], **args) == confirmed
    with pytest.raises(DomainError): service.confirm_occurrence('town', actor, project['id'], operation['operation_id'], **{**args, 'row_id': 'different-action'})
    another = service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=2, expected_rule_revision=1)
    with pytest.raises(DomainError): service.confirm_occurrence('town', actor, project['id'], another['operation_id'], **args)
    with pytest.raises(DomainError): service.confirm_occurrence('town', actor, project['id'], another['operation_id'], **{**args, 'row_id': 'template-action'})


def test_disabled_rule_does_not_prepare_new_occurrences(collab):
    _, service, actor, (project, _), _, _ = collab
    rule = save_rule(collab, active=False)
    with pytest.raises(DomainError): service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)


@pytest.mark.parametrize('changes', [{'unit': []}, {'interval': True}, {'anchor_start': '2026-02-30'}, {'span_days': True}, {'active': 1}, {'unit': 'week', 'month_end': True}])
def test_recurrence_rejects_unstructured_or_invalid_calendar_input(collab, changes):
    with pytest.raises(DomainError): save_rule(collab, **changes)


def test_concurrent_checklist_cas_keeps_one_winner(collab):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    _, service, actor, (project, _), page, _ = collab
    barrier = Barrier(2)
    def change(text):
        barrier.wait(timeout=5)
        try:
            return service.patch('town', actor, project['id'], page_id=page['id'], action_id='concurrent', expected_revision=0, changes={'checklist': [{'id': 'one', 'text': text, 'checked': False}]})['revision']
        except DomainError as error: return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(change, ['Version A', 'Version B']))
    assert sorted(map(str, results)) == ['1', 'stale_revision']


def test_concurrent_prepare_keeps_one_operation_id(collab):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    _, service, actor, (project, _), _, _ = collab
    rule, barrier = save_rule(collab), Barrier(2)
    def prepare(_):
        barrier.wait(timeout=5)
        return service.prepare_occurrence('town', actor, project['id'], rule_id=rule['id'], ordinal=1, expected_rule_revision=1)['operation_id']
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(prepare, range(2)))
    assert results[0] == results[1]
    assert service.list_occurrences('town', actor, project['id'], rule_id=rule['id'])['total'] == 1


def test_revocation_is_checked_inside_the_comment_transaction(collab, monkeypatch):
    from contextlib import contextmanager
    repo, service, actor, (project, _), page, _ = collab
    original = repo._transaction
    @contextmanager
    def revoke():
        with original() as db:
            db.execute('DELETE FROM project_grants WHERE actor_id=?', (actor['actor_id'],))
            yield db
    monkeypatch.setattr(repo, '_transaction', revoke)
    with pytest.raises(DomainError): service.add_comment('town', actor, project['id'], page_id=page['id'], action_id='action', client_id='revoked', body='Must not persist')
    assert repo._db.execute('SELECT count(*) FROM action_comments').fetchone()[0] == 0


def test_demo_exposes_only_the_current_fictional_actor():
    from travaux.action_collaboration import ActionCollaboration
    repo = Repository()
    try:
        project = repo.create_project('demo', 'DEMO', 'Fictional')
        settings = SimpleNamespace(auth_mode='password', auth_required=False, mode='public_demo')
        actor = {'tenant_id': 'demo', 'actor_id': 'responsable-demo', 'permissions': {'workspace': {'read': True, 'write': True}}}
        service = ActionCollaboration(repo, settings)
        assert service.participants('demo', actor, project['id'])['items'] == [{'id': 'responsable-demo', 'display_name': 'Visiteur de démonstration', 'role': 'visitor'}]
    finally: repo.close()


def test_http_comment_author_cannot_be_supplied_and_unknown_state_fields_are_rejected(collab):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from fastapi.testclient import TestClient
    from travaux.action_collaboration import register_action_collaboration_routes
    repo, _, actor, (project, _), page, _ = collab
    app = FastAPI()
    @app.exception_handler(DomainError)
    def error(_, failure): return JSONResponse({'error': {'code': failure.code}}, status_code=409)
    register_action_collaboration_routes(app, repo, 'town', lambda: actor, SimpleNamespace(auth_mode='oidc', auth_required=True, mode='pilot'))
    base = '/api/v1/projects/'+project['id']+'/action-collaboration'
    with TestClient(app) as client:
        forged = {'page_id': page['id'], 'action_id': 'action', 'client_id': 'http-comment', 'body': 'Comment', 'author_id': 'somebody-else'}
        assert client.post(base+'/comments', json=forged).status_code == 422
        del forged['author_id']
        saved = client.post(base+'/comments', json=forged)
        assert saved.status_code == 201 and saved.json()['author']['id'] == actor['actor_id']
        assert client.get(base+'/participants').json()['total'] == 3
        assert 'private-alice@example.invalid' not in client.get(base+'/participants').text
        assert client.patch(base, json={'page_id': page['id'], 'action_id': 'action', 'expected_revision': 0, 'changes': {'status': 'Terminé'}}).status_code == 409
