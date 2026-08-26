package api

import (
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/athenavi/chiron/internal/auth"
	"github.com/athenavi/chiron/internal/db"
	"github.com/athenavi/chiron/internal/id"
)

type UploadHandler struct {
	authenticator *auth.Authenticator
	storageRoot   string
}

func NewUploadHandler(a *auth.Authenticator, storageRoot string) *UploadHandler {
	return &UploadHandler{authenticator: a, storageRoot: storageRoot}
}

const defaultChunkSize = 2 << 20 // 2MB

func sanitizeUploadName(name string) string {
	name = strings.TrimSpace(name)
	if name == "" || len(name) > 255 {
		return ""
	}
	if !validUploadNameRe.MatchString(name) {
		return ""
	}
	if name == "." || name == ".." {
		return ""
	}
	// 闃插尽锛氫粎淇濈暀鏂囦欢鍚嶉儴鍒嗭紙鏉滅粷浠讳綍娈嬩綑鍒嗛殧绗﹀満鏅級
	name = filepath.Base(filepath.Clean(name))
	if name == "." || name == ".." {
		return ""
	}
	return name
}

func (h *UploadHandler) chunkDir(uploadID string) (string, error) {
	dir := filepath.Join(h.storageRoot, "uploads", uploadID)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	return dir, nil
}

func (h *UploadHandler) userID(r *http.Request) (string, bool) {
	claims := auth.GetClaims(r.Context())
	if claims == nil {
		return "", false
	}
	return claims.UserID, true
}

func (h *UploadHandler) claimsOf(r *http.Request) (*auth.Claims, bool) {
	c := auth.GetClaims(r.Context())
	if c == nil || c.TenantID == "" {
		return nil, false
	}
	return c, true
}

func (h *UploadHandler) Init(w http.ResponseWriter, r *http.Request) {
	claims, ok := h.claimsOf(r)
	if !ok {
		Unauthorized(w, ErrAuthRequired)
		return
	}
	var body struct {
		Name      string `json:"name"`
		Size      int64  `json:"size"`
		MimeType  string `json:"mime_type"`
		Purpose   string `json:"purpose"`
		ParentID  string `json:"parent_id"`
		Category  string `json:"category"`
		ChunkSize int    `json:"chunk_size"`
	}
	if err := DecodeJSON(w, r, &body); err != nil {
		BadRequest(w, "invalid request")
		return
	}
	body.Name = strings.TrimSpace(body.Name)
	if body.Name == "" || body.Size <= 0 {
		BadRequest(w, "name and size are required")
		return
	}
	if body.Name == "" {
		BadRequest(w, "invalid file name")
		return
	}

	if isExecutableMIME(body.MimeType, body.Name) {
		BadRequest(w, "file type not allowed")
		return
	}
	if ext := strings.ToLower(filepath.Ext(body.Name)); ext == ".html" || ext == ".htm" ||
		ext == ".xml" || ext == ".xhtml" || ext == ".swf" {
		BadRequest(w, "file type not allowed: " + ext)
		return
	}
	if body.Purpose == "" {
		body.Purpose = "generic"
	}
	if body.Purpose != "media" && body.Purpose != "kb_doc" && body.Purpose != "generic" {
		BadRequest(w, "purpose must be media / kb_doc / generic")
		return
	}

	if body.Purpose == "kb_doc" && body.Size > maxKBDocSize {
		BadRequest(w, "kb_doc upload too large (max 64MB)")
		return
	}
	chunkSize := body.ChunkSize
	if chunkSize <= 0 {
		chunkSize = defaultChunkSize
	}
	if chunkSize > 64<<20 {
		chunkSize = 64 << 20
	}
	chunkCount := int((body.Size + int64(chunkSize) - 1) / int64(chunkSize))
	if chunkCount <= 0 {
		chunkCount = 1
	}

	uploadID, err := id.UUID()
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "generate id failed")
		return
	}
	now := time.Now()
	if _, err := db.Pool.Exec(r.Context(),
		`INSERT INTO uploads (id, tenant_id, user_id, name, size, mime_type, purpose, parent_id, category, chunk_size, chunk_count, status, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'uploading', $12, $12)`,
		uploadID, claims.TenantID, claims.UserID, body.Name, body.Size, truncateMIME(body.MimeType), body.Purpose,
		body.ParentID, body.Category, chunkSize, chunkCount, now); err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "init upload failed")
		return
	}

	OK(w, map[string]interface{}{
		"upload_id":   uploadID,
		"chunk_size":  chunkSize,
		"chunk_count": chunkCount,
	})
}

