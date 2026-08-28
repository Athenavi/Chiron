package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"strconv"
	"strings"
)

// SensitiveFields 需要脱敏的字段名列表
var SensitiveFields = []string{
	"password", "secret", "token", "key", "dsn", "credential",
	"access_key", "secret_key", "private_key", "api_key",
}

// SanitizeResponseMiddleware 脱敏响应中间件
func SanitizeResponseMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// P0-性能：流式响应（SSE/text/event-stream）跳过缓冲，直接透传
		if strings.Contains(r.Header.Get("Accept"), "text/event-stream") {
			next.ServeHTTP(w, r)
			return
		}
		// 只对JSON响应进行脱敏
		if !strings.Contains(r.Header.Get("Accept"), "application/json") &&
			!strings.Contains(r.Header.Get("Content-Type"), "application/json") {
			next.ServeHTTP(w, r)
			return
		}

		// 包装ResponseWriter以捕获响应体
		buf := &bytes.Buffer{}
		rw := &responseBufferWriter{
			ResponseWriter: w,
			buffer:         buf,
		}

		next.ServeHTTP(rw, r)

		// 如果响应是JSON，进行脱敏处理
		if rw.status < 300 && buf.Len() > 0 {
			var data interface{}
			if err := json.Unmarshal(buf.Bytes(), &data); err == nil {
				sanitizeMap(data)
				sanitized, _ := json.Marshal(data)
				w.Header().Set("Content-Length", strconv.Itoa(len(sanitized)))
				w.Write(sanitized)
				return
			}
		}

		// 如果不是JSON或解析失败，直接返回原始响应
		w.Write(buf.Bytes())
	})
}

type responseBufferWriter struct {
	http.ResponseWriter
	buffer *bytes.Buffer
	status int
}

func (rw *responseBufferWriter) WriteHeader(status int) {
	rw.status = status
	rw.ResponseWriter.WriteHeader(status)
}

func (rw *responseBufferWriter) Write(b []byte) (int, error) {
	return rw.buffer.Write(b)
}

// sanitizeMap 递归脱敏map中的数据
func sanitizeMap(data interface{}) {
	switch v := data.(type) {
	case map[string]interface{}:
		for key, val := range v {
			if isSensitiveField(key) {
				if str, ok := val.(string); ok && str != "" {
					v[key] = "********"
				}
			} else {
				sanitizeMap(val)
			}
		}
	case []interface{}:
		for _, item := range v {
			sanitizeMap(item)
		}
	}
}

// isSensitiveField 判断字段名是否敏感
func isSensitiveField(fieldName string) bool {
	lower := strings.ToLower(fieldName)
	for _, sensitive := range SensitiveFields {
		if strings.Contains(lower, sensitive) {
			return true
		}
	}
	return false
}
