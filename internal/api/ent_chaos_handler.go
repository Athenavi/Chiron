package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strconv"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
	"github.com/google/uuid"
)

// ── 混沌工程 API ─────────────────────────────────────────────
//
// TODO: 集成 Python 引擎 chaos 模块执行实际故障注入（CreateExperiment 后、
// RollbackExperiment 时），当前仅记录数据库状态。

// EntChaosHandler 提供混沌工程实验管理 API。
type EntChaosHandler struct{}

// NewEntChaosHandler 创建混沌工程 handler。
func NewEntChaosHandler() *EntChaosHandler {
	return &EntChaosHandler{}
}

// RegisterRoutes 挂载混沌工程路由（authMW + RequireEntPerm("chaos:manage")）。
func (h *EntChaosHandler) RegisterRoutes(mux *http.ServeMux, authMW func(http.Handler) http.Handler) {
	permMW := RequireEntPerm("chaos:manage")
	handle := func(pattern string, hf http.HandlerFunc) {
		mux.Handle(pattern, authMW(permMW(hf)))
	}
	handle("GET /v1/ent/chaos/experiments", h.ListExperiments)
	handle("POST /v1/ent/chaos/experiments", h.CreateExperiment)
	handle("GET /v1/ent/chaos/experiments/{id}", h.GetExperiment)
	handle("POST /v1/ent/chaos/experiments/{id}/rollback", h.RollbackExperiment)
	handle("GET /v1/ent/chaos/status", h.Status)
	handle("DELETE /v1/ent/chaos/experiments/{id}", h.DeleteExperiment)
}

func (h *EntChaosHandler) ListExperiments(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil || claims.TenantID == "" {
		Forbidden(w, "tenant_id not found")
		return
	}
	// 分页参数
	page := 1
	if p := r.URL.Query().Get("page"); p != "" {
		if n, err := strconv.Atoi(p); err == nil && n > 0 {
			page = n
		}
	}
	limit := 50
	rows, err := db.GlobalDBManager.Query(r.Context(),
		`SELECT id, fault_type, target, duration_ms, intensity, status, config, result, created_at
		 FROM ent_chaos_experiments WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3`,
		claims.TenantID, limit, (page-1)*limit)
	if err != nil {
		slog.Error("chaos list experiments", "error", err)
		InternalError(w, "failed to list experiments")
		return
	}
	defer rows.Close()
	var list []map[string]interface{}
	for rows.Next() {
		var id, faultType, target, status, configContent string
		var durationMs, result int
		var intensity float64
		if err := rows.Scan(&id, &faultType, &target, &durationMs, &intensity, &status, &configContent, &result, nil); err != nil {
			slog.Warn("chaos scan experiment", "error", err)
			continue
		}
		list = append(list, map[string]interface{}{
			"id":          id,
			"fault_type":  faultType,
			"target":      target,
			"duration_ms": durationMs,
			"result":      result,
		})
	}
	if list == nil {
		list = []map[string]interface{}{}
	}
	OK(w, map[string]interface{}{"experiments": list, "page": page})
}

