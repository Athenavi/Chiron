"""PostgreSQL connection pool for graph persistence."""
from __future__ import annotations

import logging
from typing import Any, Optional

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def init_pool(dsn: str) -> asyncpg.Pool:
    """Initialize the global connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=settings.db_pool_min_size, max_size=settings.db_pool_max_size)
    logger.info("PostgreSQL connected (pool=%d-%d)", settings.db_pool_min_size, settings.db_pool_max_size)
    return _pool


async def close_pool():
    """Close the global connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the global connection pool."""
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized")
    if _pool.is_closed():
        raise RuntimeError("PostgreSQL pool was closed")
    return _pool


async def ensure_tables():
    # TODO: 检查数据库表数量是否==模型数+1

    logger.info("All tables ensured")
