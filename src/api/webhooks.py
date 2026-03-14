"""Webhook endpoints for channel integrations."""

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime

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

        # Verify X-Telegram-Bot-Api-Secret-Token if a secret is configured.
        # Set the same token via setWebhook(secret_token=...) when registering the URL.
        _settings = get_settings()
        if _settings.telegram_webhook_secret:
            received_token = x_telegram_bot_api_secret_token or ""
            if not hmac.compare_digest(_settings.telegram_webhook_secret, received_token):
                logger.warning("telegram_webhook_invalid_secret")
                raise HTTPException(status_code=403, detail="Invalid webhook secret")

        # Get Telegram adapter
        telegram_adapter = message_router.get_adapter("telegram")
        if not telegram_adapter:
            raise HTTPException(status_code=404, detail="Telegram adapter not found")

        # Process the update
        from telegram import Update

        update = Update.de_json(body, telegram_adapter.application.bot)  # type: ignore[attr-defined]
        if update:
            await telegram_adapter.handle_incoming_message(update)

        return {"status": "ok"}

    except Exception as e:
        logger.error("telegram_webhook_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/webhook/slack")
async def slack_webhook(request: Request) -> dict:
    """
    Slack webhook endpoint for Events API.

    Returns 200 immediately after signature verification, then processes
    the event in the background.  This satisfies Slack's 3-second SLA and
    prevents retry-induced duplicate messages.
    """
    if not message_router:
        raise HTTPException(status_code=503, detail="Message router not initialized")

    try:
        # Read raw body once — needed for both HMAC verification and JSON parsing
        body_bytes = await request.body()
        body = json.loads(body_bytes)

        # ── URL verification challenge (no auth needed) ──────────────────
        if body.get("type") == "url_verification":
            logger.info("slack_url_verification_received")
            return {"challenge": body.get("challenge")}

        # ── Event callback ───────────────────────────────────────────────
        if body.get("type") == "event_callback":
            settings = get_settings()

            # Signature verification
            if settings.slack_signing_secret:
                timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
                signature = request.headers.get("X-Slack-Signature", "")

                request_time = int(timestamp) if timestamp else 0
                if abs(time.time() - request_time) > 300:
                    raise HTTPException(status_code=400, detail="Request too old")

                sig_basestring = f"v0:{timestamp}:{body_bytes.decode()}"
                expected_signature = (
                    "v0="
                    + hmac.new(
                        settings.slack_signing_secret.encode(),
                        sig_basestring.encode(),
                        hashlib.sha256,
                    ).hexdigest()
                )

                if not hmac.compare_digest(expected_signature, signature):
                    raise HTTPException(status_code=400, detail="Invalid signature")

            # ── Deduplication via event_id ────────────────────────────────
            # Slack retries if no 200 within 3 s. We process async, so Slack
            # will almost always receive 200 in time, but guard against any
            # edge-case retry causing a duplicate reply.
            event_id = body.get("event_id")
            if event_id:
                try:
                    from src.database.redis import get_redis

                    redis = get_redis()
                    dedupe_key = f"slack:event:{event_id}"
                    # SET NX with 5-minute expiry — returns True only on first call
                    already_seen = await redis.get(dedupe_key)
                    if already_seen:
                        logger.info("slack_duplicate_event_skipped", event_id=event_id)
                        return {"status": "ok"}
                    await redis.setex(dedupe_key, 300, "1")
                except Exception as redis_err:
                    # Redis unavailable — log and continue (no dedup, but don't break)
                    logger.warning("slack_dedup_redis_error", error=str(redis_err))

            # ── Get Slack adapter ─────────────────────────────────────────
            slack_adapter = message_router.get_adapter("slack")
            if not slack_adapter:
                raise HTTPException(status_code=404, detail="Slack adapter not found")

            event = body.get("event", {})
            if event:
                # Fire-and-forget: return 200 immediately, process in background.
                # This prevents Slack from timing out (3-second limit) and retrying.
                asyncio.create_task(slack_adapter.handle_incoming_message(event))

            return {"status": "ok"}

        # ── Unknown event types ──────────────────────────────────────────
        logger.warning("slack_unknown_event_type", event_type=body.get("type"))
        return {"status": "ignored"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("slack_webhook_error", error=str(e), error_type=type(e).__name__)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
                fired_at = (
                    datetime.fromisoformat(fired_at_str.replace("Z", "+00:00"))
                    if fired_at_str
                    else datetime.now(UTC)
                )
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

    return {"status": "ok", "processed": processed, "alerts_ingested": processed}
