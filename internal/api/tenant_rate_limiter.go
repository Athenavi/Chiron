package api

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
)

const tenantBucketLua = `
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local req = tonumber(ARGV[4])

local data = redis.call("HMGET", key, "tokens", "ts")
local tokens = tonumber(data[1])
local ts = tonumber(data[2])
if tokens == nil then
  tokens = capacity
  ts = now
end

local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * refill)

local allowed = 0
if tokens >= req then
  tokens = tokens - req
  allowed = 1
end

redis.call("HMSET", key, "tokens", tostring(tokens), "ts", tostring(now))
redis.call("EXPIRE", key, 300)
return tostring(allowed)
`

type TenantRateLimiter struct {
	rdb       db.RedisClient
	maxBurst  int
	refillPerSec float64
	mu     sync.Mutex
	tokens map[string]*tokenBucketLocal
}

type tokenBucketLocal struct {
	tokens     float64
	lastRefill time.Time
}

func NewTenantRateLimiter(rdb db.RedisClient, maxQPS, burst int) *TenantRateLimiter {
	return &TenantRateLimiter{
		rdb:          rdb,
		maxBurst:     burst,
		refillPerSec: float64(maxQPS),
		tokens:       make(map[string]*tokenBucketLocal),
	}
}

func (rl *TenantRateLimiter) Allow(ctx context.Context, resource, tenantID string) (bool, float64) {
	if rl.rdb == nil {
		return false, 1 // fail-close
	}
	if tenantID == "" {
		return false, 1
	}

	key := fmt.Sprintf("tenantbucket:%s:%s", resource, tenantID)
	now := float64(time.Now().UnixNano()) / 1e9

	result, err := rl.rdb.Eval(ctx, tenantBucketLua,
		[]string{key},
		rl.maxBurst, rl.refillPerSec, now, 1.0).Text()
	if err != nil {
		slog.Error("tenant rate limit Redis eval failed (fail-close)",
			"error", err, "tenant", tenantID, "resource", resource)
		return false, 1
	}
	if result == "1" {
		return true, 0
	}
	return false, 1
}

// Middleware 返回 HTTP 处理程序，用于 tenant_id + 策略参数
func (rl *TenantRateLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		claims := auth.GetClaims(r.Context())
		if claims == nil || claims.TenantID == "" {
			Unauthorized(w, ErrAuthRequired)
			return
		}
		tenantID := claims.TenantID
		resource := extractResource(r.URL.Path)

		allowed, retryAfter := rl.Allow(r.Context(), resource, tenantID)
		if !allowed {
			slog.Warn("tenant rate limit exceeded",
				"resource", resource, "tenant", tenantID, "retry_after", retryAfter)
			w.Header().Set("Retry-After", formatFloat(retryAfter))
			TooManyRequests(w)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func extractResource(path string) string {
	trimmed := strings.Trim(path, "/")
	if trimmed == "" {
		return "unknown"
	}
	parts := strings.SplitN(trimmed, "/", 4)
	if len(parts) >= 2 {
		resource := parts[1]
		if len(parts) >= 3 {
			action := parts[2]
			if action == "query" || action == "build" || action == "test" {
				return resource + "_" + action
			}
		}
		return resource
	}
	return "unknown"
}

func formatFloat(f float64) string {
	if f < 1 {
		return "1"
	}
	return strconv.Itoa(int(f))
}
