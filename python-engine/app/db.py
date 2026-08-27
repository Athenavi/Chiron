"""PostgreSQL connection pool for graph persistence.

This module provides a compatibility layer that can use either:
1. Direct asyncpg connection (legacy mode, for development)
2. Unified DB client through Go gateway (recommended for production)

The mode is controlled by USE_UNIFIED_DB_CLIENT environment variable.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Configuration: use unified client or direct connection
USE_UNIFIED = os.getenv("USE_UNIFIED_DB_CLIENT", "false").lower() == "true"

_pool: Optional[asyncpg.Pool] = None
_unified_client = None


def _get_unified_client():
    """Lazy load unified client."""
    global _unified_client
    if _unified_client is None and USE_UNIFIED:
        from app.db_client import get_db_client
        _unified_client = get_db_client()
    return _unified_client


async def init_pool(dsn: str) -> asyncpg.Pool:
    """Initialize the global connection pool (legacy mode only)."""
    if USE_UNIFIED:
        logger.info("Using unified DB client through Go gateway")
        return None
    
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=settings.db_pool_min_size, max_size=settings.db_pool_max_size)
    logger.info("PostgreSQL connected directly (pool=%d-%d)", settings.db_pool_min_size, settings.db_pool_max_size)
    return _pool


async def close_pool():
    """Close the global connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
    
    # Close unified client
    if _unified_client:
        from app.db_client import close_clients
        await close_clients()


def get_pool() -> asyncpg.Pool:
    """Get the global connection pool or unified client wrapper."""
    if USE_UNIFIED:
        client = _get_unified_client()
        if client is None:
            raise RuntimeError("Unified DB client not initialized")
        # Return a mock pool object that delegates to unified client
        return _UnifiedPoolWrapper(client)
    
    if _pool is None:
        raise RuntimeError("PostgreSQL pool not initialized")
    # Check if pool is closed (using internal attribute)
    if getattr(_pool, "_closed", False):
        raise RuntimeError("PostgreSQL pool was closed")
    return _pool


class _UnifiedPoolWrapper:
    """Wrapper to make UnifiedDBClient compatible with asyncpg.Pool interface."""
    
    def __init__(self, client):
        self._client = client
    
    async def fetchrow(self, query: str, *args):
        """Execute query and return single row."""
        result = await self._client.fetch_one(query, list(args))
        return _RowDict(result) if result else None
    
    async def fetch(self, query: str, *args):
        """Execute query and return all rows."""
        results = await self._client.fetch_all(query, list(args))
        return [_RowDict(r) for r in results]
    
    async def execute(self, query: str, *args) -> str:
        """Execute write SQL."""
        affected = await self._client.execute(query, list(args))
        return str(affected)
    
    async def executemany(self, query: str, args_list: list):
        """Batch execute."""
        queries = [query % tuple(a) if isinstance(a, tuple) else query for a in args_list]
        return await self._client.batch_execute(queries)
    
    async def transaction(self, **kwargs):
        """Return a transaction context manager (not fully implemented)."""
        raise NotImplementedError("Transactions not supported in unified mode yet")


class _RowDict(dict):
    """Dictionary-like row object compatible with asyncpg.Record."""
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


async def ensure_tables():
    """确保必要的表存在，不存在则提示需要运行迁移"""
    pool = get_pool()
    
    required_tables = [
        'users', 'sessions', 'agents', 'conversations', 'messages',
        'knowledge_bases', 'knowledge_documents', 'knowledge_chunks',
        'media_assets', 'uploads', 'workflows', 'workflow_instances',
        'cron_jobs', 'audit_logs', 'billing_records', 'credit_transactions',
        'payments', 'ent_oidc_providers', 'ent_user_identities',
        'ent_captcha_config', 'ent_quota_pools', 'ent_quota_allocations',
    ]
    
    try:
        # 查询所有已存在的表
        existing = await pool.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        existing_names = {row['table_name'] for row in existing}
        
        missing = [t for t in required_tables if t not in existing_names]
        
        if missing:
            logger.warning(
                f"Missing database tables: {', '.join(missing)}. "
                f"Please run: alembic upgrade head"
            )
            return False
        
        logger.info("All required database tables exist")
        return True
        
    except Exception as e:
        logger.error(f"Failed to check database tables: {e}")
        return False

