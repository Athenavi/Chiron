# 多实例部署（横向扩展）

面向多副本部署的配置与边界。**前提**：Redis 与 PostgreSQL 是硬依赖——Redis 不可用时
网关与引擎默认拒绝启动（见第 4 节）。

## 1. 拓扑

```
浏览器 ─► 前端容器(Nginx, 宿主机 :3000) ─► gateway 副本 1..N ─► python-engine 副本 1..M
                                                        │
                                        PostgreSQL · Redis · MinIO/S3 · Milvus
```

- `gateway` **不发布宿主机端口**（仅 `expose: 8080`）：多副本下固定端口互相抢占，且宿主机端口发布不是服务发现方案。对外只经前端 nginx 或外部 LB。
- 前端 nginx 用 `resolver 127.0.0.11` + 变量式 `proxy_pass` 重新解析服务名 `gateway`，跟随 `--scale` 变化；**这不是负载均衡**（无健康摘除、无调度算法）。生产必须前置真实 LB 并设置 `TRUSTED_PROXY_CIDRS`。
- 所有副本必须注入**完全相同**的 `APP_SECRET` / `JWT_SECRET` / `INTERNAL_TOKEN` / `REDIS_KEY_PREFIX`（不一致会造成 token 不互信或键空间错乱）。

## 2. 快速起步

```bash
cp .env.example .env
# 必填：REDIS_PASSWORD、POSTGRES_DSN（外部 PostgreSQL）、APP_SECRET
#       JWT_SECRET、INTERNAL_TOKEN、MINIO_ACCESS_KEY、MINIO_SECRET_KEY

# 1) 迁移目标 PostgreSQL（PG 由云厂商/DBA 维护，不在本 compose 内）
python -m pip install -r requirements-migrate.txt
DATABASE_DSN='postgresql://user:pwd@your-pg:5432/dbname' \
  python -m alembic -c alembic.ini upgrade head

# 2) 启动应用层
docker compose up -d redis minio etcd milvus
docker compose up -d --scale gateway=2 --scale python-engine=2
curl -s http://localhost:3000/health        # 前端入口（静态资源 + 同源反代）
```

> 应用启动会校验 schema 版本：若上一步未执行或未完成，网关会**拒绝启动**并打印期望/实际
> migration 版本（`ALLOW_SCHEMA_DRIFT=true` 可临时放行）。

## 3. 关键变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DEGRADED_MODE` | `false` | 依赖门禁：Redis 不可用时拒绝启动；仅单机开发设 `true` |
| `REDIS_KEY_PREFIX` | 空 | 多环境共用同一 Redis 时隔离键空间；**网关与引擎必须同值** |
| `PYTHON_ENGINE_ADDRESS` | `http://python-engine:8000` | 引擎静态地址（注册表为空时的回退） |
| `ENGINE_ADVERTISE_URL` | 空 | 引擎对外可达地址，设置后向 Redis 自注册；**run 归属路由的前置条件** |
| `MCP_POOL_ENABLED` | `false` | 每个开启副本会为活跃用户持有 MCP 连接（副本×用户×server 放大） |
| `STORAGE_BACKEND` | `s3` | 媒体走 MinIO；`local` 时走共享卷 `STORAGE_ROOT` |
| `SANDBOX_ROOT` / `PLUGIN_DATA_DIR` | — | 引擎沙箱与插件数据，**多副本必须共享同一卷** |
| `TRUSTED_PROXY_CIDRS` | 空 | 前置 LB 时填真实来源网段（否则 IP 限流可被伪造） |
| `TURN_RETENTION_DAYS` / `TASK_IDEMPOTENCY_RETENTION_DAYS` | 30 | 保留策略天数 |
| `RETENTION_INTERVAL_HOURS` | 6 | 保留策略执行间隔 |

## 4. 依赖门禁与就绪探针

- **启动期**：Redis 未配置或连接失败时，网关（`cmd/chiron/main.go`）与引擎（`python-engine/app/main.py`）默认**拒绝启动**（安装模式除外）。进程内降级会让各副本看到不同的限流配额、会话与事件，因此不再静默降级。
- **运行期**：就绪探针——网关 `GET /ready`（检查 PG + Redis）、引擎 `GET /readyz`（检查 Redis），依赖不可用返回 **503**；compose 的健康检查已指向这两个端点，故障副本被标记 `unhealthy`。
- 存活检查：网关 `GET /health`、引擎 `GET /healthz`。

## 5. 伸缩注意项

1. **限流**：Redis 原子令牌桶，global/tenant/user 均为**每分钟配额（总量语义）**，与副本数无关，扩缩容无需调参。
2. **会话与事件**：会话元数据、SSE 事件（Redis Stream 缓冲 + Pub/Sub 实时通道）、JWT 黑名单跨副本一致；SSE 单次 Redis 操作有 200ms 超时（抖动时丢失重放能力，不影响实时输出）；慢订阅者超 3s 丢事件，客户端凭 `Last-Event-ID` 重连补齐。
3. **引擎发现**：引擎配 `ENGINE_ADVERTISE_URL` 即向 Redis 自注册，网关每 15s 感知扩缩容；注册表为空时回退静态地址。
4. **run 归属**：引擎把「哪个实例持有该 session 的 run」写入 `engine:run:{session_id}`（TTL 300s + 100s 心跳）。审批/取消走归属路由并携带 `run_token`（陈旧 run 的审批被拒；归属指向别的实例时返回明确的 `run owned by another engine instance`）。
   **前置条件**：需要引擎自注册（`ENGINE_ADVERTISE_URL`），否则网关拿不到归属实例地址，实际仍走一致性哈希（引擎启动日志会给出明确告警）。
   **限制**：进行中 run 的现场状态（工具审批队列、持久终端、进程内簿记）仍在引擎进程内，实例故障时该 run 中断，用户重试在新实例重建。
