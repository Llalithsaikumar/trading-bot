"""
Redis client singleton and helper utilities.
Uses redis-py with hiredis parser for performance.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger

if TYPE_CHECKING:
    from redis.asyncio import Redis

# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------
_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """Return the shared async Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        logger.info("Redis client initialised", url=settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool (called on app shutdown)."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_redis() -> Redis:
    """Inject Redis client into route handlers."""
    return await get_redis_client()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def cache_set(key: str, value: str, ttl: int | None = None) -> None:
    """Set a string value with optional TTL (seconds)."""
    client = await get_redis_client()
    if ttl:
        await client.setex(key, ttl, value)
    else:
        await client.set(key, value)


async def cache_get(key: str) -> str | None:
    """Get a cached value, returns None if not found."""
    client = await get_redis_client()
    return await client.get(key)


async def cache_delete(key: str) -> None:
    client = await get_redis_client()
    await client.delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    client = await get_redis_client()
    keys = await client.keys(pattern)
    if keys:
        return await client.delete(*keys)
    return 0
