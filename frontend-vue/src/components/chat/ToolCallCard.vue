<script setup lang="ts">
import { ref, computed } from 'vue'
import { CaretRightOutlined } from '@ant-design/icons-vue'
import type { ToolCallItem } from './chat-types'

const props = defineProps<{ item: ToolCallItem; depth?: number }>()
const expanded = ref(false)

function prettyArgs(): string {
  try {
    return JSON.stringify(JSON.parse(props.item.arguments || '{}'), null, 2)
  } catch {
    return props.item.arguments || ''
  }
}

// 参数摘要：首行/关键字段（deepseek ToolRow summary 截断）
const summary = computed(() => {
  const a = props.item.arguments || ''
  if (!a) return ''
  try {
    const parsed = JSON.parse(a)
    const keys = Object.keys(parsed)
    if (keys.length === 0) return ''
    // 取前两个短字段值
    const parts = keys.slice(0, 2).map(k => {
      const v = parsed[k]
      const s = typeof v === 'string' ? v : JSON.stringify(v)
      return s.length > 40 ? s.slice(0, 40) + '…' : s
    })
    return parts.join(' · ')
  } catch {
    return a.length > 60 ? a.slice(0, 60) + '…' : a
  }
})

const padLeft = computed(() => (props.depth || 0) * 22)
</script>

<template>
  <div
    class="tool-row-wrap chat-row-shell"
    :data-state="item.status"
    :data-tool="item.name"
  >
    <!-- 工具树缩进连接线 -->
    <div
      v-if="(depth || 0) > 0"
      class="tree-guide"
      :style="{ left: `${padLeft - 14}px` }"
      aria-hidden
    />

    <div
      class="tool-row"
      :style="{ marginLeft: `${padLeft}px` }"
    >
      <button
        class="tool-main chat-row-head"
        type="button"
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        <CaretRightOutlined
          class="chat-chevron"
          :class="{ open: expanded }"
        />
        <span class="tool-name">{{ item.name }}</span>
        <span
          class="chat-sep"
          aria-hidden
        />
        <span
          class="chat-state-dot"
          :data-state="item.status"
          aria-hidden
        />
        <span class="tool-summary">{{ summary }}</span>
      </button>

      <Transition name="chat-expand">
        <div
          v-if="expanded"
          class="tool-args"
        >
          <pre>{{ prettyArgs() }}</pre>
        </div>
      </Transition>
    </div>
  </div>
</template>

<!-- 行节奏 / chevron / 状态点 / 展开动画 / reduced-motion 来自全局 .chat-* 原语（style.css）；
     此处保留工具行独有的缩进导线、running sweep 流光与参数块 -->
<style scoped>
.tool-row-wrap { position: relative; }
.tree-guide { position: absolute; top: 0; bottom: 0; width: 1px; background: var(--border); }

.tool-row { overflow: hidden; border-radius: var(--sig-radius-code); }
.tool-row:hover { background: var(--bg-hover); }
.tool-name { font-family: var(--font-mono); font-size: 13px; color: var(--text-primary); font-weight: 400; white-space: nowrap; }
.tool-summary { flex: 1; min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: var(--text-tertiary); font-size: 12px; }

/* running sweep 流光（deepseek ToolRow sweep） */
.tool-row-wrap[data-state='running'] .tool-row { position: relative; }
.tool-row-wrap[data-state='running'] .tool-row::after {
  content: ''; position: absolute; top: 0; bottom: 0; left: 0; width: 300px;
  background: linear-gradient(90deg, transparent 0%, color-mix(in srgb, var(--bg-page) 60%, transparent) 55%, transparent 100%);
  animation: toolRowSweep 2.6s ease-out infinite; pointer-events: none;
}
@keyframes toolRowSweep { 0% { left: -300px; } 90%, 100% { left: 100%; } }
@media (prefers-reduced-motion: reduce) {
  .tool-row-wrap[data-state='running'] .tool-row::after { display: none; }
}

.tool-args { padding: 8px 12px; margin: 2px 8px 6px; background: var(--bg-secondary); border: 1px solid var(--border-card); border-radius: var(--sig-radius-button); }
.tool-args pre { margin: 0; font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary); white-space: pre-wrap; word-break: break-all; }
@media (max-width: 576px) { .tool-args { margin: 2px 4px 6px; } }
</style>
