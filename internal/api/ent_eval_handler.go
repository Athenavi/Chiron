package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
	"github.com/google/uuid"
)

// ── Agent 评估系统 API ─────────────────────────────────────────────
//
// TODO: 实现评估运行执行（CreateRun 端点 + Python 引擎 eval 模块集成），
// 当前仅提供数据集 CRUD 和版本管理功能。

// EntEvalHandler 提供 Agent 评估管理 API（数据集/运行/评分）。
type EntEvalHandler struct{}

// NewEntEvalHandler 创建评估 handler。
func NewEntEvalHandler() *EntEvalHandler {
	return &EntEvalHandler{}
}

// RegisterRoutes 挂载评估路由（authMW + RequireEntPerm("eval:manage")）。
func (h *EntEvalHandler) RegisterRoutes(mux *http.ServeMux, authMW func(http.Handler) http.Handler) {
	permMW := RequireEntPerm("eval:manage")
	handle := func(pattern string, hf http.HandlerFunc) {
		mux.Handle(pattern, authMW(permMW(http.HandlerFunc(hf))))
	}
	handle("GET /v1/ent/eval/datasets", h.ListDatasets)
	handle("POST /v1/ent/eval/datasets", h.CreateDataset)
	handle("GET /v1/ent/eval/datasets/{id}", h.GetDataset)
	handle("DELETE /v1/ent/eval/datasets/{id}", h.DeleteDataset)
	handle("GET /v1/ent/eval/runs", h.ListRuns)
	handle("GET /v1/ent/eval/runs/{id}", h.GetRun)
	handle("DELETE /v1/ent/eval/runs/{id}", h.DeleteRun)
	handle("GET /v1/ent/eval/prompts", h.ListPrompts)
	handle("POST /v1/ent/eval/prompts", h.CreatePromptVersion)
	handle("GET /v1/ent/eval/prompts/{name}", h.GetPromptVersions)
}

// ── 数据集 CRUD ──

func (h *EntEvalHandler) ListDatasets(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	rows, err := db.GlobalDBManager.Query(r.Context(),
		`SELECT id, tenant_id, name, description, example_count, created_at, updated_at
		 FROM ent_eval_datasets WHERE tenant_id = $1 ORDER BY created_at DESC`, tenantID)
	if err != nil {
		slog.Error("eval list datasets", "error", err)
		InternalError(w, "failed to list datasets")
		return
	}
	defer rows.Close()
	var datasets []map[string]interface{}
	for rows.Next() {
		var id, tenantID2, name, description string
		var exampleCount int
		var createdAt, updatedAt time.Time
		if err := rows.Scan(&id, &tenantID2, &name, &description, &exampleCount, &createdAt, &updatedAt); err != nil {
			slog.Error("eval scan dataset", "error", err)
			continue
		}
		datasets = append(datasets, map[string]interface{}{
			"id": id, "tenant_id": tenantID2, "name": name, "description": description,
			"example_count": exampleCount, "created_at": createdAt, "updated_at": updatedAt,
		})
	}
	if datasets == nil {
		datasets = []map[string]interface{}{}
	}
	OK(w, map[string]interface{}{"datasets": datasets})
}

func (h *EntEvalHandler) CreateDataset(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	var body struct {
		Name        string          `json:"name"`
		Description string          `json:"description"`
		Examples    json.RawMessage `json:"examples"`
	}
	if err := DecodeJSON(w, r, &body); err != nil {
		return
	}
	if body.Name == "" {
		BadRequest(w, "name is required")
		return
	}
	id := uuid.New().String()
	_, err := db.GlobalDBManager.Exec(r.Context(),
		`INSERT INTO ent_eval_datasets (id, tenant_id, name, description, examples, example_count)
		 VALUES ($1, $2, $3, $4, $5, $6)`,
		id, tenantID, body.Name, body.Description, body.Examples, len(body.Examples))
	if err != nil {
		slog.Error("eval create dataset", "error", err)
		InternalError(w, "failed to create dataset")
		return
	}
	OK(w, map[string]interface{}{"id": id, "name": body.Name})
}

