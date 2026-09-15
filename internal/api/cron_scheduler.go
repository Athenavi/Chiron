package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/db"
	"github.com/athenavi/chiron/internal/engine"
	"github.com/athenavi/chiron/internal/id"
	"github.com/robfig/cron/v3"
)

// ─────────────────────────────────────────────────────────────
// 定时自动化：cron_jobs 执行器
// - 调度器每 60s 重载启用的 cron_jobs 并注册到 robfig/cron
// - 任务 task 字段为 JSON：{"type":"agent","agent_id":..,"prompt":..}
//                        或 {"type":"quick","user_input":..,"mode":"auto"}
// - 执行结果写回 last_run_at / last_status
// ─────────────────────────────────────────────────────────────

type cronEntry struct {
	eid      cron.EntryID
	schedule string
}

type CronScheduler struct {
	mu      sync.Mutex
	cron    *cron.Cron
	entries map[string]cronEntry
	python  *engine.PythonClient
}

// cronSchedulerPython 供 Webhook/手动触发复用执行器（StartCronScheduler 时注入）。
var cronSchedulerPython *engine.PythonClient

type jobRow struct {
	ID       string
	Name     string
	Schedule string
	Task     string
	TenantID string
	UserID   string
}

// StartCronScheduler 启动调度器（goroutine 内运行）。
func StartCronScheduler(ctx context.Context, python *engine.PythonClient) {
	s := &CronScheduler{
		cron:    cron.New(cron.WithLocation(time.UTC)), // 各网关实例调度基准统一 UTC（租约防重不变）
		entries: map[string]cronEntry{},
		python:  python,
	}
	cronSchedulerPython = python
	s.cron.Start()
	go s.syncLoop(ctx)
	slog.Info("cron scheduler started")
}

func (s *CronScheduler) syncLoop(ctx context.Context) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()
	s.sync()
	for {
		select {
		case <-ctx.Done():
			s.cron.Stop()
			return
		case <-ticker.C:
			s.sync()
		}
	}
}

func (s *CronScheduler) sync() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	rows, err := db.GlobalDBManager.Query(ctx,
		`SELECT id::text, name, schedule, task,
		        COALESCE(tenant_id::text, ''), COALESCE(user_id::text, '')
		 FROM cron_jobs WHERE enabled = true`)
	if err != nil {
		slog.Warn("cron sync failed", "error", err)
		return
	}
	defer rows.Close()

	jobs := map[string]jobRow{}
	for rows.Next() {
		var j jobRow
		if rows.Scan(&j.ID, &j.Name, &j.Schedule, &j.Task, &j.TenantID, &j.UserID) == nil {
			jobs[j.ID] = j
		}
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	// 移除已停用/删除/改 schedule 的 job
	for id, e := range s.entries {
		if j, ok := jobs[id]; !ok || j.Schedule != e.schedule {
			s.cron.Remove(e.eid)
			delete(s.entries, id)
		}
	}
	// 注册新 job / 更新 schedule
	for id, j := range jobs {
		if e, ok := s.entries[id]; ok && e.schedule == j.Schedule {
			continue
		}
		j := j // 循环变量拷贝：闭包捕获稳定值（Go 1.22 前语义）
		eid, err := s.cron.AddFunc(j.Schedule, func() {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
			defer cancel()
			s.executeScheduled(ctx, j)
		})
		if err != nil {
			slog.Warn("cron register failed", "job", j.Name, "schedule", j.Schedule, "error", err)
			continue
		}
		s.entries[id] = cronEntry{eid: eid, schedule: j.Schedule}
		slog.Info("cron job registered", "job", j.Name, "schedule", j.Schedule)
	}
}

// 租约陈旧阈值（秒）：run_lease_at 超过阈值视为持有者已崩溃/超时，允许其它实例重入。
// - scheduled（定时触发）：须大于 execute 的 10 分钟执行超时上限，正常执行期间不被抢占；
// - manual（Webhook/手动触发）：10 分钟执行上限 + 1 分钟缓冲，运行中再次触发直接拒绝（409）。
const (
	cronLeaseStaleScheduledSecs = 20 * 60
	cronLeaseStaleManualSecs    = 11 * 60
)

// errCronBusy：job 正在其它实例/当前实例运行中（租约新鲜），手动触发被拒绝。
var errCronBusy = errors.New("cron job is running")

// newLeaseToken 生成本次运行的租约归属 token（释放时用它做 CAS）。
// 生成失败不阻断执行：退化为"本次不校验归属"，至少不比改动前更差。
func newLeaseToken() string {
	t, err := id.UUID()
	if err != nil {
		slog.Warn("cron lease: generate token failed", "error", err)
		return ""
	}
	return t
}

