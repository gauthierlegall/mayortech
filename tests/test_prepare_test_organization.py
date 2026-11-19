"""Operator preparation must never repurpose a protected database."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_test_organization.py"


def prepare(path, tenant="organization-test"):
    env = {**os.environ, "TRAVAUX_OIDC_EGRESS_APPROVED": "true", "TRAVAUX_OIDC_ISSUER": "https://must-never-be-contacted.invalid", "TRAVAUX_OIDC_CLIENT_ID": "fake", "TRAVAUX_OIDC_CLIENT_SECRET": "fictitious-do-not-print"}
    return subprocess.run([sys.executable, str(SCRIPT), "--database", str(path), "--tenant", tenant, "--public-origin", "https://testserver"], env=env, text=True, capture_output=True, timeout=30)


def test_prepares_marked_persistent_fixtures_without_secrets_or_implicit_members(tmp_path):
    target = tmp_path / "test-org/workspace.sqlite3"
    first = prepare(target)
    assert first.returncode == 0, first.stderr
    result = json.loads(first.stdout)
    assert result["organization"] == "Mairie test" and result["projects"] > 0
    assert result["accounts_created"] == 0 and result["server_started"] is False
    assert "fictitious-do-not-print" not in first.stdout + first.stderr
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT tenant_id FROM test_organization_metadata WHERE singleton=1").fetchone()[0] == "organization-test"
        assert db.execute("SELECT count(*) FROM identity_members").fetchone()[0] == 0
    second = prepare(target)
    assert second.returncode == 0 and json.loads(second.stdout)["projects"] == result["projects"]


def test_refuses_unmarked_existing_database_without_altering_its_data(tmp_path):
    target = tmp_path / "existing.sqlite3"
    with sqlite3.connect(target) as db:
        db.execute("CREATE TABLE protected(value TEXT)")
        db.execute("INSERT INTO protected VALUES('preserved')")
    result = prepare(target)
    assert result.returncode != 0
    assert "non marquée" in result.stderr
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT value FROM protected").fetchone()[0] == "preserved"
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("protected",)]


def test_refuses_reusing_a_marked_database_for_another_organization(tmp_path):
    target = tmp_path / "workspace.sqlite3"
    assert prepare(target).returncode == 0
    result = prepare(target, "other-organization")
    assert result.returncode != 0
    assert "marqueur" in result.stderr
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT tenant_id FROM test_organization_metadata").fetchone()[0] == "organization-test"
