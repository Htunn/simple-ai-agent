#!/usr/bin/env python3
"""Initialize database with migrations."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from alembic import command
from alembic.config import Config

from src.config import get_settings
from src.utils import configure_logging

logger = structlog.get_logger()
settings = get_settings()


async def init_database():
    """Initialize database with Alembic migrations."""
    configure_logging(settings.log_level)

    logger.info("initializing_database")

    # Get alembic config
    alembic_cfg = Config("alembic.ini")

    try:
        # Run migrations
        logger.info("running_migrations")
        command.upgrade(alembic_cfg, "head")
        logger.info("migrations_completed")

        # Optionally seed initial data
        await seed_initial_data()

        logger.info("database_initialization_complete")

    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise


async def seed_initial_data():
    """Seed initial data (channel configs, etc)."""
    from src.database import get_db_session
    from src.database.repositories import ChannelConfigRepository

    logger.info("seeding_initial_data")

    async with get_db_session() as session:
        channel_repo = ChannelConfigRepository(session)

        # Create default channel configs
        channels = [
            ("discord", settings.default_model),
            ("telegram", settings.default_model),
        ]

        for channel_type, default_model in channels:
            existing = await channel_repo.get_by_channel_type(channel_type)
            if not existing:
                await channel_repo.create(channel_type, default_model)
                logger.info("channel_config_created", channel_type=channel_type)

    logger.info("initial_data_seeded")


if __name__ == "__main__":
    asyncio.run(init_database())
