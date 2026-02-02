"""Context builder for AI conversations."""

import uuid
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Message
from src.database.repositories import MessageRepository

logger = structlog.get_logger()


class ContextBuilder:
    """Builds conversation context from message history."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.message_repo = MessageRepository(db_session)

    async def build_context(
        self,
        conversation_id: uuid.UUID,
        max_messages: int = 20,
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, str]]:
        """
        Build conversation context for AI model.

        Args:
            conversation_id: Conversation ID
            max_messages: Maximum number of messages to include
            system_prompt: Optional system prompt to prepend

        Returns:
            List of message dictionaries for AI model
        """
        # Get recent messages
        messages = await self.message_repo.get_conversation_history(
            conversation_id, limit=max_messages
        )

        # Convert to AI format
        context = []

        # Add system prompt if provided
        if system_prompt:
            context.append({"role": "system", "content": system_prompt})

        # Add conversation messages
        for msg in messages:
            context.append({"role": msg.role, "content": msg.content})

        logger.debug(
            "context_built",
            conversation_id=str(conversation_id),
            message_count=len(context),
        )

        return context

    async def add_user_message(
        self,
        conversation_id: uuid.UUID,
        content: str,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Add user message to conversation."""
        return await self.message_repo.create(
            conversation_id=conversation_id,
            role="user",
            content=content,
            metadata=metadata,
        )

    async def add_assistant_message(
        self,
        conversation_id: uuid.UUID,
        content: str,
        model_used: str,
        token_count: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Add assistant message to conversation."""
        return await self.message_repo.create(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            model_used=model_used,
            token_count=token_count,
            metadata=metadata,
        )

    async def get_message_stats(self, conversation_id: uuid.UUID) -> dict:
        """Get statistics about conversation messages."""
        message_count = await self.message_repo.count_conversation_messages(
            conversation_id
        )
        total_tokens = await self.message_repo.get_total_tokens(conversation_id)

        return {
            "message_count": message_count,
            "total_tokens": total_tokens,
            "conversation_id": str(conversation_id),
        }
