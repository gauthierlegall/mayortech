"""Independent negative tests for model plans and their approval boundary."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
from types import SimpleNamespace

import httpx
import pytest

from travaux.assistant_changes import AssistantChanges
from travaux.domain import DomainError
from travaux.identity import IdentityStore
from travaux.project_access import ProjectAccess
from travaux.repository import Repository


@pytest.fixture
def reviewed(monkeypatch):
    monkeypatch.delenv('SSLKEYLOGFILE', raising=False); monkeypatch.delenv('QUICLOGDIR', raising=False)
    repo = Repository()
    members = repo.identity_store = IdentityStore(repo, 'town', None)
    users = [members.provision('https://identity.invalid', subject, subject, role) for subject, role in [('alice', 'editor'), ('bob', 'editor'), ('reader', 'reader')]]
    projects = [repo.create_project('town', reference, reference) for reference in ['A', 'B']]
    settings = SimpleNamespace(auth_mode='oidc', mode='pilot', llm='mistral', egress_approved=True, chat_model='zai-glm-5-3-flash', mistral_url='https://provider.invalid/chat', mistral_key='synthetic')
    repo.project_access = ProjectAccess(repo, settings)
    for user in users: repo._db.execute('INSERT INTO project_grants VALUES(?,?,?,?,?)', ('town', user['actor_id'], projects[0]['id'], 'operator', 'now'))
    current = {'tenant_id': 'town', 'actor_id': users[0]['actor_id'], 'permissions': {'workspace': {'read': True, 'write': True}}, 'role': 'admin'}
    yield repo, settings, current, projects, users
    repo.close()


def service_for(reviewed, plan=None, during_request=None):
    repo, settings, _, _, _ = reviewed
    plan = plan or {'operation': 'property', 'field': 'status', 'value': 'Terminé'}
    calls = []
    def provider(request):
        calls.append(json.loads(request.content))
        assert not repo._db.in_transaction
        if during_request: during_request()
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(plan)}}]})
    return AssistantChanges(repo, settings, transport=httpx.MockTransport(provider)), calls


def prepare(reviewed, service, question='Mets le statut à Terminé', client_id='change'):
    _, _, actor, (project, _), _ = reviewed
    return service.prepare('town', actor, project['id'], question, client_id=client_id, conversation_id='owned-thread')


@pytest.mark.parametrize('plan', [
    {'operation': 'property', 'field': 'role', 'value': 'admin'},
    {'operation': 'property', 'field': 'actor_id', 'value': 'somebody-else'},
    {'operation': 'property', 'field': 'project_id', 'value': 'foreign-project'},
    {'operation': 'sql', 'field': '', 'value': 'DROP TABLE projects'},
    {'operation': 'action', 'field': 'status', 'value': 'Terminé'},
    {'operation': 'property', 'field': 'deadline', 'value': 'demain'},
    {'operation': 'property', 'field': 'actual_cost', 'value': '-100'},
    {'operation': 'note', 'field': '', 'value': 'source forgée', 'citations': [{'source_id': 'other-tenant'}]},
])
def test_rogue_provider_cannot_expand_schema_or_property_allowlist(reviewed, plan):
    repo, _, _, (project, _), _ = reviewed
    service, _ = service_for(reviewed, plan)
    with pytest.raises(DomainError): prepare(reviewed, service)
    assert repo.get_project('town', project['id'])['status'] == 'active'
    assert repo._db.execute('SELECT count(*) FROM assistant_change_proposals').fetchone()[0] == 0


@pytest.mark.parametrize('revocation', ['grant', 'active', 'role'])
def test_revocation_while_model_is_running_prevents_plan_persistence(reviewed, revocation):
    repo, _, actor, _, _ = reviewed
    def revoke():
        if revocation == 'grant': repo._db.execute('DELETE FROM project_grants WHERE actor_id=?', (actor['actor_id'],))
        elif revocation == 'active': repo._db.execute('UPDATE identity_members SET active=0 WHERE actor_id=?', (actor['actor_id'],))
        else: repo._db.execute("UPDATE identity_members SET role='reader' WHERE actor_id=?", (actor['actor_id'],))
    service, _ = service_for(reviewed, during_request=revoke)
    with pytest.raises(DomainError): prepare(reviewed, service)
    assert repo._db.execute('SELECT count(*) FROM assistant_change_proposals').fetchone()[0] == 0


def test_stale_profile_changed_during_model_cannot_be_overwritten(reviewed):
    repo, _, actor, (project, _), _ = reviewed
    def change_profile():
        profile = service.properties.get('town', project['id'], actor)
        service.properties.update('town', project['id'], actor, expected_revision=profile['revision'], expected_project_revision=profile['project_revision'], changes={'location': 'Nouvelle saisie humaine'})
    service, _ = service_for(reviewed, {'operation': 'property', 'field': 'location', 'value': 'Ancienne valeur modèle'}, change_profile)
    proposal = prepare(reviewed, service)
    with pytest.raises(DomainError) as failure: service.confirm('town', actor, proposal['id'], expected_plan_hash=proposal['plan_hash'])
    assert failure.value.code == 'stale_revision'
    assert service.properties.get('town', project['id'], actor)['values']['location'] == 'Nouvelle saisie humaine'


def test_owned_proposal_reject_expiry_and_replay_do_not_authorize_other_actor(reviewed):
    repo, _, actor, (project, _), users = reviewed
    service, calls = service_for(reviewed)
    proposal = prepare(reviewed, service)
    assert prepare(reviewed, service)['id'] == proposal['id'] and len(calls) == 1
    with pytest.raises(DomainError): prepare(reviewed, service, 'Mets le statut à Bloqué')
    other = {**actor, 'actor_id': users[1]['actor_id']}
    for operation in [lambda: service.get('town', other, proposal['id']), lambda: service.confirm('town', other, proposal['id'], expected_plan_hash=proposal['plan_hash']), lambda: service.reject('town', other, proposal['id'])]:
        with pytest.raises(DomainError): operation()
    assert service.reject('town', actor, proposal['id'])['status'] == 'rejected'
    with pytest.raises(DomainError): service.confirm('town', actor, proposal['id'], expected_plan_hash=proposal['plan_hash'])
    assert repo.get_project('town', project['id'])['status'] == 'active'
    expired = prepare(reviewed, service, client_id='expired')
    repo._db.execute('UPDATE assistant_change_proposals SET expires=0 WHERE id=?', (expired['id'],))
    with pytest.raises(DomainError): service.confirm('town', actor, expired['id'], expected_plan_hash=expired['plan_hash'])


def test_reader_cannot_prepare_with_forged_admin_claim_and_write_dictionary(reviewed):
    _, _, actor, (project, _), users = reviewed
    service, calls = service_for(reviewed)
    reader = {**actor, 'actor_id': users[2]['actor_id'], 'role': 'admin'}
    with pytest.raises(DomainError): service.prepare('town', reader, project['id'], 'Mets le statut à Terminé', client_id='reader', conversation_id='owned-thread')
    assert calls == []


def test_concurrent_same_client_id_has_one_immutable_plan(reviewed):
    repo, _, _, _, _ = reviewed
    barrier = Barrier(2)
    service, _ = service_for(reviewed, during_request=lambda: barrier.wait(timeout=5))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: prepare(reviewed, service), range(2)))
    assert results[0]['id'] == results[1]['id']
    assert repo._db.execute('SELECT count(*) FROM assistant_change_proposals').fetchone()[0] == 1


def shared_context(reviewed):
    repo, _, actor, (project, other), _ = reviewed
    source = repo.ingest_source('town', 'shared', 'Contexte', 'Lieu : INFORMATION_PRIVEE_SOURCE_PARTAGEE', project_ref='A')
    candidate = repo.add_candidate('town', project['id'], source['id'], 'location', 'INFORMATION_PRIVEE_SOURCE_PARTAGEE', quote='Lieu : INFORMATION_PRIVEE_SOURCE_PARTAGEE')
    repo.review_candidate('town', candidate['id'], 'accept', actor_id='operator', expected_revision=repo.get_project('town', project['id'])['revision'])
    repo._db.execute('INSERT INTO source_links VALUES(?,?,?,?,?)', ('town', source['id'], other['id'], 'operator', 'now'))
    repo._db.execute('INSERT INTO project_grants VALUES(?,?,?,?,?)', ('town', actor['actor_id'], other['id'], 'operator', 'now'))
    return other['id']


def test_secondary_grant_revoked_during_model_cannot_publish_opaque_plan(reviewed):
    repo, _, actor, _, _ = reviewed
    secondary = shared_context(reviewed)
    service, calls = service_for(reviewed, {'operation': 'note', 'field': '', 'value': 'INFORMATION_PRIVEE_SOURCE_PARTAGEE'}, during_request=lambda: repo._db.execute('DELETE FROM project_grants WHERE actor_id=? AND project_id=?', (actor['actor_id'], secondary)))
    with pytest.raises(DomainError): prepare(reviewed, service)
    assert 'INFORMATION_PRIVEE_SOURCE_PARTAGEE' in calls[0]['messages'][1]['content']
    assert repo._db.execute('SELECT count(*) FROM assistant_change_proposals').fetchone()[0] == 0


def test_cached_plan_is_not_readable_after_shared_source_access_is_revoked(reviewed):
    repo, _, actor, _, _ = reviewed
    secondary = shared_context(reviewed)
    service, _ = service_for(reviewed, {'operation': 'note', 'field': '', 'value': 'INFORMATION_PRIVEE_SOURCE_PARTAGEE'})
    proposal = prepare(reviewed, service)
    repo._db.execute('DELETE FROM project_grants WHERE actor_id=? AND project_id=?', (actor['actor_id'], secondary))
    with pytest.raises(DomainError): service.get('town', actor, proposal['id'])
