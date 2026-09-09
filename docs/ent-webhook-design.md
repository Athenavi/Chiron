# 企业 Webhook 接线与可靠性设计（草案）

## 1. 现状与问题

- **半接线**：基础设施就绪（`ent_webhooks` 表 + `POST /v1/internal/webhook-event` 入口 + 投递/重试 + HMAC 签名），但引擎侧 `event_bus.emit_*`（agent.start/complete/error、knowledge.ingest/error）**全仓零调用** —— 无任何业务事件被推送。
- **at-most-once 投递**：事件进入每网关实例的进程内 `deliveryCh`（1000 缓冲），实例崩溃/重启丢缓冲事件；无持久化、无去重键、无跨实例消费语义。
- **入口在网关**：`IngestEvent` 由引擎 POST 到 `gateway_internal_url`（internal token 保护）；多个网关实例中事件仅被其所在实例处理。

## 2. 目标

1. 让企业订阅的 Webhook 事件**真实产生并可靠投递**（at-least-once + 幂等键）；
2. 投递不依赖单一网关实例（多实例共享消费、崩溃可恢复）；
3. 保持引擎侧无状态（引擎只负责"发一次事件"）。

## 3. 架构

```
引擎业务完成点（agent complete/error、kb ingest 等）
  → event_bus.emit_*(event_id, type, tenant_id, payload)         [引擎：只发一次]
  → POST /v1/internal/webhook-event（internal token）            [无状态]
网关 IngestEvent：校验后 XADD → Redis Stream `webhook:events`（MAXLEN 100000） [持久化]
  → WebhookDispatcher（每网关实例一个，消费组 webhook-workers，XREADGROUP）
      · 读事件 → 查 ent_webhooks（enabled & event_types 匹配 & tenant 匹配）
      · 逐订阅 POST（HMAC 签名 + 指数退避重试，retry_policy 上限）→ 全部成功 XACK
      · 失败至上限 → NACK/移入 DLQ 流（webhook:events:dlq），保留事件与原因
      · 崩溃恢复：消费组 PEL + idle 超时 XCLAIM（复用 engine 队列认领模式）
```

要点：
- 引擎侧与现状一致（POST 网关入口），只是入口从"投递"改为"入流"（IngestEvent 改为 XADD 后立即 202），引擎调用不需要感知可靠性改造；
- 多网关实例：谁收事件都一样（写入共享流）；投递由**消费组**负载分担（同一事件只投递一次，不重复）；承载实例崩溃由 XCLAIM 接管；
- 事件自带 `event_id`（引擎生成），外部接收方可据此幂等去重；网关重试同一 `event_id`，不重复生成。

## 4. 事件范围与业务钩子（引擎侧接线点）

| 事件 | 触发点（候选接线位置） | 说明 |
|---|---|---|
| `agent.complete` | `agent/runtime.py` run 正常收尾（done 之后、final 统计处） | 带 tokens/duration/session |
| `agent.error` | runtime 异常收尾/`type="error"` 产出点 | 带 error message |
| `knowledge.ingest` | 队列 worker `_handle_rag_index` 文档成功完成后（跨实例统一出口，非请求实例） | 带 doc/kb/chunk 数 |
| `knowledge.ingest_error` | 同 handler 失败分支 | 带错误信息 |
| `workflow.complete` | `workflow/executor.py execute_with_checkpoint` 终态写回成功后（队列 worker 统一出口） | 带 instance/结果摘要 |
| `workflow.error` | 同处异常/error 终态 | 带错误信息 |

注：agent 事件若在 http 流 handler 内 emit 会随请求实例变化；**推荐在 runtime.run 内收尾处 emit**（会话亲和下与执行实例一致，且 worker/请求两路径都覆盖）。knowledge/workflow 事件统一放各自队列 worker 完成处（所有任务必经队列，跨实例一致）。

## 5. 可靠性细节

- **持久化流**：`webhook:events`（rkey 前缀一致）XADD，`MAXLEN 100000`；DLQ `webhook:events:dlq` 同限界；
- **消费组**：`webhook-workers`，consumer 名带随机后缀；XACK 于订阅全部投递成功后（有 N 订阅者则需全部成功才 ACK；部分成功 → 记录 per-subscription 进度到 `webhook:delivered:{event_id}` hash，重投时跳过已成功者，避免部分订阅重复）；
- **per-event 进度**（可选第一版简化）：第一版采用"全订阅成功才 ACK，否则整体重投（至多 N 次进 DLQ）"，接受部分重复；若要求严格恰好一次 per-subscription，升级为进度 hash；
- **幂等键**：`event_id` 透传（`X-Webhook-Event-Id` 头）供接收方去重；
- **重试**：沿用现有指数退避（5s/10s/20s…）与 `retry_policy`（DB JSON）；实例崩溃后未 ACK 事件经 idle 认领续投；
- **限流护栏**：投递并发上限 + 对慢目标（超时）不阻塞其它订阅（per-subscription goroutine，信号量限并发）；
- **安全（必做）**：URL SSRF 防护——拒绝私网/回环/云元数据地址（现实现直接 POST 到 DB 配置的 URL，无校验）；secret 已加密存储、HMAC 签名已具备。

## 6. 验收

- 引擎完成 agent/kb 事件后 1s 内收到对应 webhook（多实例负载下）；
- kill 投递承载实例 → 事件经认领在 ≤ 阈值时间后由其它实例续投，不丢失；
- 外部 URL 5xx/超时 → 按 retry_policy 退避重试；上限后入 DLQ 并可查；
- 重复/重试事件携带相同 `X-Webhook-Event-Id`；
- 配置指向内网地址被拒绝（SSRF）。

## 7. 迁移与部署

- 网关新增 dispatcher 常驻（main.go 启动，lifecycle 可控），与引擎队列 worker 模式一致；
- 引擎侧仅在选定事件点加 `emit_*` 调用（增量接线，按事件类型分批上线）；
- 旧 `deliveryCh` 投递路径移除（不再使用）。

## 8. 已确认口径（2026-09 决策）

1. **事件范围（首批全部启用）**：`agent.complete/error`、`knowledge.ingest/ingest_error`、`workflow.complete/error`；
2. **投递语义**：at-least-once + `event_id` 幂等（`X-Webhook-Event-Id` 透传，接收方自行去重）；失败整体重投至多 N 次进 DLQ；
3. **SSRF**：默认拒绝私网/回环/云元数据 URL（白名单例外后续按需）；
4. **retry**：默认 3 次，指数退避 5s/10s/20s（可经 `retry_policy` 覆盖）。

## 9. 实施分块（供排期）

1. **网关-入流**：`IngestEvent` 改 XADD `webhook:events`（MAXLEN 10w）→ 202；
2. **网关-投递器**：`ent_webhook_dispatcher.go`（消费组 + 认领 + SSRF 校验 + HMAC + 退避 + DLQ），替换 `deliveryCh/deliveryLoop`；
3. **网关-启动**：dispatcher 常驻接入（lifecycle ctx），删除旧投递路径；
4. **引擎-接线**：agent/knowledge/workflow 完成点 `emit_*`（带 event_id）；
5. **端到端验收**：见 §6 场景。