5. **后台任务**：统一走 `engine:tasks` 消费组：失败按 `retry_count` 重投，超限进 `engine:tasks:dlq`；过期任务（`deadline`，按任务类型取值）进 DLQ 而非丢弃；进行中消息有 lease 心跳（`XCLAIM JUSTID`），副本被杀后约 10 分钟内被其它副本 reclaim；执行前经 `task_idempotency` 幂等闸门（同一键已完成则直接 ACK 跳过）。优雅下线会先排空进行中任务（最多 30s）。
6. **计费**：同一回合（turn）只扣一次——`credit_transactions.turn_id` 唯一索引 + `ON CONFLICT DO NOTHING`，重试不会重复扣费。
7. **MCP**：默认关闭；需要 MCP 工具能力的副本请显式 `MCP_POOL_ENABLED=true`。

## 6. 数据与保留策略

| 表 | 写入方 | 保留策略 |
|---|---|---|
| `turns` | 网关（每轮一行） | 网关每 `RETENTION_INTERVAL_HOURS` 清理 `TURN_RETENTION_DAYS`（默认 30 天）前**已完结**记录；`running` 不删 |
| `task_idempotency` | 引擎（每任务一行） | 引擎每 `RETENTION_INTERVAL_HOURS` 清理 `TASK_IDEMPOTENCY_RETENTION_DAYS` 前 `status <> 'running'` 记录 |

## 7. 数据库迁移与 schema 校验

- **应用不迁移**：网关启动只做只读校验（`internal/db/schema_version.go`），不执行 DDL、不需要 DDL 权限；
- **谁执行**：CI 流水线或 DBA，用 `requirements-migrate.txt` 的环境在受控窗口执行
  `python -m alembic -c alembic.ini upgrade head`（离线场景可 `--sql` 生成 DDL 审阅后执行）；
- **校验规则**：比对 `migrations/versions` 解析出的 head 与数据库 `alembic_version.version_num`；
  不一致 → `FATAL: refusing to start on mismatched schema`（`ALLOW_SCHEMA_DRIFT=true` 放行，用于迁移超前/回滚）；
  迁移链分叉（多个 head）会直接报错，必须在合并后发布；
- **滚动发布顺序**：先迁移（向后兼容的变更）→ 再滚动应用副本。破坏性变更（删列/改名）需用"扩展-迁移-收缩"两步发布。

## 8. 连接预算（扩容必读）

PostgreSQL 的 `max_connections` 是**硬上限**，而连接数随副本数线性增长：

```
网关: POSTGRES_MAX_CONN × 网关副本数
引擎: DB_POOL_MAX_SIZE  × 引擎副本数
+ 运维/监控/迁移连接
───────────────────────────────────────
合计必须留出余量（建议 ≤ max_connections 的 70%）
```

- PostgreSQL 由云厂商/DBA 维护，`max_connections` 是其**实例参数**（云实例通常按规格限制，PostgreSQL 默认仅 100）：请在扩容前确认上限，并据此下调应用侧池大小；
- 应用侧默认值：`POSTGRES_MAX_CONN=20`、`DB_POOL_MAX_SIZE=20`。**4 个副本时就应下调到 10 左右**，例如：
  `POSTGRES_MAX_CONN=10 DB_POOL_MAX_SIZE=10 docker compose up -d --scale gateway=4 --scale python-engine=4`
- 托管实例若限制严格，建议引入 PgBouncer 之类的连接池中间件（应用→PgBouncer→实例）。
- 托管数据库（RDS/Cloud SQL）请按实例规格确认上限，必要时改用 PgBouncer 之类的连接池中间件；
- Redis 侧同理（`REDIS_POOL_SIZE` 默认 100 × 副本数），需对照 `redis-cli info clients` 的 `maxclients`（默认 10000）。

## 9. 验证

```bash
docker compose config --quiet                 # 配置校验
python -m alembic heads                       # 期望单一 head
go build ./... && go vet ./...
python -m pytest python-engine/tests -q
```

运行时抽查（多副本）：

- 停 Redis 后 `GET /ready`（网关）与 `GET /readyz`（引擎）应为 503，恢复后自动回 200；
- 引擎收到 SIGTERM 时日志出现 `Queue worker stopping, waiting for N in-flight tasks...` 与 `Queue worker stopped`（说明优雅排空生效）；
- 同一 `task_id` 重复投递只执行一次（日志 `duplicate task skipped (already completed)`）；
- 同一 `turn_id` 重复扣费时余额只减一次。

## 10. 已知边界

- run 现场状态不迁移：实例故障该 run 中断（只保证「路由到正确实例 + 陈旧审批被拒」）；
- SSE 跨实例实时通道为 Pub/Sub：断连窗口内的实时事件依赖客户端携带 `Last-Event-ID` 从 Stream 重放；
- Compose 内置的 PostgreSQL、Redis、MinIO、Milvus、etcd 仍是**单点**：生产需替换为托管或集群方案（Redis Sentinel/Cluster、Patroni、分布式 MinIO、Milvus 集群、多副本 etcd），并配套备份恢复与跨可用区演练。
