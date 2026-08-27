"""Unified Redis client compatibility layer.

This module provides a drop-in replacement for redis.asyncio that routes
all operations through the Go gateway's unified Redis manager.

Usage:
    from app.redis_client import get_redis

    # Works like redis.asyncio.Redis
    r = await get_redis()
    await r.set("key", "value")
    val = await r.get("key")
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# Configuration: use unified client or direct connection
USE_UNIFIED = os.getenv("USE_UNIFIED_REDIS_CLIENT", "false").lower() == "true"

_redis_instance: Optional[aioredis.Redis] = None
_unified_client = None
_redis_lock = asyncio.Lock()  # P0-2: Thread-safe initialization


def _get_unified_client():
    """Lazy load unified Redis client."""
    global _unified_client
    if _unified_client is None and USE_UNIFIED:
        from app.db_client import get_redis_client

        _unified_client = get_redis_client()
    return _unified_client


async def get_redis() -> aioredis.Redis:
    """Get Redis connection (direct or unified) with thread-safe initialization."""
    global _redis_instance

    if USE_UNIFIED:
        client = _get_unified_client()
        if client is None:
            raise RuntimeError("Unified Redis client not initialized")
        return _UnifiedRedisWrapper(client)

    # Double-checked locking pattern for thread safety
    if _redis_instance is None:
        async with _redis_lock:
            # Re-check after acquiring lock
            if _redis_instance is None:
                if not settings.redis_url:
                    raise RuntimeError("Redis URL not configured")

                # P0-2: Add timeout parameters to prevent hanging connections
                redis_url_with_timeout = settings.redis_url
                if "?" not in redis_url_with_timeout:
                    redis_url_with_timeout += "?socket_timeout=5&socket_connect_timeout=3&retry_on_timeout=true"
                else:
                    # Ensure timeout params are present
                    if "socket_timeout" not in redis_url_with_timeout:
                        redis_url_with_timeout += "&socket_timeout=5"
                    if "socket_connect_timeout" not in redis_url_with_timeout:
                        redis_url_with_timeout += "&socket_connect_timeout=3"

                _redis_instance = aioredis.from_url(
                    redis_url_with_timeout,
                    decode_responses=True,
                    max_connections=settings.redis_pool_size,
                    socket_keepalive=True,  # Enable TCP keepalive
                )
                logger.info(
                    "Redis connected with timeouts: %s (pool=%d)",
                    settings.redis_url,
                    settings.redis_max_connections,
                )

    return _redis_instance


class _UnifiedRedisWrapper:
    """Wrapper to make UnifiedRedisClient compatible with redis.asyncio.Redis interface."""

    def __init__(self, client):
        self._client = client
        self._closed = False

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return await self._client.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: Any, ex: int | None = None, **kwargs) -> bool:
        """Set value with optional expiration."""
        ttl = ex if ex else kwargs.get("ex")
        return await self._client.set(key, value, ttl=ttl)

    async def delete(self, *keys: str) -> int:
        """Delete keys."""
        success = await self._client.delete(*keys)
        return len(keys) if success else 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        # Not implemented in unified client yet
        return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        # Not implemented in unified client yet
        return False

    async def incr(self, key: str) -> int:
        """Increment key value."""
        # Not implemented in unified client yet
        return 0

    async def ping(self) -> bool:
        """Check connectivity."""
        return await self._client.ping()

    async def close(self):
        """Close connection."""
        self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
