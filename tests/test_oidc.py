"""Real signed ID tokens exchanged against a deterministic HTTP provider."""
import hashlib
import json
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from joserfc import jwt
from joserfc.jwk import RSAKey

from travaux.auth import SessionStore
from travaux.config import Settings
from travaux.domain import DomainError
from travaux.identity import IdentityStore
from travaux.repository import Repository

ISSUER = "https://identity.example/realm/town"


@pytest.fixture
def oidc(tmp_path, monkeypatch):
    monkeypatch.delenv("SSLKEYLOGFILE", raising=False)
    monkeypatch.delenv("QUICLOGDIR", raising=False)
    monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEY", Fernet.generate_key().decode())
    from travaux.oidc import OIDCConfiguration, OIDCService
    settings = Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "oidc.sqlite3", tenant_id="town-a", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
    repo, sessions = Repository(settings.db_path), SessionStore(settings.db_path)
    members = IdentityStore(repo, settings.tenant_id, sessions)
    member = members.provision(ISSUER, "agent-a", "Agent A", "editor")
    key = RSAKey.generate_key(2048, parameters={"kid": "test-key"})
    state = {"claims": {}, "calls": [], "nonce": None, "status": 200, "token": None}

    def transport(request):
        state["calls"].append((request.method, request.url.path))
        if request.url.path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json={"issuer": ISSUER, "authorization_endpoint": ISSUER + "/authorize", "token_endpoint": ISSUER + "/token", "jwks_uri": ISSUER + "/keys", "response_types_supported": ["code"]})
        if request.url.path.endswith("/keys"):
            return httpx.Response(200, json={"keys": [key.as_dict(private=False)]})
        if request.url.path.endswith("/token"):
            body = parse_qs(request.content.decode())
            state["verifier"] = body.get("code_verifier", [""])[0]
            assert body["redirect_uri"] == ["https://travaux.example/api/v1/auth/callback"]
            now = int(time.time())
            claims = {"iss": ISSUER, "sub": "agent-a", "aud": "client-a", "nonce": state["nonce"], "iat": now, "exp": now + 300, "auth_time": now, "acr": "town:phishing-resistant", **state["claims"]}
            token = state["token"] or jwt.encode({"alg": "RS256", "kid": "test-key"}, claims, key)
            return httpx.Response(state["status"], json={"id_token": token, "access_token": "not-stored", "token_type": "Bearer"})
        raise AssertionError("Unexpected endpoint")

    http = httpx.Client(transport=httpx.MockTransport(transport), follow_redirects=False)
    config = OIDCConfiguration(issuer=ISSUER, client_id="client-a", client_secret="only-fake-secret", allowed_hosts=("identity.example",), required_acr=("town:phishing-resistant",))
    service = OIDCService(repo, settings, sessions, members, configuration=config, http=http)
    yield service, state, member, repo, sessions
    http.close()
    repo.close()


def begin(service, state):
    response = service.start()
    query = parse_qs(urlsplit(response["authorization_url"]).query)
    state["nonce"] = query["nonce"][0]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["openid profile email"]
    assert query["redirect_uri"] == ["https://travaux.example/api/v1/auth/callback"]
    return response, query


def test_pkce_signed_identity_creates_only_individual_session(oidc):
    service, state, member, repo, sessions = oidc
    response, query = begin(service, state)
    token = service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])
    assert sessions.resolve(token) == {"actor_id": member["actor_id"], "tenant_id": "town-a"}
    import base64
    assert query["code_challenge"][0] == base64.urlsafe_b64encode(hashlib.sha256(state["verifier"].encode()).digest()).rstrip(b"=").decode()
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])
    assert sum(path.endswith("/token") for _, path in state["calls"]) == 1
    assert "not-stored" not in json.dumps([tuple(row) for row in repo._db.execute("SELECT * FROM identity_flows")])


def test_login_requests_fresh_identity_instead_of_silently_reusing_another_account(oidc):
    service, state, _, _, _ = oidc
    _, query = begin(service, state)
    assert query["prompt"] == ["login"]


@pytest.mark.parametrize("claims", [
    {"iss": "https://other.example"}, {"aud": "other-client"}, {"nonce": "wrong"},
    {"exp": 1}, {"iat": 4102444800}, {"auth_time": 1}, {"acr": "password-only"},
    {"aud": ["client-a", "other"], "azp": "other"}, {"sub": "unknown"},
])
def test_invalid_or_unapproved_claims_never_issue_session(oidc, claims):
    service, state, _, repo, _ = oidc
    response, query = begin(service, state)
    state["claims"] = claims
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_wrong_browser_and_expired_flow_do_not_exchange_a_code(oidc):
    service, state, _, repo, _ = oidc
    response, query = begin(service, state)
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding="different-browser")
    assert not any(path.endswith("/token") for _, path in state["calls"])
    with repo._transaction() as db:
        db.execute("UPDATE identity_flows SET expires=0")
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])


def test_invalid_signature_and_unsigned_tokens_are_rejected(oidc):
    service, state, _, repo, _ = oidc
    response, query = begin(service, state)
    other = RSAKey.generate_key(2048, parameters={"kid": "test-key"})
    now = int(time.time())
    state["token"] = jwt.encode({"alg": "RS256", "kid": "test-key"}, {"iss": ISSUER, "sub": "agent-a", "aud": "client-a", "nonce": state["nonce"], "iat": now, "exp": now+300}, other)
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_configuration_requires_https_issuer_and_an_explicit_mfa_policy():
    from travaux.oidc import OIDCConfiguration
    with pytest.raises(ValueError):
        OIDCConfiguration(issuer="http://identity.example", client_id="a", client_secret="b", allowed_hosts=("identity.example",), required_acr=("mfa",))
    with pytest.raises(ValueError):
        OIDCConfiguration(issuer=ISSUER, client_id="a", client_secret="b", allowed_hosts=("identity.example",))
