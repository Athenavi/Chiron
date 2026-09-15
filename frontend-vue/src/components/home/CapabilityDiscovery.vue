<script setup lang="ts">
/**
 * 能力发现：把后端能力注册中心（GET /v1/capabilities）搬到首页。
 *
 * 后端一直有这套"互通的发现侧" —— 六类工作台的能力都挂了真实执行器
 * （python-engine/app/core/capabilities.py 的 preload_default_capabilities），
 * 但前端从未调用过：用户只能靠自己知道"平台能做什么"，能力注册中心成了死资产。
 * 这里把它变成可检索、可跳转的入口。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Input, Tag } from 'ant-design-vue'
import { SearchOutlined } from '@ant-design/icons-vue'
import { listCapabilities, searchCapabilities, type Capability } from '../../api'
import { setChatPrefill } from '../chat/chatPrefill'

const router = useRouter()

const capabilities = ref<Capability[]>([])
const loading = ref(true)
const error = ref(false)
const keyword = ref('')
const searched = ref(false)

const WORKSTATION_LABEL: Record<string, string> = {
  skill: '技能',
  knowledge: '知识',
  agent: 'Agent',
  workflow: '工作流',
  plugin: '插件',
  dialogue: '对话',
}

/** 按工作台分组，组内保持后端顺序（注册顺序就是"核心能力优先"的顺序） */
const grouped = computed(() => {
  const order = ['dialogue', 'agent', 'workflow', 'skill', 'knowledge', 'plugin']
  const buckets = new Map<string, Capability[]>()
  for (const cap of capabilities.value) {
    // 不再用 `|| 'other'` 兜底：workstation_type 的类型是 WorkstationType（见
    // src/types/workstation.ts），契约外的值不该悄悄进入分组，而该在类型层被挡下。
    const key = cap.workstation_type
    const list = buckets.get(key) ?? []
    list.push(cap)
    buckets.set(key, list)
  }
  return [...buckets.entries()].sort(
    (a, b) => order.indexOf(a[0]) - order.indexOf(b[0]),
  )
})

async function load() {
  loading.value = true
  error.value = false
  try {
    capabilities.value = await listCapabilities()
  } catch {
    error.value = true
    capabilities.value = []
  } finally {
    loading.value = false
  }
}

/**
 * 搜索走 /v1/capabilities/search（按关键词/标签/描述匹配并排序），
 * 清空关键词时回到全量列表 —— 不让用户卡在"搜过就回不去"的状态。
 */
async function onSearch() {
  const q = keyword.value.trim()
  if (!q) {
    searched.value = false
    await load()
    return
  }
  loading.value = true
  try {
    capabilities.value = await searchCapabilities(q)
    searched.value = true
    error.value = false
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
}

/**
 * 投递这条能力：跳进对话并预填一句开场。
 *
 * 为什么不带 `?focus=<capability_id>` 去对应工作台：注册表里的 `capability_id`
 * 是**能力类型**（``skill:execute_python`` / ``knowledge:kb_search``），不是某个
 * 资源实例的 id 或名字 —— 目标页里没有可定位的条目，跳过去只会落到一个空白列表。
 * 能力最终都是在对话里被用起来的，所以直接把它带进对话。
 */
function useCapability(cap: Capability) {
  const label = cap.name || cap.capability_id
  setChatPrefill({
    title: label,
    text: cap.description || '',
    kind: 'capability',
    source: 'capability',
  })
  void router.push('/chat')
}

onMounted(load)
</script>

<template>
  <section class="capability-discovery">
    <h2 class="section-title">
      {{ $t('能力发现') }}
    </h2>
    <p class="section-sub">
      {{ $t('平台能做什么，一目了然；点一条直接带进对话用起来') }}
    </p>

    <div class="cap-search">
      <SearchOutlined class="cap-search-icon" />
      <Input
        v-model:value="keyword"
        :placeholder="$t('搜能力（如 检索 / 代码 / 周报）')"
        allow-clear
        @press-enter="onSearch"
        @change="(e: any) => { if (!e?.target?.value) onSearch() }"
      />
    </div>

    <p
      v-if="loading"
      class="cap-hint"
    >
      {{ $t('加载中…') }}
    </p>
    <p
      v-else-if="error"
      class="cap-hint"
    >
      {{ $t('能力列表加载失败（能力注册中心不可用时不影响其它功能）') }}
    </p>
    <p
      v-else-if="capabilities.length === 0"
      class="cap-hint"
    >
      {{ searched ? '没有匹配的能力' : '暂无已注册能力' }}
    </p>
    <div
      v-else
      class="cap-groups"
    >
      <div
        v-for="[type, items] in grouped"
        :key="type"
        class="cap-group"
      >
        <div class="cap-group-head">
          <span class="cap-group-name">{{ WORKSTATION_LABEL[type] || type }}</span>
          <span class="cap-group-count">{{ items.length }}</span>
        </div>
        <div class="cap-list">
          <button
            v-for="cap in items"
            :key="cap.capability_id"
            type="button"
            class="cap-item"
            :title="cap.capability_id"
            @click="useCapability(cap)"
          >
            <span class="cap-name">{{ cap.name || cap.capability_id }}</span>
            <span class="cap-desc">{{ cap.description }}</span>
            <span class="cap-meta">
              <Tag v-if="cap.capability_type">
                {{ cap.capability_type }}
              </Tag>
              <span
                v-if="cap.stats?.call_count"
                class="cap-stats"
              >已调用 {{ cap.stats.call_count }} 次</span>
            </span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.capability-discovery { max-width: 960px; margin: 0 auto; padding: 40px 24px 0; }
.section-title { font-size: 24px; font-weight: 650; color: var(--text-primary); text-align: center; margin: 0 0 8px; }
.section-sub { text-align: center; color: var(--text-secondary); font-size: 14px; margin: 0 0 20px; }

.cap-search { display: flex; align-items: center; gap: 8px; max-width: 420px; margin: 0 auto 20px; }
.cap-search-icon { color: var(--text-muted); }

.cap-hint { text-align: center; color: var(--text-muted); font-size: 13px; padding: 16px 0; }

.cap-groups { display: flex; flex-direction: column; gap: 18px; }
.cap-group-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.cap-group-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.cap-group-count { font-size: 11px; color: var(--text-muted); }

.cap-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 8px; }
.cap-item {
  display: flex; flex-direction: column; gap: 4px; align-items: flex-start;
  padding: 10px 12px; text-align: left; cursor: pointer;
  border: 1px solid var(--border-card); border-radius: var(--sig-radius-card);
  background: var(--bg-card); color: inherit;
  transition: border-color 0.15s ease, transform 0.15s ease;
}
.cap-item:hover { border-color: var(--primary); transform: translateY(-1px); }
.cap-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.cap-desc {
  font-size: 12px; color: var(--text-secondary); line-height: 1.5;
  overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.cap-meta { display: flex; align-items: center; gap: 6px; margin-top: 2px; }
.cap-stats { font-size: 11px; color: var(--text-muted); }
</style>
