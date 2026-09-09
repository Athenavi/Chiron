# Redis Key 前缀统一(设计草案)

目标:多套环境(dev/prod/隔离租户)共用同一 Redis 时互不干扰(队列/审计/密钥集/限流互踩)。

## 键空间清单(现无前缀,默认 DB0)
| 归属 | 键/频道 |
|---|---|
| 网关 | `session:{id}`、`jwt:blacklist:{jti}`(+频道 `jwt:blacklist:sync`)、频道 `chiron:events`、流 `audit:events`、`ratelimit:*`、`sem:{name}`、`agent:run-lock:{sid}`(+频道 `agent:cancel`)、`llm:keys:{provider}`/`llm:keys:ver`(+频道 `llm:keys:changed`) |
| 引擎 | `session:{id}`、`budget:{tenant}:{yyyy-mm}`、流 `engine:tasks`/`engine:tasks:dlq`、`engine:worker:inflight`、`ratelimit:{tenant}:{s,m}`、`llm:keys:*`(读)/`llm:fail:{provider}:{digest}`、`jwt:blacklist:{jti}` |

## 机制
- 新环境变量 **`REDIS_KEY_PREFIX`**(如 `dev:` / `prod:`),默认空 = 当前行为(兼容存量)。
- 接入方式:两端统一在键组装处加前缀。为避免逐点手拼出错,建议:
  - **Go**:`internal/db` 暴露 `RedisKey(name string) string`(读一次 env 缓存),现有各调用点替换键字面量;
  - **Python**:`app/config.py settings.redis_key_prefix` + 每模块键常量改用 `f"{settings.redis_key_prefix}…"`(键构建集中到少量常量/helper,避免散落)。
- 频道名(Subscribe/Publish 的 channel)同样加前缀;Redis **流与消费组名**沿用组名但流键带前缀(组挂流上,无需改动组名)。

## 存量与迁移
- 启用前缀 = 进入**新键空间**:队列/审计流/会话等旧数据对启用前缀的实例不可见。
- 迁移策略(按需):
  - 新环境直接设前缀;
  - 存量环境升级:停服窗口内设前缀即可(旧流/键按保留期自然过期或手动清);如需保留历史审计/队列,另行复制任务(不建议自动双写)。
- 故障语义沿用 docs/redis-failure-semantics.md(前缀不改变 fail 分级)。

## 实施建议(分批,接入点小而多)
1. 先两端加配置读取与 helper(不动键);
2. 逐个命名空间替换(会话→黑名单→限流/信号量→审计/队列→llm keys),每批跑 vet/compile;
3. 联调:同 Redis 跑 `dev:` 与 `prod:` 两前缀实例互不影响。

状态:设计草案,待评审后按批实现。
