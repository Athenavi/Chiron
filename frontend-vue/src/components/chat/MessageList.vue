<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { ArrowDownOutlined } from '@ant-design/icons-vue'
import MessageItem from './MessageItem.vue'
import type { ChatItem } from './chat-types'

const props = defineProps<{
  items: ChatItem[]
  loading: boolean
  focusIndex?: number | null   // 跳转目标（用户消息索引）
  focusToken?: number          // 递增触发跳转
  hasMore?: boolean            // P 性能：是否还有更早的消息
  loadingEarlier?: boolean     // P 性能：正在加载更早消息
  /** P2-E: 首次加载会话历史时的骨架屏 */
  initialLoading?: boolean
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

const SCROLL_THRESHOLD = 120
const TOP_LOAD_THRESHOLD = 60

function isUserAnchor(item: ChatItem | undefined): boolean {
  return !!item && item.kind === 'text' && item.role === 'user'
}

/**
 * 稳定唯一渲染 key。
 * 同一条 assistant 消息会拆成多个 item（reasoning / text / tool_call / tool_result），
 * 它们的 id 可能来自同一个消息 id，故加 kind 前缀避免 key 冲突导致节点错位复用。
 * turn_stats 等无 id 的 item 用下标兜底（kind 前缀保证不与有 id 的项碰撞）。
 */
function itemKey(item: ChatItem, index: number): string {
  return item.id ? `${item.kind}:${item.id}` : `${item.kind}:idx${index}`
}

function onScroll() {
  const el = scrollRef.value
  if (!el) return
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < SCROLL_THRESHOLD
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
}

// 新消息到达：跟随底部时自动滚到底；否则累积未读数
watch(() => props.items.length, async (n, prev) => {
  if (!stickToBottom.value) {
    if (typeof prev === 'number' && n > prev) unseenCount.value += n - prev
    return
  }
  await nextTick()
  const el = scrollRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
})

function scrollToBottom() {
  const el = scrollRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
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
        <span class="loading-dot" /><span class="loading-dot" /><span class="loading-dot" />
      </template>
      <span v-else>加载更早的消息</span>
    </div>

    <!-- 消息列表：直接渲染（不需要虚拟滚动）
         所有 item 类型统一交给 MessageItem 按 kind 分发（text / reasoning /
         tool_call / tool_result / turn_stats / date_divider），此处只额外处理
         kb_hits（统一任务模式的专属标签，不属于 ChatItem 联合类型） -->
    <div class="message-container">
      <template v-for="(item, i) in items" :key="itemKey(item, i)">
        <MessageItem
          v-if="(item as any).kind !== 'kb_hits'"
          :item="item"
          :anchor-key="isUserAnchor(item) ? i : undefined"
          :highlighted="highlightIndex === i"
          @retry-from="(id: string, text: string) => emit('retry-from', id, text)"
          @regenerate="(id: string) => emit('regenerate', id)"
          @continue="(id: string) => emit('continue', id)"
          @retry-failed="(id: string) => emit('retry-failed', id)"
        />
        <div
          v-else
          class="kb-hits-tag"
        >
          <span class="kb-hits-text">引用了知识库（×{{ (item as any).count || 1 }}）</span>
          <a
            v-if="(item as any).kb_id"
            class="kb-hits-link"
            href="#"
            title="查看引用的知识库"
            @click.prevent
          >查看知识库</a>
        </div>
      </template>
    </div>

    <div
      v-if="loading"
      class="loading-indicator"
    >
      <span class="loading-dot" /><span class="loading-dot" /><span class="loading-dot" />
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
.loading-indicator { display: flex; justify-content: center; gap: 6px; padding: 14px 0; }
.loading-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-tertiary); animation: dotPulse 1.4s ease-in-out infinite; }
.loading-dot:nth-child(2) { animation-delay: 0.2s; }
.loading-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotPulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
.back-to-bottom { position: sticky; bottom: 16px; left: calc(50% - 22px); width: 44px; height: 44px; border-radius: 50%; border: 1px solid var(--border); background: var(--bg-card); color: var(--text-secondary); cursor: pointer; box-shadow: var(--sig-shadow-card); display: flex; align-items: center; justify-content: center; z-index: 10; }
.back-to-bottom:hover { color: var(--primary); border-color: var(--primary); }
.back-badge { position: absolute; top: -4px; right: -4px; min-width: 18px; height: 18px; padding: 0 4px; border-radius: 9px; background: var(--primary); color: #fff; font-size: 11px; line-height: 18px; text-align: center; }
.back-fade-enter-active, .back-fade-leave-active { transition: opacity 0.2s, transform 0.2s; }
.back-fade-enter-from, .back-fade-leave-to { opacity: 0; transform: translateY(8px); }
</style>