func (h *EntChaosHandler) CreateExperiment(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil {
		Forbidden(w, "unauthorized")
		return
	}
	if claims.TenantID == "" {
		Forbidden(w, "tenant_id not found")
		return
	}
	var body struct {
		FaultType  string  `json:"fault_type"`
		Target     string  `json:"target"`
		DurationMs int     `json:"duration_ms"`
		Intensity  float64 `json:"intensity"`
		ConfigJSON string  `json:"config"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		BadRequest(w, "invalid json body")
		return
	}
	if body.FaultType == "" || body.Target == "" {
		BadRequest(w, "fault_type and target are required")
		return
	}
	if body.DurationMs <= 0 {
		body.DurationMs = 1000
	}
	if body.Intensity <= 0 {
		body.Intensity = 0.5
	}
	configData := body.ConfigJSON
	if configData == "" {
		configData = "{}"
	}
	idExp := uuid.New().String()
	idErr := db.GlobalDBManager.QueryRow(r.Context(),
		`INSERT INTO ent_chaos_experiments (id, tenant_id, fault_type, target, duration_ms, intensity, config, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, NOW()) RETURNING id`,
		idExp, claims.TenantID, body.FaultType, body.Target, body.DurationMs, body.Intensity, configData).
		Scan(&idExp)
	if idErr != nil {
		slog.Error("chaos create experiment", "error", idErr)
		InternalError(w, "failed to create experiment")
		return
	}
	OK(w, map[string]string{"status": "created"})
}

func (h *EntChaosHandler) GetExperiment(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil || claims.TenantID == "" {
		Forbidden(w, "tenant_id not found")
		return
	}
	expID := r.PathValue("id")
	if expID == "" {
		BadRequest(w, "id is required")
		return
	}
	var expIDOut, faultType, target, status, configContent string
	var durationMs, result int
	var intensity float64
	err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT id, fault_type, target, duration_ms, intensity, status, config, result, created_at
		 FROM ent_chaos_experiments WHERE id = $1 AND tenant_id = $2`, expID, claims.TenantID).
		Scan(&expIDOut, &faultType, &target, &durationMs, &intensity, &status, &configContent, &result, nil)
	if err != nil {
		NotFound(w, "experiment not found")
		return
	}
	OK(w, map[string]interface{}{
		"id":          expIDOut,
		"fault_type":  faultType,
		"target":      target,
		"duration_ms": durationMs,
		"status":      status,
	})
}

func (h *EntChaosHandler) RollbackExperiment(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil || claims.TenantID == "" {
		Forbidden(w, "tenant_id not found")
		return
	}
	expID := r.PathValue("id")
	if expID == "" {
		BadRequest(w, "id is required")
		return
	}
	tag, err := db.GlobalDBManager.Exec(r.Context(),
		`UPDATE ent_chaos_experiments SET status = 'rolled_back' WHERE id = $1 AND tenant_id = $2`, expID, claims.TenantID)
	if err != nil {
		slog.Error("chaos rollback experiment", "error", err)
		InternalError(w, "failed to rollback experiment")
		return
	}
	if tag.RowsAffected() == 0 {
		NotFound(w, "experiment not found")
		return
	}
	OK(w, map[string]string{"status": "rolled_back"})
}

func (h *EntChaosHandler) Status(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil {
		Forbidden(w, "tenant_id not found")
		return
	}
	tenantID := claims.TenantID
	var activeCount, totalCount int
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT COUNT(*) FROM ent_chaos_experiments WHERE tenant_id = $1 AND status = 'running'`, tenantID).Scan(&activeCount); err != nil {
		slog.Warn("chaos status: count active failed", "error", err)
	}
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT COUNT(*) FROM ent_chaos_experiments WHERE tenant_id = $1`, tenantID).Scan(&totalCount); err != nil {
		slog.Warn("chaos status: count total failed", "error", err)
	}
	OK(w, map[string]interface{}{
		"active_count": activeCount,
		"total_count":  totalCount,
		"has_active":   activeCount > 0,
	})
}

func (h *EntChaosHandler) DeleteExperiment(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil || claims.TenantID == "" {
		Forbidden(w, "tenant_id not found")
		return
	}
	expID := r.PathValue("id")
	if expID == "" {
		BadRequest(w, "id is required")
		return
	}
	tag, err := db.GlobalDBManager.Exec(r.Context(),
		`DELETE FROM ent_chaos_experiments WHERE id = $1 AND tenant_id = $2`, expID, claims.TenantID)
	if err != nil {
		slog.Error("chaos delete experiment", "error", err)
		InternalError(w, "failed to delete experiment")
		return
	}
	if tag.RowsAffected() == 0 {
		NotFound(w, "experiment not found")
		return
	}
	OK(w, map[string]string{"status": "deleted"})
}