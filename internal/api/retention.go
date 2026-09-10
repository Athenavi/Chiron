package api

import (
	"context"
	"log/slog"
	"os"
	"strconv"
	"time"

	"github.com/athenavi/chiron/internal/db"
)

// ── 保留策略（A7/C1）──
//
// turns / task_idempotency 这类"每回合/每任务写一行"的表如果不清理，企业化长期运行会
// 持续膨胀（turns ≈ 每轮对话一行，task_idempotency ≈ 每个后台任务一行）。
//
// 分工：本文件清理 turns（网关写入）；task_idempotency 由引擎侧同类清理负责
// （python-engine/app/queue/idempotency.py 的 purge_older_than）。
//
// 可配置：TURN_RETENTION_DAYS（默认 30）、RETENTION_INTERVAL_HOURS（默认 6）。

const (
	retentionIntervalDefault = 6 * time.Hour
	turnRetentionDaysDefault = 30
	retentionTimeout         = 30 * time.Second
)

// StartRetentionCleaner 启动 turns 保留策略清理循环（受 lifecycleCtx 控制）。
func StartRetentionCleaner(ctx context.Context) {
	if db.Pool == nil {
		return
	}
	days := turnRetentionDays()
	interval := retentionInterval()
	go func() {
		ticker := time.NewTicker(interval)
		defer ticker.Stop()
		slog.Info("turn retention cleaner started",
			"retention_days", days, "interval_hours", int(interval.Hours()))
		for {
			select {
			case <-ctx.Done():
				slog.Info("turn retention cleaner stopped")
				return
			case <-ticker.C:
				purgeFinishedTurns(ctx, days)
			}
		}
	}()
}

func turnRetentionDays() int {
	if v := os.Getenv("TURN_RETENTION_DAYS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return n
		}
	}
	return turnRetentionDaysDefault
}

func retentionInterval() time.Duration {
	if v := os.Getenv("RETENTION_INTERVAL_HOURS"); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			return time.Duration(n) * time.Hour
		}
	}
	return retentionIntervalDefault
}

// purgeFinishedTurns 删除保留期外已完结的回合。
// running 状态不删（避免误删进行中的现场）；created_at 在模型里生成为 VARCHAR(255)
// （写入值是 PG NOW() 的文本形式），因此显式 ::timestamptz 解析——解析失败只会让本次
// 清理报错并留下告警，不影响主链路。
func purgeFinishedTurns(ctx context.Context, days int) {
	cctx, cancel := context.WithTimeout(context.WithoutCancel(ctx), retentionTimeout)
	defer cancel()
	tag, err := db.Pool.Exec(cctx,
		`DELETE FROM turns
		 WHERE status <> 'running'
		   AND created_at::timestamptz < NOW() - make_interval(days => $1)`,
		days)
	if err != nil {
		slog.Warn("turn retention purge failed", "retention_days", days, "error", err)
		return
	}
	if n := tag.RowsAffected(); n > 0 {
		slog.Info("turn retention purge done", "removed", n, "retention_days", days)
	}
}
