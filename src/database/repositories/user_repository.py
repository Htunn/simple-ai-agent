"""User repository for database operations."""

import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User

logger = structlog.get_logger()


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_channel_user(
        self, channel_type: str, channel_user_id: str
    ) -> Optional[User]:
        """Get user by channel type and channel user ID."""
        result = await self.session.execute(
            select(User).where(
                User.channel_type == channel_type,
                User.channel_user_id == channel_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        channel_type: str,
        channel_user_id: str,
        username: Optional[str] = None,
        preferred_model: Optional[str] = None,
    ) -> User:
        """Create a new user."""
        user = User(
            channel_type=channel_type,
            channel_user_id=channel_user_id,
            username=username,
            preferred_model=preferred_model,
        )
        self.session.add(user)
        await self.session.flush()
        logger.info(
            "user_created",
            user_id=str(user.id),
            channel_type=channel_type,
            channel_user_id=channel_user_id,
        )
        return user

    async def get_or_create(
        self, channel_type: str, channel_user_id: str, username: Optional[str] = None
    ) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_channel_user(channel_type, channel_user_id)
        if user is None:
            user = await self.create(channel_type, channel_user_id, username)
        return user

    async def update_preferred_model(
        self, user_id: uuid.UUID, model: str
    ) -> Optional[User]:
        """Update user's preferred model."""
        user = await self.get_by_id(user_id)
        if user:
            user.preferred_model = model
            await self.session.flush()
            logger.info("user_model_updated", user_id=str(user_id), model=model)
        return user
