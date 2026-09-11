<script setup lang="ts">
import { ref, watch, nextTick, computed, onErrorCaptured, onMounted, onUpdated } from 'vue'
import { ArrowDownOutlined } from '@ant-design/icons-vue'
import MessageItem from './MessageItem.vue'
import type { ChatItem } from './chat-types'
import { createTranscriptViewport } from './transcriptViewport'
import { captureAnchor, resolveRestoreOffset, type RowRect } from './transcriptAnchor'
import { createLedger } from './transcriptMeasurementLedger'
import {
  applyMeasurements,
  buildGeometry,
  computeWindowRange,
  coversViewport,
  toSegments,
  type WindowRange,
} from './transcriptWindow'

const props = defineProps<{
  items: ChatItem[]
  loading: boolean
  focusIndex?: number | null   // 跳转目标（用户消息索引）
  focusToken?: number          // 递增触发跳转
  hasMore?: boolean            // P 性能：是否还有更早的消息
  loadingEarlier?: boolean     // P 性能：正在加载更早消息
  /** P2-E: 首次加载会话历史时的骨架屏 */
  initialLoading?: boolean
  /** 行尺寸测量（默认 offsetHeight）。注入点让窗口化逻辑可在无布局环境下被测试。 */
  measureRow?: (el: HTMLElement) => number
  /** 视口高度（默认 el.clientHeight）。同样为可测性保留注入点。 */
  viewportHeight?: number
  /** 常驻尾部行数：活跃轮 + 最近若干轮，不参与卸载。 */
  residentTailRows?: number
  /** 行数超过该值才启用窗口化（小会话直接全量渲染，无风险）。 */
  windowingMinRows?: number
}>()

const emit = defineEmits<{
  (e: 'load-earlier'): void
  /** P1-1 用户消息编辑后重发 */
  (e: 'retry-from', itemId: string, text: string): void
  /** P1-1 助手消息重新生成 */
  (e: 'regenerate', itemId: string): void
  /** P2-F 停止后继续生成 */
  (e: 'continue', itemId: string): void
  /** P1-3 失败消息重试 */
  (e: 'retry-failed', itemId: string): void
}>()

const scrollRef = ref<HTMLDivElement | null>(null)
const stickToBottom = ref(true)
const highlightIndex = ref<number | null>(null)
const showBackToBottom = ref(false)
const unseenCount = ref(0)
/** fail-closed 降级开关：置位后停止一切窗口化与滚动编排，只做全量静态渲染。 */
const safeMode = ref(false)

const SCROLL_THRESHOLD = 120
const TOP_LOAD_THRESHOLD = 60
const DEFAULT_OVERSCAN_PX = 800
const DEFAULT_RESIDENT_TAIL_ROWS = 40
const DEFAULT_WINDOWING_MIN_ROWS = 150
/** 连续覆盖失败达到该次数即永久降级为全量渲染。 */
const COVER_FAILURE_LIMIT = 2

/**
 * 滚动单写者：本组件不再直接写 scrollTop，一律经 vp 提交意图，
 * 使"程序跟随"与"用户滚动"可归因（writer provenance），
 * 用户在阅读时自动跟随让位而不是把视口拽回底部。
 */
const vp = createTranscriptViewport({ leaseMs: 1200, bottomThreshold: SCROLL_THRESHOLD })

// ── 窗口化状态 ───────────────────────────────────────────────
const ledger = createLedger()
const measuredSizes = ref<ReadonlyMap<string, number>>(new Map())
const windowRange = ref<WindowRange>({ start: 0, end: 0, tailStart: 0, tailEnd: 0 })
/** 首次渲染先全量，挂载后测量再切窗口：避免首屏用未经测量的几何画出空白。 */
const fullRender = ref(true)
let coverFailures = 0

/** 用户输入早于 scroll 事件到达：提前取得租约，避免流式增长抢走阅读位置。 */
function onUserInput() {
  vp.noteUserInput()
}

/**
 * 子组件渲染异常时降级（fail-closed）：本会话不再做窗口化与滚动编排，
 * 只保留全量静态渲染 —— 避免"渲染失败 + 窗口/编排写入"叠加成空白视口。
 */
