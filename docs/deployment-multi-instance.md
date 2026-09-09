# Chiron 多实例(横向扩展)部署指南

> 面向"企业化多副本部署"的基线文档。本文描述的配置已落地到
> `docker-compose.yml`(批 A);批 B(令牌桶限流总量化 / 配置跨副本热更 / WS 下线统一 SSE)
> 见第 4 节,批 D(RPA 跨实例桥接)见文末。

## 1. 拓扑

```
                 ┌──────────────┐
   浏览器/前端 ───►  LB(可选)    │
                 └──────┬───────┘
          ┌─────────────┴──────────────┐
          ▼                            ▼
   gateway 副本 1..N            python-engine 副本 1..M
   (无状态;RPA WS 连接、       (无状态;会话/队列 Redis 化;
    事件/会话/限流走 Redis)      agent 沙箱走共享卷)
          │        │      │            │
          ▼        ▼      ▼            ▼
      PostgreSQL   Redis  MinIO/S3   Milvus(可选)  共享卷(sandbox/plugins)
```

- **副本无本地状态**:会话元数据、SSE 事件、后台任务、审计、限流全部经 Redis/PG;
  文件类数据分三层:媒体走对象存储、沙箱/插件走共享卷、临时走本地盘。
- 所有副本必须注入**完全相同**的 `APP_SECRET` / `JWT_SECRET` / `INTERNAL_TOKEN` /
  `REDIS_KEY_PREFIX`(任一不一致都会造成 token 不互信或 Redis 键空间隔离错乱)。

## 2. Compose 快速起步(多副本)

```bash
# 1) 准备 .env(最少必填见下方)
cp .env.example .env   # 然后填写全部 required 变量

# 2) 启动基础件
docker compose up -d postgres redis minio etcd milvus temporal

# 3) 启动多副本应用层(示例:网关 2 副本、引擎 2 副本)
docker compose up -d --scale gateway=2 --scale python-engine=2
```

> 单机 `docker compose` 不带 LB:`gateway:8080` 服务名做 DNS 轮询,
> 应用层已验证无状态,可直接多副本。生产建议前置真实负载均衡器
> (并设置 `TRUSTED_PROXY_CIDRS` 为 LB 网段)。

### 必填环境变量(required,缺失则 compose 拒绝启动)

| 变量 | 用途 |
|---|---|
| `POSTGRES_PASSWORD` | PG 密码;`POSTGRES_DSN` 需指向 `postgres:5432/chiron0827` |
| `REDIS_PASSWORD` | Redis 密码(网关 `REDIS_ADDR/PASSWORD`,引擎 `REDIS_URL` 共用) |
| `APP_SECRET` / `JWT_SECRET` / `INTERNAL_TOKEN` | 全副本一致;推荐显式设置(不依赖 APP_SECRET 派生) |
| `POSTGRES_DSN` | 全副本一致,示例 `postgresql://postgres:<pwd>@postgres:5432/chiron0827` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | 网关 S3 媒体存储与 Milvus 共用 |

### 多副本关键变量(批 A 引入)

| 变量 | 默认 | 说明 |
|---|---|---|
| `PYTHON_ENGINE_ADDRESS` | `http://python-engine:8000` | 逗号分隔引擎列表;**新增/下线引擎副本须同步更新并滚动重启网关** |
| `REDIS_KEY_PREFIX` | 空 | 多环境共用同一 Redis 时隔离键空间(如 `prod:`);**网关与引擎必须同值** |
| `STORAGE_BACKEND` | `s3` | 媒体存储:compose 默认走 MinIO;纯本机开发可改 `local` |
| `STORAGE_ROOT` | `/app/workspace` | `local` 兜底目录(挂 workspace 共享卷) |
| `S3_ENDPOINT` 等 | MinIO 内网地址 | 网关媒体对象存储 |
| `PLUGIN_DATA_DIR` | `/srv/chiron/plugins` | 网关与引擎**同卷共享** |
| `SANDBOX_ROOT` | `/srv/chiron/sandbox`(引擎容器) | agent 沙箱根,多副本挂同一共享卷 |
| `RATE_LIMIT_INSTANCES` | 已废弃 | 批 B-1′ 令牌桶为总量语义,不再按副本数放大;变量保留仅为兼容旧配置,代码已不使用 |
| `TRUSTED_PROXY_CIDRS` | 空 | 前置 LB 时填真实来源网段 |
| `HTTP_HOST` | `0.0.0.0`(引擎) | 引擎必须对外监听供网关访问 |
| `MCP_POOL_ENABLED` | `true` | 每启用副本对活跃用户各持 MCP 连接;副本增多后按需关闭部分实例 |
| `INSTANCE_ID` | 空 | K8s 注入;compose 留空由引擎自生成 |
| `ENGINE_ADVERTISE_URL` | 空(批 E1) | 引擎对外可达地址(如 `http://engine-0:8000`),设置后引擎向 Redis 自注册、网关 15s 内动态感知扩缩容;为空则不注册,网关回退 `PYTHON_ENGINE_ADDRESS` 静态列表 |

