"""Conversation repository for database operations."""

import uuid
from datetime import datetime
from typing import Any, Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Conversation

logger = structlog.get_logger()


class ConversationRepository:
    """Repository for conversation database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_active_by_user(
        self, user_id: uuid.UUID, channel_type: str
    ) -> Optional[Conversation]:
        """Get active conversation for a user on a specific channel."""
        result = await self.session.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.channel_type == channel_type,
                Conversation.is_active == True,
            )
            .order_by(desc(Conversation.last_activity))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        channel_type: str,
        model_override: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            user_id=user_id,
            channel_type=channel_type,
            model_override=model_override,
            metadata=metadata or {},
        )
        self.session.add(conversation)
        await self.session.flush()
        logger.info(
            "conversation_created",
            conversation_id=str(conversation.id),
            user_id=str(user_id),
            channel_type=channel_type,
        )
        return conversation

    async def get_or_create_active(
        self, user_id: uuid.UUID, channel_type: str
    ) -> Conversation:
        """Get active conversation or create new one."""
        conversation = await self.get_active_by_user(user_id, channel_type)
        if conversation is None:
            conversation = await self.create(user_id, channel_type)
        return conversation

    async def update_activity(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Update last activity timestamp."""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.last_activity = datetime.utcnow()
            await self.session.flush()
        return conversation

    async def deactivate(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Deactivate a conversation."""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.is_active = False
            await self.session.flush()
            logger.info("conversation_deactivated", conversation_id=str(conversation_id))
        return conversation

    async def set_model_override(
        self, conversation_id: uuid.UUID, model: str
    ) -> Optional[Conversation]:
        """Set model override for a conversation."""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.model_override = model
            await self.session.flush()
            logger.info(
                "conversation_model_updated",
                conversation_id=str(conversation_id),
                model=model,
            )
        return conversation