onErrorCaptured((err) => {
  if (!safeMode.value) {
    safeMode.value = true
    console.error('[MessageList] 渲染异常，降级为全量静态渲染', err)
  }
  return false   // 已处理，不再向上冒泡导致整页白屏
})

function isUserAnchor(item: ChatItem | undefined): boolean {
  return !!item && item.kind === 'text' && item.role === 'user'
}

/**
 * 稳定唯一渲染 key = 回合身份 + kind + id。
 * 同一条 assistant 消息会拆成多个 item（reasoning / text / tool_call / tool_result），
 * 它们的 id 可能来自同一个消息 id，故加 kind 前缀避免 key 冲突导致节点错位复用。
 * 最外层用回合身份（turnId）而不是下标：历史补丁、分页插入都不会让身份跨回合漂移，
 * 这也是滚动锚点（data-item-key）必须保持稳定的原因。无 turnId（实时流/旧数据）记 '-'。
 */
function itemKey(item: ChatItem, index: number): string {
  const scope = item.turnId ? `t:${item.turnId}` : 't:-'
  const body = item.id ? `${item.kind}:${item.id}` : `${item.kind}:idx${index}`
  return `${scope}:${body}`
}

// ── 窗口计算 ─────────────────────────────────────────────────
const measure = (el: HTMLElement): number =>
  props.measureRow ? props.measureRow(el) : el.offsetHeight

const viewportHeightOf = (el: HTMLElement): number =>
  props.viewportHeight ?? el.clientHeight

const rowSpecs = computed(() => props.items.map((it, i) => ({ key: itemKey(it, i), kind: it.kind })))
const geometry = computed(() => buildGeometry(applyMeasurements(rowSpecs.value, measuredSizes.value)))

/** 小会话与降级态一律全量渲染。 */
const windowingEnabled = computed(() =>
  !safeMode.value &&
  props.items.length > (props.windowingMinRows ?? DEFAULT_WINDOWING_MIN_ROWS))

/** 当前渲染的连续段落；全量渲染时是一段覆盖整表。 */
const renderSegments = computed(() =>
  fullRender.value
    ? [{ start: 0, end: props.items.length }]
    : toSegments(windowRange.value))

/**
 * 渲染节点序列：行 + 段间占位。
 * 占位让未挂载部分仍占用真实高度，滚动条才不会跳；全量渲染时不含任何占位。
 */
const renderNodes = computed(() => {
  const geo = geometry.value
  const full = fullRender.value
  const nodes: Array<
    { kind: 'spacer'; height: number; key: string } |
    { kind: 'row'; item: ChatItem; index: number; key: string }
  > = []
  let cursor = 0
  renderSegments.value.forEach((seg, si) => {
    const gap = (geo.offsets[seg.start] ?? 0) - cursor
    if (!full && gap > 0) nodes.push({ kind: 'spacer', height: gap, key: `gap:${si}` })
    for (let i = seg.start; i < seg.end; i++) {
      const item = props.items[i]
      if (!item) continue
      nodes.push({ kind: 'row', item, index: i, key: itemKey(item, i) })
    }
    cursor = geo.offsets[seg.end] ?? cursor
  })
  const tailGap = full ? 0 : Math.max(0, geo.total - cursor)
  if (tailGap > 0) nodes.push({ kind: 'spacer', height: tailGap, key: 'gap:tail' })
  return nodes
})

/**
 * 提交窗口区间。全量渲染（`fullRender`）只关心 [start, end)：此时尾部区间无意义，
 * 显式置 0 而不是让调用方补字段，避免"缺字段"的字面量绕过类型检查。
 */
function setRange(next: WindowRange | { start: number; end: number }) {
  const cur = windowRange.value
  if (cur.start === next.start && cur.end === next.end) return   // 避免无变化赋值触发重渲染循环
  const tailStart = 'tailStart' in next ? next.tailStart : 0
  const tailEnd = 'tailEnd' in next ? next.tailEnd : 0
  windowRange.value = { start: next.start, end: next.end, tailStart, tailEnd }
}

/**
 * 重算窗口。覆盖判定不通过时**退回全量渲染**（绝不提交未覆盖的窗口），
 * 连续失败达到阈值则永久降级 —— 宁可慢，也不留空白。
 */
