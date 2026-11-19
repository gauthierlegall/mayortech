"""Bounded Telegram Bot API transport; no endpoint supplied by chat content."""

import json
import re

import httpx

from .domain import DomainError


class DeliveryUncertain(Exception):
    """Bot API has no idempotency key: an ambiguous send must not be replayed."""


class ProviderRejected(Exception):
    def __init__(self, retry_after=0):
        self.retry_after = retry_after


def telegram_request(token, method, payload, *, policy, transport=None):
    if not policy.egress_approved or "api.telegram.org" not in policy.allowed_hosts:
        raise DomainError("forbidden", "La sortie Telegram n’est pas autorisée par l’administrateur.")
    if not re.fullmatch(r"[0-9]{5,20}:[A-Za-z0-9_-]{20,150}", token):
        raise DomainError("integration_unavailable", "Le jeton du bot doit être vérifié.")
    if method not in {"getMe", "setWebhook", "deleteWebhook", "getUpdates", "sendMessage"}:
        raise DomainError("forbidden", "Cette opération Telegram n’est pas autorisée.")
    policy.endpoint("https://api.telegram.org/", resolve=transport is None)
    try:
        with httpx.Client(timeout=20, follow_redirects=False, trust_env=False, transport=transport) as client:
            with client.stream(
                "POST", f"https://api.telegram.org/bot{token}/{method}", json=payload
            ) as response:
                raw = bytearray()
                for part in response.iter_bytes():
                    raw.extend(part)
                    if len(raw) > 500_000:
                        raise DeliveryUncertain()
                if response.status_code >= 500:
                    raise DeliveryUncertain()
                try:
                    body = json.loads(raw)
                except (ValueError, UnicodeError):
                    raise DeliveryUncertain() from None
                if not isinstance(body, dict) or not body.get("ok"):
                    parameters = body.get("parameters", {}) if isinstance(body, dict) else {}
                    after = parameters.get("retry_after", 0)
                    raise ProviderRejected(min(max(after, 0), 3600) if type(after) is int else 0)
                return body.get("result")
    except httpx.HTTPError:
        # Never propagate an HTTPX exception containing the secret token URL.
        raise DeliveryUncertain() from None
