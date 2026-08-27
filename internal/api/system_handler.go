package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/athenavi/chiron/internal/db"
	"github.com/athenavi/chiron/internal/monitor"
)

// SystemHandler provides health, metrics, and trace endpoints.
type SystemHandler struct{}

func NewSystemHandler() *SystemHandler {
	return &SystemHandler{}
}

// HealthScores returns calculated health scores based on live metrics.
func (h *SystemHandler) HealthScores(w http.ResponseWriter, r *http.Request) {
	m := monitor.Snapshot()

	requestsTotal := toFloat64(m["requests_total"])
	toolErrors := toFloat64(m["tool_errors"])
	llmErrors := toFloat64(m["llm_errors"])

	// Calculate scores from real metrics
	uptime := time.Now().Unix() - int64(toFloat64(m["uptime_seconds"]))
	_ = uptime

	healthScores := []map[string]interface{}{
		{
			"label": "Performance",
			"score": perfScore(requestsTotal),
			"color": "bg-green-500",
		},
		{
			"label": "Reliability",
			"score": reliabilityScore(requestsTotal, toolErrors+llmErrors),
			"color": "bg-blue-500",
		},
		{
			"label": "Activity",
			"score": activityScore(requestsTotal),
			"color": "bg-amber-500",
		},
		{
			"label": "API Health",
			"score": apiHealthScore(m),
			"color": "bg-green-500",
		},
		{
			"label": "System",
			"score": systemScore(m),
			"color": "bg-blue-500",
		},
	}

	OK(w, map[string]interface{}{
		"scores": healthScores,
		"uptime": m["uptime_seconds"],
	})
}

// Metrics returns the live monitor snapshot as a key-value map.
func (h *SystemHandler) Metrics(w http.ResponseWriter, r *http.Request) {
	OK(w, monitor.Snapshot())
}

// PrometheusMetrics 输出 Prometheus 文本格式指标（供 Prometheus 抓取）。
// 端点 /metrics 公开暴露（生产部署建议加内网限制或 basicauth）。
func (h *SystemHandler) PrometheusMetrics(w http.ResponseWriter, r *http.Request) {
	s := monitor.Snapshot()
	w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
	// counter 类型指标（snapshot key → prometheus metric name）
	counters := [][2]string{
		{"requests_total", "Total HTTP requests"},
		{"llm_calls", "Total LLM API calls"},
		{"llm_errors", "Total LLM API errors"},
		{"tool_calls", "Total tool executions"},
		{"tool_errors", "Total tool execution errors"},
	}
	for _, c := range counters {
		fmt.Fprintf(w, "# HELP chiron_%s %s\n# TYPE chiron_%s counter\nchiron_%s %v\n", c[0], c[1], c[0], c[0], s[c[0]])
	}
	// gauge 类型指标
	gauges := [][2]string{
		{"requests_active", "Active HTTP requests"},
		{"uptime_seconds", "Process uptime in seconds"},
	}
	for _, g := range gauges {
		fmt.Fprintf(w, "# HELP chiron_%s %s\n# TYPE chiron_%s gauge\nchiron_%s %v\n", g[0], g[1], g[0], g[0], s[g[0]])
	}
}

// Spans returns completed tracing spans for debugging.
func (h *SystemHandler) Spans(w http.ResponseWriter, r *http.Request) {
	limit := 50
	spans := monitor.GetCompletedSpans(limit)
	OK(w, map[string]interface{}{"spans": spans})
}

// Traces returns recent tool call executions as trace entries.
func (h *SystemHandler) Traces(w http.ResponseWriter, r *http.Request) {
	rows, err := db.ReadPool().Query(r.Context(),
		`SELECT id, tool_name, is_error, duration_ms, created_at
		 FROM tool_calls
		 ORDER BY created_at DESC
		 LIMIT 50`)
	if err != nil {
		OK(w, map[string]interface{}{"traces": []interface{}{}})
		return
	}
	defer rows.Close()

	traces := make([]map[string]interface{}, 0)
	for rows.Next() {
		var id, toolName string
		var isError bool
		var durationMs int64
		var createdAt time.Time

		if err := rows.Scan(&id, &toolName, &isError, &durationMs, &createdAt); err != nil {
			continue
		}

		status := "ok"
		if isError {
			status = "error"
		}

		traces = append(traces, map[string]interface{}{
			"id":          id,
			"type":        toolName,
			"name":        "Tool: " + toolName,
			"status":      status,
			"duration_ms": float64(durationMs),
			"timestamp":   createdAt.Format(time.RFC3339),
		})
	}
	if err := rows.Err(); err != nil {
		InternalError(w, "failed to iterate traces")
		return
	}

	OK(w, map[string]interface{}{"traces": traces})
}

func toFloat64(v interface{}) float64 {
	switch n := v.(type) {
	case float64:
		return n
	case int64:
		return float64(n)
	case int:
		return float64(n)
	}
	return 0
}

func perfScore(totalRequests float64) int {
	if totalRequests == 0 {
		return 95 // Perfect score when no load
	}
	return 85
}

