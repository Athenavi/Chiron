package broadcast

import (
	"context"
	"encoding/json"
	"log/slog"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/db"
	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
)

// ── 会话事件缓冲（跨实例断线重放）──
// 带 SessionID 的事件在实时 fanout 前先 XADD 到 per-session Redis Stream：
// 每会话保留最近 sseEventsMaxLen 条，滑动 sseEventsTTL 过期；XADD 流 ID 即事件
// 全局单调 ID（跨实例一致排序），SSE 重连按 Last-Event-ID 补发缺口。
const (
	sseEventsMaxLen = 200
	sseEventsTTL    = time.Hour
)

// slowSubSem 限制慢订阅者重试 goroutine 数量（P1 修复：事件风暴下防止
// goroutine 无界堆积导致 DoS）。超出上限时直接丢弃事件（SSE 可重连补发）。
var slowSubSem = make(chan struct{}, 512)

// Event is a generic event for SSE broadcasting.
// ID 由发布端在写入会话缓冲流后填充（XADD 流 ID），非空时 SSE 输出 id: 行。
type Event struct {
	ID        string      `json:"id,omitempty"`
	Type      string      `json:"type"`
	Data      interface{} `json:"data"`
	SessionID string      `json:"session_id,omitempty"`
}

// Hub manages SSE subscribers and cross-instance event broadcasting.
type Hub struct {
	mu         sync.RWMutex
	subs       map[string]chan Event
	closed     bool
	pubsub     *redis.PubSub
	rdb        db.RedisClient
	channel    string
	localOnly  bool
	instanceID string
}

// envelope wraps an event with its originating instance for deduplication.
type envelope struct {
	Origin string `json:"origin"`
	Event  Event  `json:"event"`
}

func NewHub(rdb db.RedisClient) *Hub {
	h := &Hub{
		subs:       make(map[string]chan Event),
		rdb:        rdb,
		channel:    db.RedisKey("chiron:events"),
		localOnly:  rdb == nil,
		instanceID: uuid.New().String(),
	}

	if !h.localOnly {
		h.pubsub = rdb.Subscribe(context.Background(), h.channel)
		go h.redisListener()
	}

	return h
}

func (h *Hub) Subscribe(id string) chan Event {
	h.mu.Lock()
	defer h.mu.Unlock()

	if oldCh, ok := h.subs[id]; ok {
		close(oldCh)
	}
	ch := make(chan Event, 256)
	h.subs[id] = ch
	return ch
}

func (h *Hub) Unsubscribe(id string) {
	h.mu.Lock()
	defer h.mu.Unlock()

	if ch, ok := h.subs[id]; ok {
		close(ch)
		delete(h.subs, id)
	}
}

func (h *Hub) Publish(event Event) {
	// 会话事件先写入 per-session 缓冲流，取得全局单调 ID（跨实例一致排序/重放依据）；
	// 缓冲失败（Redis 故障）时仅失去重放能力，实时 fanout 照常。
	if !h.localOnly && event.SessionID != "" {
		event.ID = h.appendSessionEvent(context.Background(), event)
	}

	// Local fan-out with goroutine per slow subscriber (non-blocking, no dropping)
	h.mu.RLock()
	if h.closed {
		h.mu.RUnlock()
		return
	}
	for _, ch := range h.subs {
		select {
		case ch <- event:
		default:
			// Slow subscriber: spawn goroutine so fast subscribers aren't blocked
			select {
			case slowSubSem <- struct{}{}:
				go func(c chan Event) {
					defer func() {
						if r := recover(); r != nil {
							// channel 已关闭，丢弃事件即可
						}
						<-slowSubSem
					}()
					timer := time.NewTimer(3 * time.Second)
					defer timer.Stop()
					select {
					case c <- event:
					case <-timer.C:
						slog.Warn("subscriber too slow, dropping event after 3s timeout")
					}
				}(ch)
			default:
				slog.Warn("too many slow subscribers, dropping event")
			}
		}
	}
	h.mu.RUnlock()

	// Cross-instance via Redis
	if !h.localOnly {
		env := envelope{Origin: h.instanceID, Event: event}
		data, err := json.Marshal(env)
		if err != nil {
			slog.Error("publish: failed to marshal envelope", "error", err)
			return
		}
		if err := h.rdb.Publish(context.Background(), h.channel, data).Err(); err != nil {
			slog.Error("redis publish failed", "error", err)
		}
	}
}

