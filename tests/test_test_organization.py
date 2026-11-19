import sqlite3

import pytest

from travaux.config import Settings, ensure_public_demo_database


def config(tmp_path, **changes):
    return Settings(mode="staging", auth_mode="oidc", db_path=tmp_path / "test-org.sqlite3", tenant_id="test-org", public_origin="https://testserver", allowed_hosts=("testserver",), test_organization_self_join=True, **changes)


def test_self_join_requires_a_new_separate_marked_database(tmp_path):
    configured = config(tmp_path)
    connection = sqlite3.connect(configured.db_path)
    connection.execute("CREATE TABLE private_records(id TEXT)")
    connection.commit()
    connection.close()
    with pytest.raises(ValueError):
        ensure_public_demo_database(configured)


def test_fictional_self_join_database_can_never_be_reopened_as_private_data(tmp_path):
    configured = config(tmp_path)
    ensure_public_demo_database(configured)
    ensure_public_demo_database(configured)
    private = Settings(mode="staging", auth_mode="oidc", db_path=configured.db_path, tenant_id="test-org", public_origin="https://testserver", allowed_hosts=("testserver",))
    with pytest.raises(ValueError):
        ensure_public_demo_database(private)
