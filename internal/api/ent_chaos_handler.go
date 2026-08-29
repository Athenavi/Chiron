package api

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
	"github.com/google/uuid"
)

// ── 混沌工程 API ─────────────────────────────────────────────

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
	rows, err := db.GlobalDBManager.Query(r.Context(),
		`SELECT id, fault_type, target, duration_ms, intensity, status, config, result, created_at
		 FROM ent_chaos_experiments ORDER BY created_at DESC`)
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
	OK(w, map[string]interface{}{"experiments": list})
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
	insertErr := db.GlobalDBManager.QueryRow(r.Context(),
		`INSERT INTO ent_chaos_experiments (id, tenant_id, fault_type, target, duration_ms, intensity, config, created_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, NOW()) RETURNING id`,
		uuid.New().String(), claims.TenantID, body.FaultType, body.Target, body.DurationMs, body.Intensity, configData).
		Scan(&insertErr)
	if insertErr != nil {
		slog.Error("chaos create experiment", "error", insertErr)
		InternalError(w, "failed to create experiment")
		return
	}
	OK(w, map[string]string{"status": "created"})
}

func (h *EntChaosHandler) GetExperiment(w http.ResponseWriter, r *http.Request) {
	expID := r.PathValue("id")
	if expID == "" {
		BadRequest(w, "id is required")
		return
	}
	rowErr := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT id, fault_type, target, duration_ms, intensity, status, config, result, created_at
		 FROM ent_chaos_experiments WHERE id = $1`, expID).
		Scan(&rowErr)`
	if rowErr != nil {
		NotFound(w, "experiment not found")
		return
	}
	OK(w, "experiment_found")
}

func (h *EntChaosHandler) RollbackExperiment(w http.ResponseWriter, r *http.Request) {
	expID := r.PathValue("id")
	if expID == "" {
		BadRequest(w, "id is required")
		return
	}
	tag, err := db.GlobalDBManager.Exec(r.Context(),
		`UPDATE ent_chaos_experiments SET status = 'rolled_back' WHERE id = $1`, expID)
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
	var activeCount, totalCount int
	_ = db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT COUNT(*) FROM ent_chaos_experiments WHERE status = 'running'`).Scan(&activeCount)
	_ = db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT COUNT(*) FROM ent_chaos_experiments`).Scan(&totalCount)
	OK(w, map[string]interface{}{
		"active_count": activeCount,
		"total_count":  totalCount,
		"has_active":   activeCount > 0,
	})
}

func (h *EntChaosHandler) DeleteExperiment(w http.ResponseWriter, r *http.Request) {
	expID := r.PathValue("id")
	if expID == "" {
		BadRequest(w, "id is required")
		return
	}
	tag, err := db.GlobalDBManager.Exec(r.Context(),
		`DELETE FROM ent_chaos_experiments WHERE id = $1`, expID)
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