function recomputeWindow() {
  const el = scrollRef.value
  if (!el || !windowingEnabled.value) {
    fullRender.value = true
    setRange({ start: 0, end: props.items.length })
    return
  }
  const n = props.items.length
  const geo = geometry.value
  const scrollTop = el.scrollTop
  const viewportHeight = viewportHeightOf(el)
  const range = computeWindowRange(geo, n, scrollTop, viewportHeight, {
    overscanPx: DEFAULT_OVERSCAN_PX,
    residentTail: props.residentTailRows ?? DEFAULT_RESIDENT_TAIL_ROWS,
  })
  if (!coversViewport(geo, range, scrollTop, viewportHeight)) {
    if (++coverFailures >= COVER_FAILURE_LIMIT) {
      safeMode.value = true
      console.warn('[MessageList] 窗口覆盖连续失败，已降级为全量渲染')
    }
    fullRender.value = true
    setRange({ start: 0, end: n })
    return
  }
  coverFailures = 0
  fullRender.value = false
  setRange(range)
}

/** 测量已挂载的行并原子发布几何快照。 */
function measureMountedRows() {
  const el = scrollRef.value
  if (!el || !windowingEnabled.value || fullRender.value) return
  el.querySelectorAll<HTMLElement>('[data-item-key]').forEach((node) => {
    ledger.stage(node.dataset.itemKey as string, measure(node))
  })
  const snapshot = ledger.publish()
  if (snapshot) measuredSizes.value = snapshot
}

let windowRecomputePending = false
/** 滚动过程中按帧节流重算窗口。 */
function scheduleWindowRecompute() {
  if (windowRecomputePending) return
  windowRecomputePending = true
  const run = () => {
    windowRecomputePending = false
    recomputeWindow()
  }
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(run)
  else setTimeout(run, 16)
}

onMounted(() => {
  measureMountedRows()
  recomputeWindow()
})

onUpdated(() => {
  measureMountedRows()
  recomputeWindow()
})

// ── 滚动与锚点 ───────────────────────────────────────────────
function onScroll() {
  const el = scrollRef.value
  if (!el) return
  vp.handleScroll(el)              // 归因：确认程序写入 / 判定用户滚动并夺取租约
  const atBottom = vp.isAtBottom(el)
  stickToBottom.value = atBottom
  if (atBottom) {
    showBackToBottom.value = false
    unseenCount.value = 0
  } else {
    showBackToBottom.value = true
  }
  if (props.hasMore && !props.loadingEarlier && el.scrollTop <= TOP_LOAD_THRESHOLD) {
    emit('load-earlier')
  }
  scheduleWindowRecompute()
}

/** 收集当前渲染行的几何（相对滚动容器视口顶部），供锚点计算使用。 */
function collectRows(el: HTMLElement): RowRect[] {
  const cTop = el.getBoundingClientRect().top
  const out: RowRect[] = []
  el.querySelectorAll<HTMLElement>('[data-item-key]').forEach((n) => {
    const r = n.getBoundingClientRect()
    out.push({ key: n.dataset.itemKey as string, top: r.top - cTop, bottom: r.bottom - cTop })
  })
  return out
}

/** 上一次渲染的首项 key：用于把「头部插入」与「尾部追加」区分开。 */
let lastHeadKey: string | null = null

// 列表长度变化：头部插入（历史分页）保持视口锚点；尾部追加按贴底意图跟随
watch(() => props.items.length, async (n, prev) => {
  const el = scrollRef.value
  const headKey = props.items.length ? itemKey(props.items[0], 0) : null
  const grew = typeof prev === 'number' && n > prev
  const prepended = grew && lastHeadKey !== null && headKey !== lastHeadKey
  lastHeadKey = headKey
  if (!el || safeMode.value) return

  if (prepended) {
    // prepend 前（DOM 仍为旧状态）捕获锚点，更新后按锚点行还原视口。
    // 锚点法只依赖锚点行自身位置，因此对"窗口化导致总高度变化"免疫。
    const anchor = captureAnchor(collectRows(el))
    await nextTick()
    if (anchor) {
      const offset = resolveRestoreOffset(anchor, collectRows(el), el.scrollTop)
      if (offset !== null) vp.restore(el, offset)
    }
    return
  }

  if (!stickToBottom.value) {
    if (grew) unseenCount.value += n - (prev as number)
    return
  }
  await nextTick()
  // 经单写者跟随：用户租约未过期时会被拒绝（不抢用户正在阅读的位置）
  vp.follow(el)
})

