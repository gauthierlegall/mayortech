"""Opt-in Telegram bridge with encrypted inbox/outbox and scoped conversations.

Telegram is an external service, not a sovereign municipal datastore. The
default payload is an alert and an authenticated application link. Full chat
content requires both an institution approval and a user's explicit opt-in.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
import json
import re
import secrets as random_secrets
import time
from uuid import uuid4

from .connection_hub import IntegrationPolicy, SecretVault
from .conversations import ConversationService
from .domain import DomainError, canonical_json, content_hash, utc_now
from .notifications import NotificationService
from .retrieval import DossierRetrieval
from .telegram_transport import DeliveryUncertain, ProviderRejected, telegram_request


class TelegramBridge:
    def __init__(
        self,
        repo,
        settings,
        *,
        conversations=None,
        policy=None,
        vault=None,
        transport=None,
        permissions=None,
        calendars=None,
    ):
        self.repo, self.settings, self.transport = repo, settings, transport
        self.policy, self.vault = policy or IntegrationPolicy.from_env(), vault or SecretVault(settings)
        if calendars is None and settings.auth_required:
            from .calendars import CalendarService
            from .connection_hub import ConnectionHub

            calendars = CalendarService(repo, settings, hub=ConnectionHub(repo, settings, policy=self.policy))
        self.notifications = NotificationService(repo, settings, calendars=calendars)
        self.conversations = conversations or ConversationService(
            repo, settings, retrieval=DossierRetrieval(repo, settings, calendars=calendars)
        )
        self.permissions = permissions
        with repo._lock:
            repo._db.executescript("""
                CREATE TABLE IF NOT EXISTS telegram_config(
                    tenant_id TEXT PRIMARY KEY,secret_ciphertext TEXT NOT NULL,bot_id INTEGER NOT NULL,
                    bot_username TEXT NOT NULL,delivery_mode TEXT NOT NULL,content_relay_approved INTEGER NOT NULL,
                    verified_at TEXT NOT NULL,offset INTEGER NOT NULL DEFAULT 0,last_worker_tick TEXT);
                CREATE TABLE IF NOT EXISTS telegram_pairings(
                    token_hash TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,
                    owner_scope TEXT NOT NULL,conversation_id TEXT NOT NULL,expires_at TEXT NOT NULL,used_at TEXT,
                    FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS telegram_links(
                    id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,owner_scope TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,conversation_id TEXT NOT NULL,last_sequence INTEGER NOT NULL,
                    created_at TEXT NOT NULL,UNIQUE(tenant_id,chat_id),UNIQUE(tenant_id,actor_id,owner_scope),
                    FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE);
                CREATE TABLE IF NOT EXISTS telegram_incoming(
                    tenant_id TEXT NOT NULL,update_id INTEGER NOT NULL,payload_hash TEXT NOT NULL,
                    payload_ciphertext TEXT NOT NULL,status TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
                    available_at REAL NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                    last_error TEXT NOT NULL DEFAULT '',PRIMARY KEY(tenant_id,update_id));
                CREATE TABLE IF NOT EXISTS telegram_outbox(
                    id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,owner_scope TEXT NOT NULL,
                    link_id TEXT NOT NULL,event_key TEXT NOT NULL,payload_ciphertext TEXT NOT NULL,
                    status TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,available_at REAL NOT NULL DEFAULT 0,
                    provider_message_id INTEGER,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
                    last_error TEXT NOT NULL DEFAULT '',UNIQUE(tenant_id,link_id,event_key));
            """)

    def _private(self):
        if not self.settings.auth_required or self.settings.mode == "public_demo":
            raise DomainError(
                "forbidden",
                "La connexion Telegram est réservée à un espace protégé. La démonstration n’envoie aucun message.",
            )

    def _configuration(self, tenant, *, secrets=False):
        with self.repo._lock:
            row = self.repo._db.execute(
                "SELECT * FROM telegram_config WHERE tenant_id=?", (tenant,)
            ).fetchone()
        if row is None:
            return None
        config = dict(row)
        if secrets:
            self._private()
            envelope = self.vault.decrypt(config["secret_ciphertext"])
            if envelope.get("tenant_id") != tenant:
                raise DomainError("forbidden", "Ce bot n’appartient pas à cet espace.")
            config.update({key: envelope[key] for key in ("bot_token", "webhook_secret")})
        return config

    def _api(self, config, method, payload):
        return telegram_request(
            config["bot_token"], method, payload, policy=self.policy, transport=self.transport
        )

    def _encrypt(self, tenant, payload):
        return self.vault.encrypt({"tenant_id": tenant, "payload": payload})

    def _decrypt(self, tenant, ciphertext):
        envelope = self.vault.decrypt(ciphertext)
        if envelope.get("tenant_id") != tenant:
            raise DomainError("forbidden", "Cet événement n’appartient pas à cet espace.")
        return envelope["payload"]

    def _stored_actor(self, tenant, actor_id):
        current = {"tenant_id": tenant, "actor_id": actor_id}
        if self.permissions is None:
            # A standalone worker resolves the same server-side role model.
            from .governance import GovernanceService

            governance = GovernanceService(self.repo, tenant, self.settings)
            current["permissions"] = governance.permissions(current)
        else:
            current["permissions"] = self.permissions(current)
        ConversationService._identity(tenant, current, "telegram")
        return current

    def status(self, tenant, current, owner_scope):
        identity = ConversationService._identity(tenant, current, owner_scope)
        config = self._configuration(tenant)
        with self.repo._lock:
            link = self.repo._db.execute(
                "SELECT * FROM telegram_links WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                (tenant, identity, owner_scope),
            ).fetchone()
            counts = self.repo._db.execute(
                "SELECT status,count(*) AS total FROM telegram_outbox WHERE tenant_id=? AND actor_id=? AND owner_scope=? GROUP BY status",
                (tenant, identity, owner_scope),
            ).fetchall()
        private = self.settings.auth_required and self.settings.mode != "public_demo"
        allowed = private and self.policy.egress_approved and "api.telegram.org" in self.policy.allowed_hosts
        online = bool(
            config
            and config["last_worker_tick"]
            and (
                datetime.now(timezone.utc) - datetime.fromisoformat(config["last_worker_tick"])
            ).total_seconds()
            < 120
        )
        return {
            "configured": bool(config),
            "linked": bool(link),
            "available": allowed,
            "bot_username": config["bot_username"] if config else None,
            "delivery_mode": config["delivery_mode"] if config else None,
            "content_relay_approved": bool(config and config["content_relay_approved"]),
            "conversation_id": link["conversation_id"] if link else None,
            "default_policy": "alerts_links_only",
            "worker_online": online,
            "last_worker_tick": config["last_worker_tick"] if config else None,
            "can_configure": allowed
            and current.get("permissions", {}).get("organization", {}).get("write") is True,
            "delivery": {row["status"]: row["total"] for row in counts},
            "reason": None
            if allowed
            else "demo_no_external_connection"
            if not private
            else "operator_egress_approval_required",
        }

    def configure(
        self,
        tenant,
        current,
        *,
        bot_token,
        egress_approved,
        delivery_mode="polling",
        content_relay_approved=False,
    ):
        self._private()
        ConversationService._identity(tenant, current, "telegram-config")
        if (
            current.get("permissions", {}).get("organization", {}).get("write") is not True
            or egress_approved is not True
        ):
            raise DomainError(
                "forbidden", "L’administrateur doit autoriser explicitement ce service externe."
            )
        if delivery_mode not in {"polling", "webhook"} or type(content_relay_approved) is not bool:
            raise DomainError("invalid_input", "Mode de connexion Telegram invalide.")
        if not self.policy.egress_approved or "api.telegram.org" not in self.policy.allowed_hosts:
            raise DomainError(
                "forbidden", "L’opérateur doit autoriser api.telegram.org dans la politique de sortie."
            )
        config = {"bot_token": bot_token, "webhook_secret": random_secrets.token_urlsafe(32)}
        try:
            bot = self._api(config, "getMe", {})
            if (
                not isinstance(bot, dict)
                or bot.get("is_bot") is not True
                or type(bot.get("id")) is not int
                or not isinstance(bot.get("username"), str)
                or not re.fullmatch(r"[A-Za-z0-9_]{5,32}", bot["username"])
            ):
                raise ProviderRejected()
            if delivery_mode == "webhook":
                self._api(
                    config,
                    "setWebhook",
                    {
                        "url": self.settings.public_origin.rstrip("/")
                        + "/api/v1/integrations/telegram/webhook",
                        "secret_token": config["webhook_secret"],
                        "allowed_updates": ["message"],
                    },
                )
            else:
                self._api(config, "deleteWebhook", {"drop_pending_updates": False})
        except (DeliveryUncertain, ProviderRejected):
            raise DomainError(
                "integration_unavailable",
                "Le bot n’a pas confirmé la connexion. Le jeton n’est pas affiché ni journalisé ; vérifiez sa configuration.",
            ) from None
        encrypted = self.vault.encrypt({"tenant_id": tenant, **config})
        with self.repo._transaction() as db:
            previous = db.execute(
                "SELECT bot_id FROM telegram_config WHERE tenant_id=?", (tenant,)
            ).fetchone()
            if previous and previous["bot_id"] != bot["id"]:
                db.execute("DELETE FROM telegram_links WHERE tenant_id=?", (tenant,))
                db.execute("DELETE FROM telegram_pairings WHERE tenant_id=?", (tenant,))
                db.execute("DELETE FROM telegram_incoming WHERE tenant_id=?", (tenant,))
                db.execute(
                    "UPDATE telegram_config SET offset=0,last_worker_tick=NULL WHERE tenant_id=?", (tenant,)
                )
                db.execute(
                    "UPDATE telegram_outbox SET status='cancelled' WHERE tenant_id=? AND status IN ('pending','sending')",
                    (tenant,),
                )
            db.execute(
                "INSERT INTO telegram_config VALUES(?,?,?,?,?,?,?,0,NULL) ON CONFLICT(tenant_id) DO UPDATE SET secret_ciphertext=excluded.secret_ciphertext,bot_id=excluded.bot_id,bot_username=excluded.bot_username,delivery_mode=excluded.delivery_mode,content_relay_approved=excluded.content_relay_approved,verified_at=excluded.verified_at",
                (
                    tenant,
                    encrypted,
                    bot["id"],
                    bot["username"],
                    delivery_mode,
                    int(content_relay_approved),
                    utc_now(),
                ),
            )
        return self.status(tenant, current, "private:" + current["actor_id"])

    def pair(self, tenant, current, owner_scope, *, conversation_id=None):
        self._private()
        identity = ConversationService._identity(tenant, current, owner_scope)
        if owner_scope != "private:" + identity:
            raise DomainError("forbidden", "Connectez votre compte individuel avant d’appairer Telegram.")
        config = self._configuration(tenant)
        if config is None:
            raise DomainError(
                "integration_unavailable",
                "Un administrateur doit d’abord connecter le bot de l’organisation.",
            )
        if conversation_id:
            self.conversations.get(tenant, current, owner_scope, conversation_id)
        else:
            conversation_id = self.conversations.create(
                tenant, current, owner_scope, title="Conversation Telegram"
            )["id"]
        token = random_secrets.token_urlsafe(32)
        expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        with self.repo._transaction() as db:
            db.execute(
                "DELETE FROM telegram_pairings WHERE tenant_id=? AND actor_id=? AND owner_scope=? AND used_at IS NULL",
                (tenant, identity, owner_scope),
            )
            db.execute(
                "INSERT INTO telegram_pairings VALUES(?,?,?,?,?,?,NULL)",
                (content_hash(token), tenant, identity, owner_scope, conversation_id, expiry),
            )
        # Telegram's documented /start deep-link payload: URL-safe, <=64 chars.
        return {
            "url": f"https://t.me/{config['bot_username']}?start={token}",
            "expires_at": expiry,
            "conversation_id": conversation_id,
            "policy": "alerts_links_only",
        }

    def unlink(self, tenant, current, owner_scope):
        identity = ConversationService._identity(tenant, current, owner_scope)
        with self.repo._transaction() as db:
            db.execute(
                "DELETE FROM telegram_links WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                (tenant, identity, owner_scope),
            )
            db.execute(
                "DELETE FROM telegram_pairings WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                (tenant, identity, owner_scope),
            )
            db.execute(
                "UPDATE telegram_outbox SET status='cancelled' WHERE tenant_id=? AND actor_id=? AND owner_scope=? AND status='pending'",
                (tenant, identity, owner_scope),
            )
        self.notifications.update_preferences(
            tenant, current, owner_scope, telegram_enabled=False, conversation_sync=False
        )
        return {"linked": False}

    @staticmethod
    def _clean_update(update):
        if (
            not isinstance(update, dict)
            or type(update.get("update_id")) is not int
            or not 0 <= update["update_id"] < 2**63
        ):
            raise DomainError("invalid_input", "Événement Telegram invalide.")
        message = update.get("message", {})
        if not isinstance(message, dict):
            return {"update_id": update["update_id"], "ignored": True}
        chat, sender = message.get("chat", {}), message.get("from", {})
        if (
            not isinstance(chat, dict)
            or not isinstance(sender, dict)
            or chat.get("type") != "private"
            or type(chat.get("id")) is not int
            or not 0 < chat["id"] < 2**63
            or type(sender.get("id")) is not int
            or sender["id"] != chat["id"]
            or type(message.get("message_id")) is not int
            or not isinstance(message.get("text"), str)
            or not 1 <= len(message["text"]) <= 2000
        ):
            return {"update_id": update["update_id"], "ignored": True}
        return {
            "update_id": update["update_id"],
            "chat_id": chat["id"],
            "text": message["text"],
            "message_id": message["message_id"],
        }

    def _queue_update(self, tenant, update, *, expected_ciphertext):
        clean = self._clean_update(update)
        digest, now = content_hash(canonical_json(update)), utc_now()
        status = "ignored" if clean.get("ignored") else "pending"
        with self.repo._transaction() as db:
            active = db.execute(
                "SELECT secret_ciphertext,bot_id FROM telegram_config WHERE tenant_id=?", (tenant,)
            ).fetchone()
            if active is None or active["secret_ciphertext"] != expected_ciphertext:
                return {"accepted": False, "status": "stale_configuration", "replayed": False}
            clean["bot_id"] = active["bot_id"]
            encrypted = self._encrypt(tenant, clean)
            prior = db.execute(
                "SELECT payload_hash,status FROM telegram_incoming WHERE tenant_id=? AND update_id=?",
                (tenant, clean["update_id"]),
            ).fetchone()
            if prior:
                if prior["payload_hash"] != digest:
                    raise DomainError(
                        "idempotency_conflict",
                        "Cet identifiant Telegram est déjà associé à un autre événement.",
                    )
                return {"accepted": True, "status": prior["status"], "replayed": True}
            db.execute(
                "INSERT INTO telegram_incoming VALUES(?,?,?,?,?,0,0,?,?, '')",
                (tenant, clean["update_id"], digest, encrypted, status, now, now),
            )
        return {"accepted": True, "status": status, "replayed": False}

    def accept_webhook(self, tenant, secret, update):
        self._private()
        config = self._configuration(tenant, secrets=True)
        if (
            not config
            or config["delivery_mode"] != "webhook"
            or not isinstance(secret, str)
            or not hmac.compare_digest(secret.encode("utf-8"), config["webhook_secret"].encode("ascii"))
        ):
            raise DomainError("forbidden", "La signature de ce webhook n’est pas autorisée.")
        return self._queue_update(tenant, update, expected_ciphertext=config["secret_ciphertext"])

    def _queue_outbound(self, db, tenant, link, key, text, href, *, contains_content=False):
        payload = {
            "chat_id": link["chat_id"],
            "text": text[:3500],
            "href": href,
            "contains_content": contains_content,
        }
        now = utc_now()
        db.execute(
            "INSERT OR IGNORE INTO telegram_outbox VALUES(?,?,?,?,?,?,?,'pending',0,0,NULL,?,?, '')",
            (
                str(uuid4()),
                tenant,
                link["actor_id"],
                link["owner_scope"],
                link["id"],
                key,
                self._encrypt(tenant, payload),
                now,
                now,
            ),
        )

    def _process_incoming(self, tenant, clean):
        current_config = self._configuration(tenant)
        if current_config is None or current_config["bot_id"] != clean.get("bot_id"):
            return
        with self.repo._lock:
            link = self.repo._db.execute(
                "SELECT * FROM telegram_links WHERE tenant_id=? AND chat_id=?", (tenant, clean["chat_id"])
            ).fetchone()
        match = re.fullmatch(r"/start(?:@[A-Za-z0-9_]+)?\s+([A-Za-z0-9_-]{43})", clean["text"].strip())
        if match:
            with self.repo._transaction() as db:
                pairing = db.execute(
                    "SELECT * FROM telegram_pairings WHERE tenant_id=? AND token_hash=? AND used_at IS NULL AND expires_at>?",
                    (tenant, content_hash(match.group(1)), utc_now()),
                ).fetchone()
                if not pairing:
                    return
                current = self._stored_actor(tenant, pairing["actor_id"])
                self.conversations.get(tenant, current, pairing["owner_scope"], pairing["conversation_id"])
                if link and (
                    link["actor_id"] != pairing["actor_id"] or link["owner_scope"] != pairing["owner_scope"]
                ):
                    raise DomainError("forbidden", "Ce compte Telegram est déjà relié à un autre accès.")
                db.execute(
                    "DELETE FROM telegram_links WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                    (tenant, pairing["actor_id"], pairing["owner_scope"]),
                )
                last = db.execute(
                    "SELECT coalesce(max(sequence),0) FROM chat_messages WHERE conversation_id=?",
                    (pairing["conversation_id"],),
                ).fetchone()[0]
                link_id, now = str(uuid4()), utc_now()
                db.execute(
                    "INSERT INTO telegram_links VALUES(?,?,?,?,?,?,?,?)",
                    (
                        link_id,
                        tenant,
                        pairing["actor_id"],
                        pairing["owner_scope"],
                        clean["chat_id"],
                        pairing["conversation_id"],
                        last,
                        now,
                    ),
                )
                db.execute(
                    "UPDATE telegram_pairings SET used_at=? WHERE token_hash=?", (now, pairing["token_hash"])
                )
                new_link = dict(db.execute("SELECT * FROM telegram_links WHERE id=?", (link_id,)).fetchone())
                href = f"#/conversation/{pairing['conversation_id']}"
                self._queue_outbound(
                    db,
                    tenant,
                    new_link,
                    "paired",
                    "Telegram est relié à votre espace Travaux. Les alertes contiennent uniquement un lien, tant que vous n’activez pas la conversation complète.",
                    href,
                )
            self.notifications.update_preferences(
                tenant, current, pairing["owner_scope"], telegram_enabled=True, conversation_sync=False
            )
            return
        if link is None:
            return
        current = self._stored_actor(tenant, link["actor_id"])
        if clean["text"].strip() == "/stop":
            self.unlink(tenant, current, link["owner_scope"])
            return
        config = self._configuration(tenant)
        preferences = self.notifications.preferences(tenant, current, link["owner_scope"])
        if not (
            preferences["telegram_enabled"]
            and preferences["conversation_sync"]
            and config["content_relay_approved"]
        ):
            with self.repo._transaction() as db:
                self._queue_outbound(
                    db,
                    tenant,
                    link,
                    "disabled:" + str(clean["update_id"]),
                    "La conversation complète n’est pas activée. Retrouvez votre espace et ses réglages dans Travaux.",
                    f"#/conversation/{link['conversation_id']}",
                )
            return
        self.conversations.send(
            tenant,
            current,
            link["owner_scope"],
            link["conversation_id"],
            clean["text"],
            "telegram:" + link["id"] + ":" + str(clean["update_id"]),
            channel="telegram",
        )

    def preferences_changed(self, tenant, current, owner_scope):
        # Changes are forward-only: enabling relay never dumps older chat history.
        identity = ConversationService._identity(tenant, current, owner_scope)
        with self.repo._transaction() as db:
            db.execute(
                "UPDATE telegram_links SET last_sequence=(SELECT coalesce(max(sequence),0) FROM chat_messages WHERE conversation_id=telegram_links.conversation_id) WHERE tenant_id=? AND actor_id=? AND owner_scope=?",
                (tenant, identity, owner_scope),
            )

    def _prepare_outbox(self, tenant, config):
        with self.repo._lock:
            links = [
                dict(row)
                for row in self.repo._db.execute(
                    "SELECT * FROM telegram_links WHERE tenant_id=?", (tenant,)
                ).fetchall()
            ]
        for link in links:
            try:
                current = self._stored_actor(tenant, link["actor_id"])
                self.conversations.get(tenant, current, link["owner_scope"], link["conversation_id"])
            except DomainError:
                continue
            preferences = self.notifications.preferences(tenant, current, link["owner_scope"])
            if preferences["telegram_enabled"]:
                self.notifications.refresh(tenant, current, link["owner_scope"])
            with self.repo._transaction() as db:
                messages = db.execute(
                    "SELECT * FROM chat_messages WHERE conversation_id=? AND sequence>? ORDER BY sequence LIMIT 200",
                    (link["conversation_id"], link["last_sequence"]),
                ).fetchall()
                relay = bool(config["content_relay_approved"] and preferences["conversation_sync"])
                for message in messages:
                    if not preferences["telegram_enabled"] or (
                        message["role"] == "user" and (not relay or message["channel"] == "telegram")
                    ):
                        continue
                    href = f"#/conversation/{link['conversation_id']}"
                    text = (
                        f"{'Vous' if message['role'] == 'user' else 'Assistant'} : {message['content']}"
                        if relay
                        else "Une réponse est disponible dans votre conversation Travaux."
                    )
                    self._queue_outbound(
                        db, tenant, link, "message:" + message["id"], text, href, contains_content=relay
                    )
                if messages:
                    db.execute(
                        "UPDATE telegram_links SET last_sequence=? WHERE id=?",
                        (messages[-1]["sequence"], link["id"]),
                    )
                if preferences["telegram_enabled"]:
                    notes = db.execute(
                        "SELECT n.* FROM user_notifications n WHERE n.tenant_id=? AND n.actor_id=? AND n.owner_scope=? AND n.read_at IS NULL AND n.resolved_at IS NULL AND n.created_at>=? AND NOT EXISTS(SELECT 1 FROM telegram_outbox o WHERE o.tenant_id=n.tenant_id AND o.link_id=? AND o.event_key='notification:'||n.id) ORDER BY n.created_at,n.id LIMIT 30",
                        (tenant, link["actor_id"], link["owner_scope"], link["created_at"], link["id"]),
                    ).fetchall()
                    for note in notes:
                        self._queue_outbound(
                            db,
                            tenant,
                            link,
                            "notification:" + note["id"],
                            "Un point de votre suivi Travaux attend votre attention.",
                            note["href"],
                        )

    def _dispatch(self, tenant, config, maximum=20):
        sent, unknown = 0, 0
        for _ in range(maximum):
            with self.repo._transaction() as db:
                row = db.execute(
                    "SELECT * FROM telegram_outbox WHERE tenant_id=? AND status='pending' AND available_at<=? ORDER BY created_at,id LIMIT 1",
                    (tenant, time.time()),
                ).fetchone()
                if row is None:
                    break
                row = dict(row)
                db.execute(
                    "UPDATE telegram_outbox SET status='sending',attempts=attempts+1,updated_at=? WHERE id=?",
                    (utc_now(), row["id"]),
                )
                link = db.execute(
                    "SELECT * FROM telegram_links WHERE tenant_id=? AND id=?", (tenant, row["link_id"])
                ).fetchone()
            state, error, retry_at, provider_id = "cancelled", "", 0, None
            try:
                current = self._stored_actor(tenant, row["actor_id"])
                preferences = self.notifications.preferences(tenant, current, row["owner_scope"])
                active_config = self._configuration(tenant, secrets=True)
                with self.repo._lock:
                    link = self.repo._db.execute(
                        "SELECT * FROM telegram_links WHERE tenant_id=? AND id=?", (tenant, row["link_id"])
                    ).fetchone()
                if link and active_config and preferences["telegram_enabled"]:
                    payload = self._decrypt(tenant, row["payload_ciphertext"])
                    if payload["contains_content"] and not (
                        active_config["content_relay_approved"] and preferences["conversation_sync"]
                    ):
                        payload["text"] = "Une réponse est disponible dans votre conversation Travaux."
                    url = self.settings.public_origin.rstrip("/") + "/" + payload["href"]
                    result = self._api(
                        active_config,
                        "sendMessage",
                        {
                            "chat_id": link["chat_id"],
                            "text": payload["text"] + "\n\n" + url,
                            "link_preview_options": {"is_disabled": True},
                        },
                    )
                    if not isinstance(result, dict) or type(result.get("message_id")) is not int:
                        raise DeliveryUncertain()
                    state, provider_id = "sent", result["message_id"]
                    sent += 1
            except DeliveryUncertain:
                state, error = "unknown", "provider_delivery_unconfirmed"
                unknown += 1
            except ProviderRejected as failure:
                state = "pending" if failure.retry_after else "failed"
                error, retry_at = "provider_rejected", time.time() + failure.retry_after
            except DomainError:
                state, error = "cancelled", "access_or_configuration_unavailable"
            with self.repo._transaction() as db:
                db.execute(
                    "UPDATE telegram_outbox SET status=?,last_error=?,available_at=?,provider_message_id=?,updated_at=? WHERE id=?",
                    (state, error, retry_at, provider_id, utc_now(), row["id"]),
                )
        return sent, unknown

    def tick(self, tenant):
        if not self.settings.auth_required or self.settings.mode == "public_demo":
            return {"blocked": True, "incoming_processed": 0, "sent": 0, "unknown": 0}
        config = self._configuration(tenant, secrets=True)
        if config is None:
            return {"blocked": True, "incoming_processed": 0, "sent": 0, "unknown": 0}
        if not self.policy.egress_approved or "api.telegram.org" not in self.policy.allowed_hosts:
            return {"blocked": True, "incoming_processed": 0, "sent": 0, "unknown": 0}
        now = utc_now()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        retention = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with self.repo._transaction() as db:
            self.conversations._purge(db)
            db.execute(
                "DELETE FROM telegram_incoming WHERE tenant_id=? AND created_at<?", (tenant, retention)
            )
            db.execute(
                "DELETE FROM telegram_outbox WHERE tenant_id=? AND created_at<? AND status!='sending'",
                (tenant, retention),
            )
            db.execute(
                "DELETE FROM telegram_pairings WHERE tenant_id=? AND expires_at<?", (tenant, retention)
            )
            # An inbound question can be replayed with a durable client ID. An
            # outbound send cannot: a crash may have happened after delivery.
            db.execute(
                "UPDATE telegram_incoming SET status='pending' WHERE tenant_id=? AND status='processing' AND updated_at<?",
                (tenant, cutoff),
            )
            db.execute(
                "UPDATE telegram_outbox SET status='unknown',last_error='worker_interrupted_after_send' WHERE tenant_id=? AND status='sending' AND updated_at<?",
                (tenant, cutoff),
            )
            db.execute("UPDATE telegram_config SET last_worker_tick=? WHERE tenant_id=?", (now, tenant))
        if config["delivery_mode"] == "polling":
            try:
                updates = self._api(
                    config,
                    "getUpdates",
                    {"offset": config["offset"], "timeout": 0, "limit": 20, "allowed_updates": ["message"]},
                )
                if not isinstance(updates, list):
                    raise ProviderRejected()
                for update in updates:
                    self._queue_update(tenant, update, expected_ciphertext=config["secret_ciphertext"])
                    with self.repo._transaction() as db:
                        db.execute(
                            "UPDATE telegram_config SET offset=max(offset,?) WHERE tenant_id=? AND secret_ciphertext=?",
                            (update["update_id"] + 1, tenant, config["secret_ciphertext"]),
                        )
            except (DeliveryUncertain, ProviderRejected):
                return {
                    "blocked": False,
                    "incoming_processed": 0,
                    "sent": 0,
                    "unknown": 0,
                    "poll_error": "provider_unavailable",
                }
        processed = 0
        for _ in range(10):
            with self.repo._transaction() as db:
                row = db.execute(
                    "SELECT * FROM telegram_incoming WHERE tenant_id=? AND status='pending' AND available_at<=? ORDER BY update_id LIMIT 1",
                    (tenant, time.time()),
                ).fetchone()
                if row is None:
                    break
                row = dict(row)
                db.execute(
                    "UPDATE telegram_incoming SET status='processing',attempts=attempts+1,updated_at=? WHERE tenant_id=? AND update_id=?",
                    (utc_now(), tenant, row["update_id"]),
                )
            state, error, retry = "done", "", 0
            try:
                clean = self._decrypt(tenant, row["payload_ciphertext"])
                if clean["update_id"] != row["update_id"]:
                    raise DomainError("invalid_input", "Événement incompatible.")
                self._process_incoming(tenant, clean)
                processed += 1
            except DomainError as failure:
                retry = time.time() + 30
                state, error = ("pending" if row["attempts"] < 4 else "failed"), failure.code
            with self.repo._transaction() as db:
                db.execute(
                    "UPDATE telegram_incoming SET status=?,last_error=?,available_at=?,updated_at=? WHERE tenant_id=? AND update_id=? AND payload_hash=? AND payload_ciphertext=?",
                    (
                        state,
                        error,
                        retry,
                        utc_now(),
                        tenant,
                        row["update_id"],
                        row["payload_hash"],
                        row["payload_ciphertext"],
                    ),
                )
        self._prepare_outbox(tenant, config)
        sent, unknown = self._dispatch(tenant, config)
        return {"blocked": False, "incoming_processed": processed, "sent": sent, "unknown": unknown}


def main():
    """Separate network-enabled operator worker, never the isolated ingest worker."""
    import argparse
    from .config import Settings
    from .repository import Repository

    parser = argparse.ArgumentParser(description="Pont Telegram Travaux — aucun jeton en ligne de commande")
    parser.add_argument("command", choices=["worker"])
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=5)
    args = parser.parse_args()
    if not 2 <= args.interval <= 60:
        parser.error("Intervalle attendu entre 2 et 60 secondes.")
    settings = Settings.from_env()
    if not settings.auth_required or settings.mode == "public_demo":
        parser.error("Ce worker exige un espace protégé et une autorisation de sortie explicite.")
    repo = Repository(settings.db_path)
    bridge = TelegramBridge(repo, settings)
    try:
        while True:
            try:
                print(json.dumps(bridge.tick(settings.tenant_id)), flush=True)
            except DomainError as failure:
                print(json.dumps({"error": failure.code}), flush=True)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        repo.close()


if __name__ == "__main__":
    main()
