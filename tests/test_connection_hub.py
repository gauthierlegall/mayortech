import json
from dataclasses import replace

import pytest

from travaux.config import Settings
from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.connection_hub import ConnectionHub, IntegrationPolicy, SecretVault


def settings(tmp_path, mode="staging"):
    if mode == "demo":
        return Settings(db_path=tmp_path / "connections.sqlite3")
    return Settings(
        mode=mode,
        db_path=tmp_path / "connections.sqlite3",
        tenant_id="commune",
        password_hash="scrypt$x$x",
        public_origin="https://travaux.example.org",
        allowed_hosts=("travaux.example.org",),
    )


ADMIN = {
    "actor_id": "operator",
    "tenant_id": "commune",
    "permissions": {"organization": {"write": True}, "workspace": {"read": True, "write": True}},
}


class FakeReader:
    probes = 0

    def __init__(self, profile, secrets, policy):
        assert secrets["password"] == "secret-not-in-db"

    def probe(self):
        type(self).probes += 1
        return {"calendars": [{"id": "calendar-a", "name": "Service travaux"}], "mail_folders": []}

    def calendar_events(self, selected, start, end):
        assert selected == ["calendar-a"]
        return {
            "calendar-a": [
                {
                    "remote_uid": "event1",
                    "recurrence_id": "",
                    "title": "Visite du portail",
                    "start": "2026-11-20T09:00:00+01:00",
                    "end": "2026-11-20T10:00:00+01:00",
                    "all_day": False,
                    "timezone": "Europe/Paris",
                    "status": "confirmed",
                    "description": "Visite annoncée",
                    "source_url": "",
                }
            ]
        }

    def close(self):
        pass


def make_hub(tmp_path):
    cfg = settings(tmp_path)
    repo = Repository(cfg.db_path)
    policy = IntegrationPolicy(egress_approved=True, allowed_hosts=("cal.example.org",))
    return ConnectionHub(repo, cfg, policy=policy, reader_factory=FakeReader), repo


@pytest.mark.parametrize("test_profile", [True, False])
@pytest.mark.parametrize("admin", [True, False])
def test_status_exposes_explicit_test_organization_boolean_without_granting_access(tmp_path, test_profile, admin):
    hub, _ = make_hub(tmp_path)
    hub.settings = replace(hub.settings, auth_mode="oidc", test_organization_self_join=test_profile)
    actor = ADMIN if admin else {"actor_id":"reader","tenant_id":"commune","permissions":{"organization":{"write":False}}}
    result = hub.status(actor)
    assert result["test_organization"] is test_profile
    assert result["can_manage"] is admin
    assert result["external_connections_enabled"] is (admin and not test_profile)
    if not admin:
        assert result["connections"] == []


def test_secret_vault_never_stores_plaintext_and_refuses_changed_key(tmp_path, monkeypatch):
    cfg = settings(tmp_path)
    vault = SecretVault(cfg)
    encrypted = vault.encrypt({"password": "secret-not-in-db"})
    assert "secret-not-in-db" not in encrypted
    assert vault.decrypt(encrypted) == {"password": "secret-not-in-db"}
    assert (tmp_path / ".connector-vault.key").is_file()
    monkeypatch.setenv("TRAVAUX_CONNECTOR_SECRET_KEY", "a" * 44)
    with pytest.raises(DomainError):
        SecretVault(cfg).decrypt(encrypted)


def test_profile_probe_selection_and_secret_redaction(tmp_path):
    hub, repo = make_hub(tmp_path)
    saved = hub.create(
        ADMIN,
        {
            "provider": "caldav",
            "label": "Agenda travaux",
            "endpoint": "https://cal.example.org/dav",
            "username": "agent",
            "password": "secret-not-in-db",
        },
    )
    assert saved["status"] == "not_tested" and saved["has_secret"]
    assert "secret-not-in-db" not in json.dumps(saved)
    assert (
        "secret-not-in-db"
        not in bytes(
            repo._db.execute("SELECT secret_ciphertext FROM connector_connections").fetchone()[0], "utf8"
        ).decode()
    )
    probed = hub.probe(ADMIN, saved["id"], expected_revision=saved["revision"])
    assert probed["status"] == "verified"
    assert probed["calendars"][0]["id"] == "calendar-a"
    selected = hub.select(
        ADMIN, saved["id"], calendar_ids=["calendar-a"], folder_ids=[], expected_revision=probed["revision"]
    )
    assert selected["selected_calendar_ids"] == ["calendar-a"]
    with pytest.raises(DomainError):
        hub.select(
            ADMIN,
            saved["id"],
            calendar_ids=["invented"],
            folder_ids=[],
            expected_revision=selected["revision"],
        )
    with pytest.raises(DomainError):
        hub.select(ADMIN, saved["id"], calendar_ids=[], folder_ids=[], expected_revision=saved["revision"])
    assert "password" not in json.dumps(hub.status(ADMIN))


