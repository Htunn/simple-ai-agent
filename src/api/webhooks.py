"""Webhook endpoints for channel integrations."""

import hashlib
import hmac
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from src.channels.router import MessageRouter
from src.config import get_settings

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


@router.post("/webhook/alertmanager")
async def alertmanager_webhook(
    request: Request,
    x_alertmanager_secret: str | None = Header(None),
) -> dict:
    """
    Alertmanager webhook receiver endpoint.

    Receives alert payloads from Prometheus Alertmanager (v2 API format).
    Validates optional HMAC secret, persists AlertEvent rows, routes
    active/resolved alerts to the AIOps notification channel.
    """
    settings = get_settings()

    # Optional HMAC secret validation
    if settings.alertmanager_webhook_secret:
        body_bytes = await request.body()
        expected = hmac.new(
            settings.alertmanager_webhook_secret.encode(),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()
        received = x_alertmanager_secret or ""
        if not hmac.compare_digest(expected, received):
            logger.warning("alertmanager_webhook_invalid_secret")
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
        body = __import__("json").loads(body_bytes)
    else:
        body = await request.json()

    alerts: list[dict] = body.get("alerts", [])
    if not alerts:
        return {"status": "ok", "processed": 0}

    logger.info("alertmanager_webhook_received", alert_count=len(alerts))

    processed = 0
    notifications: list[str] = []

    # Import DB + models lazily to avoid circular imports at module load time
    try:
        from src.database import get_db_session
        from src.database.models import AlertEvent

        async with get_db_session() as db_session:
            for alert in alerts:
                labels: dict = alert.get("labels", {})
                annotations: dict = alert.get("annotations", {})
                status: str = alert.get("status", "firing")  # firing | resolved
                rule_name: str = labels.get("alertname", "UnknownAlert")
                severity: str = labels.get("severity", "warning")

                # Parse timestamps
                fired_at_str = alert.get("startsAt")
                resolved_at_str = alert.get("endsAt")
                fired_at = datetime.fromisoformat(fired_at_str.replace("Z", "+00:00")) if fired_at_str else datetime.now(timezone.utc)
                resolved_at = None
                if resolved_at_str and status == "resolved":
                    resolved_at = datetime.fromisoformat(resolved_at_str.replace("Z", "+00:00"))

                # Persist alert event
                alert_event = AlertEvent(
                    id=uuid.uuid4(),
                    rule_name=rule_name,
                    severity=severity,
                    status=status,
                    source="alertmanager",
                    labels=labels,
                    annotations=annotations,
                    fired_at=fired_at,
                    resolved_at=resolved_at,
                )
                db_session.add(alert_event)

                # Build notification message
                icon = "🔥" if status == "firing" else "✅"
                summary = annotations.get("summary", annotations.get("message", rule_name))
                description = annotations.get("description", "")
                namespace = labels.get("namespace", "")
                pod = labels.get("pod", labels.get("instance", ""))
                resource_hint = f" `{pod}`" if pod else (f" ns=`{namespace}`" if namespace else "")

                msg_parts = [f"{icon} **Alert {status.upper()}**: `{rule_name}`{resource_hint}"]
                msg_parts.append(f"Severity: `{severity}` | Source: Alertmanager")
                if summary:
                    msg_parts.append(f"Summary: {summary}")
                if description:
                    msg_parts.append(f"Details: {description}")
                notifications.append("\n".join(msg_parts))
                processed += 1

            await db_session.commit()

    except Exception as e:
        logger.error("alertmanager_db_error", error=str(e))
        # Still try to route notification even if DB fails

    # Route notifications to AIOps channel
    if notifications and message_router:
        try:
            aiops_channel = settings.aiops_notification_channel
            if aiops_channel:
                # aiops_notification_channel format: "channel_type:user_or_channel_id"
                parts = aiops_channel.split(":", 1)
                if len(parts) == 2:
                    ch_type, ch_id = parts
                    for notification in notifications:
                        await message_router.send_message(ch_type, ch_id, notification)
            else:
                logger.debug("aiops_notification_channel_not_configured")
        except Exception as e:
            logger.error("alertmanager_notification_error", error=str(e))

    return {"status": "ok", "processed": processed}
