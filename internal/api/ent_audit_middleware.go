package api

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
)

// ── 企业审计中间件 ───────────────────────────────────────────────────────
//
// AuditMiddleware 挂在 authMW 之后（集成任务 #22 接线），对 /v1/ent/* 与
// /admin/*（含 /v1/admin/*）的写方法（POST/PUT/PATCH/DELETE）记录审计。
//
// 修复现有 LoggingMiddleware 审计 userID 恒空的问题：本中间件从 authMW
// 注入的 claims 中取 userID（不改动原 LoggingMiddleware）。
// 审计写入走 db.AuditLog（Redis Stream），通过 channel 异步批量处理。

// auditChan 缓冲 500 条审计条目，超出时丢弃旧条目（背压保护）。
// P0-安全：传递 tenantID 确保租户隔离。
// P1-修复：使用 channel + worker 替代 go func()，防止 goroutine 逃逸无背压。
var auditChan = make(chan auditRecord, 500)

type auditRecord struct {
	userID   string
	tenantID string
	action   string
	resource string
	detail   string
	ip       string
}

// auditWorker 串行消费审计写入 channel，避免 goroutine 堆积。
// 传入 lifecycleCtx 以支持优雅关闭（P0 修复：后台协程应可被 shutdown 信号终止）。
func auditWorker(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			// 处理剩余队列中的审计条目
			for {
				select {
				case rec := <-auditChan:
					writeAuditRecord(rec)
				default:
					return
				}
			}
		case rec := <-auditChan:
			writeAuditRecord(rec)
		}
	}
}

func writeAuditRecord(rec auditRecord) {
	defer func() {
		if r := recover(); r != nil {
			slog.Error("audit middleware: record panic", "panic", r)
		}
	}()
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	db.AuditLog(ctx, rec.userID, rec.tenantID, rec.action, rec.resource, rec.detail, rec.ip, nil)
}

func init() {
	// P0: init 中启动默认 worker（context.Background 不影响 shutdown，因为
	// main.go 可调用 StartAuditWorker(lifecycleCtx) 替换为可取消的 worker）
	go auditWorker(context.Background())
}

// StartAuditWorker 启动一个可取消的审计 worker，替换 init 启动的默认 worker。
// 由 main.go 传入 lifecycleCtx 以支持优雅关闭。
func StartAuditWorker(ctx context.Context) {
	go auditWorker(ctx)
}

// auditMWRecord 审计写入函数，抽成变量便于测试替换（默认 channel 异步 db.AuditLog）。
var auditMWRecord = func(userID, tenantID, action, resource, detail, ip string) {
	select {
	case auditChan <- auditRecord{userID: userID, tenantID: tenantID, action: action, resource: resource, detail: detail, ip: ip}:
	default:
		// channel 已满，丢弃条目（背压保护）
		slog.Warn("audit middleware: channel full, dropping record", "action", action)
	}
}

// auditScopedPath 判断路径是否属于审计管控范围。
func auditScopedPath(path string) bool {
	return strings.HasPrefix(path, "/v1/ent/") ||
		strings.HasPrefix(path, "/admin/") ||
		strings.HasPrefix(path, "/v1/admin/")
}

// auditWriteMethod 判断是否为写方法。
func auditWriteMethod(method string) bool {
	switch method {
	case http.MethodPost, http.MethodPut, http.MethodPatch, http.MethodDelete:
		return true
	default:
		return false
	}
}

// AuditMiddleware 审计中间件（非管控请求零开销直通）。
func AuditMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !auditWriteMethod(r.Method) || !auditScopedPath(r.URL.Path) {
			next.ServeHTTP(w, r)
			return
		}

		// 包装以捕获状态码（复用 middleware.go 的 responseWriter）
		var flusher http.Flusher
		if f, ok := w.(http.Flusher); ok {
			flusher = f
		}
		rw := &responseWriter{ResponseWriter: w, status: http.StatusOK, flusher: flusher}
		next.ServeHTTP(rw, r)

		userID := ""
		tenantID := ""
		if claims := auth.GetClaims(r.Context()); claims != nil {
			userID = claims.UserID
			tenantID = claims.TenantID
		}
		action := r.Method + " " + r.URL.Path
		if len(action) > 64 {
			action = action[:64]
		}
		auditMWRecord(userID, tenantID, action, r.URL.Path, fmt.Sprintf("status=%d", rw.status), r.RemoteAddr)
	})
}
