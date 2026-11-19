"""Explicit offline maintenance of tenant-bound connector ciphertexts."""
import time

from .connection_hub import SecretVault
from .domain import DomainError


def rotate_connector_secrets(repo, settings, *, workers_paused=False):
    if workers_paused is not True or not settings.auth_required:
        raise DomainError("forbidden", "Arrêtez les services qui écrivent les secrets avant leur rotation.")
    vault = SecretVault(settings)
    # Fixed table/column names only. No caller-supplied SQL identifier.
    targets = [("connector_connections", "secret_ciphertext"), ("identity_flows", "secret_ciphertext"), ("mail_oauth_flows", "secret_ciphertext"), ("cloud_mail_checkpoints", "cursor_ciphertext")]
    rotated = 0
    with repo._transaction() as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "mail_oauth_refresh_leases" in tables and db.execute("SELECT 1 FROM mail_oauth_refresh_leases WHERE tenant_id=? AND expires>? LIMIT 1", (settings.tenant_id, time.time())).fetchone():
            raise DomainError("invalid_state", "Un renouvellement de connexion est encore en cours. Attendez avant de réessayer.")
        for table, column in targets:
            if table not in tables:
                continue
            rows = db.execute(f"SELECT rowid AS vault_row,{column} AS sealed FROM {table} WHERE tenant_id=? AND {column}<>''", (settings.tenant_id,)).fetchall()
            for row in rows:
                sealed = vault.rotate(row["sealed"])
                db.execute(f"UPDATE {table} SET {column}=? WHERE rowid=? AND tenant_id=?", (sealed, row["vault_row"], settings.tenant_id))
                rotated += 1
    return {"rotated": rotated, "tenant_scoped": True, "atomic": True}
