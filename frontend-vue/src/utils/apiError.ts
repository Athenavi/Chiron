/**
 * 把 HTTP/网络错误翻译成用户能看懂的话。
 *
 * 为什么需要它：axios 的 `error.message` 是 "Request failed with status code 402"
 * 这类给开发者看的字符串 —— 摆给用户等于让他去猜发生了什么。而后端返回的
 * `error` 字段是 API 语义（`insufficient credits — please recharge in Billing`），
 * 英文且面向集成方；本地化留给前端。
 *
 * 优先级：已知状态码的中文说明 → 后端文案 → 兜底文案。
 */

interface ApiErrorLike {
  response?: {
    status?: number
    data?: { error?: string; message?: string }
  }
  code?: string
  message?: string
}

/** 已知状态码的中文说明；未知返回 null（交给后端文案或兜底） */
export function statusMessage(status?: number): string | null {
  switch (status) {
    case 400: return '请求内容不被接受，请检查后重试'
    case 401: return '登录状态已失效，请重新登录'
    case 402: return '今日免费额度已用尽且余额不足，请到「计费」页充值'
    case 403: return '没有权限执行该操作'
    case 404: return '请求的资源不存在，可能已被删除'
    case 408: return '请求超时，请重试'
    case 413: return '内容过大，请精简后重试'
    case 429: return '请求过于频繁，请稍后再试'
    case 500:
    case 502:
    case 503:
    case 504: return '服务暂时不可用，请稍后重试'
    default: return null
  }
}

export function describeApiError(error: unknown, fallback = '请求失败，请稍后重试'): string {
  const err = (error ?? {}) as ApiErrorLike
  const status = err.response?.status
  const serverMessage = err.response?.data?.error || err.response?.data?.message

  const known = statusMessage(status)
  if (known) return known
  if (serverMessage) return serverMessage
  if (status) return `请求失败（HTTP ${status}）`

  const message = err.message || ''
  if (err.code === 'ECONNABORTED' || /timeout/i.test(message)) return '请求超时，请重试'
  if (/network\s*error/i.test(message)) return '网络连接失败，请检查网络后重试'
  return fallback
}
