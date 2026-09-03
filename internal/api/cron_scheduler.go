package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/db"
	"github.com/athenavi/chiron/internal/engine"
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
		cron:    cron.New(),
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
				s.execute(ctx, j)
			})
		if err != nil {
			slog.Warn("cron register failed", "job", j.Name, "schedule", j.Schedule, "error", err)
			continue
		}
		s.entries[id] = cronEntry{eid: eid, schedule: j.Schedule}
		slog.Info("cron job registered", "job", j.Name, "schedule", j.Schedule)
	}
}

func (s *CronScheduler) execute(ctx context.Context, j jobRow) {
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
	_, _ = db.GlobalDBManager.Exec(execCtx,
		`UPDATE cron_jobs SET last_run_at = NOW(), last_status = $1 WHERE id = $2`,
		status, j.ID)
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
		`SELECT name, COALESCE(system_prompt,''), COALESCE(tools,'[]'::jsonb)::text,
		        COALESCE(llm_config,'{}'::jsonb)::text, max_turns, timeout_seconds
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
	sessionID := fmt.Sprintf("uni_%d", time.Now().UnixMilli())
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
	// 异步执行（webhook 尽快返回）
	go func() {
		defer func() {
			if r := recover(); r != nil {
				slog.Error("cron webhook async panic", "job", jobID, "panic", r)
			}
		}()
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
		defer cancel()
		s := &CronScheduler{python: cronSchedulerPython}
		rows, err := db.GlobalDBManager.Query(ctx,
			`SELECT id::text, name, schedule, task, COALESCE(tenant_id::text,''), COALESCE(user_id::text,'')
			 FROM cron_jobs WHERE id = $1`, jobID)
		if err == nil && rows.Next() {
			var j jobRow
			if rows.Scan(&j.ID, &j.Name, &j.Schedule, &j.Task, &j.TenantID, &j.UserID) == nil {
				s.execute(ctx, j)
			}
		}
		if rows != nil {
			rows.Close()
		}
	}()
	OK(w, map[string]interface{}{"status": "triggered"})
}

// HandleCronTrigger 管理端手动触发：POST /v1/admin/cron-jobs/{id}/trigger
func (h *AdminHandler) HandleCronTrigger(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var tenantID, userID string
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT COALESCE(tenant_id::text,''), COALESCE(user_id::text,'') FROM cron_jobs WHERE id = $1`, id).Scan(&tenantID, &userID); err != nil {
		NotFound(w, "job not found")
		return
	}
	var j jobRow
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT id::text, name, schedule, task, COALESCE(tenant_id::text,''), COALESCE(user_id::text,'')
		 FROM cron_jobs WHERE id = $1`, id).Scan(&j.ID, &j.Name, &j.Schedule, &j.Task, &j.TenantID, &j.UserID); err != nil {
		NotFound(w, "job not found")
		return
	}
	go func() {
		defer func() {
			if r := recover(); r != nil {
				slog.Error("cron trigger async panic", "job", id, "panic", r)
			}
		}()
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
		defer cancel()
		s := &CronScheduler{python: cronSchedulerPython}
		s.execute(ctx, j)
	}()
	_ = tenantID
	_ = userID
	OK(w, map[string]interface{}{"status": "triggered"})
}
