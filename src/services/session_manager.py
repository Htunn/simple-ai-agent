"""Session management service with Redis caching."""

import json
import uuid
from dataclasses import asdict, dataclass
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.redis import RedisCache
from src.database.repositories import ConversationRepository, UserRepository

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class SessionData:
    """Session data structure."""

    conversation_id: str
    user_id: str
    channel_type: str
    message_count: int
    last_activity: str


class SessionManager:
    """Manages user sessions with Redis caching."""

    def __init__(self, redis_cache: RedisCache, db_session: AsyncSession):
        self.cache = redis_cache
        self.db_session = db_session
        self.user_repo = UserRepository(db_session)
        self.conversation_repo = ConversationRepository(db_session)

    def _session_key(self, channel_type: str, channel_user_id: str) -> str:
        """Generate session cache key."""
        return f"session:{channel_type}:{channel_user_id}"

    async def get_or_create_session(
        self, channel_type: str, channel_user_id: str, username: Optional[str] = None
    ) -> SessionData:
        """Get existing session from cache or database, or create new one."""
        cache_key = self._session_key(channel_type, channel_user_id)

        # Check Redis cache first
        cached = await self.cache.hgetall(cache_key)
        if cached:
            logger.debug("session_cache_hit", channel_type=channel_type)
            return SessionData(**cached)

        # Get or create user
        user = await self.user_repo.get_or_create(
            channel_type, channel_user_id, username
        )

        # Get or create active conversation
        conversation = await self.conversation_repo.get_or_create_active(
            user.id, channel_type
        )

        # Create session data
        session_data = SessionData(
            conversation_id=str(conversation.id),
            user_id=str(user.id),
            channel_type=channel_type,
            message_count=0,
            last_activity=conversation.last_activity.isoformat(),
        )

        # Cache in Redis with TTL
        await self._cache_session(cache_key, session_data)

        logger.info(
            "session_created",
            conversation_id=session_data.conversation_id,
            user_id=session_data.user_id,
            channel_type=channel_type,
        )

        return session_data

    async def _cache_session(self, cache_key: str, session_data: SessionData) -> None:
        """Cache session data in Redis."""
        session_dict = asdict(session_data)
        for key, value in session_dict.items():
            await self.cache.hset(cache_key, key, str(value))
        await self.cache.expire(cache_key, settings.session_ttl_seconds)

    async def update_session_activity(
        self, channel_type: str, channel_user_id: str
    ) -> None:
        """Update session last activity timestamp."""
        cache_key = self._session_key(channel_type, channel_user_id)
        session_data = await self.get_or_create_session(channel_type, channel_user_id)

        # Update in database
        await self.conversation_repo.update_activity(
            uuid.UUID(session_data.conversation_id)
        )

        # Update cache TTL
        await self.cache.expire(cache_key, settings.session_ttl_seconds)

    async def increment_message_count(
        self, channel_type: str, channel_user_id: str
    ) -> int:
        """Increment message count in session."""
        cache_key = self._session_key(channel_type, channel_user_id)
        count_str = await self.cache.hget(cache_key, "message_count")
        count = int(count_str) if count_str else 0
        count += 1
        await self.cache.hset(cache_key, "message_count", str(count))
        return count

    async def clear_session(self, channel_type: str, channel_user_id: str) -> None:
        """Clear session cache and deactivate conversation."""
        cache_key = self._session_key(channel_type, channel_user_id)
        session_data = await self.get_or_create_session(channel_type, channel_user_id)

        # Deactivate conversation
        await self.conversation_repo.deactivate(
            uuid.UUID(session_data.conversation_id)
        )

        # Clear cache
        await self.cache.delete(cache_key)

        logger.info(
            "session_cleared",
            conversation_id=session_data.conversation_id,
            channel_type=channel_type,
        )

    async def get_conversation_id(
        self, channel_type: str, channel_user_id: str
    ) -> uuid.UUID:
        """Get conversation ID for a session."""
        session_data = await self.get_or_create_session(channel_type, channel_user_id)
        return uuid.UUID(session_data.conversation_id)
