<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Tabs, TabPane } from 'ant-design-vue'
import PerformanceView from './PerformanceView.vue'
import QueueView from './QueueView.vue'
import CacheView from './CacheView.vue'

/**
 * 运行时监控（合并原「性能监控 / 队列监控 / 缓存监控」三个页面）。
 *
 * 合并理由：
 * - 三者是同一类信息（运行时状态），数据源互不重叠但页面体量都很小（模板各 ~100-140 行），
 *   却各占一个菜单项；合并后「总览监控」从 4 项收敛为 2 项（仪表盘 + 运行时监控）。
 * - 仪表盘的 4 张核心指标卡与这三个页面的核心指标重复，合并后职责边界清晰：
 *   仪表盘 = 概览（进来即知），本页 = 排障（按需深入）。
 *
 * 懒加载：只有被访问过的 Tab 才挂载对应子页面（Tabs 默认保留已挂载内容），
 * 避免进入页面就同时请求 /v1/admin/performance + queue + cache 三个端点。
 */
type MonitorTab = 'performance' | 'queue' | 'cache'

const TABS: MonitorTab[] = ['performance', 'queue', 'cache']

const route = useRoute()
const router = useRouter()

function normalizeTab(v: unknown): MonitorTab {
  return typeof v === 'string' && (TABS as string[]).includes(v) ? (v as MonitorTab) : 'performance'
}

const activeTab = ref<MonitorTab>(normalizeTab(route.query.tab))
// 已挂载过的 Tab 集合（懒加载 + 切回时不重新请求）
const mountedTabs = ref<Set<MonitorTab>>(new Set([activeTab.value]))

// 旧路由 /admin/performance|queue|cache 会重定向到本页并带 ?tab=，此处跟随
watch(() => route.query.tab, (v) => {
  const t = normalizeTab(v)
  activeTab.value = t
  mountedTabs.value = new Set([...mountedTabs.value, t])
})

watch(activeTab, (t) => {
  mountedTabs.value = new Set([...mountedTabs.value, t])
})

function onTabChange(key: string | number) {
  const t = normalizeTab(key)
  if (t === activeTab.value) return
  activeTab.value = t
  // 写回 URL：刷新/分享/外部链接都能定位到同一个 Tab
  void router.replace({ path: '/admin/monitor', query: { tab: t } })
}
</script>

<template>
  <div class="monitor-page">
    <Tabs
      :active-key="activeTab"
      @change="onTabChange"
    >
      <TabPane
        key="performance"
        tab="性能"
      >
        <PerformanceView v-if="mountedTabs.has('performance')" />
      </TabPane>
      <TabPane
        key="queue"
        tab="队列"
      >
        <QueueView v-if="mountedTabs.has('queue')" />
      </TabPane>
      <TabPane
        key="cache"
        tab="缓存"
      >
        <CacheView v-if="mountedTabs.has('cache')" />
      </TabPane>
    </Tabs>
  </div>
</template>

<style scoped>
.monitor-page { padding: 0 4px; }
</style>
