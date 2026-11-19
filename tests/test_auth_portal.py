"""The public entry pages expose capabilities, never application data or secrets."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from travaux.api import create_app
from travaux.config import Settings


@pytest.fixture
def portal(tmp_path):
    app = create_app(Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "portal.sqlite3", tenant_id="private", public_origin="https://testserver", allowed_hosts=("testserver",)))
    with TestClient(app, base_url="https://testserver") as client:
        yield app, client


def test_unconfigured_private_entry_is_explicit_and_does_not_grant_access(portal):
    _, client = portal
    response = client.get("/api/v1/auth/options")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"method": "oidc", "login_available": False, "signup_available": False, "recovery_available": False, "demo_available": False, "private_access_url": "", "label": "Connexion de la collectivité"}
    assert "set-cookie" not in response.headers
    assert client.get("/api/v1/projects").status_code == 401


def test_capabilities_reflect_server_oidc_service_not_client_parameters(portal):
    app, client = portal
    original = app.state.identity_login
    app.state.identity_login = SimpleNamespace(available=True, signup_available=True, recovery_available=False, close=lambda: None)
    try:
        options = client.get("/api/v1/auth/options?signup_available=true&recovery_available=true").json()
        assert options["login_available"] and options["signup_available"]
        assert options["recovery_available"] is False
        assert set(options) == {"method", "login_available", "signup_available", "recovery_available", "demo_available", "private_access_url", "label"}
    finally:
        app.state.identity_login = original


def test_public_demo_keeps_legacy_session_and_never_offers_real_account_creation(tmp_path):
    with TestClient(create_app(Settings(mode="public_demo", public_origin="https://testserver", allowed_hosts=("testserver",), db_path=tmp_path / "public.sqlite3")), base_url="https://testserver") as client:
        options = client.get("/api/v1/auth/options").json()
        assert options["method"] == "demo" and options["demo_available"]
        assert not any(options[key] for key in ("login_available", "signup_available", "recovery_available"))
        assert "auth" not in client.get("/api/v1/session").json()


def test_dedicated_html_entries_are_same_origin_csp_protected_and_not_cached(portal):
    _, client = portal
    for path in ("/connexion.html", "/inscription.html", "/mot-de-passe-oublie.html"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert '<html lang="fr">' in response.text
        assert 'name="referrer" content="no-referrer"' in response.text
    assert client.get("/demo.html").status_code == 200


def test_public_private_access_is_explicit_https_configuration_not_a_query_redirect(tmp_path):
    settings = Settings(db_path=tmp_path / "front-door.sqlite3", private_access_origin="https://espace.example.invalid")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/auth/options?private_access_url=https://bad.invalid").json()["private_access_url"] == "https://espace.example.invalid/connexion.html"
    for url in ("http://private.invalid", "https://user:password@private.invalid", "https://private.invalid?next=elsewhere", "https://private.invalid/path", "https://private.invalid#fragment"):
        with pytest.raises(ValueError):
            Settings(private_access_origin=url)
