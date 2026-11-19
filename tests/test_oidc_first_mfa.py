"""An enrolled factor is not a signed MFA proof; require a fresh verified login."""
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_oidc import oidc as _oidc_fixture
from travaux.domain import DomainError
from travaux.oidc import register_identity_routes

oidc = _oidc_fixture


def prepare(service, state, claims):
    service.configuration = replace(service.configuration, required_amr=("pwd", "otp"))
    started = service.start()
    query = parse_qs(urlsplit(started["authorization_url"]).query)
    state["nonce"] = query["nonce"][0]
    state["claims"] = claims
    return started, query


def test_signed_first_enrollment_requests_reauthentication_without_a_session(oidc):
    service, state, _, repo, _ = oidc
    started, query = prepare(service, state, {"amr": ["pwd"], "email_verified": True})
    with pytest.raises(DomainError) as rejected:
        service.finish(state=query["state"][0], code="synthetic-first-code", binding=started["binding"], allow_onboarding=True)
    assert rejected.value.code == "identity_mfa_required"
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
    assert repo._db.execute("SELECT consumed FROM identity_flows").fetchone()[0] == 1
    with pytest.raises(DomainError) as replay:
        service.finish(state=query["state"][0], code="synthetic-first-code", binding=started["binding"])
    assert replay.value.code == "unauthenticated"


@pytest.mark.parametrize("invalid", [{"nonce": "wrong"}, {"iss": "https://wrong.example"}, {"auth_time": 0}, {"aud": "wrong-client"}])
def test_invalid_identity_never_receives_the_successful_enrollment_marker(oidc, invalid):
    service, state, _, repo, _ = oidc
    started, query = prepare(service, state, {"amr": ["pwd"], "email_verified": True, **invalid})
    with pytest.raises(DomainError) as rejected:
        service.finish(state=query["state"][0], code="synthetic-code", binding=started["binding"])
    assert rejected.value.code == "unauthenticated"
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_only_the_second_complete_signed_mfa_flow_can_issue_a_session(oidc):
    service, state, _, repo, sessions = oidc
    first, query = prepare(service, state, {"amr": ["pwd"], "email_verified": True})
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="first-code", binding=first["binding"])
    second, query = prepare(service, state, {"amr": ["pwd", "otp"], "email_verified": True})
    assert "prompt=login" in second["authorization_url"]
    token = service.finish(state=query["state"][0], code="second-code", binding=second["binding"])
    assert sessions.resolve(token)["tenant_id"] == "town-a"
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1


def test_http_first_enrollment_redirects_to_an_explicit_step_without_session_cookie(oidc):
    original, state, _, repo, sessions = oidc
    app = FastAPI()
    service = register_identity_routes(app, repo, original.settings, sessions, original.members)
    service.configuration = replace(original.configuration, required_amr=("pwd", "otp"))
    service.policy, service.http, service.owns_http = original.policy, original.http, False
    with TestClient(app, base_url="https://travaux.example") as client:
        started = client.post("/api/v1/auth/start", json={"intent": "login"})
        query = parse_qs(urlsplit(started.json()["authorization_url"]).query)
        state["nonce"] = query["nonce"][0]
        state["claims"] = {"amr": ["pwd"], "email_verified": True}
        response = client.get("/api/v1/auth/callback", params={"state": query["state"][0], "code": "synthetic-code"}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/connexion.html?auth=reauthenticate"
        assert "travaux_session=" not in response.headers.get("set-cookie", "")
        assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
