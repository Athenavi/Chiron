# DR: LLM Provider 密钥管理(多引擎目标架构草案)

状态:草案,待评审。实现前需先完成 P1 取 key 接口与 Redis 数据结构设计。

## 目标
多引擎实例无缝扩展 + 功能独立。管理端添加的 LLM provider 密钥:加密落库、全实例一致、热路径高性能。

## 决策
- **R1 多实例为目标**:密钥集合/手动状态跨引擎实例一致。
- **R2 集中派**:网关负责 LLM 密钥的增删改、加解密与手动状态;引擎不再持有 APP_SECRET;明文仅经内部端点(`X-Internal-Token`)下发给引擎,引擎内存/Redis 使用。
- **R3 存储载体**:新建独立表 `llm_provider_keys`(provider/encrypted_key/status/remark/version…);密文用 Go `internal/settings` 加密体系(APP_SECRET 派生),加密单轨。作废 migration `9f3c2a1e7d04`(admin_api_keys 加 provider/encrypted_key)及引擎本地加密实现。
- **R4 Redis 强依赖**:明文 keyset(固定 TTL + 续期)、key 级熔断/权重/失败计数均存 Redis(原子操作);引擎热路径不打 DB;DB 仅网关低频写入与对账。
- **R5 变更同步**:网关写 DB → 更新 Redis keyset + 版本号 → Redis pub/sub 通知 → 各引擎重载;版本号兜底对账。
- **R6 dev 配置注入**:chiron-cli/启动器以 APP_SECRET 派生 `JWT_SECRET`/`INTERNAL_TOKEN` 注入引擎进程 env;引擎不再自读 APP_SECRET 派生。
- **R7 匿名流量**:存在按浏览器/设备唯一标识的未登录 LLM 调用;明文 TTL/配额需同时覆盖登录用户与匿名设备(匿名身份语义待细化)。
- **R8 统一熔断**:合并 `gateway/circuit_breaker.py`(per-provider)与 `smart_key_pool` 内嵌熔断为单一 Redis 共享实现。
- **R9 管理端 API 迁网关**:`/v1/admin/api-keys` 移入 Go(直连 DB + settings 加密 + 复用 Redis hub 广播)。

## 已识别债务 / 待设计(实现阶段处理)
- **P1**:密钥池(`get_key`)与真实 LLM 调用链(GatewayRouter/provider)当前断开——需先设计取 key 接口与 provider 改造。
- **G5**:明确"引擎不依赖网关"边界(引擎 LLM 主链路不依赖网关,仅启动/变更拉取)。
- 旧 `data/api_keys.json`(若有)不迁移;`admin_api_keys` 表恢复原访问密钥语义,不含 LLM 行。
- 上一轮引擎侧改动(smart_key_pool DB 写入、main.py admin 503、测试)在实现阶段按本决议回退或重写。

## 影响面
migration(新建表/回退旧迁移)、网关(管理 API + settings 加密 + Redis keyset/pub-sub)、引擎(去 APP_SECRET、密钥加载与取 key 改造、熔断合并)、启动器(env 注入)、compose(引擎 env 调整)、测试。

## 实施细化(2026-09 定稿,待实现)
> 决策:取 key 采用 **V1 本地环+预留 V2 Redis 原子接口**;provider **内部持 key 集合并轮换**;自动停用 **Redis 共享失败计数 + 冷却窗**。

- **表 `llm_provider_keys`**:id uuid pk、provider varchar(50) not null、encrypted_key text not null、key_hash varchar(64) unique not null(sha256("provider:key") 防重)、status varchar(20) default 'active'、remark text、created_at/updated_at timestamptz;index(provider)。密文由 Go `internal/settings` 加解密(APP_SECRET 派生,单轨)。
- **Redis keyset**:`HSET llm:keys:{provider}` field=key_id(sha256[:12]) → JSON{key 明文,status};`llm:keys:ver` 版本号;变更 PUBLISH `llm:keys:changed`。失败计数 `llm:fail:{provider}:{key_id}` INCR+EXPIRE(窗口);达阈值→keyset 置 circuit_open 并附冷却到期时间;冷却过期任一实例 CAS 置回 active。
- **引擎 KeyRing**:内存明文镜像(版本 poll ~5s + 可选 pub 订阅),TTL 兜底强制回源;接口 KeyRing.get_active(provider)/report_failure(key_id)…;实现 LocalKeyRing(V1)与预留 RedisKeyRing(同接口,V2)。
- **provider 多 key**:OpenAI/DeepSeek/Anthropic Provider 构造接收 key 集合;client 按 key LRU 缓存;调用前经 KeyRing 取 key,失败换 key 重试一次并上报(本地冷却+Redis 计数);router 层 provider 熔断保留,key 级在 provider 内部。
- **网关管理端(Go)**:`/v1/admin/api-keys`(list/stats/add/status/delete)改网关本地实现(adminRead/adminWrite 权限不变,响应结构兼容前端);写 DB+keyset+ver+pub 原子链;删除引擎侧 4 个 admin 函数与路由。
- **去 APP_SECRET**:引擎仅经显式 JWT_SECRET/INTERNAL_TOKEN(chiron-cli/启动器注入派生值;compose 已显式);config.py 移除 app_secret 派生依赖,缺失即启动错误。
- **env 保底**:settings.xxx_api_key 仍作为引擎启动种子注入 KeyRing(管理端配置为空时可直连)。
- **实施顺序**:①migration+网关加密 CRUD+keyset/pub;②引擎 KeyRing+provider 多 key+删除引擎 admin;③去 APP_SECRET 与启动器注入;④联调验证(多实例增删/停用/冷却收敛、Redis 故障降级按 docs/redis-failure-semantics.md)。

