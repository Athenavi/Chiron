package api

import (
	"context"
	"log/slog"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/db"
)

// ── SharedSemaphore：跨实例信号量 ───────────────────────────────
//
// 多网关实例下，进程内 chan 信号量只约束单实例，全局并发上限随实例数放大。
// SharedSemaphore 以 Redis Lua 原子计数为权威（key: sem:<name>，INCR 至多 limit，
// 超限 DECR 还原；acquire 成功即续期 TTL），Redis 不可用时回退到进程内 chan
// 兑底（fail-open + 降级告警，此时多实例下为近似限制，与既有行为一致）。

const (
	semaphoreKeyPrefix = "sem:"
	// semaphoreTTL Redis 计数键 TTL：持有者崩溃时计数在 TTL 后自动清零，
	// 避免永久泄漏；正常 release 显式 DECR。取值需远大于单次任务时长。
	semaphoreTTL = 5 * time.Minute
	// semaphorePoll 阻塞等待全局槽位的轮询间隔。
	semaphorePoll = 100 * time.Millisecond
)

const semAcquireLua = `
local v = redis.call('INCR', KEYS[1])
if v > tonumber(ARGV[1]) then
  redis.call('DECR', KEYS[1])
  return 0
end
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
`

const semReleaseLua = `
redis.call('DECR', KEYS[1])
return 1
`

// SharedSemaphore 全局/租户级并发信号量。
// limit <= 0 时视为不限制（与调用方约定；构造时归一到 1 的语义见 NewSharedSemaphore）。
type SharedSemaphore struct {
	name  string
	limit int64
	local chan struct{} // Redis 不可用时的本地兑底
	rdb   db.RedisClient

	mu      sync.Mutex
	warned  bool
}

// NewSharedSemaphore 构造命名信号量。rdb 可为 nil（纯本地模式）。
// limit <= 0 表示不限制（不占用 Redis/本地槽位，恒可获取）。
func NewSharedSemaphore(rdb db.RedisClient, name string, limit int) *SharedSemaphore {
	if limit < 0 {
		limit = 0
	}
	localCap := limit
	if localCap == 0 {
		localCap = 1 // 不限制模式仍给本地一个"恒成功"槽位占位；见 TryAcquire 短路
	}
	return &SharedSemaphore{
		name:  name,
		limit: int64(limit),
		local: make(chan struct{}, localCap),
		rdb:   rdb,
	}
}

// TryAcquire 非阻塞获取。返回的 release 必须调用；未获取时返回 ok=false。
func (s *SharedSemaphore) TryAcquire(ctx context.Context) (release func(), ok bool) {
	if s.limit == 0 {
		return func() {}, true // 不限制
	}
	if s.rdb != nil {
		res := s.rdb.Eval(ctx, semAcquireLua, []string{semaphoreKeyPrefix + s.name},
			s.limit, int(semaphoreTTL.Seconds()))
		resErr := res.Err()
		if resErr == nil {
			if n, err := res.Int(); err == nil && n == 1 {
				var once sync.Once
				return func() {
					once.Do(func() {
						// 释放为尽力而为：计数键崩溃后由 TTL 兜底，故忽略错误。
						_ = s.rdb.Eval(context.Background(), semReleaseLua,
							[]string{semaphoreKeyPrefix + s.name}).Err()
					})
				}, true
			}
			return nil, false // Redis 计数已满
		}
		s.warnDegrade(resErr)
	}
	select {
	case s.local <- struct{}{}:
		return func() { <-s.local }, true
	default:
		return nil, false
	}
}

// Acquire 阻塞直到获取槽位或 ctx 取消。Redis 为权威时轮询全局槽位。
func (s *SharedSemaphore) Acquire(ctx context.Context) (release func(), ok bool) {
	if s.limit == 0 {
		return func() {}, true
	}
	for {
		if release, ok := s.TryAcquire(ctx); ok {
			return release, true
		}
		select {
		case <-ctx.Done():
			return nil, false
		case <-time.After(semaphorePoll):
		}
	}
}

func (s *SharedSemaphore) warnDegrade(err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.warned {
		s.warned = true
		slog.Warn("shared semaphore degraded to in-process (Redis unavailable)",
			"sem", s.name, "error", err)
	}
}
