<script setup lang="ts">
import { ref, computed } from 'vue'
import { CaretRightOutlined } from '@ant-design/icons-vue'

const props = defineProps<{ content: string; streaming?: boolean }>()
const expanded = ref(false)

// 折叠摘要：running 跟随最新行，完成显示首行（deepseek ReasoningRow 语义）
const summary = computed(() => {
  const text = props.content.trimEnd()
  if (props.streaming) {
    const nl = text.lastIndexOf('\n')
    return nl === -1 ? text : text.slice(nl + 1)
  }
  const nl = text.indexOf('\n')
  return nl === -1 ? text : text.slice(0, nl)
})
</script>

<template>
  <div
    class="reasoning-row chat-row-shell"
    :data-state="streaming ? 'running' : 'ok'"
  >
    <button
      class="reasoning-main chat-row-head"
      type="button"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <CaretRightOutlined
        class="chat-chevron"
        :class="{ open: expanded }"
      />
      <span
        class="think-icon"
        aria-hidden
      >💭</span>
      <span class="think-label">Think</span>
      <span
        class="chat-sep"
        aria-hidden
      />
      <span
        class="chat-state-dot"
        :data-state="streaming ? 'running' : 'done'"
        aria-hidden
      />
      <span class="think-summary">{{ summary }}</span>
    </button>
    <Transition name="chat-expand">
      <div
        v-if="expanded"
        class="think-body"
      >
        {{ content }}
      </div>
    </Transition>
  </div>
</template>

<!-- 行节奏 / chevron / 状态点 / 展开动画 / reduced-motion 均由全局 .chat-* 原语提供
     （src/style.css），此处只保留 Think 行独有的内容样式 -->
<style scoped>
.think-icon { font-size: 12px; flex-shrink: 0; }
.think-label { font-weight: 600; color: var(--text-primary); font-size: 13px; }
.think-summary { flex: 1; min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; color: var(--text-tertiary); font-size: 12px; text-align: left; }
.reasoning-row[data-state='running'] .think-summary { color: var(--primary); }
.think-body { padding: 10px 12px; font-size: 13px; line-height: 1.7; color: var(--text-secondary); background: var(--bg-secondary); border: 1px solid var(--border-card); border-radius: var(--sig-radius-button); margin-top: 2px; white-space: pre-wrap; }
</style>
