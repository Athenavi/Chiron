/**
 * 后端稳定错误码 → 文案（en-US）。
 * 键与 internal/api/error_codes.go 的 Code* 常量一一对应，勿改键名。
 */
export default {
  // Authentication / authorization
  auth_required: 'Your session has expired. Please sign in again.',
  forbidden: 'You do not have permission to perform this action.',
  // Request
  invalid_request: 'The request was rejected. Please review and try again.',
  not_found: 'The requested resource does not exist or has been deleted.',
  // Rate limit & quota
  rate_limited: 'Too many requests. Please try again shortly.',
  quota_exceeded: 'Your quota has been reached. Please contact your administrator.',
  insufficient_credits: 'Free quota exhausted and balance is insufficient — please top up under Billing.',
  // Network & client-side (fallback when backend sends no code)
  timeout: 'Request timed out. Please try again.',
  network_error: 'Network connection failed. Please check your connection and try again.',
  payload_too_large: 'The payload is too large. Please trim it and try again.',
  http_status: 'Request failed (HTTP {status})',
  // Server
  service_unavailable: 'Service temporarily unavailable. Please try again later.',
  internal_error: 'Something went wrong on our side. Please try again later.',
  request_failed: 'Request failed. Please try again later.',
}
