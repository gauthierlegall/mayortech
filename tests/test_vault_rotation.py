"""Professional keys are supplied separately and rotate without losing tokens."""
import pytest
from cryptography.fernet import Fernet

from travaux.config import Settings
from travaux.connection_hub import SecretVault
from travaux.domain import DomainError


def private(tmp_path):
    return Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "data/store.sqlite3", public_origin="https://travaux.example", allowed_hosts=("travaux.example",))


def test_oidc_vault_never_generates_a_key_beside_the_database(tmp_path, monkeypatch):
    for variable in ("TRAVAUX_CONNECTOR_SECRET_KEY", "TRAVAUX_CONNECTOR_SECRET_KEYS", "TRAVAUX_CONNECTOR_KEY_FILE"):
        monkeypatch.delenv(variable, raising=False)
    configured = private(tmp_path)
    with pytest.raises(DomainError):
        SecretVault(configured).encrypt({"refresh_token": "only-fake"})
    assert not (configured.db_path.parent / ".connector-vault.key").exists()


def test_rotation_reads_old_ciphertexts_but_writes_only_with_new_key(tmp_path, monkeypatch):
    old, new = Fernet.generate_key(), Fernet.generate_key()
    monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEY", old.decode())
    vault = SecretVault(private(tmp_path))
    original = vault.encrypt({"refresh_token": "only-fake"})
    monkeypatch.delenv("TRAVAUX_CONNECTOR_SECRET_KEY")
    monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEYS", ",".join([new.decode(), old.decode()]))
    assert vault.decrypt(original)["refresh_token"] == "only-fake"
    rotated = vault.rotate(original)
    assert Fernet(new).decrypt(rotated.encode())
    monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEYS", new.decode())
    assert vault.decrypt(rotated)["refresh_token"] == "only-fake"
    with pytest.raises(DomainError):
        vault.decrypt(original)


def test_external_key_file_is_read_only_and_cannot_be_in_the_data_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("TRAVAUX_CONNECTOR_SECRET_KEY", raising=False)
    monkeypatch.delenv("TRAVAUX_CONNECTOR_SECRET_KEYS", raising=False)
    configured = private(tmp_path)
    configured.db_path.parent.mkdir()
    bad = configured.db_path.parent / "bad.key"
    bad.write_bytes(Fernet.generate_key())
    monkeypatch.setenv("TRAVAUX_CONNECTOR_KEY_FILE", str(bad))
    with pytest.raises(DomainError):
        SecretVault(configured).encrypt({"refresh_token": "only-fake"})
    good = tmp_path / "separate-key.key"
    good.write_bytes(Fernet.generate_key())
    monkeypatch.setenv("TRAVAUX_CONNECTOR_KEY_FILE", str(good))
    vault = SecretVault(configured)
    assert vault.decrypt(vault.encrypt({"a": 1})) == {"a": 1}