// sessionIDSuffix 给定时任务的统一会话 id 提供一段随机后缀。
// 失败时回退到纳秒时间戳 —— 仍比单用毫秒时间戳更不易碰撞。
func sessionIDSuffix() string {
	if t := newLeaseToken(); len(t) >= 8 {
		return t[:8]
	}
	return fmt.Sprintf("%d", time.Now().UnixNano())
}

// tryAcquireLease 行级 CAS 抢租约：跨网关实例同一 job 同时只允许一个执行者。
// staleSecs 决定持有者"多久未续租视为已崩溃"，scheduled 与 manual 阈值不同。
//
// token 同时写入 run_lease_token，供释放时校验归属 —— 原实现释放时不看归属，
// 持有者超时被接管后回来会清掉新持有者的租约，制造重复执行窗口。
func (s *CronScheduler) tryAcquireLease(ctx context.Context, j jobRow, staleSecs int, token string) (bool, error) {
	tag, err := db.GlobalDBManager.Exec(ctx,
		`UPDATE cron_jobs SET run_lease_at = NOW(), run_lease_token = $3
		 WHERE id = $1 AND enabled = true
		   AND (run_lease_at IS NULL
		        OR run_lease_at < NOW() - make_interval(secs => $2))`,
		j.ID, staleSecs, token)
	if err != nil {
		slog.Warn("cron lease acquire failed", "job", j.Name, "error", err)
		return false, err
	}
	return tag.RowsAffected() == 1, nil
}

// cronSlotTTL 调度槽位键的存活时间：只需覆盖"同一次调度被多副本重复触发"的时间窗
// （秒级~分钟级），取 10 分钟既有充足余量，也不会让键长期堆积（每个 job 每分钟至多一个）。
const cronSlotTTL = 10 * time.Minute

// cronSlotAcquireLua 抢占调度槽位（SET NX EX），与 retention.go 的互斥键同形。
const cronSlotAcquireLua = `
if redis.call('SET', KEYS[1], '1', 'NX', 'EX', ARGV[1]) then
  return 1
end
return 0
`

// tryAcquireScheduleSlot 抢占"本次调度"的跨实例幂等槽位。
//
// 背景：cron 触发时刻由各网关副本自己的 robfig/cron 决定（注册相位不同 → 触发时刻
// 可能相差数百毫秒），而 DB 租约在任务结束时立刻释放（run_lease_at = NULL）。于是
// 短任务下"同一次调度"可能被两个副本各执行一遍（A 跑完后 B 才触发）。槽位键把幂等
// 单位从"运行中"细化到"某次调度"：同一 slot 只有第一个副本能执行。
//
// slot 取分钟粒度（UTC）——本项目的 schedule 是 5 字段 cron 表达式，最细粒度即 1 分钟。
// Redis 不可用时返回 true，退化为改动前的 DB 租约语义（不变差）。
func tryAcquireScheduleSlot(ctx context.Context, jobID string, now time.Time) bool {
	if db.Redis == nil {
		return true
	}
	key := db.RedisKey("cron:slot:" + jobID + ":" + now.UTC().Format("200601021504"))
	res := db.Redis.Eval(ctx, cronSlotAcquireLua, []string{key}, int(cronSlotTTL.Seconds()))
	if err := res.Err(); err != nil {
		slog.Debug("cron slot acquire failed, falling back to lease only",
			"job", jobID, "error", err)
		return true
	}
	n, err := res.Int()
	return err != nil || n == 1
}

// executeScheduled 定时触发入口：先抢"本次调度"槽位（防多副本重复触发同一次调度），
// 再抢 DB 行租约（防同一 job 并发运行）；任一失败即跳过本轮。
func (s *CronScheduler) executeScheduled(ctx context.Context, j jobRow) {
	if !tryAcquireScheduleSlot(ctx, j.ID, time.Now()) {
		slog.Debug("cron job skipped: schedule slot already claimed", "job", j.Name)
		return
	}
	token := newLeaseToken()
	ok, err := s.tryAcquireLease(ctx, j, cronLeaseStaleScheduledSecs, token)
	if err != nil {
		return
	}
	if !ok {
		slog.Debug("cron job skipped: lease held by another instance", "job", j.Name)
		return
	}
	s.runJob(ctx, j, token)
}