func (h *EntEvalHandler) GetDataset(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	id := r.PathValue("id")
	if id == "" {
		BadRequest(w, "id is required")
		return
	}
	var name, description string
	var exampleCount int
	var examples []byte
	var createdAt, updatedAt time.Time
	err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT id, tenant_id, name, description, examples, example_count, created_at, updated_at
		 FROM ent_eval_datasets WHERE id = $1 AND tenant_id = $2`, id, tenantID).
		Scan(&id, &tenantID, &name, &description, &examples, &exampleCount, &createdAt, &updatedAt)
	if err != nil {
		NotFound(w, "dataset not found")
		return
	}
	var examplesParsed interface{}
	if err := json.Unmarshal(examples, &examplesParsed); err != nil {
		slog.Warn("eval: unmarshal dataset examples failed", "error", err)
		examplesParsed = []interface{}{}
	}
	OK(w, map[string]interface{}{
		"id": id, "tenant_id": tenantID, "name": name, "description": description,
		"examples": examplesParsed, "example_count": exampleCount,
		"created_at": createdAt, "updated_at": updatedAt,
	})
}

func (h *EntEvalHandler) DeleteDataset(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	id := r.PathValue("id")
	if id == "" {
		BadRequest(w, "id is required")
		return
	}
	tag, err := db.GlobalDBManager.Exec(r.Context(), `DELETE FROM ent_eval_datasets WHERE id = $1 AND tenant_id = $2`, id, tenantID)
	if err != nil {
		InternalError(w, "failed to delete dataset")
		return
	}
	if tag.RowsAffected() == 0 {
		NotFound(w, "dataset not found")
		return
	}
	OK(w, map[string]interface{}{"deleted": true})
}

// ── 评估运行 ──

func (h *EntEvalHandler) ListRuns(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	rows, err := db.GlobalDBManager.Query(r.Context(),
		`SELECT id, tenant_id, dataset_name, dataset_id, summary, status, created_at
		 FROM ent_eval_runs WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 50`, tenantID)
	if err != nil {
		slog.Error("eval list runs", "error", err)
		InternalError(w, "failed to list runs")
		return
	}
	defer rows.Close()
	var runs []map[string]interface{}
	for rows.Next() {
		var id, tenantID2, datasetName, datasetID, status string
		var summary []byte
		var createdAt time.Time
		if err := rows.Scan(&id, &tenantID2, &datasetName, &datasetID, &summary, &status, &createdAt); err != nil {
			slog.Error("eval scan run", "error", err)
			continue
		}
		var summaryParsed interface{}
		_ = json.Unmarshal(summary, &summaryParsed)
		runs = append(runs, map[string]interface{}{
			"id": id, "tenant_id": tenantID2, "dataset_name": datasetName,
			"dataset_id": datasetID, "summary": summaryParsed, "status": status, "created_at": createdAt,
		})
	}
	if runs == nil {
		runs = []map[string]interface{}{}
	}
	OK(w, map[string]interface{}{"runs": runs})
}

func (h *EntEvalHandler) GetRun(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	id := r.PathValue("id")
	if id == "" {
		BadRequest(w, "id is required")
		return
	}
	var datasetName, datasetID, status string
	var results, summary []byte
	var createdAt time.Time
	err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT id, tenant_id, dataset_name, dataset_id, results, summary, status, created_at
		 FROM ent_eval_runs WHERE id = $1 AND tenant_id = $2`, id, tenantID).
		Scan(&id, &tenantID, &datasetName, &datasetID, &results, &summary, &status, &createdAt)
	if err != nil {
		NotFound(w, "run not found")
		return
	}
	var resultsParsed, summaryParsed interface{}
	if err := json.Unmarshal(results, &resultsParsed); err != nil {
		slog.Warn("eval: unmarshal run results failed", "error", err)
		resultsParsed = []interface{}{}
	}
	if err := json.Unmarshal(summary, &summaryParsed); err != nil {
		slog.Warn("eval: unmarshal run summary failed", "error", err)
		summaryParsed = map[string]interface{}{}
	}
	OK(w, map[string]interface{}{
		"id": id, "tenant_id": tenantID, "dataset_name": datasetName, "dataset_id": datasetID,
		"results": resultsParsed, "summary": summaryParsed, "status": status, "created_at": createdAt,
	})
}

