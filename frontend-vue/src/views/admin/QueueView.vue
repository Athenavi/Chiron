<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Card, Descriptions, DescriptionsItem, Button, Table, Spin, message } from 'ant-design-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { getQueueStats, flushQueue, pauseQueue } from '@/api/admin'

import { useI18n } from 'vue-i18n'
const { t } = useI18n()
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const loading = ref(false)
const flushLoading = ref(false)
const isPaused = ref(false)

/**
 * 事件队列 = Redis Stream（webhook:events）的真实积压。
 * 数据源见后端 GetQueueStats：此前读取的 queue:tasks:length / queue:vip:length
 * 在全仓库没有写入方，因此恒为 0；现改由 Redis Stream 命令直接观测。
 */
const queueStats = ref({
  taskQueueLength: 0,
  vipQueueLength: 0,
  groups: 0,
  consumers: 0,
  lag: 0,
  throughput: 0,
  activeRequests: 0,
})

const queueHistory = ref<{ taskLength: number; pendingLength: number }[]>([])

const queueChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: queueHistory.value.length
      ? queueHistory.value.map((_, i) => `T-${queueHistory.value.length - i}`)
      : ['--'],
  },
  yAxis: { type: 'value', name: t('队列积压') },
  series: [
    {
      name: t('事件队列积压'),
      type: 'line',
      data: queueHistory.value.length ? queueHistory.value.map(h => h.taskLength) : [0],
      smooth: true,
    },
    {
      name: t('待确认消息'),
      type: 'line',
      data: queueHistory.value.length ? queueHistory.value.map(h => h.pendingLength) : [0],
      smooth: true,
    },
  ],
}))

const waitingTasks = ref<any[]>([])

const columns = [
  { title: t('消息 ID'), dataIndex: 'task_id', width: 180 },
  { title: t('用户 ID'), dataIndex: 'user_id', width: 120 },
  { title: t('事件类型'), dataIndex: 'content', ellipsis: true },
  { title: t('入队时间'), dataIndex: 'queued_at', width: 200 },
  { title: t('位置'), dataIndex: 'position', width: 80 },
]

async function fetchData() {
  loading.value = true
  try {
    const data = await getQueueStats()
    queueStats.value = {
      taskQueueLength: data.task_queue_length || 0,
      vipQueueLength: data.vip_queue_length || 0,
      groups: data.groups || 0,
      consumers: data.consumers || 0,
      lag: data.lag || 0,
      throughput: data.throughput_qps || 0,
      activeRequests: data.active_requests || 0,
    }
    waitingTasks.value = data.waiting_tasks || []

    queueHistory.value.push({
      taskLength: data.task_queue_length || 0,
      pendingLength: data.vip_queue_length || 0,
    })
    if (queueHistory.value.length > 20) {
      queueHistory.value.shift()
    }
  } catch {
    message.error(t('获取队列数据失败'))
  } finally {
    loading.value = false
  }
}

async function handleFlushQueue() {
  flushLoading.value = true
  try {
    await flushQueue()
    message.success(t('队列已清空'))
    await fetchData()
  } catch {
    message.error(t('清空队列失败'))
  } finally {
    flushLoading.value = false
  }
}

async function handlePauseQueue() {
  try {
    const pause = !isPaused.value
    await pauseQueue(pause)
    isPaused.value = pause
    message.success(pause ? t('已暂停消费') : t('已恢复消费'))
  } catch {
    message.error(t('操作失败'))
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="queue-monitor">
    <Spin :spinning="loading">
      <div class="metric-grid">
        <Card :title="$t('队列状态')">
          <Descriptions
            bordered
            :column="1"
          >
            <DescriptionsItem :label="$t('事件队列积压')">
              {{ queueStats.taskQueueLength }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('待确认消息')">
              {{ queueStats.vipQueueLength }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('未投递积压')">
              {{ queueStats.lag }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('消费者组')">
              {{ queueStats.groups }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('消费者数量')">
              {{ queueStats.consumers }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('活跃请求')">
              {{ queueStats.activeRequests }}
            </DescriptionsItem>
            <DescriptionsItem :label="$t('吞吐量')">
              {{ queueStats.throughput }} QPS
            </DescriptionsItem>
          </Descriptions>
        </Card>
        <Card :title="$t('队列积压趋势')">
          <VChart
            :option="queueChartOption"
            style="height: var(--chart-h, 300px)"
            autoresize
          />
        </Card>
      </div>

      <Card
        :title="$t('等待队列')"
        style="margin-top: 16px"
      >
        <template #extra>
          <Button
            type="primary"
            ghost
            :loading="flushLoading"
            @click="handleFlushQueue"
          >
            {{ $t('清空队列') }}
          </Button>
          <Button
            style="margin-left: 8px"
            @click="handlePauseQueue"
          >
            {{ isPaused ? $t('恢复消费') : $t('暂停消费') }}
          </Button>
        </template>
        <Table
          :columns="columns"
          :data-source="waitingTasks"
          :pagination="false"
          :scroll="{ x: 720 }"
        >
          <template #emptyText>
            <div class="empty-block">
              <span class="empty-icon">📭</span><span class="empty-text">{{ $t('暂无数据') }}</span>
            </div>
          </template>
        </Table>
      </Card>
    </Spin>
  </div>
</template>

<style scoped>
.queue-monitor { padding: 0; --chart-h: 300px; }

/* 卡片网格:auto-fill,窄屏自动降列 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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

/* 移动端:图表压缩高度、卡片头换行、触控目标 */
@media (max-width: 768px) {
  .queue-monitor { --chart-h: 220px; }
  .queue-monitor :deep(.ant-card-head-wrapper) { flex-wrap: wrap; row-gap: 8px; }
  .queue-monitor :deep(.ant-card-extra) { margin-left: 0; }
  .queue-monitor :deep(.ant-btn) { min-height: 40px; }
}
</style>
