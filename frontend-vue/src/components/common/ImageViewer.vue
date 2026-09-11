<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ZoomInOutlined, ZoomOutOutlined, DownloadOutlined, ExportOutlined, CloseOutlined } from '@ant-design/icons-vue'
import { closeImageViewer, useImageViewer } from './imageViewerState'

const { current } = useImageViewer()

const MIN_SCALE = 0.25
const MAX_SCALE = 6
const STEP = 0.25

const scale = ref(1)
const percent = computed(() => Math.round(scale.value * 100))

// 换图时回到原始大小（沿用上一张的缩放会很困惑）
watch(current, () => { scale.value = 1 })

function zoom(delta: number) {
  const next = scale.value + delta
  scale.value = Math.min(MAX_SCALE, Math.max(MIN_SCALE, Number(next.toFixed(2))))
}

function onKeydown(event: KeyboardEvent) {
  if (!current.value) return
  if (event.key === 'Escape') closeImageViewer()
  else if (event.key === '+' || event.key === '=') zoom(STEP)
  else if (event.key === '-') zoom(-STEP)
  else if (event.key === '0') scale.value = 1
}

onMounted(() => { window.addEventListener('keydown', onKeydown) })
onBeforeUnmount(() => { window.removeEventListener('keydown', onKeydown) })
</script>

<template>
  <Teleport to="body">
    <div
      v-if="current"
      class="viewer-mask"
      role="dialog"
      aria-modal="true"
      aria-label="图片查看器"
      @click.self="closeImageViewer"
    >
      <div class="viewer-bar">
        <span class="viewer-name">{{ current.alt || '图片' }}</span>
        <span class="viewer-percent">{{ percent }}%</span>
        <button
          class="viewer-btn"
          type="button"
          title="缩小（-）"
          @click="zoom(-STEP)"
        >
          <ZoomOutOutlined />
        </button>
        <button
          class="viewer-btn"
          type="button"
          title="放大（+）"
          @click="zoom(STEP)"
        >
          <ZoomInOutlined />
        </button>
        <button
          class="viewer-btn"
          type="button"
          title="原始大小（0）"
          @click="scale = 1"
        >
          1:1
        </button>
        <a
          class="viewer-btn"
          :href="current.src"
          target="_blank"
          rel="noopener noreferrer"
          title="在新标签打开"
        >
          <ExportOutlined />
        </a>
        <a
          class="viewer-btn"
          :href="current.src"
          :download="current.alt || 'image'"
          title="下载"
        >
          <DownloadOutlined />
        </a>
        <button
          class="viewer-btn"
          type="button"
          title="关闭（Esc）"
          @click="closeImageViewer"
        >
          <CloseOutlined />
        </button>
      </div>
      <img
        class="viewer-img"
        :src="current.src"
        :alt="current.alt || ''"
        :style="{ transform: `scale(${scale})` }"
        @wheel.prevent="zoom($event.deltaY > 0 ? -STEP : STEP)"
      >
    </div>
  </Teleport>
</template>

<style scoped>
.viewer-mask {
  position: fixed; inset: 0; z-index: 1000;
  display: flex; flex-direction: column; align-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.82);
  overflow: auto;
}
.viewer-bar {
  position: sticky; top: 0; z-index: 1;
  display: flex; align-items: center; gap: 6px;
  max-width: 100%; padding: 6px 10px; margin-bottom: 12px;
  border-radius: var(--radius-full);
  background: rgba(24, 24, 27, 0.86);
  color: #fafafa;
}
.viewer-name { max-width: 40vw; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
.viewer-percent { min-width: 44px; text-align: right; font-size: 12px; font-variant-numeric: tabular-nums; opacity: 0.75; }
.viewer-btn {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 28px; height: 28px; padding: 0 6px;
  border: none; border-radius: var(--radius-sm);
  background: none; color: inherit; font-size: 12px; cursor: pointer;
  text-decoration: none;
}
.viewer-btn:hover { background: rgba(255, 255, 255, 0.14); }
.viewer-btn:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }
.viewer-img {
  max-width: min(96vw, 1600px); max-height: none;
  transition: transform 120ms ease-out;
  transform-origin: center;
}
@media (prefers-reduced-motion: reduce) { .viewer-img { transition: none; } }
</style>
