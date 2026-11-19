import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from travaux.config import Settings
from travaux.connection_hub import IntegrationPolicy
from travaux.conversations import ConversationService
from travaux.domain import DomainError
from travaux.repository import Repository
from travaux.telegram_bridge import TelegramBridge


TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnop"
ACTOR = {
    "tenant_id": "town",
    "actor_id": "alice",
    "permissions": {"workspace": {"read": True}, "organization": {"write": True}},
}


@pytest.fixture
def bot(tmp_path):
    settings = Settings(
        mode="staging",
        db_path=tmp_path / "bot.sqlite3",
        tenant_id="town",
        password_hash="scrypt$test",
        public_origin="https://travaux.example.invalid",
        allowed_hosts=("travaux.example.invalid",),
    )
    repo = Repository(settings.db_path)
    project = repo.create_project("town", "TRV-042", "Projet NOM-SENSIBLE")
    repo.ingest_source(
        "town", "source", "[TRV-042] Mail sensible", "Le thermolaquage NOM-SENSIBLE attend une validation."
    )
    conversations = ConversationService(repo, settings)
    sent = []

    def api(request):
        method = request.url.path.rsplit("/", 1)[-1]
        payload = json.loads(request.content)
        if method == "getMe":
            return httpx.Response(
                200,
                json={"ok": True, "result": {"id": 123456789, "is_bot": True, "username": "TravauxTestBot"}},
            )
        if method == "sendMessage":
            sent.append(payload)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": len(sent)}})
        return httpx.Response(200, json={"ok": True, "result": True})

    policy = IntegrationPolicy(egress_approved=True, allowed_hosts=("api.telegram.org",))
    bridge = TelegramBridge(
        repo,
        settings,
        conversations=conversations,
        policy=policy,
        transport=httpx.MockTransport(api),
        permissions=lambda current: ACTOR["permissions"],
    )
    yield repo, project, conversations, bridge, sent
    repo.close()


def setup_pair(bot, *, relay=False):
    _, project, conversations, bridge, _ = bot
    bridge.configure(
        "town",
        ACTOR,
        bot_token=TOKEN,
        egress_approved=True,
        delivery_mode="webhook",
        content_relay_approved=relay,
    )
    thread = conversations.create("town", ACTOR, "private:alice", project_id=project["id"])
    pairing = bridge.pair("town", ACTOR, "private:alice", conversation_id=thread["id"])
    token = parse_qs(urlsplit(pairing["url"]).query)["start"][0]
    secret = bridge._configuration("town", secrets=True)["webhook_secret"]
    update = {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "chat": {"id": 321, "type": "private"},
            "from": {"id": 321},
            "text": "/start " + token,
        },
    }
    bridge.accept_webhook("town", secret, update)
    bridge.tick("town")
    return thread, secret, update


def test_public_demo_refuses_tokens_pairing_and_network(tmp_path):
    settings = Settings(db_path=tmp_path / "public.sqlite3")
    repo = Repository(settings.db_path)
    bridge = TelegramBridge(
        repo, settings, transport=httpx.MockTransport(lambda request: pytest.fail("network forbidden"))
    )
    with pytest.raises(DomainError):
        bridge.configure("town", ACTOR, bot_token=TOKEN, egress_approved=True)
    with pytest.raises(DomainError):
        bridge.pair("town", ACTOR, "guest:test")
    assert bridge.tick("town")["blocked"] is True
    assert not (tmp_path / ".connector-vault.key").exists()
    repo.close()


def test_config_token_encrypted_and_get_dto_contains_no_secret(bot):
    repo, _, _, bridge, _ = bot
    state = bridge.configure("town", ACTOR, bot_token=TOKEN, egress_approved=True)
    assert state["configured"] and state["bot_username"] == "TravauxTestBot"
    assert TOKEN not in str(state) and "webhook_secret" not in str(state)
    assert TOKEN.encode() not in Path(repo.path).read_bytes()


