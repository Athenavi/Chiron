"""Test unified database and Redis clients."""
import asyncio
import os
import pytest


# Set environment before importing
os.environ["USE_UNIFIED_DB_CLIENT"] = "true"
os.environ["USE_UNIFIED_REDIS_CLIENT"] = "true"


@pytest.mark.asyncio
async def test_unified_db_client():
    """Test unified database client operations."""
    from app.db_client import get_db_client
    
    db = get_db_client()
    
    # Test health check
    health = await db.health_check()
    assert "available" in health
    print(f"DB Health: {health}")
    
    # Test ping
    is_alive = await db.ping()
    print(f"DB Ping: {is_alive}")


@pytest.mark.asyncio
async def test_unified_redis_client():
    """Test unified Redis client operations."""
    from app.db_client import get_redis_client
    
    redis = get_redis_client()
    
    # Test health check
    health = await redis.health_check()
    assert "available" in health
    print(f"Redis Health: {health}")
    
    # Test basic operations
    await redis.set("test_key", "test_value", ttl=60)
    value = await redis.get("test_key")
    assert value == "test_value"
    
    await redis.delete("test_key")
    value = await redis.get("test_key")
    assert value is None
    
    print("Redis operations successful")


@pytest.mark.asyncio
async def test_compatibility_layer():
    """Test that existing code still works with compatibility layer."""
    from app.db import get_pool
    from app.redis_client import get_redis
    
    # Test DB pool wrapper
    pool = get_pool()
    print(f"Pool type: {type(pool)}")
    
    # Test Redis wrapper
    redis = await get_redis()
    print(f"Redis type: {type(redis)}")
    
    # Basic operations should work
    await redis.set("compat_test", "value")
    val = await redis.get("compat_test")
    assert val == "value"
    
    await redis.delete("compat_test")
    print("Compatibility layer works!")


if __name__ == "__main__":
    asyncio.run(test_unified_db_client())
    asyncio.run(test_unified_redis_client())
    asyncio.run(test_compatibility_layer())
    print("\n✅ All tests passed!")
