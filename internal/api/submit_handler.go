package api

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/billing"
	"github.com/athenavi/chiron/internal/broadcast"
	"github.com/athenavi/chiron/internal/engine"
	"github.com/athenavi/chiron/internal/session"
)

// SubmitHandler proxies /submit requests to the Python AI engine.
type SubmitHandler struct {
	python     *engine.PythonClient
	sessionMgr *session.Manager
	eventHub   *broadcast.Hub
	biller     engine.Biller
}

func NewSubmitHandler(python *engine.PythonClient, sessionMgr *session.Manager, eventHub *broadcast.Hub, biller engine.Biller) *SubmitHandler {
	return &SubmitHandler{
		python:     python,
		sessionMgr: sessionMgr,
		eventHub:   eventHub,
		biller:     biller,
	}
}

func (h *SubmitHandler) SubmitApproval(w http.ResponseWriter, r *http.Request) {
	var req struct {
		SessionID  string `json:"session_id"`
		ToolCallID string `json:"tool_call_id"`
		Approved   bool   `json:"approved"`
		Reason     string `json:"reason"`
		UserID     string `json:"user_id,omitempty"`
	}
	if err := DecodeJSON(w, r, &req); err != nil {
		BadRequest(w, "invalid request")
		return
	}
	if req.SessionID == "" || req.ToolCallID == "" {
		BadRequest(w, "session_id and tool_call_id are required")
		return
	}
	var out map[string]any
	if claims := auth.GetClaims(r.Context()); claims != nil {
		req.UserID = claims.UserID
	}
	if err := h.python.PostJSON(r.Context(), "/v1/agent/approval", req, &out); err != nil {
		slog.Error("approval: python proxy failed", "session", req.SessionID, "error", err)
		InternalError(w, "approval proxy failed")
		return
	}
	JSON(w, http.StatusOK, APIResponse{Success: true, Data: out})
}

// HandleSubmit proxies the submit request to Python engine and streams SSE events.
func (h *SubmitHandler) HandleSubmit(ctx context.Context, userID, sessionID, content string, llmConfig map[string]interface{}) {
	defer cancel()
	if sessionID != "" {
		sessionCancels.Store(sessionID, sessionCancel{userID: userID, cancel: cancel})
		defer sessionCancels.Delete(sessionID)
	}

	storeCtx, storeCancel := context.WithTimeout(context.WithoutCancel(ctx), 10*time.Second)
	defer storeCancel()

	h.sessionMgr.SaveUserMessage(storeCtx, sessionID, userID, content)

	histMsgs := make([]map[string]string, 0)
	if hist, err := h.sessionMgr.GetMessages(ctx, sessionID, 50); err == nil && len(hist) > 0 {
		const maxHistory = 8
		start := 0
		if len(hist) > maxHistory {
			start = len(hist) - maxHistory
		}
		for _, m := range hist[start:] {
			if (m.Role == "user" || m.Role == "assistant" || m.Role == "tool") && m.Content != "" {
				histMsgs = append(histMsgs, map[string]string{"role": m.Role, "content": m.Content})
			}
		}
	}

	defaultMaxTurns := 5
	if llmConfig != nil {
		if mt, ok := llmConfig["max_turns"].(float64); ok && mt > 0 {
			defaultMaxTurns = int(mt)
		}
	}
	pythonReq := map[string]interface{}{
		"session_id": sessionID,
		"user_id":    userID,
		"content":    content,
		"history":    histMsgs,
		"max_turns":  defaultMaxTurns,
	}
	if llmConfig != nil {
		pythonReq["llm_config"] = llmConfig
	}

	events, err := h.python.RunSSE(ctx, "/v1/agent/submit", pythonReq,
		map[string]string{"X-User-ID": userID})
	if err != nil {
		slog.Error("submit: python proxy failed", "error", err)
		h.eventHub.Publish(broadcast.Event{Type: "text", SessionID: sessionID, Data: map[string]string{"content": "Service temporarily unavailable. Please try again."}})
		h.eventHub.Publish(broadcast.Event{Type: "turn_done", SessionID: sessionID, Data: map[string]string{"session_id": sessionID}})
		return
	}

	var finalContent string
	var inputTokens, outputTokens int
	turnToolCallIDs := []string{}
	var textBuf strings.Builder
	lastTextFlush := time.Now()
	flushText := func() {
		if textBuf.Len() == 0 {
			return
		}
		payload := textBuf.String()
		textBuf.Reset()
		finalContent += payload
		h.eventHub.Publish(broadcast.Event{
			Type: "text", SessionID: sessionID,
			Data: engine.PythonEvent{Type: "text", Content: payload},
		})
		lastTextFlush = time.Now()
	}

	for evt := range events {
		if evt.Type == "text" && evt.Content != "" && !isThinking {
			textBuf.WriteString(evt.Content)
			if time.Since(lastTextFlush) >= textFrameInterval {
				flushText()
			}
		} else {
			flushText() // 闈?text 浜嬩欢鍏堝啿鍒风紦鍐诧紝淇濇寔椤哄簭
			h.eventHub.Publish(broadcast.Event{Type: evt.Type, SessionID: sessionID, Data: evt})
		}
		case "tool_call":
			h.sessionMgr.SaveToolCall(storeCtx, sessionID, evt.ID, evt.Name, evt.Arguments)
			if evt.ID != "" {
				turnToolCallIDs = append(turnToolCallIDs, evt.ID)
			}
		case "tool_result":
			h.sessionMgr.UpdateToolCall(storeCtx, evt.ID, evt.Content, strings.Contains(evt.Content, `"error"`))
		case "guardrail_blocked":
			    h.sessionMgr.SaveToolCall(storeCtx, sessionID,
				"guard_"+evt.ID, "guardrail",
				fmt.Sprintf(`{"reason":%q}`, evt.Content))
		}
		if evt.InputTokens > 0 {
			inputTokens += evt.InputTokens
		}
		if evt.OutputTokens > 0 {
			outputTokens += evt.OutputTokens
		}
	}
	flushText() // 娴佺粨鏉熷厹搴曞啿鍒?
	if finalContent != "" || len(turnToolCallIDs) > 0 {
		toolCallsJSON, _ := json.Marshal(turnToolCallIDs)
		h.sessionMgr.SaveAssistantMessage(storeCtx, sessionID, finalContent, string(toolCallsJSON))
	} else {
		SaveUserMessage}

	if inputTokens > 0 || outputTokens > 0 {
		if h.biller != nil {
			freeCount, fcErr := h.biller.DailyFreeCount(storeCtx, userID)
			if fcErr == nil && freeCount < billing.DailyFreeLimit {
					if markErr := h.biller.MarkFreeUsage(storeCtx, userID); markErr != nil {
					slog.Error("billing: MarkFreeUsage failed", "user", userID, "error", markErr)
				}
			} else {
				// 瓒呭嚭鍏嶈垂棰濆害鎴栨煡璇㈠け璐ワ細姝ｅ父鎵ｈ垂
				if _, err := h.biller.DeductTokens(userID, inputTokens, outputTokens); err != nil {
					slog.Error("billing: DeductTokens failed", "user", userID, "error", err)
				}
			}
		}
	}

	h.eventHub.Publish(broadcast.Event{Type: "turn_done", SessionID: sessionID, Data: map[string]string{"session_id": sessionID}})
}
