package api

import (
	"encoding/json"
	"net/http"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/engine"
)

// QuickExecuteRequest represents a quick execute request.
type QuickExecuteRequest struct {
	UserInput string `json:"user_input"`
	TenantID  string `json:"tenant_id,omitempty"`
	SessionID string `json:"session_id,omitempty"`
	Mode      string `json:"mode"` // "auto" / "agent" / "workflow"
}

// QuickExecuteHandler proxies natural language requests to Python TaskRouter.
type QuickExecuteHandler struct {
	pythonClient *engine.PythonClient
}

// NewQuickExecuteHandler creates a new QuickExecuteHandler.
func NewQuickExecuteHandler(pythonClient *engine.PythonClient) *QuickExecuteHandler {
	return &QuickExecuteHandler{pythonClient: pythonClient}
}

// Handle handles the quick execute request.
// POST /v1/quick-execute
func (h *QuickExecuteHandler) Handle(w http.ResponseWriter, r *http.Request) {
	claims := auth.GetClaims(r.Context())
	if claims == nil {
		Unauthorized(w, "authentication required")
		return
	}

	var req QuickExecuteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		BadRequest(w, "invalid request body")
		return
	}

	// 构建 Python 请求
	pythonReq := map[string]any{
		"user_input": req.UserInput,
		"tenant_id":  claims.TenantID,
		"session_id": req.SessionID,
		"mode":       req.Mode,
	}

	// Proxy to Python unified_executor
	var resp map[string]any
	if h.pythonClient == nil {
		InternalError(w, "python engine not available")
		return
	}
	if err := h.pythonClient.PostJSON(r.Context(), "/v1/chat/submit", pythonReq, &resp); err != nil {
		InternalError(w, "python engine unavailable")
		return
	}

	OK(w, resp)
}

// RegisterQuickExecuteRoute registers the quick execute endpoint.
func RegisterQuickExecuteRoute(mux *http.ServeMux, authMW func(http.Handler) http.Handler, rlMW func(http.Handler) http.Handler, pythonClient *engine.PythonClient) {
	handler := NewQuickExecuteHandler(pythonClient)
	mux.Handle("POST /v1/quick-execute", authMW(rlMW(http.HandlerFunc(handler.Handle))))
}
