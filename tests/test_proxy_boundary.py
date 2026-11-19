"""Forwarded addresses are honored only from an explicit inspected proxy peer."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from travaux.config import Settings


def echo_client(peer, forwarded, trusted):
    app = FastAPI()

    @app.get("/")
    def client_address(request: Request):
        return {"client": request.client.host}

    with TestClient(ProxyHeadersMiddleware(app, trusted_hosts=list(trusted)), client=(peer, 12345)) as client:
        return client.get("/", headers={"X-Forwarded-For": forwarded}).json()["client"]


def test_configuration_defaults_to_no_forwarded_address_trust(monkeypatch):
    monkeypatch.delenv("TRAVAUX_TRUSTED_PROXY_IPS", raising=False)
    assert Settings().trusted_proxy_ips == ()
    monkeypatch.setenv("TRAVAUX_TRUSTED_PROXY_IPS", "192.0.2.10,2001:db8::10")
    assert Settings.from_env().trusted_proxy_ips == ("192.0.2.10", "2001:db8::10")


@pytest.mark.parametrize("peer", ["*", "0.0.0.0/0", "192.0.2.0/24", "proxy.example", "192.0.2.10\n", ""])
def test_wildcard_subnet_hostname_and_control_characters_are_not_proxy_grants(peer):
    with pytest.raises(ValueError):
        Settings(trusted_proxy_ips=(peer,))


def test_a_direct_caller_cannot_forge_its_address_with_forwarded_headers():
    assert echo_client("198.51.100.1", "203.0.113.99", ("192.0.2.10",)) == "198.51.100.1"
    assert echo_client("192.0.2.10", "203.0.113.99", ()) == "192.0.2.10"


def test_an_explicitly_trusted_proxy_preserves_distinct_visitors_for_rate_limits():
    for visitor in ("203.0.113.1", "203.0.113.2"):
        assert echo_client("192.0.2.10", visitor, ("192.0.2.10",)) == visitor
    # Even a chain does not trust a caller-supplied leftmost identity beyond the
    # nearest untrusted hop. The Caddy contract replaces the header altogether.
    assert echo_client("192.0.2.10", "203.0.113.99, 198.51.100.5", ("192.0.2.10",)) == "198.51.100.5"


@pytest.mark.parametrize("trusted", [(), ("192.0.2.10",)])
def test_serve_passes_only_the_explicit_peer_allowlist_to_the_real_server_entry(monkeypatch, trusted):
    from travaux import cli
    import travaux.api
    import uvicorn
    application = object()
    calls = []
    monkeypatch.setattr(cli.Settings, "from_env", lambda: Settings(trusted_proxy_ips=trusted))
    monkeypatch.setattr(cli, "ensure_public_demo_database", lambda settings: None)
    monkeypatch.setattr(travaux.api, "create_app", lambda settings: application)
    monkeypatch.setattr(uvicorn, "run", lambda app, **options: calls.append((app, options)))
    monkeypatch.setattr("sys.argv", ["travaux", "serve"])
    cli._main()
    assert len(calls) == 1 and calls[0][0] is application
    assert calls[0][1]["proxy_headers"] is bool(trusted)
    assert calls[0][1]["forwarded_allow_ips"] == list(trusted)
