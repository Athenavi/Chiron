package db

import (
	"os"
	"sync"
)

// Redis 键统一前缀(N2,见 docs/redis-key-prefix-design.md):
// 多套环境(dev/prod/隔离)共用同一 Redis 时以 REDIS_KEY_PREFIX 隔离键空间。
// 默认空 = 既有行为,存量兼容。所有 Redis key/channel/stream 名必须经 RedisKey() 组装。

var (
	redisKeyPrefixOnce sync.Once
	redisKeyPrefix     string
)

// RedisKey 给 Redis key/channel/stream 加统一前缀。
// 只应在程序启动早期(env 已加载后)被调用;结果带前缀完整名。
func RedisKey(name string) string {
	redisKeyPrefixOnce.Do(func() {
		redisKeyPrefix = os.Getenv("REDIS_KEY_PREFIX")
	})
	return redisKeyPrefix + name
}
