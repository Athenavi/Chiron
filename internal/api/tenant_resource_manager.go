package api

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/db"
)

// ── TenantResourceManager 租户资源隔离管理器 ──────────────────────────
//
// 集中管理每个租户的并发执行上限和存储配额，补全现有限流体系：
//   - 并发限流：TenantRateLimiter（QPS）+ DistributedRateLimiter（RPM）
//     → 新增 per-tenant goroutine 并发上限
//   - 存储配额：按租户限制存储使用量（基于 ent_quota_pools 或独立 SQL）
//
// 设计原则：默认不限制（0 = unlimited），仅配置了配额时才激活。

// TenantResourceConfig 租户资源配置（从 DB 或环境变量加载）
type TenantResourceConfig struct {
	TenantID          string
	MaxConcurrency    int   // 并发 agent/worker 上限（0 = 使用全局默认）
	MaxStorageBytes   int64 // 存储配额（0 = 不限制）
	MaxStorageFiles   int   // 文件数量上限（0 = 不限制）
}

// TenantResourceManager 租户资源管理器
type TenantResourceManager struct {
	mu           sync.RWMutex
	quotas       map[string]*TenantResourceConfig    // tenantID → config
	semaphores   map[string]chan struct{}            // tenantID → 并发信号量
	globalSem    chan struct{}                        // 全局并发信号量（回退）
	cleanupStop  chan struct{}
}

// NewTenantResourceManager 创建租户资源管理器
// globalConcurrency: 全局并发上限（当 tenant 未配置时使用）
func NewTenantResourceManager(globalConcurrency int) *TenantResourceManager {
	trm := &TenantResourceManager{
		quotas:      make(map[string]*TenantResourceConfig),
		semaphores:  make(map[string]chan struct{}),
		globalSem:   make(chan struct{}, globalConcurrency),
		cleanupStop: make(chan struct{}),
	}
	return trm
}

// StartCleanup 启动定期清理过期租户配置的协程
func (trm *TenantResourceManager) StartCleanup(ctx context.Context, interval time.Duration) {
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				trm.cleanupStale()
			}
		}
	}()
}

// cleanupStale 清理已不再活跃的租户信号量（保留配额配置）
func (trm *TenantResourceManager) cleanupStale() {
	trm.mu.Lock()
	defer trm.mu.Unlock()
	// 只清理信号量，保留配额配置以便重新加载
	trm.semaphores = make(map[string]chan struct{})
}

// SetQuota 设置租户的资源配置
func (trm *TenantResourceManager) SetQuota(cfg TenantResourceConfig) {
	trm.mu.Lock()
	defer trm.mu.Unlock()
	trm.quotas[cfg.TenantID] = &cfg
	// 如果设置了并发上限，重建信号量
	if cfg.MaxConcurrency > 0 {
		trm.semaphores[cfg.TenantID] = make(chan struct{}, cfg.MaxConcurrency)
	}
	slog.Info("tenant resource quota set",
		"tenant", cfg.TenantID,
		"max_concurrency", cfg.MaxConcurrency,
		"max_storage_bytes", cfg.MaxStorageBytes,
	)
}

// GetQuota 获取租户资源配置
func (trm *TenantResourceManager) GetQuota(tenantID string) *TenantResourceConfig {
	trm.mu.RLock()
	defer trm.mu.RUnlock()
	return trm.quotas[tenantID]
}

// RemoveQuota 移除租户资源配置
func (trm *TenantResourceManager) RemoveQuota(tenantID string) {
	trm.mu.Lock()
	defer trm.mu.Unlock()
	delete(trm.quotas, tenantID)
	delete(trm.semaphores, tenantID)
}

// Acquire 尝试获取租户并发执行许可
// 返回释放函数（必须调用）。如果租户有独立配置则使用租户级信号量，
// 否则使用全局信号量。
func (trm *TenantResourceManager) Acquire(tenantID string) (release func(), acquired bool) {
	trm.mu.RLock()
	sem, hasTenantSem := trm.semaphores[tenantID]
	trm.mu.RUnlock()

	if hasTenantSem {
		select {
		case sem <- struct{}{}:
			return func() { <-sem }, true
		default:
			return nil, false // 租户并发上限已满
		}
	}

	// 回退到全局信号量
	select {
	case trm.globalSem <- struct{}{}:
		return func() { <-trm.globalSem }, true
	default:
		return nil, false // 全局并发上限已满
	}
}

// CheckStorageQuota 检查租户存储配额是否允许添加指定大小的文件
// 需要 DB 查询当前用量，仅在配额配置 > 0 时生效
func (trm *TenantResourceManager) CheckStorageQuota(ctx context.Context, tenantID string, fileSize int64) (allowed bool, used int64, limit int64) {
	trm.mu.RLock()
	cfg, ok := trm.quotas[tenantID]
	trm.mu.RUnlock()

	if !ok || cfg.MaxStorageBytes <= 0 {
		return true, 0, 0 // 未配置存储配额
	}

	// 查询当前存储用量
	var currentBytes int64
	err := db.GlobalDBManager.QueryRow(ctx,
		`SELECT COALESCE(SUM(file_size), 0) FROM media WHERE tenant_id = $1`, tenantID).Scan(&currentBytes)
	if err != nil {
		slog.Warn("tenant resource: check storage quota failed", "tenant", tenantID, "error", err)
		return true, 0, cfg.MaxStorageBytes // fail-open
	}

	if currentBytes+fileSize > cfg.MaxStorageBytes {
		return false, currentBytes, cfg.MaxStorageBytes
	}
	return true, currentBytes, cfg.MaxStorageBytes
}

// CheckFileCountQuota 检查租户文件数量是否超限
func (trm *TenantResourceManager) CheckFileCountQuota(ctx context.Context, tenantID string) (allowed bool, current int, limit int) {
	trm.mu.RLock()
	cfg, ok := trm.quotas[tenantID]
	trm.mu.RUnlock()

	if !ok || cfg.MaxStorageFiles <= 0 {
		return true, 0, 0
	}

	var currentCount int
	err := db.GlobalDBManager.QueryRow(ctx,
		`SELECT COUNT(*) FROM media WHERE tenant_id = $1`, tenantID).Scan(&currentCount)
	if err != nil {
		slog.Warn("tenant resource: check file count quota failed", "tenant", tenantID, "error", err)
		return true, 0, cfg.MaxStorageFiles
	}

	if currentCount >= cfg.MaxStorageFiles {
		return false, currentCount, cfg.MaxStorageFiles
	}
	return true, currentCount, cfg.MaxStorageFiles
}