def test_pairing_is_single_use_private_and_update_idempotent(bot):
    _, _, _, bridge, _ = bot
    thread, secret, update = setup_pair(bot)
    assert bridge.status("town", ACTOR, "private:alice")["conversation_id"] == thread["id"]
    assert bridge.accept_webhook("town", secret, update)["replayed"] is True
    assert bridge.tick("town")["incoming_processed"] == 0
    changed = {**update, "message": {**update["message"], "text": "changed"}}
    with pytest.raises(DomainError):
        bridge.accept_webhook("town", secret, changed)
    with pytest.raises(DomainError):
        bridge.accept_webhook("town", "wrong", {"update_id": 3})


def test_alerts_only_default_never_exports_dossier_text(bot):
    _, _, conversations, bridge, sent = bot
    thread, _, _ = setup_pair(bot)
    conversations.send("town", ACTOR, "private:alice", thread["id"], "thermolaquage", "web-question")
    bridge.tick("town")
    assert sent and all(
        "NOM-SENSIBLE" not in item["text"] and "thermolaquage" not in item["text"] for item in sent
    )
    assert any("#/conversation/" in item["text"] for item in sent)
    assert all(item.get("link_preview_options", {}).get("is_disabled") is True for item in sent)


def test_full_relay_requires_admin_and_user_opt_in_and_keeps_one_thread(bot):
    _, _, conversations, bridge, sent = bot
    thread, secret, _ = setup_pair(bot, relay=True)
    bridge.notifications.update_preferences(
        "town", ACTOR, "private:alice", telegram_enabled=True, conversation_sync=True
    )
    conversations.send("town", ACTOR, "private:alice", thread["id"], "thermolaquage", "web-full")
    bridge.tick("town")
    assert any("Vous : thermolaquage" in item["text"] for item in sent)
    assert any("NOM-SENSIBLE" in item["text"] for item in sent)
    incoming = {
        "update_id": 2,
        "message": {
            "message_id": 2,
            "chat": {"id": 321, "type": "private"},
            "from": {"id": 321},
            "text": "Pourquoi le thermolaquage ?",
        },
    }
    bridge.accept_webhook("town", secret, incoming)
    bridge.tick("town")
    history = conversations.get("town", ACTOR, "private:alice", thread["id"])["messages"]
    assert len(history) == 4 and history[-2]["channel"] == "telegram"
    before = len(sent)
    bridge.accept_webhook("town", secret, incoming)
    bridge.tick("town")
    assert len(sent) == before


def test_group_messages_cannot_pair_or_query_dossiers(bot):
    _, _, _, bridge, _ = bot
    _, secret, _ = setup_pair(bot, relay=True)
    group = {
        "update_id": 9,
        "message": {
            "message_id": 9,
            "chat": {"id": -42, "type": "group"},
            "from": {"id": 321},
            "text": "thermolaquage",
        },
    }
    result = bridge.accept_webhook("town", secret, group)
    assert result["status"] == "ignored"


def test_ambiguous_send_is_not_automatically_replayed(bot):
    _, _, conversations, bridge, sent = bot
    thread, _, _ = setup_pair(bot)
    conversations.send("town", ACTOR, "private:alice", thread["id"], "thermolaquage", "uncertain")

    def timeout(request):
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    bridge.transport = httpx.MockTransport(timeout)
    bridge.tick("town")
    status = bridge.status("town", ACTOR, "private:alice")
    assert status["delivery"]["unknown"] >= 1
    before = len(sent)
    bridge.tick("town")
    assert len(sent) == before


def test_user_opt_in_without_institution_approval_cannot_export_content(bot):
    _, _, conversations, bridge, sent = bot
    thread, _, _ = setup_pair(bot, relay=False)
    bridge.notifications.update_preferences(
        "town", ACTOR, "private:alice", telegram_enabled=True, conversation_sync=True
    )
    conversations.send("town", ACTOR, "private:alice", thread["id"], "thermolaquage", "user-only")
    bridge.tick("town")
    assert all("NOM-SENSIBLE" not in item["text"] and "thermolaquage" not in item["text"] for item in sent)