// triggerManual Webhook/手动触发入口：同步抢短租约；job 运行中返回 errCronBusy（调用方回 409），
// 抢到后异步执行，让触发请求尽快返回。
func (s *CronScheduler) triggerManual(j jobRow) error {
	token := newLeaseToken()
	acquireCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	ok, err := s.tryAcquireLease(acquireCtx, j, cronLeaseStaleManualSecs, token)
	if err != nil {
		return err
	}
	if !ok {
		return errCronBusy
	}
	go func() {
		defer func() {
			if r := recover(); r != nil {
				slog.Error("cron job async panic", "job", j.Name, "panic", r)
			}
		}()
		runCtx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
		defer cancel()
		s.runJob(runCtx, j, token)
	}()
	return nil
}

// runJob 实际执行任务体，结束时释放租约并记录本次运行结果。
func (s *CronScheduler) runJob(ctx context.Context, j jobRow, token string) {
	// Add a timeout to prevent hanging jobs from blocking the cron executor
	execCtx, cancel := context.WithTimeout(ctx, 10*time.Minute)
	defer cancel()

	start := time.Now()
	status := "success"
	errMsg := ""
	if s.python == nil {
		status = "failed"
		errMsg = "python engine unavailable"
	} else {
		status, errMsg = s.parseAndExecute(execCtx, j)
	}
	// 释放租约并记录本次运行结果：仅当租约仍属于本次 token 时才清。否则本实例超时
	// 被接管后完成时，会把新持有者的租约一并清掉 —— 那时任何实例都能立刻再抢，
	// 同一次调度被执行两遍。
	// 运行结果（last_run_at / last_status）不参与 CAS：本次确实运行过，记录它是对的。
	if token != "" {
		_, _ = db.GlobalDBManager.Exec(execCtx,
			`UPDATE cron_jobs SET run_lease_at = NULL, run_lease_token = NULL,
			        last_run_at = NOW(), last_status = $1
			 WHERE id = $2 AND run_lease_token = $3`,
			status, j.ID, token)
	} else {
		_, _ = db.GlobalDBManager.Exec(execCtx,
			`UPDATE cron_jobs SET last_run_at = NOW(), last_status = $1 WHERE id = $2`,
			status, j.ID)
	}
	if status != "success" {
		slog.Warn("cron job failed", "job", j.Name, "error", errMsg, "duration", time.Since(start))
	}
}

// parseAndExecute 解析并执行 cron 任务，返回状态和错误信息。
func (s *CronScheduler) parseAndExecute(ctx context.Context, j jobRow) (status, errMsg string) {
	switch {
	case strings.Contains(j.Task, `"type":"agent"`), strings.Contains(j.Task, `"type": "agent"`):
		var t struct {
			AgentID string `json:"agent_id"`
			Prompt  string `json:"prompt"`
		}
		if err := json.Unmarshal([]byte(j.Task), &t); err != nil {
			slog.Warn("cron: unmarshal agent task failed", "job", j.Name, "error", err)
			return "failed", "invalid agent task config"
		}
		if t.AgentID == "" {
			return "failed", "agent_id required"
		}
		if err := s.runAgent(ctx, j.TenantID, j.UserID, t.AgentID, t.Prompt); err != nil {
			return "failed", err.Error()
		}
		return "success", ""
	default: // quick / 通用统一任务
		var t struct {
			UserInput string `json:"user_input"`
			Mode      string `json:"mode"`
		}
		if err := json.Unmarshal([]byte(j.Task), &t); err != nil {
			slog.Warn("cron: unmarshal quick task failed", "job", j.Name, "error", err)
			return "failed", "invalid quick task config"
		}
		if t.UserInput == "" {
			return "failed", "user_input required"
		}
		if err := s.runQuick(ctx, j.TenantID, j.UserID, t.UserInput, t.Mode); err != nil {
			return "failed", err.Error()
		}
		return "success", ""
	}
}

func (s *CronScheduler) runAgent(ctx context.Context, tenantID, userID, agentID, prompt string) error {
	var name, systemPrompt, tools, llmConfig string
	var maxTurns, timeout int
	if err := db.GlobalDBManager.QueryRow(ctx,
		// tools / llm_config 是 json 列（不是 jsonb），缺省值必须用 '[]'::json /
		// '{}'::json —— 否则 COALESCE 运行时报 "could not convert type jsonb to json"。
		`SELECT name, COALESCE(system_prompt,''), COALESCE(tools,'[]'::json)::text,
		        COALESCE(llm_config,'{}'::json)::text, max_turns, timeout_seconds
		 FROM agents WHERE id = $1 AND tenant_id = $2 AND user_id = $3`,
		agentID, tenantID, userID).Scan(&name, &systemPrompt, &tools, &llmConfig, &maxTurns, &timeout); err != nil {
		return fmt.Errorf("load agent: %w", err)
	}
	body := map[string]interface{}{
		"task":            prompt,
		"session_id":      fmt.Sprintf("cron_%s_%d", agentID, time.Now().Unix()),
		"agent_name":      name,
		"system_prompt":   systemPrompt,
		"tools":           tools,
		"llm_config":      llmConfig,
		"max_turns":       maxTurns,
		"timeout_seconds": timeout,
	}
	params := url.Values{}
	params.Set("user_id", userID)
	params.Set("tenant_id", tenantID)
	endpoint := "/v1/agents/dispatch?" + params.Encode()
	var resp map[string]interface{}
	return s.python.PostJSON(ctx, endpoint, body, &resp)
}

