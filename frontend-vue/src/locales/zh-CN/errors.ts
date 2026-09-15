/**
 * 后端稳定错误码 → 文案（zh-CN，源语言）。
 *
 * 键必须与 internal/api/error_codes.go 的 Code* 常量一一对应：
 * 后端在响应里带 `code`，前端按当前语言查本表渲染；查不到则回退响应里的 `error` 原文
 * （见 src/utils/apiError.ts 的优先级）。
 *
 * 改文案只改这里；不要改键名 —— 键是与后端约定的契约。
 */
export default {
  // 认证 / 授权
  auth_required: '登录状态已失效，请重新登录',
  forbidden: '没有权限执行该操作',
  // 请求
  invalid_request: '请求内容不被接受，请检查后重试',
  not_found: '请求的资源不存在，可能已被删除',
  // 限流与配额
  rate_limited: '请求过于频繁，请稍后再试',
  quota_exceeded: '已达配额上限，请联系管理员',
  insufficient_credits: '今日免费额度已用尽且余额不足，请到「计费」页充值',
  // 网络与客户端（后端未给 code 时的兜底）
  timeout: '请求超时，请重试',
  network_error: '网络连接失败，请检查网络后重试',
  payload_too_large: '内容过大，请精简后重试',
  http_status: '请求失败（HTTP {status}）',
  // 服务端
  service_unavailable: '服务暂时不可用，请稍后重试',
  internal_error: '服务异常，请稍后重试',
  request_failed: '请求失败，请稍后重试',
}
