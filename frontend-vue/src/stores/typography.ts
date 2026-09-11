/**
 * 阅读排版偏好（正文字号 / 行距 / 行间距）。
 *
 * 为什么落到 <html> 的内联 CSS 变量而不是逐层透传 prop：这些值同时被消息正文、
 * 行间距以及后续的行式组件读取，逐个透传会让每个新组件都得记得接一遍；
 * 变量只写一次，且切换主题时不需要重新应用（主题改的是另一批变量）。
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'chiron:typography:v1'

export interface TypographyState {
  /** 正文字号（px） */
  textSize: number
  /** 正文行高倍数 */
  leading: number
  /** 消息行间距（px） */
  gap: number
}

/** 默认值与接入前的硬编码值一致：不设置时视觉零变化 */
export const TYPOGRAPHY_DEFAULTS: TypographyState = { textSize: 16, leading: 1.75, gap: 6 }

export const TEXT_SIZE_OPTIONS = [
  { label: '紧凑', value: 14 },
  { label: '标准', value: 16 },
  { label: '宽大', value: 18 },
]
export const LEADING_OPTIONS = [
  { label: '紧', value: 1.6 },
  { label: '标准', value: 1.75 },
  { label: '松', value: 2 },
]
export const GAP_OPTIONS = [
  { label: '紧凑', value: 2 },
  { label: '标准', value: 6 },
  { label: '宽松', value: 14 },
]

function clampNumber(value: unknown, min: number, max: number, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value)
    ? Math.min(max, Math.max(min, value))
    : fallback
}

function read(): TypographyState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...TYPOGRAPHY_DEFAULTS }
    const parsed = JSON.parse(raw) as Partial<TypographyState>
    return {
      textSize: clampNumber(parsed.textSize, 12, 22, TYPOGRAPHY_DEFAULTS.textSize),
      leading: clampNumber(parsed.leading, 1.2, 2.4, TYPOGRAPHY_DEFAULTS.leading),
      gap: clampNumber(parsed.gap, 0, 32, TYPOGRAPHY_DEFAULTS.gap),
    }
  } catch {
    return { ...TYPOGRAPHY_DEFAULTS }
  }
}

export const useTypographyStore = defineStore('typography', () => {
  const state = ref<TypographyState>(read())

  /** 写入 <html> 内联变量：组件样式只读变量，不感知 store */
  function apply() {
    const root = document.documentElement
    root.style.setProperty('--chat-text-size', `${state.value.textSize}px`)
    root.style.setProperty('--chat-text-leading', String(state.value.leading))
    root.style.setProperty('--chat-msg-gap', `${state.value.gap}px`)
  }

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.value))
    } catch { /* 隐私模式 / 配额满：偏好本次会话内生效即可 */ }
  }

  function setTextSize(value: number) { state.value = { ...state.value, textSize: value } }
  function setLeading(value: number) { state.value = { ...state.value, leading: value } }
  function setGap(value: number) { state.value = { ...state.value, gap: value } }
  function reset() { state.value = { ...TYPOGRAPHY_DEFAULTS } }

  // flush: 'sync' —— 变量要立刻落到 <html>，否则读者会先看到旧字号再跳变
  watch(state, () => { apply(); persist() }, { immediate: true, deep: true, flush: 'sync' })

  return { state, apply, setTextSize, setLeading, setGap, reset }
})
