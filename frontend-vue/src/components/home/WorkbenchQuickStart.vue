<script setup lang="ts">
/**
 * 首页的协作入口：把知识库 / Agent / 技能 / 工作流"带着"一起进入对话。
 *
 * 之前首页的六张卡片是六个互不相干的跳转按钮 —— 进去之后的组合能力
 * （对话页的 context chips）用户根本不知道存在。这里把"带能力进对话"
 * 提到最外层，并且选项直接来自各工作台的真实数据。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Select } from 'ant-design-vue'
import {
  listAgents,
  listKnowledgeBases,
  listSkillResources,
  listWorkflows,
  type WorkbenchResource,
} from '../../api'
import { buildContextQuery, type ContextChip, type ContextChipType } from '../chat/contextChips'

interface Source {
  type: ContextChipType
  label: string
  placeholder: string
  load: () => Promise<WorkbenchResource[]>
}

const router = useRouter()

const sources: Source[] = [
  { type: 'kb', label: '知识库', placeholder: '检索增强', load: listKnowledgeBases },
  {
    type: 'agent',
    label: 'Agent',
    placeholder: '指定执行者',
    load: async () => (await listAgents()).map(a => ({ id: a.id, name: a.name })),
  },
  { type: 'skill', label: '技能', placeholder: '装配技能', load: listSkillResources },
  { type: 'workflow', label: '工作流', placeholder: '按编排执行', load: listWorkflows },
]

const emptyOptions = (): Record<ContextChipType, WorkbenchResource[]> => ({ kb: [], agent: [], skill: [], workflow: [] })
const options = ref<Record<ContextChipType, WorkbenchResource[]>>(emptyOptions())
const picked = ref<Record<ContextChipType, string[]>>({ kb: [], agent: [], skill: [], workflow: [] })
const loading = ref(true)

onMounted(async () => {
  // 各工作台接口互相独立：任一失败只让那一类为空，不拖垮整个入口
  const results = await Promise.all(sources.map(async (source) => {
    try {
      return [source.type, await source.load()] as const
    } catch {
      return [source.type, [] as WorkbenchResource[]] as const
    }
  }))
  const next = emptyOptions()
  for (const [type, list] of results) next[type] = list
  options.value = next
  loading.value = false
})

const selectOptions = computed(() => {
  const out = {} as Record<ContextChipType, { value: string; label: string }[]>
  for (const { type } of sources) out[type] = options.value[type].map(r => ({ value: r.id, label: r.name }))
  return out
})

const pickedCount = computed(() => Object.values(picked.value).reduce((total, values) => total + values.length, 0))
const hasAnyResource = computed(() => sources.some(s => options.value[s.type].length > 0))

function startChat() {
  const chips: ContextChip[] = []
  for (const { type } of sources) {
    for (const value of picked.value[type]) chips.push({ type, label: value, value })
  }
  // query 约定（同名参数可重复）与对话页读 URL 共用 buildContextQuery/parseContextQuery
  router.push({ path: '/chat', query: buildContextQuery(chips) })
}
</script>

<template>
  <section class="quickstart">
    <h2 class="quickstart-title">
      带着工作台能力开对话
    </h2>
    <p class="quickstart-sub">
      勾选这次要用到的能力，进入对话后它们会作为上下文生效（可多选）
    </p>
    <div class="quickstart-grid">
      <div
        v-for="source in sources"
        :key="source.type"
        class="quickstart-field"
      >
        <label class="quickstart-label">{{ source.label }}</label>
        <Select
          v-model:value="picked[source.type]"
          mode="multiple"
          :options="selectOptions[source.type]"
          :placeholder="source.placeholder"
          :loading="loading"
          :disabled="!loading && options[source.type].length === 0"
          allow-clear
          show-search
          option-filter-prop="label"
          class="quickstart-select"
        />
      </div>
    </div>
    <div class="quickstart-actions">
      <Button
        type="primary"
        :disabled="pickedCount === 0"
        @click="startChat"
      >
        开始对话{{ pickedCount ? `（${pickedCount}）` : '' }}
      </Button>
      <span v-if="!loading && !hasAnyResource" class="quickstart-hint">
        还没有可用资源；也可以先进任一工作台，在详情里点「在对话中使用」
      </span>
    </div>
  </section>
</template>

<style scoped>
.quickstart {
  max-width: var(--chat-content-width);
  margin: 0 auto;
  padding: 0 var(--space-6) var(--space-12);
}

.quickstart-title {
  font-size: var(--fs-2xl);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-2);
}

.quickstart-sub {
  font-size: var(--fs-base);
  color: var(--text-secondary);
  margin-bottom: var(--space-5);
}

.quickstart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.quickstart-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.quickstart-label {
  font-size: var(--fs-sm);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-secondary);
}

.quickstart-select {
  width: 100%;
}

.quickstart-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.quickstart-hint {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}

@media (max-width: 640px) {
  .quickstart {
    padding: 0 var(--space-4) var(--space-10);
  }
}
</style>