func reliabilityScore(total, errors float64) int {
	if total == 0 {
		return 98
	}
	rate := errors / total
	if rate > 0.1 {
		return 60
	}
	if rate > 0.05 {
		return 75
	}
	return int(98 - rate*100)
}

func activityScore(total float64) int {
	if total > 1000 {
		return 95
	}
	if total > 100 {
		return 80
	}
	if total > 10 {
		return 65
	}
	return 50
}

func apiHealthScore(m map[string]interface{}) int {
	active := toFloat64(m["requests_active"])
	if active > 100 {
		return 70
	}
	return 92
}

func systemScore(m map[string]interface{}) int {
	uptime := toFloat64(m["uptime_seconds"])
	if uptime > 86400 {
		return 90 // Running > 24h
	}
	if uptime > 3600 {
		return 85 // Running > 1h
	}
	return 80
}

// DatabaseHealth 数据库健康检查端点（供 Python 引擎调用）
func (h *SystemHandler) DatabaseHealth(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	result := db.GlobalDBManager.HealthCheck(ctx)
	OK(w, result)
}

// RedisHealth Redis 健康检查端点（供 Python 引擎调用）
func (h *SystemHandler) RedisHealth(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	result := db.GlobalRedisManager.HealthCheck(ctx)
	OK(w, result)
}

// DBQuery 执行 SQL 查询并返回结果（供 Python 引擎调用）
func (h *SystemHandler) DBQuery(w http.ResponseWriter, r *http.Request) {
	var req struct {
		SQL  string        `json:"sql"`
		Args []interface{} `json:"args,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	if req.SQL == "" {
		BadRequest(w, "sql is required")
		return
	}

	ctx := r.Context()
	results, err := db.GlobalDBManager.FetchAll(ctx, req.SQL, req.Args...)
	if err != nil {
		InternalError(w, fmt.Sprintf("query failed: %v", err))
		return
	}

	OK(w, map[string]interface{}{
		"rows": results,
		"count": len(results),
	})
}

// DBExecute 执行 SQL 写操作（供 Python 引擎调用）
func (h *SystemHandler) DBExecute(w http.ResponseWriter, r *http.Request) {
	var req struct {
		SQL  string        `json:"sql"`
		Args []interface{} `json:"args,omitempty"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	if req.SQL == "" {
		BadRequest(w, "sql is required")
		return
	}

	ctx := r.Context()
	rowsAffected, err := db.GlobalDBManager.Execute(ctx, req.SQL, req.Args...)
	if err != nil {
		InternalError(w, fmt.Sprintf("execute failed: %v", err))
		return
	}

	OK(w, map[string]interface{}{
		"rows_affected": rowsAffected,
	})
}

// DBBatchExecute 批量执行 SQL（供 Python 引擎调用）
func (h *SystemHandler) DBBatchExecute(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Queries []string `json:"queries"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	if len(req.Queries) == 0 {
		BadRequest(w, "queries is required")
		return
	}

	ctx := r.Context()
	err := db.GlobalDBManager.BatchExecute(ctx, req.Queries)
	if err != nil {
		InternalError(w, fmt.Sprintf("batch execute failed: %v", err))
		return
	}

	OK(w, map[string]interface{}{
		"success": true,
	})
}

// RedisGet 获取 Redis 键值（供 Python 引擎调用）
func (h *SystemHandler) RedisGet(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Key string `json:"key"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	if req.Key == "" {
		BadRequest(w, "key is required")
		return
	}

	ctx := r.Context()
	val, err := db.GlobalRedisManager.Get(ctx, req.Key)
	if err != nil {
		InternalError(w, fmt.Sprintf("redis get failed: %v", err))
		return
	}

	OK(w, map[string]interface{}{
		"value": val,
	})
}

// RedisSet 设置 Redis 键值（供 Python 引擎调用）
func (h *SystemHandler) RedisSet(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Key   string      `json:"key"`
		Value interface{} `json:"value"`
		TTL   int64       `json:"ttl,omitempty"` // seconds
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	if req.Key == "" {
		BadRequest(w, "key is required")
		return
	}

	ctx := r.Context()
	expiration := time.Duration(0)
	if req.TTL > 0 {
		expiration = time.Duration(req.TTL) * time.Second
	}

	err := db.GlobalRedisManager.Set(ctx, req.Key, req.Value, expiration)
	if err != nil {
		InternalError(w, fmt.Sprintf("redis set failed: %v", err))
		return
	}

	OK(w, map[string]interface{}{
		"success": true,
	})
}

// RedisDel 删除 Redis 键（供 Python 引擎调用）
func (h *SystemHandler) RedisDel(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Keys []string `json:"keys"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	if len(req.Keys) == 0 {
		BadRequest(w, "keys is required")
		return
	}

	ctx := r.Context()
	err := db.GlobalRedisManager.Del(ctx, req.Keys...)
	if err != nil {
		InternalError(w, fmt.Sprintf("redis del failed: %v", err))
		return
	}

	OK(w, map[string]interface{}{
		"success": true,
	})
}