function scrollToBottom() {
  const el = scrollRef.value
  if (!el) return
  vp.release()                     // 用户显式要求回底：租约作废，跟随立即生效
  vp.follow(el)
  stickToBottom.value = true
  showBackToBottom.value = false
  unseenCount.value = 0
}

// 轨迹跳转：滚动到对应用户消息 + 高亮闪烁
watch(() => props.focusToken, async () => {
  if (props.focusIndex == null) return
  stickToBottom.value = false
  // 查找对应用户消息的 DOM 元素并滚动到可见区域
  await nextTick()
  const el = scrollRef.value
  if (el) {
    const target = el.querySelector<HTMLElement>(`[data-chat-anchor-key="${props.focusIndex}"]`)
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
  highlightIndex.value = props.focusIndex
  setTimeout(() => { if (highlightIndex.value === props.focusIndex) highlightIndex.value = null }, 2000)
})

const badgeText = computed(() => (unseenCount.value > 99 ? '99+' : String(unseenCount.value)))
</script>

<template>
  <div
    ref="scrollRef"
    class="message-list"
    @scroll.passive="onScroll"
    @wheel.passive="onUserInput"
    @touchstart.passive="onUserInput"
  >
    <!-- P2-E: 首次加载骨架屏 -->
    <div
      v-if="initialLoading"
      class="skeleton-list"
    >
      <div
        v-for="n in 4"
        :key="n"
        class="skeleton-msg"
        :class="n % 2 === 0 ? 'user' : 'assistant'"
      >
        <div class="skeleton-avatar" />
        <div class="skeleton-lines">
          <div
            class="skeleton-line"
            :style="{ width: 60 + (n * 7) % 30 + '%' }"
          />
          <div
            class="skeleton-line"
            :style="{ width: 80 + (n * 11) % 15 + '%' }"
          />
        </div>
      </div>
    </div>
    <div
      v-else-if="items.length === 0"
      class="list-empty-placeholder"
    />

    <!-- P 性能：触顶加载更早（infinite scroll） -->
    <div
      v-if="props.hasMore || props.loadingEarlier"
      class="earlier-loader"
    >
      <template v-if="props.loadingEarlier">
        <span class="loading-dot chat-pulse" /><span class="loading-dot chat-pulse" /><span class="loading-dot chat-pulse" />
      </template>
      <span v-else>加载更早的消息</span>
    </div>

    <!-- 消息列表：窗口化渲染（只挂载窗口内的行，其余用 spacer 占位）。
         所有 item 类型统一交给 MessageItem 按 kind 分发（text / reasoning /
         tool_call / tool_result / turn_stats / date_divider），此处只额外处理
         kb_hits（统一任务模式的专属标签，不属于 ChatItem 联合类型） -->
    <div class="message-container">
      <template
        v-for="node in renderNodes"
        :key="node.key"
      >
        <!-- 段间与首尾占位：未挂载部分仍占真实高度，滚动条不跳 -->
        <div
          v-if="node.kind === 'spacer'"
          class="window-spacer"
          :style="{ height: (node as any).height + 'px' }"
        />
        <!-- data-item-key：锚点定位用的稳定身份（不能被内容补丁改写） -->
        <div
          v-else
          class="chat-row"
          :data-item-key="node.key"
        >
          <MessageItem
            v-if="(node as any).item.kind !== 'kb_hits'"
            :item="(node as any).item"
            :anchor-key="isUserAnchor((node as any).item) ? (node as any).index : undefined"
            :highlighted="highlightIndex === (node as any).index"
            @retry-from="(id: string, text: string) => emit('retry-from', id, text)"
            @regenerate="(id: string) => emit('regenerate', id)"
            @continue="(id: string) => emit('continue', id)"
            @retry-failed="(id: string) => emit('retry-failed', id)"
          />
          <div
            v-else
            class="kb-hits-tag"
          >
            <span class="kb-hits-text">引用了知识库（×{{ (node as any).item.count || 1 }}）</span>
            <a
              v-if="(node as any).item.kb_id"
              class="kb-hits-link"
              href="#"
              title="查看引用的知识库"
              @click.prevent
            >查看知识库</a>
          </div>
        </div>
      </template>
    </div>

    <div
      v-if="loading"
      class="loading-indicator"
    >
      <span class="loading-dot chat-pulse" /><span class="loading-dot chat-pulse" /><span class="loading-dot chat-pulse" />
    </div>

    <!-- 回到底部按钮：离开底部时显示 + 新消息未读徽标（deepseek bottom-follow 语义补充） -->
    <Transition name="back-fade">
      <button
        v-if="showBackToBottom"
        class="back-to-bottom"
        type="button"
        :title="'回到底部' + (unseenCount ? `（${unseenCount} 条新消息）` : '')"
        @click="scrollToBottom"
      >
        <ArrowDownOutlined />
        <span
          v-if="unseenCount"
          class="back-badge"
        >{{ badgeText }}</span>
      </button>
    </Transition>
  </div>
</template>

<style scoped>
.message-list { flex: 1; overflow-y: auto; position: relative; contain: layout style; }
.list-empty-placeholder { height: 24px; }

/* P2-E: 首屏骨架屏 */
.skeleton-list { padding: 16px 24px; }
.skeleton-msg { display: flex; gap: 12px; margin-bottom: 24px; }
.skeleton-msg.user { flex-direction: row-reverse; }
.skeleton-avatar { width: 28px; height: 28px; border-radius: 50%; background: var(--bg-hover); flex-shrink: 0; animation: skeleton-pulse 1.4s ease-in-out infinite; }
.skeleton-lines { flex: 1; display: flex; flex-direction: column; gap: 8px; max-width: 70%; }
.skeleton-msg.user .skeleton-lines { align-items: flex-end; }
.skeleton-line { height: 14px; border-radius: 4px; background: var(--bg-hover); animation: skeleton-pulse 1.4s ease-in-out infinite; }
.skeleton-line:nth-child(2) { animation-delay: 0.2s; }
@keyframes skeleton-pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .skeleton-avatar, .skeleton-line { animation: none; } }
/* ── 移动端：骨架屏间距/头像压缩 ── */
@media (max-width: 768px) {
  .skeleton-list { padding: 12px 16px; }
  .skeleton-msg { gap: 10px; margin-bottom: 18px; }
  .skeleton-avatar { width: 24px; height: 24px; }
  .skeleton-lines { max-width: 85%; }
}
@media (max-width: 576px) { .skeleton-list { padding: 10px 12px; } }
.earlier-loader { display: flex; align-items: center; justify-content: center; gap: 6px; height: 36px; font-size: 12px; color: var(--text-tertiary); }
/* 消息容器：正常文档流，不遮挡 */
.message-container { width: 100%; }
/* 行容器：仅承载锚点身份，不引入布局变化（无 margin/padding） */
.chat-row { width: 100%; }
/* 窗口占位：只提供高度，不参与锚点身份收集 */
.window-spacer { width: 100%; flex: none; }
.loading-indicator { display: flex; justify-content: center; gap: 6px; padding: 14px 0; }
/* 尺寸/底色保留，脉冲与错峰延迟由全局 .chat-pulse 提供（src/style.css） */
.loading-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-tertiary); }
.back-to-bottom { position: sticky; bottom: 16px; left: calc(50% - 22px); width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-secondary); cursor: pointer; box-shadow: var(--sig-shadow-card); display: flex; align-items: center; justify-content: center; z-index: 10; }
.back-to-bottom:hover { color: var(--primary); border-color: var(--primary); }
.back-badge { position: absolute; top: -4px; right: -4px; min-width: 18px; height: 18px; padding: 0 4px; border-radius: 9px; background: var(--primary); color: #fff; font-size: 11px; line-height: 18px; text-align: center; }
.back-fade-enter-active, .back-fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.back-fade-enter-from, .back-fade-leave-to { opacity: 0; transform: translateY(8px); }
</style>
