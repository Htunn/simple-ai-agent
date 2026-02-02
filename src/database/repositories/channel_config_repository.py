"""Channel config repository for database operations."""

from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ChannelConfig

logger = structlog.get_logger()


class ChannelConfigRepository:
    """Repository for channel configuration database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_channel_type(self, channel_type: str) -> Optional[ChannelConfig]:
        """Get channel config by channel type."""
        result = await self.session.execute(
            select(ChannelConfig).where(ChannelConfig.channel_type == channel_type)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        channel_type: str,
        default_model: str,
        settings: Optional[dict[str, Any]] = None,
    ) -> ChannelConfig:
        """Create a new channel config."""
        config = ChannelConfig(
            channel_type=channel_type,
            default_model=default_model,
            settings=settings or {},
        )
        self.session.add(config)
        await self.session.flush()
        logger.info(
            "channel_config_created",
            channel_type=channel_type,
            default_model=default_model,
        )
        return config

    async def get_or_create(
        self, channel_type: str, default_model: str
    ) -> ChannelConfig:
        """Get existing config or create new one."""
        config = await self.get_by_channel_type(channel_type)
        if config is None:
            config = await self.create(channel_type, default_model)
        return config

    async def update_default_model(
        self, channel_type: str, model: str
    ) -> Optional[ChannelConfig]:
        """Update default model for a channel."""
        config = await self.get_by_channel_type(channel_type)
        if config:
            config.default_model = model
            await self.session.flush()
            logger.info(
                "channel_model_updated", channel_type=channel_type, model=model
            )
        return config
