"""Webhook endpoints for channel integrations."""

import hmac
import hashlib
from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from src.channels.router import MessageRouter

logger = structlog.get_logger()
router = APIRouter()

# Global router instance (will be set by main app)
message_router: MessageRouter | None = None


def set_message_router(router_instance: MessageRouter) -> None:
    """Set the global message router instance."""
    global message_router
    message_router = router_instance


@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict:
    """
    Telegram webhook endpoint.

    Receives updates from Telegram Bot API.
    """
    if not message_router:
        raise HTTPException(status_code=503, detail="Message router not initialized")

    try:
        # Get request body
        body = await request.json()

        # TODO: Implement signature verification when webhook secret is configured
        # For now, accept all requests in development

        # Get Telegram adapter
        telegram_adapter = message_router.get_adapter("telegram")
        if not telegram_adapter:
            raise HTTPException(status_code=404, detail="Telegram adapter not found")

        # Process the update
        from telegram import Update

        update = Update.de_json(body, telegram_adapter.application.bot)
        if update:
            await telegram_adapter.handle_incoming_message(update)

        return {"status": "ok"}

    except Exception as e:
        logger.error("telegram_webhook_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/discord")
async def discord_webhook(request: Request) -> dict:
    """
    Discord webhook endpoint (if using webhooks instead of gateway).

    For now, Discord uses WebSocket gateway, but this can be extended.
    """
    raise HTTPException(
        status_code=501, detail="Discord uses WebSocket gateway, not webhooks"
    )


@router.get("/webhook/test")
async def webhook_test() -> dict:
    """Test endpoint to verify webhooks are working."""
    return {"status": "webhooks_active", "message": "Webhook server is running"}