def test_revoke_content_approval_downgrades_already_queued_payload(bot):
    repo, _, conversations, bridge, sent = bot
    thread, _, _ = setup_pair(bot, relay=True)
    bridge.notifications.update_preferences(
        "town", ACTOR, "private:alice", telegram_enabled=True, conversation_sync=True
    )
    conversations.send("town", ACTOR, "private:alice", thread["id"], "thermolaquage", "before-revoke")
    config = bridge._configuration("town", secrets=True)
    bridge._prepare_outbox("town", config)
    with repo._transaction() as db:
        db.execute("UPDATE telegram_config SET content_relay_approved=0 WHERE tenant_id='town'")
    # A worker may already hold a configuration snapshot when an administrator
    # revokes relay. Authorization must be re-read immediately before delivery.
    bridge._dispatch("town", config)
    assert all("NOM-SENSIBLE" not in item["text"] and "thermolaquage" not in item["text"] for item in sent)


def test_expired_pairing_and_foreign_chat_never_gain_thread_access(bot):
    repo, project, conversations, bridge, _ = bot
    bridge.configure("town", ACTOR, bot_token=TOKEN, egress_approved=True, delivery_mode="webhook")
    thread = conversations.create("town", ACTOR, "private:alice", project_id=project["id"])
    pairing = bridge.pair("town", ACTOR, "private:alice", conversation_id=thread["id"])
    token = parse_qs(urlsplit(pairing["url"]).query)["start"][0]
    with repo._transaction() as db:
        db.execute("UPDATE telegram_pairings SET expires_at='2000-01-01T00:00:00+00:00'")
    secret = bridge._configuration("town", secrets=True)["webhook_secret"]
    bridge.accept_webhook(
        "town",
        secret,
        {
            "update_id": 42,
            "message": {
                "message_id": 42,
                "chat": {"id": 321, "type": "private"},
                "from": {"id": 321},
                "text": "/start " + token,
            },
        },
    )
    bridge.tick("town")
    assert not bridge.status("town", ACTOR, "private:alice")["linked"]
    with pytest.raises(DomainError):
        bridge.accept_webhook("town", "é", {"update_id": 43})


def test_deleting_thread_also_revokes_telegram_link(bot):
    _, _, conversations, bridge, _ = bot
    thread, _, _ = setup_pair(bot, relay=True)
    conversations.delete("town", ACTOR, "private:alice", thread["id"])
    assert bridge.status("town", ACTOR, "private:alice")["linked"] is False


