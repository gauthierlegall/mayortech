"""Independent review regressions; no external identity provider is called."""
import pytest

from test_oidc import oidc as _oidc_fixture
from travaux.domain import DomainError

oidc = _oidc_fixture


def test_oidc_network_refuses_tls_key_logging_before_any_provider_request(oidc, monkeypatch):
    service, state, _, _, _ = oidc
    monkeypatch.setenv("SSLKEYLOGFILE", "synthetic-review-path")
    with pytest.raises(DomainError):
        service.start()
    assert state["calls"] == []


def test_oidc_accepts_an_exact_https_issuer_with_a_trailing_slash():
    from travaux.oidc import OIDCConfiguration
    config = OIDCConfiguration(issuer="https://identity.example/", client_id="client-a", client_secret="test-only", allowed_hosts=("identity.example",), required_acr=("institution:mfa",))
    assert config.issuer == "https://identity.example/"
