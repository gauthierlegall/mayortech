"""The real Keycloak 26 client must emit the claims required by the backend."""

import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[3]


def test_initial_realm_keeps_native_basic_scope_for_signed_auth_time():
    template = json.loads((ROOT / "deploy/keycloak/realm-test.example.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(
        "private_candidate_scope_contract", ROOT / "deploy/private-site/candidate.py"
    )
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    client = candidate.realm(template, "synthetic-client-secret", "synthetic-smtp-secret")["clients"][0]
    assert {"basic", "profile", "email"}.issubset(client["defaultClientScopes"])
    assert not any(
        mapper.get("protocolMapper") == "oidc-hardcoded-claim-mapper" for mapper in client["protocolMappers"]
    )


def test_initial_realm_uses_the_verified_alternative_implicit_tls_endpoint():
    template = json.loads((ROOT / "deploy/keycloak/realm-test.example.json").read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location(
        "private_candidate_smtp_contract", ROOT / "deploy/private-site/candidate.py"
    )
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    smtp = candidate.realm(template, "synthetic-client-secret", "synthetic-smtp-secret")["smtpServer"]
    assert smtp["host"] == "smtp.resend.com" and smtp["port"] == "2465"
    assert smtp["ssl"] == "true" and smtp["starttls"] == "false" and smtp["debug"] == "false"