def test_public_and_local_demo_never_save_credentials_or_open_network(tmp_path):
    for mode in ["demo", "public_demo"]:
        root = tmp_path / mode
        root.mkdir()
        cfg = settings(root, mode)
        repo = Repository(cfg.db_path)
        hub = ConnectionHub(
            repo,
            cfg,
            policy=IntegrationPolicy(egress_approved=True, allowed_hosts=("cal.example.org",)),
            reader_factory=FakeReader,
        )
        actor = {**ADMIN, "tenant_id": cfg.tenant_id}
        before = FakeReader.probes
        with pytest.raises(DomainError):
            hub.create(
                actor,
                {
                    "provider": "caldav",
                    "label": "Agenda",
                    "endpoint": "https://cal.example.org",
                    "username": "a",
                    "password": "x",
                },
            )
        assert FakeReader.probes == before
        assert not (root / ".connector-vault.key").exists()
        assert hub.status(actor)["public_demo"] == (mode == "public_demo")


def test_admin_and_tenant_boundary(tmp_path):
    hub, _ = make_hub(tmp_path)
    for actor in [
        {**ADMIN, "tenant_id": "other"},
        {**ADMIN, "permissions": {"organization": {"write": False}}},
    ]:
        with pytest.raises(DomainError):
            hub.create(
                actor,
                {
                    "provider": "caldav",
                    "label": "Agenda",
                    "endpoint": "https://cal.example.org",
                    "username": "a",
                    "password": "x",
                },
            )
    with pytest.raises(DomainError):
        hub.create(
            ADMIN,
            {
                "provider": "caldav",
                "label": "Agenda",
                "endpoint": "http://cal.example.org",
                "username": "a",
                "password": "x",
            },
        )
    with pytest.raises(DomainError):
        hub.create(
            ADMIN,
            {
                "provider": "caldav",
                "label": "Agenda",
                "endpoint": "https://not-approved.example.org",
                "username": "a",
                "password": "x",
            },
        )
    with pytest.raises(DomainError):
        hub.create(
            ADMIN,
            {
                "provider": "caldav",
                "label": "Agenda",
                "endpoint": "https://user:pass@cal.example.org",
                "username": "a",
                "password": "x",
            },
        )


def test_onboarding_is_actor_scoped_revision_checked_and_optional(tmp_path):
    hub, _ = make_hub(tmp_path)
    initial = hub.onboarding(ADMIN)
    assert initial["revision"] == 0 and not initial["completed"]
    saved = hub.save_onboarding(
        ADMIN, {"completed_steps": ["welcome", "email"], "dismissed": False, "expected_revision": 0}
    )
    assert saved["completed_steps"] == ["welcome", "email"] and saved["revision"] == 1
    assert hub.onboarding({**ADMIN, "actor_id": "someone-else"})["completed_steps"] == []
    with pytest.raises(DomainError):
        hub.save_onboarding(ADMIN, {"completed_steps": ["done"], "expected_revision": 1})
    with pytest.raises(DomainError):
        hub.save_onboarding(ADMIN, {"completed_steps": [], "expected_revision": 0})


def test_mail_status_distinguishes_verified_readiness_from_actual_mail_collection(tmp_path):
    hub, _ = make_hub(tmp_path)

    class MailReader(FakeReader):
        def probe(self):
            return {"calendars": [], "mail_folders": [{"id": "inbox", "name": "Réception"}]}

        def collect_mail(self, repo, tenant, connection_id, *, guard):
            guard()
            return {"accepted": 0, "batches": [], "more_available": False, "remote_write_enabled": False}

    hub.reader_factory = MailReader
    assert hub.mail_status(ADMIN)["status"] == "not_connected"
    saved = hub.create(
        ADMIN,
        {
            "provider": "exchange",
            "label": "Mairie",
            "endpoint": "https://cal.example.org/EWS/Exchange.asmx",
            "username": "agent",
            "mailbox": "agent@example.org",
            "password": "secret-not-in-db",
        },
    )
    probed = hub.probe(ADMIN, saved["id"], expected_revision=saved["revision"])
    selected = hub.select(
        ADMIN, saved["id"], calendar_ids=[], folder_ids=["inbox"], expected_revision=probed["revision"]
    )
    ready = hub.mail_status(ADMIN)
    assert ready["status"] == "ready" and ready["last_successful_mail_sync_at"] is None
    assert ready["can_send"] is False
    synced = hub.sync_mail(ADMIN, saved["id"], expected_revision=selected["revision"])
    assert synced["connection"]["last_mail_sync_at"]
    assert hub.mail_status(ADMIN)["status"] == "read_only"
    hub.disconnect(ADMIN, saved["id"], expected_revision=synced["connection"]["revision"])
    assert hub.mail_status(ADMIN)["status"] == "not_connected"
