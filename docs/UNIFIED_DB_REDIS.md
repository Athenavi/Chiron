# 统一数据库和 Redis 连接管理

## 概述

本架构将 PostgreSQL 和 Redis 的连接管理集中到 Go 网关层,Python 引擎通过 HTTP API 间接访问数据库,实现:

- ✅ **统一管理**: 所有连接由 Go 集中控制
- ✅ **无缝扩展**: 支持读写分离、故障转移、分片
- ✅ **统一监控**: 单一健康检查和统计接口
- ✅ **安全性提升**: 减少数据库暴露面

## 架构设计

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────┐
│ Python Engine   │  HTTP   │ Go Gateway   │  pgx/   │ PostgreSQL  │
│                 │ ──────> │              │ ──────> │             │
│ app/db_client.py│         │ internal/db/ │  redis  │ Redis       │
└─────────────────┘         └──────────────┘         └─────────────┘
```

## 启用方式

### 方法 1: 环境变量(推荐)

```bash
# .env 或 docker-compose.yml
USE_UNIFIED_DB_CLIENT=true
USE_UNIFIED_REDIS_CLIENT=true
```

### 方法 2: 代码配置

```python
# python-engine/app/main.py 启动时
import os
os.environ["USE_UNIFIED_DB_CLIENT"] = "true"
```

## API 端点

所有内部端点需要 `X-Internal-Token` 鉴权。

### 数据库操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/internal/db/query` | POST | 执行查询,返回结果集 |
| `/v1/internal/db/execute` | POST | 执行写操作,返回影响行数 |
| `/v1/internal/db/batch-execute` | POST | 批量执行 SQL |
| `/v1/internal/db/health` | GET | 健康检查 |

### Redis 操作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/v1/internal/redis/get` | POST | 获取键值 |
| `/v1/internal/redis/set` | POST | 设置键值 |
| `/v1/internal/redis/del` | POST | 删除键 |
| `/v1/internal/redis/health` | GET | 健康检查 |

## Python 使用示例

### 数据库查询

```python
from app.db import get_pool

# 旧代码无需修改,get_pool() 自动路由
pool = get_pool()
# P0-3: 明确指定需要的列，避免 SELECT *
rows = await pool.fetch("SELECT id, name, email FROM users WHERE id = $1", user_id)
```

### 直接使用统一客户端

```python
from app.db_client import get_db_client

db = get_db_client()

# 查询 - P0-3: 明确指定需要的列
user = await db.fetch_one("SELECT id, name, email FROM users WHERE id = $1", [user_id])
users = await db.fetch_all("SELECT id, name, email FROM users")

# 写入
affected = await db.execute("UPDATE users SET name = $1 WHERE id = $2", ["New Name", user_id])

# 健康检查
health = await db.health_check()
print(f"DB Available: {health['available']}")
```

### Redis 操作

```python
from app.redis_client import get_redis

# 旧代码无需修改
r = await get_redis()
await r.set("key", "value", ex=3600)
val = await r.get("key")
```

### 直接使用统一客户端

```python
from app.db_client import get_redis_client

redis = get_redis_client()

# 基本操作
await redis.set("counter", 42, ttl=300)
value = await redis.get("counter")
await redis.delete("counter")

# 健康检查
health = await redis.health_check()
print(f"Redis Available: {health['available']}")
```

## 迁移指南

### 现有代码兼容性

✅ **完全兼容**: 现有使用 `get_pool()` 和 `get_redis()` 的代码无需修改

```python
# 这段代码在两种模式下都能工作
from app.db import get_pool
from app.redis_client import get_redis

pool = get_pool()
rows = await pool.fetch("SELECT ...")

redis = await get_redis()
await redis.set("key", "value")
```

### 渐进式迁移步骤

1. **测试环境验证**
   ```bash
   # 开发环境先启用统一模式
   export USE_UNIFIED_DB_CLIENT=true
   export USE_UNIFIED_REDIS_CLIENT=true
   python -m app.main
   ```

2. **监控日志**
   查看日志确认请求是否正确路由到 Go 网关:
   ```
   INFO: Using unified DB client through Go gateway
   INFO: Unified DB client initialized (through Go gateway)
   ```

3. **性能对比**
   - 直接连接: ~1ms/查询
   - 统一客户端: ~2-3ms/查询 (含 HTTP 开销)
   - 收益: 统一监控、易扩展、更安全

4. **生产部署**
   ```yaml
   # docker-compose.yml
   services:
     python-engine:
       environment:
         - USE_UNIFIED_DB_CLIENT=true
         - USE_UNIFIED_REDIS_CLIENT=true
         - INTERNAL_TOKEN=${APP_SECRET}
   ```

## 优势对比

| 特性 | 直连模式 | 统一模式 |
|------|---------|---------|
| 连接管理 | 分散在各模块 | Go 集中管理 |
| 监控指标 | 各自独立 | 统一 Dashboard |
| 读写分离 | 需手动配置 | 自动路由 |
| 故障转移 | 复杂 | 透明切换 |
| 安全暴露面 | 大(多连接) | 小(单入口) |
| 扩展性 | 困难 | 容易 |

## 故障排查

### 问题: 统一客户端初始化失败

**症状**: 
```
RuntimeError: Unified DB client not initialized
```

**解决**:
1. 检查 `INTERNAL_TOKEN` 是否配置
2. 确认 Go 网关已启动并可访问
3. 查看日志中的 HTTP 错误信息

### 问题: 性能下降

**原因**: HTTP 调用增加 ~1-2ms 延迟

**优化**:
1. 启用 HTTP 连接池复用
2. 批量操作使用 `batch_execute`
3. 热点数据考虑本地缓存

### 问题: 事务不支持

**现状**: 统一模式暂不支持跨请求事务

**替代方案**:
1. 使用 `batch_execute` 原子执行多条 SQL
2. 关键事务保留直连模式(混合部署)

## 最佳实践

1. **优先使用统一模式**: 生产环境默认启用
2. **开发环境灵活切换**: 通过环境变量控制
3. **批量操作**: 减少 HTTP 往返次数
4. **健康检查**: 定期检查 `health_check()` 状态
5. **错误处理**: 捕获 `DBClientError` 和 `RedisClientError`

## 未来规划

- [ ] 支持 gRPC 协议(降低延迟)
- [ ] 完整的事务支持
- [ ] 更多 Redis 命令(exists, expire, incr 等)
- [ ] 自动降级机制(HTTP 失败时回退直连)