def test_standalone_worker_constructor_reads_agenda_and_creates_its_reminder(tmp_path):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from travaux.governance import GovernanceService

    settings = Settings(
        mode="staging",
        db_path=tmp_path / "standalone.sqlite3",
        tenant_id="town",
        password_hash="scrypt$test",
        public_origin="https://travaux.example.invalid",
        allowed_hosts=("travaux.example.invalid",),
    )
    repo = Repository(settings.db_path)
    current = {"tenant_id": "town", "actor_id": "responsable"}
    current["permissions"] = GovernanceService(repo, "town", settings).permissions(current)
    project = repo.create_project("town", "CAL-42", "Portail")
    delivered = []

    def api(request):
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "getMe":
            return httpx.Response(
                200,
                json={"ok": True, "result": {"id": 123456789, "is_bot": True, "username": "TravauxTestBot"}},
            )
        if method == "sendMessage":
            delivered.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": {"message_id": len(delivered)}})
        return httpx.Response(200, json={"ok": True, "result": True})

    policy = IntegrationPolicy(egress_approved=True, allowed_hosts=("api.telegram.org",))
    bridge = TelegramBridge(repo, settings, policy=policy, transport=httpx.MockTransport(api))
    bridge.configure(
        "town",
        current,
        bot_token=TOKEN,
        egress_approved=True,
        delivery_mode="webhook",
        content_relay_approved=True,
    )
    tomorrow = datetime.now(ZoneInfo("Europe/Paris")).date() + timedelta(days=1)
    content = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//FR\r\nBEGIN:VEVENT\r\nUID:worker-meeting\r\n"
        + f"DTSTART;VALUE=DATE:{tomorrow:%Y%m%d}\r\nDTEND;VALUE=DATE:{tomorrow + timedelta(days=1):%Y%m%d}\r\n"
        + "SUMMARY:Visite agenda du worker\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
    )
    calendar = bridge.notifications.calendars
    calendar.import_ics(current, content=content, name="Agenda du worker")
    event = calendar.events(current)["items"][0]
    calendar.assign(current, event["id"], project_id=project["id"], expected_revision=event["revision"])
    thread = bridge.conversations.create("town", current, "private:responsable", project_id=project["id"])
    pairing = bridge.pair("town", current, "private:responsable", conversation_id=thread["id"])
    token = parse_qs(urlsplit(pairing["url"]).query)["start"][0]
    secret = bridge._configuration("town", secrets=True)["webhook_secret"]

    def incoming(number, text):
        return {
            "update_id": number,
            "message": {
                "message_id": number,
                "chat": {"id": 987, "type": "private"},
                "from": {"id": 987},
                "text": text,
            },
        }

    bridge.accept_webhook("town", secret, incoming(1, "/start " + token))
    bridge.tick("town")
    bridge.notifications.update_preferences("town", current, "private:responsable", conversation_sync=True)
    # Reconstruct exactly as the CLI does: no calendar/conversation service injection.
    worker = TelegramBridge(repo, settings, policy=policy, transport=httpx.MockTransport(api))
    worker.accept_webhook("town", secret, incoming(2, "Quels rendez-vous demain ?"))
    worker.tick("town")
    history = worker.conversations.get("town", current, "private:responsable", thread["id"])["messages"]
    assert "Visite agenda du worker" in history[-1]["content"]
    assert any(item.get("kind") == "calendar" for item in history[-1]["citations"])
    assert any(
        item["kind"] == "calendar"
        for item in worker.notifications.list("town", current, "private:responsable")["items"]
    )
    repo.close()


def test_bot_rotation_resets_cursor_inbox_and_old_links_before_new_low_update_ids(bot):
    repo, _, conversations, bridge, _ = bot
    thread, old_secret, _ = setup_pair(bot)
    old_config = bridge._configuration("town", secrets=True)
    bridge.accept_webhook(
        "town",
        old_secret,
        {
            "update_id": 5,
            "message": {
                "message_id": 5,
                "chat": {"id": 321, "type": "private"},
                "from": {"id": 321},
                "text": "Old bot pending question",
            },
        },
    )
    conversations.send("town", ACTOR, "private:alice", thread["id"], "thermolaquage", "old-bot-pending")
    bridge._prepare_outbox("town", old_config)
    with repo._transaction() as db:
        db.execute("UPDATE telegram_config SET offset=900000 WHERE tenant_id='town'")
    updates, offsets = [], []

    def new_api(request):
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "getMe":
            return httpx.Response(
                200,
                json={"ok": True, "result": {"id": 222222222, "is_bot": True, "username": "TravauxOtherBot"}},
            )
        if method == "getUpdates":
            offsets.append(json.loads(request.content)["offset"])
            return httpx.Response(200, json={"ok": True, "result": updates})
        if method == "sendMessage":
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 999}})
        return httpx.Response(200, json={"ok": True, "result": True})

    bridge.transport = httpx.MockTransport(new_api)
    bridge.configure(
        "town",
        ACTOR,
        bot_token=TOKEN.replace("123456789", "222222222"),
        egress_approved=True,
        delivery_mode="polling",
    )
    assert bridge._configuration("town")["offset"] == 0
    assert not bridge.status("town", ACTOR, "private:alice")["linked"]
    assert (
        repo._db.execute("SELECT count(*) FROM telegram_incoming WHERE tenant_id='town'").fetchone()[0] == 0
    )
    assert (
        repo._db.execute(
            "SELECT count(*) FROM telegram_outbox WHERE tenant_id='town' AND status='pending'"
        ).fetchone()[0]
        == 0
    )
    pairing = bridge.pair("town", ACTOR, "private:alice", conversation_id=thread["id"])
    token = parse_qs(urlsplit(pairing["url"]).query)["start"][0]
    updates.append(
        {
            "update_id": 5,
            "message": {
                "message_id": 5,
                "chat": {"id": 987, "type": "private"},
                "from": {"id": 987},
                "text": "/start " + token,
            },
        }
    )
    bridge.tick("town")
    assert offsets == [0] and bridge.status("town", ACTOR, "private:alice")["linked"]
    stale = bridge._queue_update(
        "town", {"update_id": 6}, expected_ciphertext=old_config["secret_ciphertext"]
    )
    assert stale["accepted"] is False and stale["status"] == "stale_configuration"


