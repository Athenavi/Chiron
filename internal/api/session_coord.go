package api

import (
	"context"
	"errors"
	"log/slog"
	"strings"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/db"
)

// ── Agent 跨实例协调 ─────────────────────────────────────────────
//
// 多网关实例下 agent 任务的"同一 session 防重"与"取消"原依赖进程内
// sessionCancels(仅单实例有效)。这里补齐:
//  1. 同 session Redis 运行锁(agent:run-lock:<sid>,SET NX + TTL),杜绝重复执行;
//  2. 取消经 Redis 广播(agent:cancel),持有该 session 的实例执行真实取消。
// Redis 不可用时均兑底为本地行为并告警(与 SharedSemaphore 一致)。

const (
	agentRunLockPrefix = "agent:run-lock:"
	agentRunLockTTL    = 12 * time.Minute // 长任务兜底；正常结束显式释放
	agentCancelChannel = "agent:cancel"
)

const sessionRunLockLua = `
if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'EX', ARGV[2]) then
  return 1
end
return 0
`

var errRedisUnavailable = errors.New("redis unavailable")

// AcquireSessionRunLock 为 session 抢占跨实例运行锁（原子 SET NX + TTL）。
// 返回：release（Redis 获锁时非 nil，任务结束/取消必须调用）、ok=是否持有、
// err!=nil 表示 Redis 不可用——调用方应兑底为进程内 sessionCancels。
func AcquireSessionRunLock(ctx context.Context, sessionID, owner string) (release func(), ok bool, err error) {
	if db.Redis == nil {
		return nil, false, errRedisUnavailable
	}
	res := db.Redis.Eval(ctx, sessionRunLockLua,
		[]string{agentRunLockPrefix + sessionID}, owner, int(agentRunLockTTL.Seconds()))
	if resErr := res.Err(); resErr != nil {
		return nil, false, resErr
	}
	n, _ := res.Int()
	if n != 1 {
		return nil, false, nil // 已被其它实例持有（同 session 正在运行）
	}
	var once sync.Once
	return func() {
		once.Do(func() {
			_ = db.Redis.Del(context.Background(), agentRunLockPrefix+sessionID).Err()
		})
	}, true, nil
}

// CancelSessionBroadcast 把取消请求广播给所有网关实例（本实例未命中时调用）。
// payload: sessionID|userID，接收端校验归属后执行取消。
func CancelSessionBroadcast(ctx context.Context, sessionID, userID string) error {
	if db.Redis == nil {
		return errRedisUnavailable
	}
	payload := sessionID + "|" + userID
	if err := db.Redis.Publish(ctx, agentCancelChannel, payload).Err(); err != nil {
		return err
	}
	slog.Info("session cancel broadcast", "session_id", sessionID)
	return nil
}

// StartAgentCancelSubscriber 启动跨实例取消订阅（main 中调用一次）。
// 收到广播后在本实例 sessionCancels 中查找并校验用户，命中则取消该任务。
func StartAgentCancelSubscriber(ctx context.Context) {
	if db.Redis == nil {
		slog.Warn("agent cancel subscriber disabled: redis unavailable")
		return
	}
	go func() {
		pubsub := db.Redis.Subscribe(ctx, agentCancelChannel)
		defer pubsub.Close()
		ch := pubsub.Channel()
		slog.Info("agent cancel subscriber started")
		for {
			select {
			case <-ctx.Done():
				return
			case msg, ok := <-ch:
				if !ok {
					slog.Warn("agent cancel subscriber channel closed")
					return
				}
				parts := strings.SplitN(msg.Payload, "|", 2)
				if len(parts) != 2 {
					continue
				}
				sessionID, userID := parts[0], parts[1]
				if v, loaded := sessionCancels.LoadAndDelete(sessionID); loaded {
					sc := v.(sessionCancel)
					if sc.userID != userID {
						sessionCancels.Store(sessionID, sc) // 非本人 session，放回
						continue
					}
					sc.cancel()
					slog.Info("session cancelled via cross-instance broadcast",
						"session_id", sessionID)
				}
			}
		}
	}()
}
