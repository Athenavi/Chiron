<script setup lang="ts">
/**
 * 从引擎可用工具中挑选，把**完整定义**写进 Agent 的工具配置。
 *
 * 之前 Agent 的工具只能手写 JSON，而可用工具名（尤其是插件 / MCP 注入的代理工具）
 * 无从得知。这里列出 `GET /v1/tools` 的全部工具（Go 已带出 parameters schema），
 * 勾选即写入；同时保留手写条目 —— 选择器只是补充，不是替代。
 */
import { computed, onMounted, ref } from 'vue'
import { Select, message } from 'ant-design-vue'
import { listTools } from '../../api'
import type { ToolInfo } from '../../utils/toolList'

const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const tools = ref<ToolInfo[]>([])
const loading = ref(true)
const picked = ref<string[]>([])

/** 取现有配置里的工具名（容忍字符串条目与坏 JSON） */
function configuredNames(): Set<string> {
  try {
    const parsed = JSON.parse(props.modelValue || '[]')
    if (!Array.isArray(parsed)) return new Set()
    const names = parsed
      .map((item: any) => (typeof item === 'string' ? item : item?.name))
      .filter((name: unknown): name is string => typeof name === 'string' && name.length > 0)
    return new Set(names)
  } catch {
    return new Set()
  }
}

onMounted(async () => {
  try {
    tools.value = await listTools()
  } catch {
    tools.value = []
  } finally {
    loading.value = false
  }
  // 已配置的工具回填成勾选态
  const configured = configuredNames()
  picked.value = tools.value.filter(t => configured.has(t.name)).map(t => t.name)
})

const options = computed(() => tools.value.map(t => ({
  value: t.name,
  label: t.description ? `${t.name} — ${t.description}` : t.name,
})))

function onChange(value: unknown) {
  // antd 的 update:value 类型是 SelectValue（可能是单值/数字），统一成名字数组
  const names = (Array.isArray(value) ? value : value == null ? [] : [value]).map(item => String(item))
  picked.value = names

  let handwritten: any[] = []
  let parseFailed = false
  try {
    const parsed = JSON.parse(props.modelValue || '[]')
    if (Array.isArray(parsed)) handwritten = parsed
    else if (props.modelValue.trim()) parseFailed = true
  } catch {
    parseFailed = !!props.modelValue.trim()
  }
  if (parseFailed) {
    message.warning('现有工具配置不是合法 JSON，已按本次选择重写')
  }

  // 保留用户手写、且不在引擎列表里的条目（引擎里的按最新 schema 重写）
  const known = new Set(tools.value.map(t => t.name))
  const keep = handwritten.filter((item: any) => {
    const name = typeof item === 'string' ? item : item?.name
    return typeof name === 'string' && name && !known.has(name)
  })

  const chosen = tools.value
    .filter(t => names.includes(t.name))
    .map(t => (t.parameters === undefined
      ? { name: t.name, description: t.description }
      : { name: t.name, description: t.description, parameters: t.parameters }))

  emit('update:modelValue', JSON.stringify([...keep, ...chosen]))
}
</script>

<template>
  <div class="tool-picker">
    <Select
      mode="multiple"
      :value="picked"
      :options="options"
      :loading="loading"
      placeholder="从引擎可用工具中挑选（含插件提供的）"
      allow-clear
      show-search
      option-filter-prop="label"
      class="tool-picker-select"
      @update:value="onChange"
    />
    <p class="tool-picker-hint">
      勾选会写入上方配置（手写条目保留）；安装插件后，它提供的工具也会出现在这里。
    </p>
  </div>
</template>

<style scoped>
.tool-picker {
  margin-top: 8px;
}

.tool-picker-select {
  width: 100%;
}

.tool-picker-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--text-secondary, #9aa3b2);
}
</style>
