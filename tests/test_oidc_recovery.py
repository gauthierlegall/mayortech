"""Recovery stays inside the same signed, MFA-validated OIDC code flow."""
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest

from test_oidc import oidc as _oidc_fixture
from travaux.domain import DomainError

oidc = _oidc_fixture


def test_recovery_requires_explicit_configuration_without_network_or_state(oidc):
    service, state, _, repo, _ = oidc
    assert getattr(service, "recovery_available", False) is False
    with pytest.raises(DomainError):
        service.start(intent="recovery")
    assert state["calls"] == []
    assert repo._db.execute("SELECT count(*) FROM identity_flows").fetchone()[0] == 0


def test_recovery_authorization_retains_pkce_nonce_and_never_stores_email_hint(oidc):
    service, state, _, repo, sessions = oidc
    reset = "https://identity.example/realm/town/protocol/openid-connect/forgot-credentials"
    service.configuration = replace(service.configuration, reset_url=reset)
    assert service.recovery_available is True
    response = service.start(intent="recovery", login_hint="person@example.invalid")
    assert urlsplit(response["authorization_url"]).path.endswith("/protocol/openid-connect/forgot-credentials")
    query = parse_qs(urlsplit(response["authorization_url"]).query)
    assert query["login_hint"] == ["person@example.invalid"]
    assert query["code_challenge_method"] == ["S256"] and query["nonce"] and query["state"]
    envelope = repo._db.execute("SELECT secret_ciphertext FROM identity_flows").fetchone()[0]
    assert service.vault.decrypt(envelope).keys() == {"nonce", "verifier", "intent"}
    state["nonce"] = query["nonce"][0]
    token = service.finish(state=query["state"][0], code="fake-recovery-code", binding=response["binding"])
    assert sessions.resolve(token)["tenant_id"] == "town-a"
    assert "person@example.invalid" not in str([tuple(row) for row in repo._db.execute("SELECT * FROM identity_flows")])


@pytest.mark.parametrize("target", ["http://identity.example/reset", "https://evil.example/reset", "https://identity.example:444/reset", "https://user:password@identity.example/reset", "https://identity.example/reset?redirect=elsewhere", "https://identity.example/reset#fragment"])
def test_recovery_url_must_be_an_explicit_allowed_https_endpoint(oidc, target):
    service, _, _, _, _ = oidc
    with pytest.raises(ValueError):
        replace(service.configuration, reset_url=target)


def test_reset_change_invalidates_pending_flow_configuration(oidc):
    service, state, _, repo, _ = oidc
    service.configuration = replace(service.configuration, reset_url="https://identity.example/forgot-credentials")
    response = service.start(intent="recovery")
    query = parse_qs(urlsplit(response["authorization_url"]).query)
    state["nonce"] = query["nonce"][0]
    service.configuration = replace(service.configuration, reset_url="https://identity.example/new-forgot-credentials")
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


@pytest.mark.parametrize("hint", ["not-an-email", "person@example.invalid\r\nInjected: value", "person@example.invalid\x00", "<script>@example.invalid", "space person@example.invalid", "person@localhost", "x" * 250 + "@example.invalid", 123, None])
def test_login_hint_rejects_injection_or_invalid_input_before_network(oidc, hint):
    service, state, _, repo, _ = oidc
    with pytest.raises(DomainError):
        service.start(login_hint=hint)
    assert state["calls"] == []
    assert repo._db.execute("SELECT count(*) FROM identity_flows").fetchone()[0] == 0


def test_login_hint_is_optional_and_env_reset_is_loaded_without_network(oidc, monkeypatch):
    service, state, _, _, _ = oidc
    started = service.start(login_hint="")
    assert "login_hint" not in parse_qs(urlsplit(started["authorization_url"]).query)
    monkeypatch.setenv("TRAVAUX_OIDC_EGRESS_APPROVED", "true")
    monkeypatch.setenv("TRAVAUX_OIDC_ISSUER", service.configuration.issuer)
    monkeypatch.setenv("TRAVAUX_OIDC_CLIENT_ID", "fake-client")
    monkeypatch.setenv("TRAVAUX_OIDC_CLIENT_SECRET", "fake-client-secret")
    monkeypatch.setenv("TRAVAUX_OIDC_ALLOWED_HOSTS", "identity.example")
    monkeypatch.setenv("TRAVAUX_OIDC_REQUIRED_AMR", "pwd,otp")
    monkeypatch.setenv("TRAVAUX_OIDC_RESET_URL", "https://identity.example/forgot-credentials")
    config = type(service.configuration).from_env(service.settings)
    assert config.reset_url == "https://identity.example/forgot-credentials"
    assert len(state["calls"]) == 1


def test_recovery_callback_still_rejects_a_password_only_identity(oidc):
    service, state, _, repo, _ = oidc
    service.configuration = replace(service.configuration, reset_url="https://identity.example/forgot-credentials")
    response = service.start(intent="recovery")
    query = parse_qs(urlsplit(response["authorization_url"]).query)
    state["nonce"] = query["nonce"][0]
    state["claims"] = {"acr": "password-only"}
    with pytest.raises(DomainError):
        service.finish(state=query["state"][0], code="fake-code", binding=response["binding"])
    assert repo._db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_recovery_http_controller_uses_only_fixed_html_callback_destination(oidc):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from travaux.oidc import register_identity_routes
    original, state, _, repo, sessions = oidc
    app = FastAPI()
    service = register_identity_routes(app, repo, original.settings, sessions, original.members)
    service.configuration = replace(original.configuration, reset_url="https://identity.example/forgot-credentials")
    service.policy, service.http, service.owns_http = original.policy, original.http, False
    with TestClient(app, base_url="https://travaux.example") as client:
        start = client.post("/api/v1/auth/start", json={"intent": "recovery", "login_hint": "person@example.invalid"})
        assert start.status_code == 200
        query = parse_qs(urlsplit(start.json()["authorization_url"]).query)
        state["nonce"] = query["nonce"][0]
        result = client.get("/api/v1/auth/callback", params={"state": query["state"][0], "code": "fake-code", "next": "https://evil.example"}, follow_redirects=False)
        assert result.status_code == 303 and result.headers["location"] == "/connexion.html?auth=connected"
        assert "SameSite=strict" in result.headers["set-cookie"] and "Secure" in result.headers["set-cookie"]
        failed = client.get("/api/v1/auth/callback", params={"state": "invalid", "code": "fake-code", "next": "https://evil.example"}, follow_redirects=False)
        assert failed.headers["location"] == "/connexion.html?auth=failed"
