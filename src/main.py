"""Main application entry point."""

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.ai import GitHubModelsClient
from src.api import health_router, limiter, set_message_router, webhook_router
from src.channels import create_router
from src.config import get_settings
from src.database import close_db, close_redis, init_db, init_redis
from src.mcp.mcp_manager import MCPManager
from src.services import MessageHandler
from src.utils import configure_logging

logger = structlog.get_logger()
settings = get_settings()

# Global instances
router = None
handler = None
mcp_manager = None
watchloop = None
approval_manager = None
playbook_executor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global router, handler, mcp_manager, watchloop, approval_manager, playbook_executor

    logger.info("starting_application", environment=settings.environment)

    # Configure logging
    configure_logging(settings.log_level)

    # Initialize database
    logger.info("initializing_database")
    await init_db()

    # Initialize Redis
    logger.info("initializing_redis")
    await init_redis()

    # Create message router and adapters
    logger.info("creating_message_router")
    router = create_router()

    # Create AI client
    logger.info("initializing_ai_client")
    ai_client = GitHubModelsClient()

    # Initialize MCP manager (manages multiple MCP servers with different transports)
    logger.info("initializing_mcp_manager")
    mcp_manager = MCPManager()
    
    # Start all configured MCP servers
    try:
        if await mcp_manager.start():
            server_info = mcp_manager.get_server_info()
            logger.info("mcp_servers_started", 
                       servers=server_info['connected_servers'],
                       total_tools=server_info['total_tools'])
        else:
            logger.warning("mcp_manager_initialization_failed")
            mcp_manager = None
    except Exception as e:
        logger.warning("mcp_initialization_error", error=str(e))
        # Continue without MCP if it fails
        mcp_manager = None

    # Create message handler
    logger.info("creating_message_handler")
    handler = MessageHandler(router, ai_client, mcp_manager)

    # Set handler for router
    router.set_message_handler(handler.handle_message)

    # Set router for webhook endpoints
    set_message_router(router)

    # ──────────────────────────────────────────────────────────────
    # AIOps: initialise approval manager (requires Redis + MCPManager)
    # ──────────────────────────────────────────────────────────────
    try:
        from src.database.redis import get_redis
        from src.services.approval_manager import ApprovalManager
        approval_manager = ApprovalManager(redis_client=get_redis(), mcp_manager=mcp_manager)
        # Expose on handler so NLP layer can forward approval responses
        handler.approval_manager = approval_manager
        logger.info("approval_manager_initialized")
    except Exception as e:
        logger.warning("approval_manager_init_failed", error=str(e))
        approval_manager = None

    # ──────────────────────────────────────────────────────────────
    # AIOps: K8s watch-loop (proactive cluster health polling)
    # ──────────────────────────────────────────────────────────────
    if settings.k8s_watchloop_enabled:
        try:
            from src.aiops.playbooks import PlaybookExecutor, PlaybookRegistry
            from src.aiops.rule_engine import RuleEngine
            from src.monitoring.watchloop import K8sWatchLoop

            rule_engine = RuleEngine()
            # Hoist registry + executor once at startup — not per-event
            _pb_registry = PlaybookRegistry()
            playbook_executor = PlaybookExecutor(
                registry=_pb_registry,
                mcp_manager=mcp_manager,
                approval_manager=approval_manager,
                notify_callback=router.send_message if router else None,
            )

            async def _on_cluster_event(event) -> None:
                """Route watch-loop events → rule engine → approval / auto-remediation."""
                try:
                    matches = rule_engine.evaluate(event.to_dict())
                    if not matches:
                        return

                    # Notify AIOps channel about detected issue
                    if settings.aiops_notification_channel:
                        parts = settings.aiops_notification_channel.split(":", 1)
                        if len(parts) == 2:
                            ch_type, ch_id = parts
                            icon = {"critical": "🚨", "high": "🔴", "medium": "🟡", "low": "🔵"}.get(event.severity, "⚠️")
                            playbook_names = [r for _, r in matches]
                            alert_msg = (
                                f"{icon} **AIOps Alert** [{event.severity.upper()}]\n"
                                f"Type: `{event.event_type}`\n"
                                f"Resource: `{event.resource_kind}/{event.resource_name}`"
                                + (f" in `{event.namespace}`" if event.namespace else "")
                                + f"\n{event.message}"
                            )
                            if matches:
                                alert_msg += f"\n\n🔧 Playbooks queued: `{', '.join(playbook_names)}`"
                                if approval_manager:
                                    alert_msg += "\nHigh-risk steps will require your approval."
                            await router.send_message(ch_type, ch_id, alert_msg)

                    # Execute playbooks via PlaybookExecutor
                    if settings.auto_remediation_enabled and playbook_executor:
                        ch_type, ch_id = "", ""
                        if settings.aiops_notification_channel:
                            parts = settings.aiops_notification_channel.split(":", 1)
                            if len(parts) == 2:
                                ch_type, ch_id = parts

                        for _, playbook_id in matches:
                            try:
                                run = await playbook_executor.execute(
                                    playbook_id=playbook_id,
                                    incident_context=event.to_dict(),
                                    channel_type=ch_type,
                                    channel_target=ch_id,
                                    requested_by="watchloop",
                                )
                                logger.info(
                                    "playbook_run_finished",
                                    playbook=playbook_id,
                                    status=run.status,
                                    steps_done=len(run.step_outputs),
                                )
                            except Exception as pb_exc:
                                logger.error("playbook_execution_error",
                                             playbook=playbook_id, error=str(pb_exc))
                except Exception as exc:
                    logger.error("watchloop_event_handler_error", error=str(exc))

            watchloop = K8sWatchLoop(
                event_callback=_on_cluster_event,
                interval=settings.k8s_watchloop_interval,
            )
            asyncio.create_task(watchloop.start())
            logger.info(
                "k8s_watchloop_started",
                interval=settings.k8s_watchloop_interval,
            )
        except Exception as e:
            logger.warning("k8s_watchloop_init_failed", error=str(e))
            watchloop = None

    # Start all channel adapters
    logger.info("starting_channel_adapters")
    asyncio.create_task(router.start_all())

    logger.info("application_started_successfully")

    yield

    # Shutdown
    logger.info("shutting_down_application")

    # Stop K8s watch-loop
    if watchloop:
        await watchloop.stop()
        logger.info("k8s_watchloop_stopped")

    # Stop channel adapters
    await router.stop_all()

    # Close MCP manager and all servers
    if mcp_manager:
        await mcp_manager.stop()

    # Close database connections
    await close_db()

    # Close Redis connection
    await close_redis()

    logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="Clawbot AI Agent",
    description="Multi-channel AI agent with GitHub Models integration",
    version="0.1.0",
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(health_router, tags=["Health"])
app.include_router(webhook_router, prefix="/api", tags=["Webhooks"])


def get_watchloop():
    """Return current watchloop instance (for health checks)."""
    return watchloop


def get_approval_manager():
    """Return current approval manager instance."""
    return approval_manager


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Clawbot AI Agent",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )
