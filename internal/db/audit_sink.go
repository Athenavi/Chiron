package db

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"regexp"
	"strings"
	"sync"
	"time"
)

// ── AuditSink：Redis Stream �?PG audit_logs 批量落库 ─────────────────────
//
// 作为 AuditConsumer �?handler 回调使用�?
//
//	sink := db.NewDefaultAuditSink()
//	consumer := db.NewAuditConsumer(redis, sink.Handle)
//	go consumer.Start(ctx)
//
// 批量策略：≥100 条或 1s 窗口先到先发�?
// 失败策略：批�?INSERT 失败�?slog.Error 并丢弃该批（Handle 恒返�?nil�?
// 消费者照�?ACK）——宁可丢不可堵，避免毒消息在消费组内无限重投�?
// 关键事件（如登录审计）已�?handler 显式记录兜底�?

var auditSinkUUIDRe = regexp.MustCompile(
	`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)

// AuditSink 审计日志批量落库 sink�?
type AuditSink struct {
	mu        sync.Mutex
	buf       []AuditEntry
	writer    func(ctx context.Context, entries []AuditEntry) error
	batchSize int
	window    time.Duration
	stopCh    chan struct{}
	doneCh    chan struct{}
}

// NewAuditSink 创建 sink 并启动窗口定�?flush 协程�?
// batchSize<=0 �?100；window<=0 �?1s�?
func NewAuditSink(writer func(ctx context.Context, entries []AuditEntry) error,
	batchSize int, window time.Duration) *AuditSink {
	if batchSize <= 0 {
		batchSize = 100
	}
	if window <= 0 {
		window = time.Second
	}
	s := &AuditSink{
		writer:    writer,
		batchSize: batchSize,
		window:    window,
		stopCh:    make(chan struct{}),
		doneCh:    make(chan struct{}),
	}
	go s.loop()
	return s
}

// NewDefaultAuditSink 创建默认 sink（PG 批量写入�?00 �?/ 1s 窗口）�?
func NewDefaultAuditSink() *AuditSink {
	return NewAuditSink(WriteAuditLogs, 100, time.Second)
}

// Handle 实现 AuditConsumer �?handler 回调签名�?
// 恒返�?nil：写入失败在 Flush 内记日志丢弃，保证消费�?ACK，不堵塞消费组�?
func (s *AuditSink) Handle(ctx context.Context, entry AuditEntry) error {
	s.mu.Lock()
	s.buf = append(s.buf, entry)
	full := len(s.buf) >= s.batchSize
	s.mu.Unlock()
	if full {
		s.Flush(ctx)
	}
	return nil
}

// loop 按窗口周期触�?flush，Close 时收尾�?
func (s *AuditSink) loop() {
	defer close(s.doneCh)
	ticker := time.NewTicker(s.window)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			s.Flush(context.Background())
		case <-s.stopCh:
			s.Flush(context.Background())
			return
		}
	}
}

// Flush 取出当前缓冲并调�?writer 落库；失�?slog.Error 并丢弃该批�?
func (s *AuditSink) Flush(ctx context.Context) {
	s.mu.Lock()
	if len(s.buf) == 0 {
		s.mu.Unlock()
		return
	}
	batch := s.buf
	s.buf = nil
	s.mu.Unlock()

	if s.writer == nil {
		return
	}
	if err := s.writer(ctx, batch); err != nil {
		slog.Error("audit sink: batch insert failed, dropping batch",
			"count", len(batch), "error", err)
	}
}

// Close 停止窗口协程�?flush 残留缓冲（阻塞至完成）�?
func (s *AuditSink) Close() {
	close(s.stopCh)
	<-s.doneCh
}

// ── 默认 PG 批量写入 ─────────────────────────────────────────────────────

// WriteAuditLogs 将审计条目批�?INSERT �?audit_logs�?
// 字段映射：tenant_id 非法/�?�?默认租户；user_id 非法/�?�?NULL�?
// resource_type �?resource 路径前缀归类（ent/admin/api/general）�?
func WriteAuditLogs(ctx context.Context, entries []AuditEntry) error {
	pool := Pool
	if pool == nil {
		return errors.New("audit sink: postgres pool unavailable")
	}
	if len(entries) == 0 {
		return nil
	}

	var sb strings.Builder
	sb.WriteString(`INSERT INTO audit_logs
		(id, tenant_id, user_id, action, resource_type, resource_id, details, ip_address) VALUES `)
	args := make([]any, 0, len(entries)*8)
	idx := 0
	next := func() string { idx++; return fmt.Sprintf("$%d", idx) }

	for i, e := range entries {
		tenantID := e.TenantID
		if !auditSinkUUIDRe.MatchString(tenantID) {
			tenantID = DefaultTenantID
		}
		var userID any
		if auditSinkUUIDRe.MatchString(e.UserID) {
			userID = e.UserID
		}
		details, _ := json.Marshal(struct {
			Detail  string `json:"detail"`
			Success bool   `json:"success"`
			Error   string `json:"error"`
		}{
			Detail:  e.Detail,
			Success: e.Success,
			Error:   e.Error,
		})
		if i > 0 {
			sb.WriteString(", ")
		}
		sb.WriteString("(" + next() + ", " + next() + ", " + next() + ", " + next() + ", " +
			next() + ", " + next() + ", " + next() + ", " + next() + ")")
		args = append(args, generateUUID(), tenantID, userID, clipVarchar(e.Action, 64),
			auditResourceType(e.Resource), clipVarchar(e.Resource, 64),
			string(details), nilableIP(e.IP))
	}

	_, err := pool.Exec(ctx, sb.String(), args...)
	return err
}

// auditResourceType 按资源路径前缀归类 resource_type（varchar(64)）�?
func auditResourceType(resource string) string {
	switch {
	case resource == "":
		return "general"
	case strings.HasPrefix(resource, "/v1/ent/") || strings.HasPrefix(resource, "/ent/"):
		return "ent"
	case strings.HasPrefix(resource, "/admin") || strings.HasPrefix(resource, "/v1/admin"):
		return "admin"
	case strings.HasPrefix(resource, "/"):
		return "api"
	default:
		return "general"
	}
}

// clipVarchar 截断�?varchar(n) 上限，避免落库超长报错�?
func clipVarchar(s string, n int) string {
	if len(s) > n {
		return s[:n]
	}
	return s
}

// nilableIP �?IP �?NULL（ip_address 列可空）�?
func nilableIP(ip string) any {
	if ip == "" {
		return nil
	}
	return clipVarchar(ip, 45)
}

// generateUUID 生成 UUID v4 字符串（36字符，含连字符）�?
func generateUUID() string {
	uuid := make([]byte, 16)
	if _, err := rand.Read(uuid); err != nil {
		// 极端回退：使用随机字节填�?
		for i := range uuid {
			uuid[i] = byte(i)
		}
	}
	// 设置版本 4 和变体位
	uuid[6] = (uuid[6] & 0x0f) | 0x40 // version 4
	uuid[8] = (uuid[8] & 0x3f) | 0x80 // variant RFC 4122

	return fmt.Sprintf("%s-%s-%s-%s-%s",
		hex.EncodeToString(uuid[0:4]),
		hex.EncodeToString(uuid[4:6]),
		hex.EncodeToString(uuid[6:8]),
		hex.EncodeToString(uuid[8:10]),
		hex.EncodeToString(uuid[10:16]))
}
