import json
import sys

import pytest
from cryptography.fernet import Fernet

from travaux.config import Settings
from travaux.connection_hub import SecretVault
from travaux.domain import DomainError
from travaux.repository import Repository


def test_first_administrator_can_be_approved_by_the_server_operator(tmp_path, monkeypatch, capsys):
    from travaux import cli
    for name, value in {"MODE": "staging", "AUTH_MODE": "oidc", "DB": str(tmp_path / "private.sqlite3"), "TENANT": "town-a", "PUBLIC_ORIGIN": "https://travaux.example", "ALLOWED_HOSTS": "travaux.example", "OIDC_ISSUER": "https://identity.example/realm/town"}.items():
        monkeypatch.setenv("TRAVAUX_"+name, value)
    monkeypatch.setattr(sys, "argv", ["travaux", "identity-member", "--subject", "test-subject", "--name", "Administrateur de recette", "--role", "admin"])
    cli._main()
    result = json.loads(capsys.readouterr().out)
    assert result["role"] == "admin" and result["active"] is True
    assert "password" not in result and "token" not in result


def test_ciphertext_rotation_is_atomic_and_requires_paused_writers(tmp_path, monkeypatch):
    from travaux.maintenance import rotate_connector_secrets
    configured = Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "private.sqlite3", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))
    old, new = Fernet.generate_key(), Fernet.generate_key()
    monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEY", old.decode())
    vault, repo = SecretVault(configured), Repository(configured.db_path)
    try:
        original = vault.encrypt({"refresh_token": "fictitious"})
        with repo._transaction() as db:
            db.execute("CREATE TABLE connector_connections(tenant_id TEXT,secret_ciphertext TEXT)")
            db.execute("INSERT INTO connector_connections VALUES(?,?)", (configured.tenant_id, original))
        monkeypatch.delenv("TRAVAUX_CONNECTOR_SECRET_KEY")
        monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEYS", new.decode()+","+old.decode())
        with pytest.raises(DomainError):
            rotate_connector_secrets(repo, configured, workers_paused=False)
        with repo._transaction() as db:
            db.execute("INSERT INTO connector_connections VALUES(?,?)", (configured.tenant_id, "corrupted"))
        with pytest.raises(DomainError):
            rotate_connector_secrets(repo, configured, workers_paused=True)
        assert repo._db.execute("SELECT secret_ciphertext FROM connector_connections LIMIT 1").fetchone()[0] == original
        with repo._transaction() as db:
            db.execute("DELETE FROM connector_connections WHERE secret_ciphertext='corrupted'")
        assert rotate_connector_secrets(repo, configured, workers_paused=True)["rotated"] == 1
        monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEYS", new.decode())
        updated = repo._db.execute("SELECT secret_ciphertext FROM connector_connections").fetchone()[0]
        assert vault.decrypt(updated) == {"refresh_token": "fictitious"}
    finally:
        repo.close()
