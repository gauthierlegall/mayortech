"""Authenticated setup and a narrowly secret-authenticated incoming webhook."""

from fastapi import Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .conversations import conversation_owner
from .telegram_bridge import TelegramBridge


class TelegramConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bot_token: str = Field(min_length=25, max_length=200)
    egress_approved: StrictBool
    delivery_mode: str = Field(default="polling", pattern="^(polling|webhook)$")
    content_relay_approved: StrictBool = False


class TelegramPairing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str | None = Field(default=None, max_length=160)


def register_telegram_routes(
    app, repo, tenant, actor, settings, *, conversations=None, hub=None, calendars=None
):
    governance = getattr(app.state, "governance", None)
    service = TelegramBridge(
        repo,
        settings,
        conversations=conversations,
        policy=hub.policy if hub else None,
        vault=hub.vault if hub else None,
        permissions=governance.permissions if governance else None,
        calendars=calendars,
    )

    @app.get("/api/v1/integrations/telegram/status")
    def status(request: Request, response: Response, current=Depends(actor)):
        return service.status(tenant, current, conversation_owner(request, response, current, settings))

    @app.post("/api/v1/integrations/telegram/configure")
    def configure(body: TelegramConfiguration, current=Depends(actor)):
        return service.configure(tenant, current, **body.model_dump())

    @app.post("/api/v1/integrations/telegram/pairing")
    def pair(body: TelegramPairing, request: Request, response: Response, current=Depends(actor)):
        return service.pair(
            tenant,
            current,
            conversation_owner(request, response, current, settings),
            conversation_id=body.conversation_id,
        )

    @app.delete("/api/v1/integrations/telegram/pairing")
    def unlink(request: Request, response: Response, current=Depends(actor)):
        return service.unlink(tenant, current, conversation_owner(request, response, current, settings))

    @app.post("/api/v1/integrations/telegram/webhook")
    def webhook(body: dict, request: Request):
        # This route has no session-actor dependency. The one exact CSRF
        # exception is owned by api.boundary; all authentication is performed
        # here with the secret Telegram header, and public/demo always refuses.
        return service.accept_webhook(
            tenant, request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""), body
        )

    return service