func (h *EntEvalHandler) DeleteRun(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	id := r.PathValue("id")
	if id == "" {
		BadRequest(w, "id is required")
		return
	}
	tag, err := db.GlobalDBManager.Exec(r.Context(), `DELETE FROM ent_eval_runs WHERE id = $1 AND tenant_id = $2`, id, tenantID)
	if err != nil {
		InternalError(w, "failed to delete run")
		return
	}
	if tag.RowsAffected() == 0 {
		NotFound(w, "run not found")
		return
	}
	OK(w, map[string]interface{}{"deleted": true})
}

// ── Prompt 版本管理 ──

func (h *EntEvalHandler) ListPrompts(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	rows, err := db.GlobalDBManager.Query(r.Context(),
		`SELECT DISTINCT name FROM ent_eval_prompts WHERE tenant_id = $1 ORDER BY name`, tenantID)
	if err != nil {
		slog.Error("eval list prompts", "error", err)
		InternalError(w, "failed to list prompts")
		return
	}
	defer rows.Close()
	var names []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			continue
		}
		names = append(names, name)
	}
	if names == nil {
		names = []string{}
	}
	OK(w, map[string]interface{}{"prompts": names})
}

func (h *EntEvalHandler) CreatePromptVersion(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	var body struct {
		Name    string `json:"name"`
		Content string `json:"content"`
		Note    string `json:"note"`
		Tags    string `json:"tags"`
	}
	if err := DecodeJSON(w, r, &body); err != nil {
		return
	}
	if body.Name == "" || body.Content == "" {
		BadRequest(w, "name and content are required")
		return
	}
	id := uuid.New().String()
	// 获取下一个版本号
	var maxVer int
	if err := db.GlobalDBManager.QueryRow(r.Context(),
		`SELECT COALESCE(MAX(version), 0) FROM ent_eval_prompts WHERE tenant_id = $1 AND name = $2`,
		tenantID, body.Name).Scan(&maxVer); err != nil {
		slog.Warn("eval: get max version failed, defaulting to 0", "error", err)
		maxVer = 0
	}
	version := maxVer + 1
	_, err := db.GlobalDBManager.Exec(r.Context(),
		`INSERT INTO ent_eval_prompts (id, tenant_id, name, version, content, note, tags)
		 VALUES ($1, $2, $3, $4, $5, $6, $7)`,
		id, tenantID, body.Name, version, body.Content, body.Note, body.Tags)
	if err != nil {
		slog.Error("eval create prompt version", "error", err)
		InternalError(w, "failed to create prompt version")
		return
	}
	OK(w, map[string]interface{}{"id": id, "name": body.Name, "version": version})
}

func (h *EntEvalHandler) GetPromptVersions(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	if name == "" {
		BadRequest(w, "name is required")
		return
	}
	claims := auth.GetClaims(r.Context())
	tenantID := evalTenantID(claims)
	rows, err := db.GlobalDBManager.Query(r.Context(),
		`SELECT id, version, content, note, tags, created_at
		 FROM ent_eval_prompts WHERE tenant_id = $1 AND name = $2 ORDER BY version DESC`,
		tenantID, name)
	if err != nil {
		slog.Error("eval get prompt versions", "error", err)
		InternalError(w, "failed to get prompt versions")
		return
	}
	defer rows.Close()
	var versions []map[string]interface{}
	for rows.Next() {
		var id, content, note, tags string
		var version int
		var createdAt time.Time
		if err := rows.Scan(&id, &version, &content, &note, &tags, &createdAt); err != nil {
			continue
		}
		versions = append(versions, map[string]interface{}{
			"id": id, "version": version, "content": content,
			"note": note, "tags": tags, "created_at": createdAt,
		})
	}
	if versions == nil {
		versions = []map[string]interface{}{}
	}
	OK(w, map[string]interface{}{"name": name, "versions": versions})
}

// ── 辅助 ──

func evalTenantID(claims *auth.Claims) string {
	if claims != nil && claims.TenantID != "" {
		return claims.TenantID
	}
	return DefaultTenantID
}