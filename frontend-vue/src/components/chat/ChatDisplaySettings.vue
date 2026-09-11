<script setup lang="ts">
import { Modal, Button, Segmented } from 'ant-design-vue'
import {
  GAP_OPTIONS,
  LEADING_OPTIONS,
  TEXT_SIZE_OPTIONS,
  useTypographyStore,
} from '../../stores/typography'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ (e: 'update:open', value: boolean): void }>()

const typography = useTypographyStore()
</script>

<template>
  <Modal
    :open="open"
    title="显示设置"
    :footer="null"
    width="420px"
    @cancel="emit('update:open', false)"
  >
    <div class="display-row">
      <span class="display-label">正文字号</span>
      <Segmented
        :value="typography.state.textSize"
        :options="TEXT_SIZE_OPTIONS"
        @change="(v: any) => typography.setTextSize(Number(v))"
      />
    </div>
    <div class="display-row">
      <span class="display-label">行距</span>
      <Segmented
        :value="typography.state.leading"
        :options="LEADING_OPTIONS"
        @change="(v: any) => typography.setLeading(Number(v))"
      />
    </div>
    <div class="display-row">
      <span class="display-label">消息间距</span>
      <Segmented
        :value="typography.state.gap"
        :options="GAP_OPTIONS"
        @change="(v: any) => typography.setGap(Number(v))"
      />
    </div>
    <div class="display-foot">
      <span class="display-hint">只影响本机阅读呈现，保存在浏览器本地。</span>
      <Button
        size="small"
        @click="typography.reset()"
      >
        恢复默认
      </Button>
    </div>
  </Modal>
</template>

<style scoped>
.display-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 0; }
.display-label { font-size: 13px; color: var(--text-secondary); }
.display-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border-subtle); }
.display-hint { font-size: 11px; color: var(--text-tertiary); }
</style>
