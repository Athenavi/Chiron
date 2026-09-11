package api

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/broadcast"
	"github.com/athenavi/chiron/internal/db"
	"github.com/athenavi/chiron/internal/session"
)

// ── Mode constants ──

const (
	ModeAsk  = "ask"
	ModeAuto = "auto"
	ModeYOLO = "yolo"
)

var validModes = map[string]bool{ModeAsk: true, ModeAuto: true, ModeYOLO: true}

// ── ModeStore ──
//
// 会话授权模式（ask / auto / yolo）：
//   - ask ：写类工具（执行/文件写/git 写/浏览器与网络访问类）需用户批准
//   - auto：仅危险工具需批准（默认）
//   - yolo：全部自动执行（secret/逃逸参数等硬性拦截仍然生效）
//
// 判定逻辑在 Python 侧（app/agent/guards.py 的 ToolGuard）；本 Store 只负责
// 模式状态的**多副本一致存储**与**归属校验**。
//
// 存储策略：Redis 优先（key: chiron:session:mode:{tenant}:{session}，TTL 1h），
// Redis 抖动时保留进程内副本作为降级依据（与 Python SessionStore 的"抖动后自动重探"同源）。
// 安全约束：key 必须含 tenant_id，否则多租户会跨租户串读模式。

const (
	// DefaultSessionMode 未显式设置时的模式（与历史行为一致）。
	DefaultSessionMode = ModeAuto
)

type ModeStore struct {
	modes          sync.Map // 降级后端：tenant:session → modeEntry
	rdb            *db.AtomicRedis
	cleanupTick    time.Duration
	sessionTTL     time.Duration
	stopCleanup    chan struct{}
	cleanupStarted bool
	cleanupMu      sync.Mutex
}

type modeEntry struct {
	mode string
	ts   time.Time
}

func NewModeStore(rdb *db.AtomicRedis) *ModeStore {
	return &ModeStore{
		rdb:            rdb,
		cleanupTick:    30 * time.Minute,
		sessionTTL:     1 * time.Hour,
		stopCleanup:    make(chan struct{}),
		cleanupStarted: false,
	}
}

// sessionModeKey 模式键：含租户与前缀，避免多租户/多环境串读。
func sessionModeKey(tenantID, sessionID string) string {
	return db.RedisKey("session:mode:" + tenantID + ":" + sessionID)
}

// degradeKey 进程内降级后端的键。
func degradeKey(tenantID, sessionID string) string {
	return tenantID + ":" + sessionID
}

// SetCleanupInterval 设置后台清理间隔（默认 30 分钟）。
// 必须在 StartCleanup 之前调用才有效。
func (s *ModeStore) SetCleanupInterval(d time.Duration) {
	s.cleanupMu.Lock()
	defer s.cleanupMu.Unlock()
	if !s.cleanupStarted {
		s.cleanupTick = d
	}
}

// SetSessionTTL 设置 session 记录的 TTL（默认 1 小时），超时未更新将被清理。
// 必须在 StartCleanup 之前调用才有效。
func (s *ModeStore) SetSessionTTL(d time.Duration) {
	s.cleanupMu.Lock()
	defer s.cleanupMu.Unlock()
	if !s.cleanupStarted {
		s.sessionTTL = d
	}
}

// StartCleanup 启动后台定期清理过期 session 的协程（仅针对进程内降级副本；
// Redis 侧由 TTL 自动过期）。由 main.go 传入 lifecycleCtx 以支持优雅关闭。
func (s *ModeStore) StartCleanup(ctx context.Context) {
	s.cleanupMu.Lock()
	if s.cleanupStarted {
		s.cleanupMu.Unlock()
		return
	}
	s.cleanupStarted = true
	s.cleanupMu.Unlock()

	go func() {
		ticker := time.NewTicker(s.cleanupTick)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				s.cleanup()
			}
		}
	}()
}

// cleanup 删除超出 TTL 的过期 session（进程内降级副本）。
func (s *ModeStore) cleanup() {
	now := time.Now()
	threshold := now.Add(-s.sessionTTL)
	var expired []string
	s.modes.Range(func(key, value interface{}) bool {
		entry, ok := value.(modeEntry)
		if ok && entry.ts.Before(threshold) {
			expired = append(expired, key.(string))
		}
		return true
	})
	for _, id := range expired {
		s.modes.Delete(id)
	}
	if len(expired) > 0 {
		slog.Info("mode store: cleaned expired sessions", "count", len(expired))
	}
}

// Get 返回会话模式：Redis 优先 → 进程内降级副本 → 默认模式。
// 判定侧在读取失败时必须 fail-safe 到更严格的模式（Python guards 负责）。
func (s *ModeStore) Get(ctx context.Context, tenantID, sessionID string) string {
	if s.rdb != nil && sessionID != "" {
		if v, err := s.rdb.Get(ctx, sessionModeKey(tenantID, sessionID)).Result(); err == nil {
			if validModes[v] {
				return v
			}
		} else {
			slog.Debug("mode store: redis get failed, falling back to in-process",
				"tenant", tenantID, "session", sessionID, "error", err)
		}
	}
	if v, ok := s.modes.Load(degradeKey(tenantID, sessionID)); ok {
		if entry, ok := v.(modeEntry); ok && time.Since(entry.ts) < s.sessionTTL {
			return entry.mode
		}
	}
	return DefaultSessionMode
}

