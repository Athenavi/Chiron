"""Unified database and Redis client for Python engine.

This module provides a unified interface to access PostgreSQL and Redis
through the Go gateway's internal API endpoints, instead of direct connections.

Benefits:
- Centralized connection management in Go layer
- Unified monitoring and health checks
- Easy scaling (read replicas, sharding)
- Reduced database exposure surface
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DBClientError(Exception):
    """Database client error."""
    pass


class RedisClientError(Exception):
    """Redis client error."""
    pass


class UnifiedDBClient:
    """Unified database client that calls Go gateway API."""

    def __init__(self, base_url: str | None = None, internal_token: str | None = None):
        self.base_url = (base_url or settings.gateway_internal_url).rstrip("/")
        self.internal_token = internal_token or settings.internal_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        client = await self._get_client()
        headers = {"X-Internal-Token": self.internal_token}
        url = f"{self.base_url}{path}"

        try:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, headers=headers, json=data)

            resp.raise_for_status()
            result = resp.json()
            if not result.get("success"):
                raise DBClientError(result.get("error", "unknown error"))
            return result.get("data", {})
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise DBClientError(f"HTTP {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise DBClientError(str(e)) from e

    async def fetch_one(self, sql: str, args: list | None = None) -> dict | None:
        """Execute query and return first row."""
        data = {"sql": sql, "args": args or []}
        result = await self._request("POST", "/v1/internal/db/query", data)
        rows = result.get("rows", [])
        return rows[0] if rows else None

    async def fetch_all(self, sql: str, args: list | None = None) -> list[dict]:
        """Execute query and return all rows."""
        data = {"sql": sql, "args": args or []}
        result = await self._request("POST", "/v1/internal/db/query", data)
        return result.get("rows", [])

    async def execute(self, sql: str, args: list | None = None) -> int:
        """Execute write SQL and return affected rows."""
        data = {"sql": sql, "args": args or []}
        result = await self._request("POST", "/v1/internal/db/execute", data)
        return result.get("rows_affected", 0)

    async def batch_execute(self, queries: list[str]) -> bool:
        """Batch execute multiple SQL statements."""
        data = {"queries": queries}
        result = await self._request("POST", "/v1/internal/db/batch-execute", data)
        return result.get("success", False)

    async def health_check(self) -> dict:
        """Check database health."""
        return await self._request("GET", "/v1/internal/db/health")

    async def ping(self) -> bool:
        """Simple connectivity check."""
        try:
            result = await self.health_check()
            return result.get("available", False) and result.get("ping_ok", False)
        except Exception:
            return False


class UnifiedRedisClient:
    """Unified Redis client that calls Go gateway API."""

    def __init__(self, base_url: str | None = None, internal_token: str | None = None):
        self.base_url = (base_url or settings.gateway_internal_url).rstrip("/")
        self.internal_token = internal_token or settings.internal_token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        client = await self._get_client()
        headers = {"X-Internal-Token": self.internal_token}
        url = f"{self.base_url}{path}"

        try:
            if method == "GET":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.post(url, headers=headers, json=data)

            resp.raise_for_status()
            result = resp.json()
            if not result.get("success"):
                raise RedisClientError(result.get("error", "unknown error"))
            return result.get("data", {})
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise RedisClientError(f"HTTP {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise RedisClientError(str(e)) from e

    async def get(self, key: str) -> str | None:
        """Get value by key."""
        data = {"key": key}
        result = await self._request("POST", "/v1/internal/redis/get", data)
        return result.get("value")

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value with optional TTL (seconds)."""
        data = {"key": key, "value": value}
        if ttl is not None:
            data["ttl"] = ttl
        result = await self._request("POST", "/v1/internal/redis/set", data)
        return result.get("success", False)

    async def delete(self, *keys: str) -> bool:
        """Delete one or more keys."""
        data = {"keys": list(keys)}
        result = await self._request("POST", "/v1/internal/redis/del", data)
        return result.get("success", False)

    async def health_check(self) -> dict:
        """Check Redis health."""
        return await self._request("GET", "/v1/internal/redis/health")

    async def ping(self) -> bool:
        """Simple connectivity check."""
        try:
            result = await self.health_check()
            return result.get("available", False) and result.get("ping_ok", False)
        except Exception:
            return False


# Global instances
_db_client: Optional[UnifiedDBClient] = None
_redis_client: Optional[UnifiedRedisClient] = None


def get_db_client() -> UnifiedDBClient:
    """Get global database client instance."""
    global _db_client
    if _db_client is None:
        _db_client = UnifiedDBClient()
    return _db_client


def get_redis_client() -> UnifiedRedisClient:
    """Get global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = UnifiedRedisClient()
    return _redis_client


async def close_clients():
    """Close all client connections."""
    global _db_client, _redis_client
    if _db_client:
        await _db_client.close()
        _db_client = None
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
