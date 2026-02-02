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
from src.services import MessageHandler
from src.utils import configure_logging

logger = structlog.get_logger()
settings = get_settings()

# Global instances
router = None
handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global router, handler

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

    # Create message handler
    logger.info("creating_message_handler")
    handler = MessageHandler(router, ai_client)

    # Set handler for router
    router.set_message_handler(handler.handle_message)

    # Set router for webhook endpoints
    set_message_router(router)

    # Start all channel adapters
    logger.info("starting_channel_adapters")
    asyncio.create_task(router.start_all())

    logger.info("application_started_successfully")

    yield

    # Shutdown
    logger.info("shutting_down_application")

    # Stop channel adapters
    await router.stop_all()

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
