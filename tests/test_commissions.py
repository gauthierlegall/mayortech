"""Unit and integration tests for municipal permanent commissions and authorization."""
from types import SimpleNamespace
import pytest

from travaux.domain import DomainError
from travaux.commissions import (
    CommissionRepository,
    COMMISSION_1_ID,
    COMMISSION_3_ID,
    COMMISSION_4_ID,
)
from travaux.project_access import ProjectAccess
from travaux.repository import Repository


@pytest.fixture
def comm_fixture():
    repo = Repository()
    repo._db.execute(
        """CREATE TABLE identity_members(
        tenant_id TEXT, actor_id TEXT, issuer TEXT, subject TEXT, email TEXT,
        display_name TEXT, role TEXT, active INTEGER, revision INTEGER,
        created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '',
        PRIMARY KEY(tenant_id, actor_id))"""
    )
    repo._db.execute(
        """CREATE TABLE identity_audit(
        id TEXT PRIMARY KEY, tenant_id TEXT, actor_id TEXT, member_id TEXT,
        action TEXT, changes TEXT, created_at TEXT)"""
    )
    # Provision members in town tenant and another tenant
    members = [
        ("town", "alice", "editor"),  # Culture editor & Finances reader
        ("town", "bob", "reader"),    # Reader only
        ("town", "admin", "admin"),   # Org admin
        ("other", "charlie", "editor") # Member of another organisation
    ]
    for tenant, actor, role in members:
        repo._db.execute(
            "INSERT INTO identity_members VALUES(?,?,?,?,?,?,?,?,?,'','')",
            (tenant, actor, "https://id.invalid", actor, f"{actor}@{tenant}.invalid", actor.title(), role, 1, 1),
        )

    comm_repo = CommissionRepository(repo)
    comm_repo.ensure_default_commissions("town")
    comm_repo.ensure_default_commissions("other")

    # Create dossiers
    p_travaux = repo.create_project(
        "town", "TRV-001", "Chantier voirie", commission_id=COMMISSION_3_ID, specialization="travaux"
    )
    p_culture = repo.create_project(
        "town", "CLT-001", "Fête des associations", commission_id=COMMISSION_4_ID, specialization="evenements"
    )
    p_finances = repo.create_project(
        "town", "FIN-001", "Budget prévisionnel", commission_id=COMMISSION_1_ID, specialization="finances"
    )
    p_culture_restricted = repo.create_project(
        "town", "CLT-CONF", "Projet culturel restreint", commission_id=COMMISSION_4_ID, visibility="restricted"
    )
    p_other = repo.create_project(
        "other", "OTH-001", "Projet autre ville", commission_id=COMMISSION_3_ID
    )

    access_service = ProjectAccess(repo, SimpleNamespace(auth_mode="oidc"))
    repo.project_access = access_service

    yield repo, comm_repo, access_service, {
        "travaux": p_travaux,
        "culture": p_culture,
        "finances": p_finances,
        "restricted": p_culture_restricted,
        "other": p_other,
    }
    repo.close()


def actor(name="alice", tenant="town", **claims):
    return {"tenant_id": tenant, "actor_id": name, **claims}


def test_four_permanent_commissions_initialized(comm_fixture):
    repo, comm_repo, _, _ = comm_fixture
    comms = comm_repo.list_commissions("town")
    assert len(comms) == 4
    codes = [c["code"] for c in comms]
    assert codes == ["finances", "enfance-jeunesse", "urbanisme-travaux", "culture-vie-associative"]


def test_migration_and_backfill_is_idempotent(comm_fixture):
    repo, comm_repo, _, projects = comm_fixture
    # Run backfill twice on the same tenant
    res1 = comm_repo.backfill_tenant("town")
    res2 = comm_repo.backfill_tenant("town")
    assert res1["commissions_count"] == 4
    assert res2["commissions_count"] == 4
    assert res1["total_projects"] >= 4
    assert res2["total_projects"] == res1["total_projects"]
    assert res2["updated_projects"] == 0  # Second run changes 0 rows


def test_multi_role_culture_and_finances(comm_fixture):
    repo, comm_repo, access_service, projects = comm_fixture
    # Assign Alice: editor in Culture (comm-4), reader in Finances (comm-1)
    comm_repo.set_member_commission_role("town", COMMISSION_4_ID, "alice", "editor", updated_by="admin")
    comm_repo.set_member_commission_role("town", COMMISSION_1_ID, "alice", "reader", updated_by="admin")

    scope = access_service.scope(actor("alice"))

    # Culture dossier: Alice can read and write
    assert scope.permits_project(projects["culture"]["id"]) is True
    assert scope.permits_project(projects["culture"]["id"], write=True) is True
    caps_culture = scope.project_capabilities(projects["culture"]["id"])
    assert caps_culture["can_read"] is True
    assert caps_culture["can_edit"] is True
    assert caps_culture["can_submit_for_review"] is True

    # Finances dossier: Alice can read but NOT write
    assert scope.permits_project(projects["finances"]["id"]) is True
    assert scope.permits_project(projects["finances"]["id"], write=True) is False
    caps_finances = scope.project_capabilities(projects["finances"]["id"])
    assert caps_finances["can_read"] is True
    assert caps_finances["can_edit"] is False
    assert caps_finances["can_submit_for_review"] is False

    with pytest.raises(DomainError):
        scope.require_project(projects["finances"]["id"], write=True)


def test_restricted_dossier_requires_explicit_grant(comm_fixture):
    repo, comm_repo, access_service, projects = comm_fixture
    # Alice is editor in Culture
    comm_repo.set_member_commission_role("town", COMMISSION_4_ID, "alice", "editor", updated_by="admin")
    scope = access_service.scope(actor("alice"))

    # Restricted dossier in Culture: NOT visible even though Alice is editor in Culture
    assert scope.permits_project(projects["restricted"]["id"]) is False
    with pytest.raises(DomainError):
        scope.require_project(projects["restricted"]["id"])

    # Grant explicit access to Alice
    repo._db.execute(
        "INSERT INTO project_grants VALUES(?,?,?,?,?)",
        ("town", "alice", projects["restricted"]["id"], "admin", "now"),
    )

    # Now accessible!
    scope_after = access_service.scope(actor("alice"))
    assert scope_after.permits_project(projects["restricted"]["id"]) is True
    assert scope_after.permits_project(projects["restricted"]["id"], write=True) is True


def test_cross_tenant_isolation(comm_fixture):
    repo, comm_repo, access_service, projects = comm_fixture
    comm_repo.set_member_commission_role("town", COMMISSION_4_ID, "alice", "editor", updated_by="admin")
    comm_repo.set_member_commission_role("other", COMMISSION_3_ID, "charlie", "editor", updated_by="charlie")

    scope_alice = access_service.scope(actor("alice", tenant="town"))
    scope_charlie = access_service.scope(actor("charlie", tenant="other"))

    # Alice cannot see other tenant's projects
    assert scope_alice.permits_project(projects["other"]["id"]) is False
    # Charlie cannot see town tenant's projects
    assert scope_charlie.permits_project(projects["culture"]["id"]) is False


def test_immediate_revocation(comm_fixture):
    repo, comm_repo, access_service, projects = comm_fixture
    comm_repo.set_member_commission_role("town", COMMISSION_4_ID, "alice", "editor", updated_by="admin")
    scope = access_service.scope(actor("alice"))
    assert scope.permits_project(projects["culture"]["id"]) is True

    # Revoke Alice from organisation
    repo._db.execute("UPDATE identity_members SET active=0 WHERE tenant_id='town' AND actor_id='alice'")

    # Existing scope immediately denies access
    assert scope.permits_project(projects["culture"]["id"]) is False
    with pytest.raises(DomainError):
        scope.require_project(projects["culture"]["id"])


def test_commission_role_optimistic_locking(comm_fixture):
    repo, comm_repo, _, _ = comm_fixture
    # First assignment revision = 1
    res1 = comm_repo.set_member_commission_role("town", COMMISSION_4_ID, "alice", "reader", updated_by="admin")
    assert res1["revision"] == 1

    # Stale revision update rejected
    with pytest.raises(DomainError) as exc_info:
        comm_repo.set_member_commission_role(
            "town", COMMISSION_4_ID, "alice", "editor", updated_by="admin", expected_revision=0
        )
    assert exc_info.value.code == "stale_revision"

    # Matching revision succeeds
    res2 = comm_repo.set_member_commission_role(
        "town", COMMISSION_4_ID, "alice", "editor", updated_by="admin", expected_revision=1
    )
    assert res2["revision"] == 2
