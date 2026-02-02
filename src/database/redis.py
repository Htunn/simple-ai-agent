"""Redis connection and session cache management."""

from typing import Any

import redis.asyncio as redis
import structlog

from src.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Redis client instance
redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection."""
    global redis_client
    redis_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("redis_initialized", url=settings.redis_url)
    return redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.aclose()
        logger.info("redis_closed")


def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return redis_client


class RedisCache:
    """Redis cache helper class."""

    def __init__(self, client: redis.Redis):
        self.client = client

    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        return await self.client.get(key)

    async def set(
        self, key: str, value: str, ttl: int | None = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        return await self.client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return bool(await self.client.exists(key))

    async def incr(self, key: str) -> int:
        """Increment counter."""
        return await self.client.incr(key)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        return await self.client.expire(key, ttl)

    async def hget(self, name: str, key: str) -> str | None:
        """Get hash field value."""
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value."""
        return await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> dict[str, Any]:
        """Get all hash fields."""
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        return await self.client.hdel(name, *keys)