def test_unread_notifications_beyond_first_page_are_enqueued_on_later_ticks(bot):
    repo, project, _, bridge, _ = bot
    setup_pair(bot)
    with repo._transaction() as db:
        for number in range(35):
            bridge.notifications._enqueue(
                db,
                "town",
                "alice",
                "private:alice",
                f"reminder:{number}",
                project["id"],
                None,
                "pending",
                "Rappel",
                "Contexte privé",
            )
    bridge.tick("town")
    bridge.tick("town")
    rows = repo._db.execute(
        "SELECT event_key,status FROM telegram_outbox WHERE tenant_id='town' AND event_key LIKE 'notification:%'"
    ).fetchall()
    assert len(rows) == 35 and all(row["status"] == "sent" for row in rows)


def test_new_bot_can_reuse_old_update_number_in_the_same_conversation(bot):
    _, _, conversations, bridge, sent = bot
    thread, secret, _ = setup_pair(bot, relay=True)

    def update(number, text):
        return {
            "update_id": number,
            "message": {
                "message_id": number,
                "chat": {"id": 321, "type": "private"},
                "from": {"id": 321},
                "text": text,
            },
        }

    bridge.notifications.update_preferences("town", ACTOR, "private:alice", conversation_sync=True)
    bridge.accept_webhook("town", secret, update(2, "thermolaquage"))
    bridge.tick("town")
    assert len(conversations.get("town", ACTOR, "private:alice", thread["id"])["messages"]) == 2

    def new_api(request):
        method = request.url.path.rsplit("/", 1)[-1]
        if method == "getMe":
            return httpx.Response(
                200,
                json={"ok": True, "result": {"id": 222222222, "is_bot": True, "username": "TravauxOtherBot"}},
            )
        if method == "sendMessage":
            sent.append(json.loads(request.content))
            return httpx.Response(200, json={"ok": True, "result": {"message_id": len(sent)}})
        return httpx.Response(200, json={"ok": True, "result": True})

    bridge.transport = httpx.MockTransport(new_api)
    bridge.configure(
        "town",
        ACTOR,
        bot_token=TOKEN.replace("123456789", "222222222"),
        egress_approved=True,
        delivery_mode="webhook",
        content_relay_approved=True,
    )
    pairing = bridge.pair("town", ACTOR, "private:alice", conversation_id=thread["id"])
    token = parse_qs(urlsplit(pairing["url"]).query)["start"][0]
    secret = bridge._configuration("town", secrets=True)["webhook_secret"]
    bridge.accept_webhook("town", secret, update(1, "/start " + token))
    bridge.tick("town")
    bridge.notifications.update_preferences("town", ACTOR, "private:alice", conversation_sync=True)
    bridge.accept_webhook("town", secret, update(2, "thermolaquage nouveau bot"))
    bridge.tick("town")
    history = conversations.get("town", ACTOR, "private:alice", thread["id"])["messages"]
    assert len(history) == 4 and history[-2]["content"] == "thermolaquage nouveau bot"
