// Package id provides a Snowflake-style unique ID generator.
//
// Format (64-bit):
//
//	1 bit  : unused (sign bit, always 0)
//	41 bits: timestamp in milliseconds since custom epoch
//	10 bits: worker ID (0-1023)
//	12 bits: sequence number (0-4095)
//
// IDs are returned as compact base62 strings (e.g. "7Jq2r3kLx9").
package id

import (
	"fmt"
	"math/rand"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/athenavi/chiron/config"
)

const (
	epochMillis int64 = 1700000000000 // 2023-11-14T22:13:20Z

	workerBits  uint8 = 10
	seqBits     uint8 = 12
	workerShift       = seqBits
	timeShift         = seqBits + workerBits
	workerMax         = -1 ^ (-1 << workerBits)
	seqMax            = -1 ^ (-1 << seqBits)
)

var (
	defaultGenerator *Generator
	once             sync.Once
)

// Generator is a Snowflake-style ID generator.
type Generator struct {
	mu       sync.Mutex
	workerID int64
	lastTime int64
	seq      int64
}

// New creates a Generator with the given worker ID (0-1023).
func New(workerID int64) (*Generator, error) {
	if workerID < 0 || workerID > workerMax {
		return nil, fmt.Errorf("worker ID must be between 0 and %d", workerMax)
	}
	return &Generator{workerID: workerID}, nil
}

// Next returns a unique base62-encoded ID string.
func (g *Generator) Next() string {
	return base62Encode(g.nextInt64())
}

// nextInt64 generates the next unique int64 ID.
func (g *Generator) nextInt64() int64 {
	g.mu.Lock()
	defer g.mu.Unlock()

	now := time.Now().UnixMilli() - epochMillis
	if now < 0 {
		// 时钟早于 epoch：只使用 sequence 保证唯一性，避免忙等死循环
		g.seq = (g.seq + 1) & seqMax
		return (0 << timeShift) | (g.workerID << workerShift) | g.seq
	}
	if now <= g.lastTime {
		// Same millisecond or clock regression — reuse lastTime to guarantee uniqueness.
		g.seq = (g.seq + 1) & seqMax
		if g.seq == 0 {
			// Sequence exhausted — wait for real clock to advance past lastTime.
			for now <= g.lastTime {
				now = time.Now().UnixMilli() - epochMillis
			}
			g.lastTime = now
		}
		return (g.lastTime << timeShift) | (g.workerID << workerShift) | g.seq
	}

	// New millisecond — reset sequence.
	g.seq = 0
	g.lastTime = now
	return (now << timeShift) | (g.workerID << workerShift) | g.seq
}

// workerIDFile 持久化 worker ID 的文件名（位于 GetDefaultDataDir() 下）。
// 首次启动自动分配并落盘：同一 data 目录重启后保持同一 worker ID；
// 多副本部署请显式设置 WORKER_ID（0-1023），或为每个实例提供独立 data 目录。
const workerIDFile = "worker.id"

// resolveWorkerID 返回实例的 snowflake worker ID，优先级：
//  1. WORKER_ID 环境变量（显式编排，多实例推荐）
//  2. data 目录下 worker.id 持久化文件（自动分配并固化，重启不变）
//  3. 随机分配并写入 worker.id
// 修复前默认恒为 0：多实例同一毫秒各自递增 seq 会产出相同 ID（JWT jti 等碰撞）。
func resolveWorkerID() int64 {
	if v := os.Getenv("WORKER_ID"); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil && n >= 0 && n <= workerMax {
			return n
		}
	}
	path := filepath.Join(config.GetDefaultDataDir(), workerIDFile)
	if b, err := os.ReadFile(path); err == nil {
		if n, err := strconv.ParseInt(strings.TrimSpace(string(b)), 10, 64); err == nil && n >= 0 && n <= workerMax {
			return n
		}
	}
	n := rand.Int63n(workerMax + 1)
	if dir := filepath.Dir(path); dir != "" {
		_ = os.MkdirAll(dir, 0o755)
	}
	if err := os.WriteFile(path, []byte(strconv.FormatInt(n, 10)), 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "id: failed to persist worker id: %v\n", err)
	}
	return n
}

// NextID returns a unique ID using the package-level default generator.
// The default generator reads WORKER_ID from environment (0-1023) or an
// auto-assigned persisted worker ID (see resolveWorkerID).
func NextID() string {
	once.Do(func() {
		wid := resolveWorkerID()
		defaultGenerator, _ = New(wid)
	})
	return defaultGenerator.Next()
}

// base62Encode encodes an int64 as a base62 string.
const base62Chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

func base62Encode(n int64) string {
	if n == 0 {
		return "0"
	}
	buf := make([]byte, 0, 12)
	for n > 0 {
		buf = append(buf, base62Chars[n%62])
		n /= 62
	}
	// Reverse
	for i, j := 0, len(buf)-1; i < j; i, j = i+1, j-1 {
		buf[i], buf[j] = buf[j], buf[i]
	}
	return string(buf)
}