func (h *UploadHandler) PutChunk(w http.ResponseWriter, r *http.Request) {
	claims, ok := h.claimsOf(r)
	if !ok {
		Unauthorized(w, ErrAuthRequired)
		return
	}
	uploadID := r.PathValue("id")
	idxStr := r.PathValue("index")
	idx, err := strconv.Atoi(idxStr)
	if err != nil || idx < 0 {
		BadRequest(w, "invalid chunk index")
		return
	}

	// 褰掑睘鏍￠獙锛堝惈 tenant_id锛岄槻璺ㄧ鎴疯鍐欏垎鐗囷級
	var owner string
	if err := db.Pool.QueryRow(r.Context(),
		`SELECT user_id FROM uploads WHERE id = $1 AND tenant_id = $2`, uploadID, claims.TenantID).Scan(&owner); err != nil || owner != claims.UserID {
		NotFound(w, "upload not found")
		return
	}

	dir, err := h.chunkDir(uploadID)
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "create chunk dir failed")
		return
	}
	dst := filepath.Join(dir, fmt.Sprintf("chunk_%d", idx))
	out, err := os.Create(dst)
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "create chunk failed")
		return
	}
	defer out.Close()
	if _, err := io.Copy(out, r.Body); err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "write chunk failed")
		return
	}

	if _, err := db.Pool.Exec(r.Context(),
		`UPDATE uploads SET chunks_received = array_append(chunks_received, $1), updated_at = NOW()
		 WHERE id = $2 AND tenant_id = $3 AND NOT ($1 = ANY(chunks_received))`, idxStr, uploadID, claims.TenantID); err != nil {
		slog.Warn("failed to record upload", "error", err)
	}
	OK(w, map[string]interface{}{"upload_id": uploadID, "index": idx, "received": true})
}

func (h *UploadHandler) GetProgress(w http.ResponseWriter, r *http.Request) {
	claims, ok := h.claimsOf(r)
	if !ok {
		Unauthorized(w, ErrAuthRequired)
		return
	}
	uploadID := r.PathValue("id")
	var received []string
	var status string
	err := db.Pool.QueryRow(r.Context(),
		`SELECT chunks_received, status FROM uploads WHERE id = $1 AND tenant_id = $2 AND user_id = $3`, uploadID, claims.TenantID, claims.UserID).
		Scan(&received, &status)
	if err != nil {
		NotFound(w, "upload not found")
		return
	}
	chunks := make([]int, 0, len(received))
	for _, s := range received {
		if n, err := strconv.Atoi(s); err == nil {
			chunks = append(chunks, n)
		}
	}
	sort.Ints(chunks)
	OK(w, map[string]interface{}{
		"upload_id":       uploadID,
		"received_chunks": chunks,
		"status":          status,
	})
}

