package api

import (
	"encoding/json"
	"log/slog"
	"net/http"
)

// Unified error message constants — single source of truth for all handlers.
const (
	ErrAuthRequired  = "authentication required"
	ErrDBUnavailable = "service temporarily unavailable"
	ErrInvalidReq    = "invalid request body"
	ErrNotFound      = "resource not found"
)

type APIResponse struct {
	Success bool        `json:"success"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
	// Code 稳定错误码（i18n）：客户端据此渲染本地化文案；Error 保留为兼容兜底。
	// 见 error_codes.go 的常量表与前端 src/utils/apiError.ts。
	Code string `json:"code,omitempty"`
	// Params 错误码的结构化参数（如 {"limit": 20}），供客户端插值。
	Params map[string]interface{} `json:"params,omitempty"`
	Meta   *Meta                  `json:"meta,omitempty"`
}

type Meta struct {
	Total   int `json:"total,omitempty"`
	Page    int `json:"page,omitempty"`
	PerPage int `json:"per_page,omitempty"`
}

func JSON(w http.ResponseWriter, status int, resp APIResponse) {
	// i18n：失败响应未显式指定 code 时按文案自动补码（既有调用点零改动）。
	if !resp.Success && resp.Code == "" {
		resp.Code = codeForMessage(resp.Error)
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(resp); err != nil {
		slog.Error("json encode response failed", "error", err, "status", status)
	}
}

func OK(w http.ResponseWriter, data interface{}) {
	JSON(w, http.StatusOK, APIResponse{Success: true, Data: data})
}

func Created(w http.ResponseWriter, data interface{}) {
	JSON(w, http.StatusCreated, APIResponse{Success: true, Data: data})
}

func Accepted(w http.ResponseWriter, data interface{}) {
	JSON(w, http.StatusAccepted, APIResponse{Success: true, Data: data})
}

func NoContent(w http.ResponseWriter) {
	w.WriteHeader(http.StatusNoContent)
}

func BadRequest(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusBadRequest, APIResponse{Success: false, Error: msg})
}

func NotFound(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusNotFound, APIResponse{Success: false, Error: msg})
}

func InternalError(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusInternalServerError, APIResponse{Success: false, Error: msg})
}

// logAndRespond logs the internal error details and returns a generic message to the client.
func logAndRespond(w http.ResponseWriter, err error, statusCode int, userMsg string) {
	slog.Error(userMsg, "error", err)
	JSON(w, statusCode, APIResponse{Success: false, Error: userMsg})
}

func Unauthorized(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusUnauthorized, APIResponse{Success: false, Error: msg})
}

func Forbidden(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusForbidden, APIResponse{Success: false, Error: msg})
}

func ServiceUnavailable(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusServiceUnavailable, APIResponse{Success: false, Error: msg})
}

// NotImplemented 返回 501：端点已暴露但功能尚未实现。
// 用于避免调用方把"未实现"当作成功（如 chaos 故障注入此前会返回 created）。
func NotImplemented(w http.ResponseWriter, msg string) {
	JSON(w, http.StatusNotImplemented, APIResponse{Success: false, Error: msg})
}

func TooManyRequests(w http.ResponseWriter) {
	JSON(w, http.StatusTooManyRequests, APIResponse{Success: false, Error: "rate limit exceeded"})
}

func DecodeJSON(w http.ResponseWriter, r *http.Request, v interface{}) error {
	// Enforce 1MB limit at the read level (not just Content-Length header)
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	return json.NewDecoder(r.Body).Decode(v)
}
