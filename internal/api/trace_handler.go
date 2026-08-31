package api

import (
	"context"
	"encoding/json"
	"log/slog"
	"net/http"
	"strconv"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
)

// TraceSpan represents a single execution span from Redis Stream.
type TraceSpan struct {
	TraceID    string         `json:"trace_id"`
	SpanName   string         `json:"span_name"`
	DurationMs int            `json:"duration_ms"`
	Timestamp  time.Time      `json:"timestamp"`
	TenantID   string         `json:"tenant_id"`
	Metadata   map[string]any `json:"metadata,omitempty"`
}

// TraceQuery aggregates all spans for a given trace_id.
type TraceQuery struct {
	TraceID         string      `json:"trace_id"`
	Tenant          string      `json:"tenant_id"`
	SpanCount       int         `json:"span_count"`
	TotalDurationMs int         `json:"total_duration_ms"`
	Spans           []TraceSpan `json:"spans"`
}

// TraceHandler provides trace query APIs with tenant isolation.
type TraceHandler struct {
	rdb db.RedisClient
}

// NewTraceHandler creates a new trace query handler.
func NewTraceHandler(rdb db.RedisClient) *TraceHandler {
	return &TraceHandler{rdb: rdb}
}

// GetTrace retrieves the complete call chain for a trace_id.
// GET /v1/traces/{trace_id}
func (h *TraceHandler) GetTrace(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil {
		Unauthorized(w, ErrAuthRequired)
		return
	}

	traceID := r.PathValue("trace_id")
	if traceID == "" {
		BadRequest(w, "trace_id is required")
		return
	}

	tenantID := claims.TenantID
	if tenantID == "" {
		tenantID = claims.UserID
	}

	spans, err := h.queryTraces(traceID, tenantID)
	if err != nil {
		slog.Error("trace query failed", "trace_id", traceID, "tenant", tenantID, "error", err)
		InternalError(w, "trace query failed")
		return
	}

	if len(spans) == 0 {
		NotFound(w, "trace not found")
		return
	}

	for _, span := range spans {
		if span.TenantID != tenantID && span.TenantID != "" {
			slog.Warn("trace span tenant mismatch (possible cross-tenant leak)",
				"trace_id", traceID,
				"claim_tenant", tenantID,
				"span_tenant", span.TenantID,
			)
			InternalError(w, "trace data integrity check failed")
			return
		}
	}

	// Build aggregated response
	totalDuration := 0
	for _, s := range spans {
		totalDuration += s.DurationMs
	}

	result := TraceQuery{
		TraceID:         traceID,
		Tenant:          tenantID,
		SpanCount:       len(spans),
		TotalDurationMs: totalDuration,
		Spans:           spans,
	}

	OK(w, result)
}

// ListTraces lists recent trace IDs for a tenant.
// GET /v1/traces?limit=20&tenant_id=xxx
func (h *TraceHandler) ListTraces(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil {
		Unauthorized(w, ErrAuthRequired)
		return
	}

	limitStr := r.URL.Query().Get("limit")
	limit, _ := strconv.Atoi(limitStr)
	if limit <= 0 || limit > 100 {
		limit = 20
	}

	tenantID := claims.TenantID
	if tenantID == "" {
		tenantID = claims.UserID
	}

	// Scan latest trace entries from Redis Stream (tenant isolated)
	streamKey := "chiron:traces:" + tenantID

	// 使用 XRevRange 读取最新的 N 条记录（避免 XRANGE 全量扫描）
	rawEntries, err := h.rdb.XRevRangeN(r.Context(), streamKey, "+", "-", int64(limit*10)).Result()
	if err != nil {
		slog.Warn("trace list scan failed", "tenant", tenantID, "error", err)
		OK(w, map[string]any{"traces": []any{}, "count": 0})
		return
	}

	// Aggregate unique trace_ids with metadata
	traceMap := make(map[string]*TraceSpan)
	for _, entry := range rawEntries {
		var span TraceSpan
		metaRaw, _ := entry.Values["metadata"].(string)
		if err := json.Unmarshal([]byte(metaRaw), &span.Metadata); err != nil {
			continue
		}

		span.TraceID, _ = entry.Values["trace_id"].(string)
		span.SpanName, _ = entry.Values["span_name"].(string)
		durationMs, _ := entry.Values["duration_ms"].(string)
		span.DurationMs, _ = strconv.Atoi(durationMs)
		timestamp, _ := entry.Values["timestamp"].(string)
		span.Timestamp, _ = time.Parse(time.RFC3339, timestamp)

		// Only keep the first occurrence of each trace_id (latest)
		if _, exists := traceMap[span.TraceID]; !exists {
			traceMap[span.TraceID] = &span
		}
	}

	// Convert to list
	traces := make([]any, 0, len(traceMap))
	for _, span := range traceMap {
		if span.TenantID != "" && span.TenantID != tenantID {
			slog.Warn("skipping cross-tenant trace entry",
				"trace_id", span.TraceID,
				"expected_tenant", tenantID,
				"actual_tenant", span.TenantID,
			)
			continue
		}

		traces = append(traces, map[string]any{
			"trace_id":    span.TraceID,
			"span_name":   span.SpanName,
			"duration_ms": span.DurationMs,
			"timestamp":   span.Timestamp.Format(time.RFC3339),
			"metadata":    span.Metadata,
		})
	}

	OK(w, map[string]any{
		"traces": traces,
		"count":  len(traces),
	})
}

// queryTraces fetches all spans for a trace_id from Redis Stream.
func (h *TraceHandler) queryTraces(traceID, tenantID string) ([]TraceSpan, error) {
	if h.rdb == nil {
		return nil, nil // Redis unavailable 鈫?return empty
	}

	streamKey := "chiron:traces:" + tenantID

	// 使用 XRevRange 读取最近 1000 条记录（避免 XRANGE 全量扫描）
	queryCtx, queryCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer queryCancel()
	entries, err := h.rdb.XRevRangeN(queryCtx, streamKey, "+", "-", 1000).Result()
	if err != nil {
		return nil, err
	}

	// Filter by trace_id and build ordered list
	var spans []TraceSpan
	for _, entry := range entries {
		entryTraceID, _ := entry.Values["trace_id"].(string)
		if entryTraceID != traceID {
			continue
		}

		var span TraceSpan
		metaRaw, _ := entry.Values["metadata"].(string)
		if err := json.Unmarshal([]byte(metaRaw), &span.Metadata); err != nil {
			continue
		}

		span.TraceID = entryTraceID
		span.SpanName, _ = entry.Values["span_name"].(string)
		durationMs, _ := entry.Values["duration_ms"].(string)
		span.DurationMs, _ = strconv.Atoi(durationMs)
		span.TenantID, _ = entry.Values["tenant_id"].(string)
		timestamp, _ := entry.Values["timestamp"].(string)
		span.Timestamp, _ = time.Parse(time.RFC3339, timestamp)

		spans = append(spans, span)
	}

	return spans, nil
}
