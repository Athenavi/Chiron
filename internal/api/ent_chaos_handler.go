package api

import (
	"net/http"

	"github.com/athenavi/chiron/internal/auth"
)

// ── 混沌工程 API ─────────────────────────────────────────────
//
// 该功能**尚未实现**，所有端点统一返回 501 Not Implemented：
//
//  1. 没有故障注入执行 —— 未接入 python-engine 的 chaos 模块；
//  2. 连数据表都不存在 —— ent_chaos_experiments 既未在 shared/models 定义，
//     也未在任何迁移中创建（对 chiron0907 / chiron0915 实测均无此表）。
//
// 此前的行为会误导调用方：
//   - CreateExperiment 只写库就返回 created、RollbackExperiment 只改状态就返回
//     rolled_back，而故障从未被注入；
//   - Status 在查表失败后静默返回 active_count=0，掩盖了表不存在的事实；
//   - List/Get/Delete 则因表不存在而 500。
//
// 路由保留，便于后续接入真正的故障注入时直接填充实现；
// 原实现可在此文件的 git 历史中找回。

const chaosNotImplemented = "chaos engineering is not implemented (no fault injection, no storage)"

// EntChaosHandler 提供混沌工程实验管理 API（当前全部返回 501）。
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

// authorize 校验租户上下文；未通过时已写出响应并返回 false。
func (h *EntChaosHandler) authorize(w http.ResponseWriter, r *http.Request) bool {
	if claims := auth.GetClaims(r.Context()); claims == nil || claims.TenantID == "" {
		Forbidden(w, "tenant_id not found")
		return false
	}
	return true
}

func (h *EntChaosHandler) ListExperiments(w http.ResponseWriter, r *http.Request) {
	if !h.authorize(w, r) {
		return
	}
	NotImplemented(w, chaosNotImplemented)
}

func (h *EntChaosHandler) CreateExperiment(w http.ResponseWriter, r *http.Request) {
	if !h.authorize(w, r) {
		return
	}
	NotImplemented(w, chaosNotImplemented)
}

func (h *EntChaosHandler) GetExperiment(w http.ResponseWriter, r *http.Request) {
	if !h.authorize(w, r) {
		return
	}
	NotImplemented(w, chaosNotImplemented)
}

func (h *EntChaosHandler) RollbackExperiment(w http.ResponseWriter, r *http.Request) {
	if !h.authorize(w, r) {
		return
	}
	NotImplemented(w, chaosNotImplemented)
}

func (h *EntChaosHandler) Status(w http.ResponseWriter, r *http.Request) {
	if !h.authorize(w, r) {
		return
	}
	NotImplemented(w, chaosNotImplemented)
}

func (h *EntChaosHandler) DeleteExperiment(w http.ResponseWriter, r *http.Request) {
	if !h.authorize(w, r) {
		return
	}
	NotImplemented(w, chaosNotImplemented)
}
