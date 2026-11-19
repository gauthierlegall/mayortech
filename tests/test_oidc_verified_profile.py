"""Only verified signed identity contact data may label membership requests."""
import pytest

from test_oidc import ISSUER, begin, oidc as _oidc_fixture
from travaux.domain import DomainError

oidc = _oidc_fixture


def finish_profile(service, state, claims):
    object.__setattr__(service.configuration, 'required_amr', ('pwd', 'otp'))
    state['claims'] = {'sub': 'new-profile', 'name': 'Camille Exemple',
                       'email': 'camille@example.invalid', 'email_verified': True,
                       'amr': ['pwd', 'otp'], **claims}
    started, query = begin(service, state)
    return service.finish(state=query['state'][0], code='controlled-code',
                          binding=started['binding'], allow_onboarding=True)


def test_new_verified_contact_is_available_to_organization_review_without_grant(oidc):
    service, state, _, repo, sessions = oidc
    token = finish_profile(service, state, {'role': 'admin', 'realm_access': {'roles': ['admin']}})
    row = repo._db.execute("SELECT email,display_name,role,active FROM identity_members WHERE subject='new-profile'").fetchone()
    assert dict(row) == {'email': 'camille@example.invalid', 'display_name': 'Camille Exemple', 'role': 'reader', 'active': 0}
    assert sessions.resolve(token)['tenant_id'] == 'onboarding:town-a'


@pytest.mark.parametrize('claims', [{'amr': ['pwd']}, {'nonce': 'wrong-browser'}, {'iss': 'https://invalid.example'}])
def test_invalid_proof_never_provisions_the_contact(oidc, claims):
    service, state, _, repo, _ = oidc
    with pytest.raises(DomainError):
        finish_profile(service, state, claims)
    assert repo._db.execute("SELECT 1 FROM identity_members WHERE subject='new-profile'").fetchone() is None


def test_unverified_contact_is_not_copied_into_member_metadata(oidc):
    service, state, _, repo, _ = oidc
    finish_profile(service, state, {'email_verified': False})
    row = repo._db.execute("SELECT email,active FROM identity_members WHERE subject='new-profile'").fetchone()
    assert row['email'] == '' and row['active'] == 0


def test_existing_approved_identity_does_not_change_from_profile_claims(oidc):
    service, state, member, repo, sessions = oidc
    token = finish_profile(service, state, {'sub': 'agent-a', 'name': 'Different label', 'role': 'admin'})
    assert sessions.resolve(token) == {'actor_id': member['actor_id'], 'tenant_id': 'town-a'}
    saved = dict(repo._db.execute("SELECT * FROM identity_members WHERE tenant_id=? AND issuer=? AND subject=?", ('town-a', ISSUER, 'agent-a')).fetchone())
    assert saved['display_name'] == member['display_name'] and saved['role'] == 'editor'
    assert saved['active'] == 1 and saved['revision'] == member['revision'] and saved['email'] == member['email']
