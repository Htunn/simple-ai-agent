"""Message repository for database operations."""

import uuid
from typing import Any, Optional

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Message

logger = structlog.get_logger()


class MessageRepository:
    """Repository for message database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        model_used: Optional[str] = None,
        token_count: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Message:
        """Create a new message."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            model_used=model_used,
            token_count=token_count,
            extra_data=metadata or {},
        )
        self.session.add(message)
        await self.session.flush()
        logger.debug(
            "message_created",
            conversation_id=str(conversation_id),
            role=role,
            content_length=len(content),
        )
        return message

    async def get_conversation_history(
        self, conversation_id: uuid.UUID, limit: int = 50
    ) -> list[Message]:
        """Get conversation history ordered by timestamp."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent_messages(
        self, conversation_id: uuid.UUID, limit: int = 10
    ) -> list[Message]:
        """Get most recent messages in reverse chronological order."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.timestamp))
            .limit(limit)
        )
        # Reverse to get chronological order
        return list(reversed(result.scalars().all()))

    async def count_conversation_messages(self, conversation_id: uuid.UUID) -> int:
        """Count messages in a conversation."""
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        return len(result.scalars().all())

    async def get_total_tokens(self, conversation_id: uuid.UUID) -> int:
        """Get total token count for a conversation."""
        result = await self.session.execute(
            select(Message).where(Message.conversation_id == conversation_id)
        )
        messages = result.scalars().all()
        return sum(msg.token_count or 0 for msg in messages)
