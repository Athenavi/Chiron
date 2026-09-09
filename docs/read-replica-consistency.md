# 只读副本（Read Replicas）一致性约束

多网关/引擎实例 + PostgreSQL 读写分离（`POSTGRES_READ_DSNS`）时的读写一致性约定。

## 路由规则
- `db.DBManager.Query / QueryRow`、`db.ReadPool()` 返回**只读副本**（round-robin，无副本时回退主库）；
- `db.Exec / Begin`、`db.Pool` 恒为主库。

## 必须走主库的关键读（安全 / 钱包语义，禁止依赖副本延迟）
以下路径**写后立即读**或属安全敏感，代码中已强制使用 `db.Pool`（主库）：
1. **RBAC 权限回源与失效**（`internal/enterprise/rbac.go`）
   - `queryEffectivePerms`：权限变更 + 缓存失效后，下一请求回源若读滞后副本会在延迟窗口内返回旧权限（被降权用户短暂仍可访问）；
   - `InvalidateGroupMembersPerms`：群组/角色变更后的成员枚举必须是最新，否则漏失效成员的旧缓存。
2. **支付订单读取**（`internal/billing/pgstore.go` `GetPayment`）：支付渠道回调确认前读取订单状态，副本延迟会导致误报 "unknown order"。
3. **余额读取**（`internal/billing/pgstore.go` `GetBalance`）：扣减/入账后读取为钱包语义，不允许副本延迟回旧值。

## 可承受副本延迟的读
- 会话/消息历史：`session.Manager` 注入主库池（本就为主读，无副本窗口）；
- 认证（`auth/local` 等注入主池）；
- 管理/统计/成本中心聚合、cron 配置同步等展示与批量场景可走副本（允许 ≤ 复制延迟的陈旧）。

## 部署要求
- 启用 `POSTGRES_READ_DSNS` 时，请使用**近同步 / 流式复制**（replica 延迟毫秒级）；
- 若使用异步复制且延迟不可忽略，应仅把纯只读统计负载指向副本，并在接入层限制可容忍延迟；
- 代码新增读路径时遵循上方"必须走主库"清单，不要把安全/钱包读交给 `ReadPool`/`QueryRow`。

## 相关实现
- `internal/db/router.go`（Router.Read/Write）、`internal/db/manager.go`（GetReadPool/GetPool）、`internal/db/postgres.go`（`Pool`/`ReadPool`）。