func (h *UploadHandler) Complete(w http.ResponseWriter, r *http.Request) {
	claims, ok := h.claimsOf(r)
	if !ok {
		Unauthorized(w, ErrAuthRequired)
		return
	}
	uploadID := r.PathValue("id")

	var up struct {
		ID        string
		UserID    string
		Name      string
		Size      int64
		MimeType  string
		Purpose   string
		ParentID  string
		Category  string
		ChunkSize int
		ChunkCnt  int
		Received  []string
	}
	err := db.Pool.QueryRow(r.Context(),
		`SELECT id, user_id, name, size, mime_type, purpose, parent_id, category, chunk_size, chunk_count, chunks_received
		 FROM uploads WHERE id = $1 AND tenant_id = $2 AND user_id = $3`, uploadID, claims.TenantID, claims.UserID).
		Scan(&up.ID, &up.UserID, &up.Name, &up.Size, &up.MimeType, &up.Purpose,
			&up.ParentID, &up.Category, &up.ChunkSize, &up.ChunkCnt, &up.Received)
	if err != nil {
		NotFound(w, "upload not found")
		return
	}
	if len(up.Received) != up.ChunkCnt {
		BadRequest(w, fmt.Sprintf("incomplete upload: %d/%d chunks received", len(up.Received), up.ChunkCnt))
		return
	}

	// 鎸夊簭鍚堝苟鍒嗙墖
	dir, err := h.chunkDir(uploadID)
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "read chunk dir failed")
		return
	}
	merged, err := h.mergeChunks(dir, up.ChunkCnt)
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "merge chunks failed")
		return
	}
	defer merged.Close()

	// 鏍￠獙鎬诲ぇ灏?	fi, err := merged.Stat()
	if err == nil && fi.Size() != up.Size {
		BadRequest(w, fmt.Sprintf("size mismatch: got %d want %d", fi.Size(), up.Size))
		return
	}

	var fileURL string
	switch up.Purpose {
	case "media":
		fileURL, err = h.finalizeMedia(r, claims.TenantID, up, merged)
	case "kb_doc":
		fileURL, err = h.finalizeKBDoc(r, claims.TenantID, up, merged)
	default:
		fileURL, err = h.finalizeGeneric(up, merged)
	}
	if err != nil {
		logAndRespond(w, err, http.StatusInternalServerError, "finalize upload failed")
		return
	}

	if _, err := db.Pool.Exec(r.Context(),
		`UPDATE uploads SET status = 'completed', updated_at = NOW() WHERE id = $1 AND tenant_id = $2`, uploadID, claims.TenantID); err != nil {
		slog.Warn("failed to record upload", "error", err)
	}
	_ = os.RemoveAll(dir)

	OK(w, map[string]interface{}{
		"upload_id": uploadID, "file_url": fileURL,
		"purpose": up.Purpose, "name": up.Name, "size": up.Size,
	})
}

func (h *UploadHandler) mergeChunks(dir string, count int) (*os.File, error) {
	merged, err := os.CreateTemp(h.storageRoot, "merged_*.tmp")
	if err != nil {
		return nil, err
	}
	for i := 0; i < count; i++ {
		part, err := os.Open(filepath.Join(dir, fmt.Sprintf("chunk_%d", i)))
		if err != nil {
			merged.Close()
			os.Remove(merged.Name())
			return nil, fmt.Errorf("open chunk %d: %w", i, err)
		}
		_, err = io.Copy(merged, part)
		part.Close()
		if err != nil {
			merged.Close()
			os.Remove(merged.Name())
			return nil, err
		}
	}
	if _, err := merged.Seek(0, io.SeekStart); err != nil {
		merged.Close()
		os.Remove(merged.Name())
		return nil, err
	}
	return merged, nil
}

func (h *UploadHandler) finalizeMedia(r *http.Request, tenantID string, up struct {
	ID        string
	UserID    string
	Name      string
	Size      int64
	MimeType  string
	Purpose   string
	ParentID  string
	Category  string
	ChunkSize int
	ChunkCnt  int
	Received  []string
}, merged *os.File) (string, error) {
	dir := "u_" + up.UserID
	name := sanitizeUploadName(up.Name)
	if name == "" {
		return "", fmt.Errorf("invalid upload name")
	}
	objectKey := fmt.Sprintf("media/%s/%s_%s", dir, shortAssetID(up.ID), name)
	dest := filepath.Join(h.storageRoot, objectKey)
	if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
		return "", err
	}
	out, err := os.Create(dest)
	if err != nil {
		return "", err
	}
	defer out.Close()
	if _, err := io.Copy(out, merged); err != nil {
		return "", err
	}

	assetID, err := id.UUID()
	if err != nil {
		return "", err
	}
	assetType := detectType(up.MimeType)
	if _, err := db.Pool.Exec(r.Context(),
		`INSERT INTO media_assets (id, tenant_id, user_id, type, name, file_url, mime_type, category, size, parent_id, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())`,
		assetID, tenantID, up.UserID, assetType, up.Name, "/"+objectKey,
		truncateMIME(up.MimeType), nullableStr(up.Category), up.Size, up.ParentID); err != nil {
		return "", err
	}
	return "/" + objectKey, nil
}

