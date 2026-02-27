"""Webhook endpoints for channel integrations."""

import hashlib
import hmac
import time
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


@router.post("/webhook/slack")
async def slack_webhook(request: Request) -> dict:
    """
    Slack webhook endpoint for Events API.
    
    Receives events from Slack (messages, app mentions, etc.)
    """
    if not message_router:
        raise HTTPException(status_code=503, detail="Message router not initialized")

    try:
        # Get request body
        body = await request.json()
        
        # Handle URL verification challenge
        if body.get("type") == "url_verification":
            logger.info("slack_url_verification_received")
            return {"challenge": body.get("challenge")}
        
        # Handle event callbacks
        if body.get("type") == "event_callback":
            from src.config import get_settings
            settings = get_settings()
            
            # Verify signing secret (optional but recommended)
            if settings.slack_signing_secret:
                timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
                signature = request.headers.get("X-Slack-Signature", "")
                
                # Calculate expected signature
                import time
                request_time = int(timestamp) if timestamp else 0
                current_time = int(time.time())
                
                # Reject old requests (prevent replay attacks)
                if abs(current_time - request_time) > 60 * 5:
                    raise HTTPException(status_code=400, detail="Request too old")
                
                # Verify signature
                import hashlib
                body_bytes = await request.body()
                sig_basestring = f"v0:{timestamp}:{body_bytes.decode()}"
                expected_signature = "v0=" + hmac.new(
                    settings.slack_signing_secret.encode(),
                    sig_basestring.encode(),
                    hashlib.sha256,
                ).hexdigest()
                
                if not hmac.compare_digest(expected_signature, signature):
                    raise HTTPException(status_code=400, detail="Invalid signature")
            
            # Get Slack adapter
            slack_adapter = message_router.get_adapter("slack")
            if not slack_adapter:
                raise HTTPException(status_code=404, detail="Slack adapter not found")
            
            # Extract and process the event
            event = body.get("event", {})
            if event:
                await slack_adapter.handle_incoming_message(event)
            
            return {"status": "ok"}
        
        # Handle other event types
        logger.warning("slack_unknown_event_type", event_type=body.get("type"))
        return {"status": "ignored"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("slack_webhook_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhook/test")
async def webhook_test() -> dict:
    """Test endpoint to verify webhooks are working."""
    return {"status": "webhooks_active", "message": "Webhook server is running"}