## 3. 存储分层(定案)

| 数据 | 介质 | 理由 |
|---|---|---|
| 媒体/上传/知识库文档 | **S3/MinIO**(`STORAGE_BACKEND=s3`) | BLOB 语义;副本一致、签名 URL |
| Agent 沙箱 | **共享 POSIX 卷**(引擎 `SANDBOX_ROOT`) | agent 文件工具/git/终端需要真文件系统与低延迟;对象存储/FUSE 不可行(性能+安全) |
| 插件数据 | **共享卷**(`PLUGIN_DATA_DIR`,网关与引擎同卷) | 小 JSON 高频写 |
| 会话/任务/事件 | Redis(键前缀统一) | 已多副本就绪 |

K8s/云部署等价物:沙箱与插件用 PVC 或 EFS(同区);本地起步可用单机卷。
安全:容器保持非 root;卷按 `{tenant}/{user}` 分目录;EFS/NFS 注意挂载选项与锁语义。

## 4. 伸缩注意事项

1. **网关横向扩展**:直接加副本;会话取消、JWT 黑名单、SSE 事件已跨实例。
2. **限流(批 B-1′)**:分布式限流为 Redis 原子令牌桶,**总量语义**(global/tenant/user
   为每分钟配额;容量=配额、按配额/60 每秒补充),与网关副本数无关——扩缩容无需调整
   任何参数;后台「系统设置」rate_limit 保存后经跨副本广播即时生效。
3. **配置热更(批 B-2′)**:后台保存 `rate_limit`(限流阈值)与 `cors`(白名单)后所有
   副本即时生效;`redis`/`storage`/`s3`/`payment`/`agent` 等分类广播告警,需滚动
   重启后生效(redis 集群切换属高风险热更项)。
4. **实时通道统一为 SSE(批 B-3′)**:`GET /ws/{sessionId}` 与 WebSocketHub 已下线
   (Vue 前端仅使用 EventSource);SSE 经 Redis Stream + Pub/Sub 跨副本一致,并支持
   Last-Event-ID 断线重放。RPA 插件通道 `GET /ws/rpa` 不受影响。
5. **引擎横向扩展(批 E1/E2 已落地)**:会话消息 Redis 化、后台任务 Redis Streams 消费组分摊;
   引擎配 `ENGINE_ADVERTISE_URL` 即向 Redis 自注册,网关每 15s 动态感知扩缩容
   (注册表为空时回退静态 `PYTHON_ENGINE_ADDRESS`);
   **注意**:agent 进行中 run 的现场状态仍在进程内——会话亲和为尽力而为,实例故障时
   该 run 中断;会话 run 锁已改为 5min TTL + 60s 心跳续期(批 E2),用户 ≤5min 后可
   重试(历史消息已持久化)。文件工具结果依赖共享沙箱卷。
6. **RPA 浏览器桥(批 D)**:插件 WS 与 `/v1/rpa/exec` 可落在不同网关副本,
   经 Redis 注册中心路由(通道 `rpa:cmd` / `rpa:res`,key `rpa:client:*`)。
   Redis 不可用时网关自动退回单机模式(`localOnly`),此时仍需单实例/粘性。
7. 扩容引擎:启用 E1(`ENGINE_ADVERTISE_URL`)后网关自动感知,无需再改静态清单。

## 5. 已知剩余项(后续批次,不影响上述基线运行)

- 批 F:迁移收敛为发布流程单点执行;RLS 逐表核查。

## 6. 验证冒烟

```bash
docker compose config            # 配置校验
docker compose up -d --scale gateway=2 --scale python-engine=2
curl -s http://localhost:8080/health          # 每个网关副本
curl -s http://localhost:8080/v1/system/health
# RPA(需真实浏览器插件):
#   插件连副本 A 的 /ws/rpa,再经任意副本 POST /v1/rpa/exec,命令应能到达插件。
```