// Set 写入会话模式：Redis 为权威副本，同时写进程内副本作为 Redis 抖动时的降级依据。
// 返回 error 仅表示 Redis 写入失败（调用方可据此提示，但本地副本已生效）。
func (s *ModeStore) Set(ctx context.Context, tenantID, sessionID, mode string) error {
	if sessionID == "" {
		return fmt.Errorf("session id is required")
	}
	if !validModes[mode] {
		return fmt.Errorf("invalid mode: %s", mode)
	}
	var redisErr error
	if s.rdb != nil {
		if err := s.rdb.Set(ctx, sessionModeKey(tenantID, sessionID), mode, s.sessionTTL).Err(); err != nil {
			redisErr = err
			slog.Warn("mode store: redis set failed, keeping in-process copy",
				"tenant", tenantID, "session", sessionID, "error", err)
		}
	}
	s.modes.Store(degradeKey(tenantID, sessionID), modeEntry{mode: mode, ts: time.Now()})
	return redisErr
}

// Delete 删除会话模式（会话删除时调用，避免键残留）。
func (s *ModeStore) Delete(ctx context.Context, tenantID, sessionID string) {
	if s.rdb != nil {
		_ = s.rdb.Del(ctx, sessionModeKey(tenantID, sessionID)).Err()
	}
	s.modes.Delete(degradeKey(tenantID, sessionID))
}

// ── HTTP Handlers ──
//
// 工具审批的**等待与决策**都在 Python 侧（runtime.py 的 _pending_approvals +
// /v1/agent/approval 转发）；Go 侧不再保留第二套实现 —— 危险工具清单与参数级判定
// 只存在于 Python 的 guards.py，避免双真相源漂移（见本次扩展性审计结论）。

type ModeHandler struct {
	store      *ModeStore
	sessionMgr *session.Manager
	hub        *broadcast.Hub
}

func NewModeHandler(store *ModeStore, sessionMgr *session.Manager, hub *broadcast.Hub) *ModeHandler {
	return &ModeHandler{store: store, sessionMgr: sessionMgr, hub: hub}
}

// ownsSession 校验会话归属（防跨用户读/改模式）。会话不存在时返回 false。
func (h *ModeHandler) ownsSession(ctx context.Context, claims *auth.Claims, sessionID string) bool {
	if claims == nil || sessionID == "" || h.sessionMgr == nil {
		return false
	}
	sess, err := h.sessionMgr.GetSession(ctx, sessionID)
	if err != nil {
		return false
	}
	return sess.UserID == claims.UserID
}

// GetMode returns the current mode for a session.
func (h *ModeHandler) GetMode(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	sessionID := r.URL.Query().Get("session_id")
	if sessionID == "" {
		BadRequest(w, "session_id is required")
		return
	}
	// 归属校验：模式属会话级敏感状态，禁止跨用户读取
	if !h.ownsSession(r.Context(), claims, sessionID) {
		Forbidden(w, "access denied")
		return
	}
	mode := h.store.Get(r.Context(), claims.TenantID, sessionID)
	OK(w, map[string]string{"mode": mode, "session_id": sessionID})
}

// SetMode changes the mode for a session.
func (h *ModeHandler) SetMode(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	var body struct {
		SessionID string `json:"session_id"`
		Mode      string `json:"mode"`
	}
	if err := DecodeJSON(w, r, &body); err != nil {
		BadRequest(w, "invalid request")
		return
	}
	if body.SessionID == "" {
		BadRequest(w, "session_id is required")
		return
	}
	if !validModes[body.Mode] {
		BadRequest(w, "invalid mode: must be ask/auto/yolo")
		return
	}
	// 归属校验：否则任何登录用户都能把**别人的会话**切到 yolo（放开全部工具审批）
	if !h.ownsSession(r.Context(), claims, body.SessionID) {
		Forbidden(w, "access denied")
		return
	}

	if err := h.store.Set(r.Context(), claims.TenantID, body.SessionID, body.Mode); err != nil {
		// Redis 写失败但进程内副本已生效：仍返回 200（避免把降级误报为失败），日志已告警
		slog.Warn("mode set degraded to in-process copy",
			"session", body.SessionID, "mode", body.Mode, "error", err)
	}

	// yolo 是高敏操作（跳过全部工具审批）：留审计痕迹
	db.AuditLog(r.Context(), claims.UserID, claims.TenantID,
		"session.mode.set", "session:"+body.SessionID, "mode="+body.Mode,
		clientIP(r), map[string]interface{}{"mode": body.Mode})

	OK(w, map[string]string{"mode": body.Mode, "session_id": body.SessionID})
}