func (s *CronScheduler) runQuick(ctx context.Context, tenantID, userID, input, mode string) error {
	if mode == "" {
		mode = "auto"
	}
	// 与前端 WorkstationNav 的 `uni_<ts>_<rand>` 同形：只用毫秒时间戳做 session id 时，
	// 同一毫秒触发的两个 job 会拿到同一个 id，结果串进同一个会话。
	sessionID := fmt.Sprintf("uni_%d_%s", time.Now().UnixMilli(), sessionIDSuffix())
	body := map[string]interface{}{
		"user_input": input,
		"mode":       mode,
		"session_id": sessionID,
	}
	params := url.Values{}
	params.Set("user_id", userID)
	params.Set("tenant_id", tenantID)
	endpoint := "/v1/chat/submit?" + params.Encode()
	var resp map[string]interface{}
	return s.python.PostJSON(ctx, endpoint, body, &resp)
}

// ── Webhook 触发：POST /v1/hooks/{jobID}?token=xxx ──

func HandleCronWebhook(w http.ResponseWriter, r *http.Request) {
	jobID := r.PathValue("jobID")
	token := r.URL.Query().Get("token")
	if jobID == "" || token == "" {
		BadRequest(w, "jobID and token are required")
		return
	}
	var enabled bool
	var storedToken string
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT enabled, webhook_token FROM cron_jobs WHERE id = $1`, jobID).Scan(&enabled, &storedToken); err != nil {
		NotFound(w, "job not found")
		return
	}
	if !enabled || storedToken == "" || storedToken != token {
		Forbidden(w, "invalid token or job disabled")
		return
	}
	// 同步抢租约：job 正在运行时返回 409；抢到才异步执行（webhook 尽快返回）。
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()
	var j jobRow
	if err := db.GlobalDBManager.QueryRow(ctx,
		`SELECT id::text, name, schedule, task, COALESCE(tenant_id::text,''), COALESCE(user_id::text,'')
		 FROM cron_jobs WHERE id = $1`, jobID).
		Scan(&j.ID, &j.Name, &j.Schedule, &j.Task, &j.TenantID, &j.UserID); err != nil {
		slog.Warn("cron webhook: load job failed", "job", jobID, "error", err)
		NotFound(w, "job not found")
		return
	}
	s := &CronScheduler{python: cronSchedulerPython}
	switch err := s.triggerManual(j); {
	case err == nil:
		OK(w, map[string]interface{}{"status": "triggered"})
	case errors.Is(err, errCronBusy):
		JSON(w, http.StatusConflict, APIResponse{Success: false, Error: "job is running"})
	default:
		slog.Warn("cron webhook trigger failed", "job", jobID, "error", err)
		InternalError(w, "trigger failed")
	}
}

// HandleCronTrigger 管理端手动触发：POST /v1/admin/cron-jobs/{id}/trigger
func (h *AdminHandler) HandleCronTrigger(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var j jobRow
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT id::text, name, schedule, task, COALESCE(tenant_id::text,''), COALESCE(user_id::text,'')
		 FROM cron_jobs WHERE id = $1`, id).Scan(&j.ID, &j.Name, &j.Schedule, &j.Task, &j.TenantID, &j.UserID); err != nil {
		NotFound(w, "job not found")
		return
	}
	// 同步抢租约：job 正在运行时返回 409；抢到后异步执行。
	s := &CronScheduler{python: cronSchedulerPython}
	switch err := s.triggerManual(j); {
	case err == nil:
		OK(w, map[string]interface{}{"status": "triggered"})
	case errors.Is(err, errCronBusy):
		JSON(w, http.StatusConflict, APIResponse{Success: false, Error: "job is running"})
	default:
		slog.Warn("cron trigger failed", "job", id, "error", err)
		InternalError(w, "trigger failed")
	}
}
