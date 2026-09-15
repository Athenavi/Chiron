package api

import (
	"context"
	"net/http"

	"github.com/athenavi/chiron/internal/auth"
)

type contextKey string

const (
	CtxKeyTenantID contextKey = "tenant_id"
	CtxKeyUserID   contextKey = "user_id"
)

func TenantMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		claims := auth.GetClaims(r.Context())
		if claims == nil {
			Unauthorized(w, ErrAuthRequired)
			return
		}
		if claims.TenantID == "" {
			Unauthorized(w, "missing tenant context")
			return
		}

		ctx := context.WithValue(r.Context(), CtxKeyTenantID, claims.TenantID)
		ctx = context.WithValue(ctx, CtxKeyUserID, claims.UserID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func RequireRole(roles ...string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			claims := auth.GetClaims(r.Context())
			if claims == nil {
				Unauthorized(w, ErrAuthRequired)
				return
			}

			hasRole := false
			for _, role := range roles {
				if claims.Role == role {
					hasRole = true
					break
				}
			}

			if !hasRole {
				Forbidden(w, "insufficient role")
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func GetUserID(r *http.Request) string {
	userID, _ := r.Context().Value(CtxKeyUserID).(string)
	return userID
}

func GetTenantID(r *http.Request) string {
	tenantID, _ := r.Context().Value(CtxKeyTenantID).(string)
	return tenantID
}

// ResolveTenantID 返回当前请求的租户 ID：claims 优先，回退默认租户。
// 用在不需要强制租户隔离的上下文（如市场门控），其中 GetTenantID 通过
// TenantMiddleware 注入，但某些路径未经过该中间件。
func ResolveTenantID(r *http.Request) string {
	claims := auth.GetClaims(r.Context())
	if claims != nil && claims.TenantID != "" {
		return claims.TenantID
	}
	return DefaultTenantID
}
