from types import SimpleNamespace

import pytest

from travaux.domain import DomainError
from travaux.notifications import NotificationService
from travaux.repository import Repository


ACTOR = {"tenant_id": "town", "actor_id": "alice", "permissions": {"workspace": {"read": True}}}


@pytest.fixture
def feed(tmp_path):
    repo = Repository(tmp_path / "notifications.sqlite3")
    project = repo.create_project("town", "TRV-042", "Nom sensible du chantier")
    source = repo.ingest_source("town", "notification-mail", "[TRV-042] Livraison", "Livraison : 2026-11-25")
    candidate = repo.add_candidate(
        "town", project["id"], source["id"], "delivery_date", "2026-11-25", kind="date", quote=source["body"]
    )
    service = NotificationService(repo, SimpleNamespace(mode="demo", public_origin=""))
    yield repo, project, candidate, service
    repo.close()


def test_pending_notifications_are_idempotent_private_and_resolve_after_review(feed):
    repo, project, candidate, service = feed
    first = service.list("town", ACTOR, "guest:a")
    again = service.list("town", ACTOR, "guest:a")
    assert len(first["items"]) == 1 and first["items"][0]["id"] == again["items"][0]["id"]
    assert first["items"][0]["project_id"] == project["id"]
    assert service.list("town", ACTOR, "guest:b")["items"][0]["id"] != first["items"][0]["id"]
    with pytest.raises(DomainError):
        service.mark_read("town", ACTOR, "guest:b", first["items"][0]["id"])
    repo.review_candidate("town", candidate["id"], "accept")
    after = service.list("town", ACTOR, "guest:a")
    assert next(item for item in after["items"] if item["id"] == first["items"][0]["id"])["resolved_at"]


def test_in_app_read_state_is_durable_and_does_not_change_project(feed):
    repo, project, _, service = feed
    before = repo.get_memory("town", project["id"])
    notification = service.list("town", ACTOR, "private:alice")["items"][0]
    service.mark_read("town", ACTOR, "private:alice", notification["id"])
    assert service.list("town", ACTOR, "private:alice")["unread"] == 0
    assert repo.get_memory("town", project["id"]) == before


def test_preferences_never_enable_external_content_by_default(feed):
    _, _, _, service = feed
    preferences = service.preferences("town", ACTOR, "private:alice")
    assert preferences == {"in_app": True, "telegram_enabled": False, "conversation_sync": False}
    updated = service.update_preferences("town", ACTOR, "private:alice", in_app=False)
    assert updated["in_app"] is False and updated["telegram_enabled"] is False