// sessionEventsKey 返回会话事件缓冲流键（统一前缀 + 会话维度命名空间）。
func sessionEventsKey(sessionID string) string {
	return db.RedisKey("sse:events:") + sessionID
}

// appendSessionEvent 将会话事件追加到 per-session Redis Stream（容量上限 + 滑动 TTL），
// 返回流 ID 作为事件全局单调 ID；失败返回空串（调用方继续实时 fanout，仅失去重放能力）。
func (h *Hub) appendSessionEvent(ctx context.Context, ev Event) string {
	payload, err := json.Marshal(ev)
	if err != nil {
		slog.Error("sse buffer: marshal event failed", "error", err)
		return ""
	}
	key := sessionEventsKey(ev.SessionID)
	id, err := h.rdb.XAdd(ctx, &redis.XAddArgs{
		Stream: key,
		MaxLen: sseEventsMaxLen,
		Approx: true,
		Values: map[string]interface{}{"e": string(payload)},
	}).Result()
	if err != nil {
		slog.Warn("sse buffer: xadd failed", "session", ev.SessionID, "error", err)
		return ""
	}
	// 滑动过期：会话持续活动时续期，空闲 1h 后清理流。
	if err := h.rdb.Expire(ctx, key, sseEventsTTL).Err(); err != nil {
		slog.Debug("sse buffer: expire failed", "session", ev.SessionID, "error", err)
	}
	return id
}

// ReplayAfter 返回某会话在 after（流 ID，不含）之后缓存的会话事件（最多 sseEventsMaxLen 条），
// 事件按流序返回并带各自 ID。after 为空 = 新连接，不补历史；Redis 不可用/无缓冲时返回空。
func (h *Hub) ReplayAfter(ctx context.Context, sessionID, after string) ([]Event, error) {
	if h.localOnly || sessionID == "" || after == "" {
		return nil, nil
	}
	msgs, err := h.rdb.XRange(ctx, sessionEventsKey(sessionID), "("+after, "+", sseEventsMaxLen).Result()
	if err != nil {
		return nil, err
	}
	events := make([]Event, 0, len(msgs))
	for _, m := range msgs {
		raw, ok := m.Values["e"].(string)
		if !ok {
			continue
		}
		var ev Event
		if err := json.Unmarshal([]byte(raw), &ev); err != nil {
			slog.Warn("sse buffer: unmarshal entry failed", "session", sessionID, "id", m.ID)
			continue
		}
		ev.ID = m.ID
		events = append(events, ev)
	}
	return events, nil
}

func (h *Hub) redisListener() {
	ch := h.pubsub.Channel()
	for msg := range ch {
		var env envelope
		if err := json.Unmarshal([]byte(msg.Payload), &env); err != nil {
			continue
		}

		// Skip events that originated from this instance (already delivered locally)
		if env.Origin == h.instanceID {
			continue
		}

		h.mu.RLock()
		if h.closed {
			h.mu.RUnlock()
			return
		}
		for _, subCh := range h.subs {
			select {
			case subCh <- env.Event:
			default:
				// Use semaphore to limit goroutine spawning (same pattern as Publish)
				select {
				case slowSubSem <- struct{}{}:
					go func(c chan Event) {
						defer func() {
							if r := recover(); r != nil {
								// channel closed, discard
							}
							<-slowSubSem
						}()
						timer := time.NewTimer(3 * time.Second)
						defer timer.Stop()
						select {
						case c <- env.Event:
						case <-timer.C:
							slog.Warn("subscriber slow, dropping after 3s timeout")
						}
					}(subCh)
				default:
					slog.Warn("too many slow subscribers (redis), dropping event")
				}
			}
		}
		h.mu.RUnlock()
	}
}

func (h *Hub) Close() {
	if h.pubsub != nil {
		h.pubsub.Close()
	}
	h.mu.Lock()
	defer h.mu.Unlock()
	h.closed = true
	for id, ch := range h.subs {
		close(ch)
		delete(h.subs, id)
	}
}

// SSE channel format: JSON lines, optional id: line for Last-Event-ID replay
func FormatSSE(event Event) string {
	data, err := json.Marshal(event)
	if err != nil {
		slog.Error("format SSE: failed to marshal event", "error", err)
		return "data: {\"error\":\"marshal failed\"}\n\n"
	}
	if event.ID != "" {
		return "id: " + event.ID + "\ndata: " + string(data) + "\n\n"
	}
	return "data: " + string(data) + "\n\n"
}
