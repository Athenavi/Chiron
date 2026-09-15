<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Card, Progress, Descriptions, DescriptionsItem, Spin, message } from 'ant-design-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { getCacheStats } from '@/api/admin'

import { useI18n } from 'vue-i18n'
const { t } = useI18n()
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const loading = ref(false)

/**
 * 缓存统计的真实来源：
 *   - 引擎侧 L1/L2/L3 命中次数与总命中率 → python-engine「GET /info」的 gateway.cache；
 *   - Redis 缓存层命中率与内存占用 → Redis INFO。
 * 历史实现读取的 cache:stats:hits / cache:stats:misses 在全仓库没有写入方，恒为 0。
 */
const cacheStats = ref({
  totalHitRate: 0,
  totalRequests: 0,
  hits: 0,
  misses: 0,
  l1Hits: 0,
  l2Hits: 0,
  l3Hits: 0,
  redisHitRate: 0,
  redisKeyspaceHits: 0,
  redisKeyspaceMisses: 0,
  redisMemory: '0 MB',
  redisMaxMemory: '',
})

const progressColor = computed(() => {
  const rate = cacheStats.value.totalHitRate
  if (rate >= 80) return '#18a058'
  if (rate >= 60) return '#f0a020'
  return '#d03050'
})

const hitRateHistory = ref<number[]>([])

const hitRateChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: hitRateHistory.value.length
      ? hitRateHistory.value.map((_, i) => `T-${hitRateHistory.value.length - i}`)
      : ['--'],
  },
  yAxis: { type: 'value', name: t('命中率'), max: 100 },
  series: [
    {
      name: t('缓存命中率'),
      type: 'line',
      data: hitRateHistory.value.length ? hitRateHistory.value : [0],
      smooth: true,
    },
  ],
}))

function formatSize(mb: number): string {
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`
}

async function fetchData() {
  loading.value = true
  try {
    const d = await getCacheStats()

    cacheStats.value = {
      totalHitRate: d.total_hit_rate || 0,
      totalRequests: d.total_requests || 0,
      hits: d.total_hits || 0,
      misses: d.total_misses || 0,
      l1Hits: d.l1_hits || 0,
      l2Hits: d.l2_hits || 0,
      l3Hits: d.l3_hits || 0,
      redisHitRate: d.redis_hit_rate || 0,
      redisKeyspaceHits: d.redis_keyspace_hits || 0,
      redisKeyspaceMisses: d.redis_keyspace_misses || 0,
      redisMemory: formatSize(d.redis_memory_mb || 0),
      redisMaxMemory: d.redis_max_memory_mb
        ? formatSize(d.redis_max_memory_mb)
        : t('未限制'),
    }

    hitRateHistory.value.push(d.total_hit_rate || 0)
    if (hitRateHistory.value.length > 20) {
      hitRateHistory.value.shift()
    }
  } catch {
    message.error(t('获取缓存数据失败'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="cache-monitor">
    <Spin :spinning="loading">
      <div class="metric-grid">
        <Card :title="$t('缓存命中率')">
          <Progress
            type="dashboard"
            :percent="cacheStats.totalHitRate"
            :stroke-color="progressColor"
            size="small"
          >
            <template #format>
              <span style="font-size: 24px; font-weight: 600">{{ cacheStats.totalHitRate }}%</span>
            </template>
          </Progress>
          <Descriptions
            bordered
            :column="1"
            style="margin-top: 16px"
          >
            <DescriptionsItem :label="$t('L1 命中次数')">
              {{ cacheStats.l1Hits }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('L2 命中次数')">
              {{ cacheStats.l2Hits }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('L3 命中次数')">
              {{ cacheStats.l3Hits }}
            </DescriptionsItem>
          </Descriptions>
        </Card>
        <Card :title="$t('缓存统计')">
          <Descriptions
            bordered
            :column="1"
          >
            <DescriptionsItem :label="$t('总请求数')">
              {{ cacheStats.totalRequests }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('缓存命中')">
              {{ cacheStats.hits }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('缓存未命中')">
              {{ cacheStats.misses }}
            </DescriptionsItem>
          </Descriptions>
        </Card>
        <Card :title="$t('Redis 缓存')">
          <Descriptions
            bordered
            :column="1"
          >
            <DescriptionsItem :label="$t('命中率')">
              {{ cacheStats.redisHitRate }}%
            </DescriptionsItem>
            <DescriptionsItem :label="$t('命中次数')">
              {{ cacheStats.redisKeyspaceHits }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('未命中次数')">
              {{ cacheStats.redisKeyspaceMisses }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('已用内存')">
              {{ cacheStats.redisMemory }}
              <template v-if="cacheStats.redisMaxMemory">
                / {{ cacheStats.redisMaxMemory }}
              </template>
            </DescriptionsItem>
          </Descriptions>
        </Card>
      </div>

      <Card
        :title="$t('缓存命中率趋势')"
        style="margin-top: 16px"
      >
        <VChart
          :option="hitRateChartOption"
          style="height: var(--chart-h, 300px)"
          autoresize
        />
      </Card>
    </Spin>
  </div>
</template>

<style scoped>
.cache-monitor { padding: 0; --chart-h: 300px; }

/* 指标卡网格:auto-fill,窄屏自动降列 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

/* 空状态统一 */
.empty-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 0;
  color: var(--text-tertiary);
}
.empty-icon { font-size: 26px; line-height: 1; opacity: 0.8; }
.empty-text { font-size: 13px; }

/* 移动端:图表高度压缩 */
@media (max-width: 768px) {
  .cache-monitor { --chart-h: 220px; }
}
</style>