// finalizeKBDoc 鍚堝苟鏂囦欢鍐呭钀?knowledge_documents锛坈ontent bytea 渚?RAG 鏋勫缓锛屾寜褰撳墠绉熸埛锛夈€
func (h *UploadHandler) finalizeKBDoc(r *http.Request, tenantID string, up struct {
	ID        string
	UserID    string
	Name      string
	Size      int64
	MimeType  string
	Purpose   string
	ParentID  string
	Category  string
	ChunkSize int
	ChunkCnt  int
	Received  []string
}, merged *os.File) (string, error) {
	if up.ParentID == "" {
		return "", fmt.Errorf("kb_doc upload requires parent_id (kb_id)")
	}
    var owner string
	if err := db.Pool.QueryRow(r.Context(),
		`SELECT user_id FROM knowledge_bases WHERE id = $1 AND tenant_id = $2`, up.ParentID, tenantID).Scan(&owner); err != nil || owner != up.UserID {
		return "", fmt.Errorf("knowledge base not found or not owned")
	}
	content, err := io.ReadAll(io.LimitReader(merged, maxKBDocSize+1))
	if err != nil {
		return "", err
	}
	if int64(len(content)) > maxKBDocSize {
		return "", fmt.Errorf("kb_doc content exceeds 64MB limit")
	}
	ext := strings.TrimPrefix(filepath.Ext(up.Name), ".")
	if ext == "" {
		ext = "txt"
	}
	docID, err := id.UUID()
	if err != nil {
		return "", err
	}
	_, err = db.Pool.Exec(r.Context(),
		`INSERT INTO knowledge_documents (id, tenant_id, knowledge_base_id, user_id, name, file_type, file_size_bytes, status, content, created_at, updated_at)
		 VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8, NOW(), NOW())`,
		docID, tenantID, up.ParentID, up.UserID, up.Name, ext, up.Size, content)
	if err != nil {
		return "", err
	}
	_, _ = db.Pool.Exec(r.Context(),
		`UPDATE knowledge_bases
		 SET document_count = (SELECT COUNT(*) FROM knowledge_documents WHERE knowledge_base_id = $1 AND tenant_id = $2),
		     total_size_bytes = COALESCE((SELECT SUM(file_size_bytes) FROM knowledge_documents WHERE knowledge_base_id = $1 AND tenant_id = $2), 0),
		     updated_at = NOW() WHERE id = $1 AND tenant_id = $2`, up.ParentID, tenantID)
	return fmt.Sprintf("/kb/%s/documents/%s", up.ParentID, docID), nil
}

// finalizeGeneric 鍚堝苟鏂囦欢鍐欏叆閫氱敤鐩綍骞惰繑鍥炲彲璁块棶 URL銆
func (h *UploadHandler) finalizeGeneric(up struct {
	ID        string
	UserID    string
	Name      string
	Size      int64
	MimeType  string
	Purpose   string
	ParentID  string
	Category  string
	ChunkSize int
	ChunkCnt  int
	Received  []string
}, merged *os.File) (string, error) {
	name := sanitizeUploadName(up.Name)
	if name == "" {
		return "", fmt.Errorf("invalid upload name")
	}
	objectKey := fmt.Sprintf("uploads/final/%s_%s", shortAssetID(up.ID), name)
	dest := filepath.Join(h.storageRoot, objectKey)
	if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
		return "", err
	}
	out, err := os.Create(dest)
	if err != nil {
		return "", err
	}
	defer out.Close()
	if _, err := io.Copy(out, merged); err != nil {
		return "", err
	}
	return "/" + objectKey, nil
}

func (h *UploadHandler) RegisterRoutes(mux *http.ServeMux, authMW func(http.Handler) http.Handler, rlMW func(http.Handler) http.Handler) {
	mux.Handle("POST /v1/uploads", authMW(rlMW(http.HandlerFunc(h.Init))))
	mux.Handle("PUT /v1/uploads/{id}/chunks/{index}", authMW(rlMW(http.HandlerFunc(h.PutChunk))))
	mux.Handle("GET /v1/uploads/{id}", authMW(rlMW(http.HandlerFunc(h.GetProgress))))
	mux.Handle("POST /v1/uploads/{id}/complete", authMW(rlMW(http.HandlerFunc(h.Complete))))
}
