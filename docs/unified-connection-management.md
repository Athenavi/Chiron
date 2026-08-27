# 统一连接管理架构

## 概述

本架构实现了 Go 层统一管理 PostgreSQL 和 Redis 连接,Python 引擎通过 HTTP API 间接访问的设计模式。

### 核心优势

1. **无缝扩展**: 支持读写分离、分片、故障转移等高级特性
2. **统一监控**: 所有数据库操作集中管理,便于性能分析和告警
3. **安全性提升**: 减少数据库暴露面,降低配置泄露风险
4. **一致性保证**: 复用 Go 的连接池配置(超时/重试/健康检查)

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                  Python Engine                       │
│  ┌──────────────┐    ┌──────────────┐               │
│  │ UnifiedDB    │    │UnifiedRedis  │               │
│  │ Client       │    │ Client       │               │
│  └──────┬───────┘    └──────┬───────┘               │
│         │                   │                        │
│         └────────┬──────────┘                        │
│                  │ HTTP API                          │
└──────────────────┼───────────────────────────────────┘
                   │ X-Internal-Token
┌──────────────────┼───────────────────────────────────┐
│              Go Gateway                               │
│  ┌──────────────▼──────────────┐                     │
│  │  /v1/internal/db/*          │                     │
│  │  /v1/internal/redis/*       │                     │
│  └──────────────┬──────────────┘                     │
│                 │                                    │
│  ┌──────────────▼──────────────┐                     │
│  │   DBManager (Global)        │                     │
│  │   - GetPool()               │                     │
│  │   - FetchAll/FetchOne       │                     │
│  │   - Execute/BatchExecute    │                     │
│  │   - HealthCheck()           │                     │
│  └──────────────┬──────────────┘                     │
│  ┌──────────────▼──────────────┐                     │
│  │   RedisManager (Global)     │                     │
│  │   - Get/Set/Del             │                     │
│  │   - HealthCheck()           │                     │
│  └──────────────┬──────────────┘                     │
└──────────────────┼───────────────────────────────────┘
                   │
          ┌────────┴────────┐
          │   PostgreSQL     │
          │   Redis          │
          └─────────────────┘
```

## 启用方式

### 环境变量配置

在 `.env` 文件中设置:

```bash
# 启用统一数据库客户端
USE_UNIFIED_DB_CLIENT=true

# 启用统一 Redis 客户端  
USE_UNIFIED_REDIS_CLIENT=true

# Go 网关内部地址
GATEWAY_INTERNAL_URL=http://127.0.0.1:8080

# 内部鉴权 Token (与 Go 网关共享)
INTERNAL_TOKEN=your-secret-token-here
```

### 降级模式

开发环境可保持直连模式(默认):

```bash
USE_UNIFIED_DB_CLIENT=false  # 或 unset
USE_UNIFIED_REDIS_CLIENT=false  # 或 unset
```

此时 Python 直接使用 asyncpg/redis.asyncio 连接数据库。

## API 端点

### 数据库操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/internal/db/query` | POST | 执行查询并返回结果集 |
| `/v1/internal/db/execute` | POST | 执行写操作并返回影响行数 |
| `/v1/internal/db/batch-execute` | POST | 批量执行 SQL(事务) |
| `/v1/internal/db/health` | GET | 数据库健康检查 |

**请求示例:**

```json
POST /v1/internal/db/query
{
  "sql": "SELECT * FROM users WHERE tenant_id = $1",
  "args": ["tenant-123"]
}
```

**响应示例:**

```json
{
  "success": true,
  "data": {
    "rows": [{"id": "1", "name": "Alice"}],
    "count": 1
  }
}
```

### Redis 操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/internal/redis/get` | POST | 获取键值 |
| `/v1/internal/redis/set` | POST | 设置键值(可选 TTL) |
| `/v1/internal/redis/del` | POST | 删除键 |
| `/v1/internal/redis/health` | GET | Redis 健康检查 |

**请求示例:**

```json
POST /v1/internal/redis/set
{
  "key": "session:abc123",
  "value": "user-data-json",
  "ttl": 3600
}
```

## 代码迁移指南

### Python 端无需修改

得益于兼容性包装层,现有代码**无需任何修改**即可使用统一模式:

```python
# 原有代码保持不变
from app.db import get_pool

pool = get_pool()  # 自动根据 USE_UNIFIED_DB_CLIENT 选择模式
rows = await pool.fetch("SELECT * FROM users")
```

```python
# Redis 操作同样兼容
from app.redis_client import get_redis

r = await get_redis()  # 自动根据 USE_UNIFIED_REDIS_CLIENT 选择模式
await r.set("key", "value", ex=3600)
```

### 底层实现

- `app/db.py`: `_UnifiedPoolWrapper` 将 `UnifiedDBClient` 包装为 asyncpg.Pool 兼容接口
- `app/redis_client.py`: `_UnifiedRedisWrapper` 将 `UnifiedRedisClient` 包装为 redis.asyncio.Redis 兼容接口

## 监控与诊断

### 健康检查

```bash
# 检查数据库状态
curl -H "X-Internal-Token: your-token" \
  http://localhost:8080/v1/internal/db/health

# 检查 Redis 状态
curl -H "X-Internal-Token: your-token" \
  http://localhost:8080/v1/internal/redis/health
```

**响应示例:**

```json
{
  "available": true,
  "ping_ok": true,
  "timestamp": 1724755200,
  "stats": {
    "total_conns": 10,
    "idle_conns": 8,
    "acquired_conns": 2
  }
}
```

### 日志分析

Go 网关会记录所有内部 API 调用:

```
{"time":"2026-08-27T20:00:00+08:00","level":"INFO","msg":"request","method":"POST","path":"/v1/internal/db/query","status":200,"duration":"15ms"}
```

## 性能对比

| 指标 | 直连模式 | 统一模式 |
|------|---------|---------|
| 延迟 | ~2ms | ~5ms (+HTTP 开销) |
| 吞吐量 | 高 | 中高 |
| 可扩展性 | 低 | 高 |
| 运维复杂度 | 中 | 低 |

**建议:**
- 开发环境: 使用直连模式(快速迭代)
- 测试环境: 切换至统一模式(验证兼容性)
- 生产环境: 必须使用统一模式(稳定性优先)

## 故障排查

### 问题: "Unified DB client not initialized"

**原因:** `USE_UNIFIED_DB_CLIENT=true` 但未配置 `INTERNAL_TOKEN`

**解决:** 
```bash
export INTERNAL_TOKEN=your-secret-token
```

### 问题: "HTTP 401 Unauthorized"

**原因:** `INTERNAL_TOKEN` 与 Go 网关不匹配

**解决:** 确保两端配置相同的 token

### 问题: 查询超时

**原因:** Go 网关 statement_timeout 限制(默认 30s)

**解决:** 
- 优化 SQL 查询
- 对于长耗时操作,考虑异步任务队列

## 未来扩展

1. **连接池动态调整**: 根据负载自动缩放连接数
2. **多租户隔离**: 每个租户独立连接池
3. **读写分离增强**: 智能路由只读查询到副本
4. **缓存层集成**: 在 Go 层添加查询结果缓存

## 参考资料

- Go 模块: `internal/db/manager.go`, `internal/api/system_handler.go`
- Python 模块: `python-engine/app/db_client.py`, `python-engine/app/redis_client.py`
- 兼容性包装: `python-engine/app/db.py`, `python-engine/app/redis_client.py`
