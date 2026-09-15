package api

import (
	"encoding/base64"
	"log/slog"
	"net/http"
	"strings"

	"github.com/athenavi/chiron/internal/db"
	"github.com/athenavi/chiron/internal/id"
)

// ─────────────────────────────────────────────────────────────
// 内部媒体端点（受 X-Internal-Token 保护，见 internalTokenMW）
//
// 用途：让 Python 引擎的 agent 工具（media_create / image_generate）把产物
// 直接写入 Go 侧媒体库（media_assets 表 + 配置的对象存储后端）。
//
// 背景：python-engine/app/tools/media.py 原先写的是引擎进程本地的 LocalStore
//（app/media/store.py），与「媒体库」页面读取的 media_assets 完全隔离，
// 因此 agent 生成的资产在媒体库里看不到。
// ─────────────────────────────────────────────────────────────

// internalMediaCreateRequest 是 agent 工具写入媒体资产的请求体。
// 归属信息（tenant_id/user_id）来自 Python 侧的工具执行上下文，由引擎携带。
type internalMediaCreateRequest struct {
	TenantID string   `json:"tenant_id"`
	UserID   string   `json:"user_id"`
	Name     string   `json:"name"`
	Type     string   `json:"type"`
	Category string   `json:"category"`
	MimeType string   `json:"mime_type"`
	Tags     []string `json:"tags"`
	// Content 为纯文本快捷字段；ContentBase64 用于二进制安全传输（图片/音频等）。
	Content       string `json:"content"`
	ContentBase64 string `json:"content_base64"`
}

// InternalCreateAsset POST /v1/internal/media/assets
func (h *MediaHandler) InternalCreateAsset(w http.ResponseWriter, r *http.Request) {
	var body internalMediaCreateRequest
	if err := DecodeJSON(w, r, &body); err != nil {
		BadRequest(w, ErrInvalidReq)
		return
	}
	body.Name = strings.TrimSpace(body.Name)
	if body.Name == "" {
		BadRequest(w, "name is required")
		return
	}
	if body.TenantID == "" || body.UserID == "" {
		BadRequest(w, "tenant_id and user_id are required")
		return
	}

	var data []byte
	switch {
	case body.ContentBase64 != "":
		decoded, err := base64.StdEncoding.DecodeString(body.ContentBase64)
		if err != nil {
			BadRequest(w, "content_base64 is not valid base64")
			return
		}
		data = decoded
	case body.Content != "":
		data = []byte(body.Content)
	default:
		BadRequest(w, "content or content_base64 is required")
		return
	}

	// 与直传路径同等的安全校验：拒绝可执行/脚本类内容落地
	declaredMIME := truncateMIME(body.MimeType)
	detectedMIME := truncateMIME(http.DetectContentType(data))
	mimeType := detectedMIME
	if declaredMIME != "" && declaredMIME == detectedMIME {
		mimeType = declaredMIME
	}
	if isExecutableMIME(mimeType, body.Name) {
		BadRequest(w, "file type not allowed: "+mimeType)
		return
	}

	assetType := body.Type
	if assetType == "" {
		assetType = detectType(mimeType)
	}

	assetID, err := id.UUID()
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "generate id failed")
		return
	}
	// 与用户直传共用同一键布局：media/<tenantID>/<assetID>/<name>
	objectKey := mediaObjectKey(body.TenantID, assetID, sanitizeUploadName(body.Name))

	if err := h.store.Write(r.Context(), objectKey, data); err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "save file failed")
		return
	}
	fileURL := h.objectURL(objectKey)

	if _, err := db.GlobalDBManager.Exec(r.Context(),
		`INSERT INTO media_assets (id, tenant_id, user_id, type, name, file_url, file_path, mime_type, category, tags, size, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), NOW())`,
		assetID, body.TenantID, body.UserID, assetType, body.Name, fileURL, objectKey,
		mimeType, nullableStr(body.Category), strings.Join(body.Tags, ","), len(data)); err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "create asset failed")
		return
	}

	slog.Info("internal media asset created", "asset_id", assetID, "tenant_id", body.TenantID, "type", assetType, "size", len(data))
	OK(w, map[string]interface{}{
		"id":       assetID,
		"name":     body.Name,
		"type":     assetType,
		"file_url": fileURL,
		"size":     len(data),
	})
}
