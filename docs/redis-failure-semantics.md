# Redis 故障语义(统一约定)

基线:**应用强依赖 Redis**(分布式限流/队列/审计流/黑名单/并发与运行协调)。故障时按"安全/一致性关键"与"体验/缓存"分级,默认 **fail-close(安全优先)**,仅缓存/只读体验类允许 fail-open。

## fail-close(拒绝,安全优先)
| 组件 | Redis 不可用时行为 |
|---|---|
| JWT 黑名单(网关 AuthMiddleware) | 检查失败即 401"authentication service unavailable"(不允许登出 token 复用) |
| 分布式限流 | `RATE_LIMIT_FAIL_CLOSE=true` 时写操作 503 拒绝 |
| 引擎 Auth(JWT/黑名单) | Bearer 直连路径拒绝 |

## fail-open + 本地兑底(降级,记录告警)
| 组件 | Redis 不可用时行为 | 兑底 |
|---|---|---|
| 会话缓存 | Redis→PG 兜底 | 正确降级 |
| 审计 | 不启 consumer,直写 PG | 正确降级 |
| 事件 hub/SSE | 本地内存广播 | 仅单实例 |
| 引擎限流 | 本地限流兑底(非裸奔) | 单实例语义 |
| SharedSemaphore / session 运行锁 / 取消广播 | 本地兑底 + 降级告警 | 跨实例约束退化为单实例 |

## 原则
- 已拉黑 token 的**本地正缓存**(15min)在 Redis 故障时仍生效(登出即时性不倒退)。
- Redis 恢复后自动回到分布式语义,无需重启。
- 多实例部署必须保证 Redis 可用;单实例降级模式(无 Redis)仅限开发/轻量部署。

## 变更记录
- 2026-09:JWT 黑名单改 fail-close;引擎限流增加本地兑底(LocalTenantRateLimiter)。
