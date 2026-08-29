<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import type { TableColumnsType } from 'ant-design-vue'
import { api } from '../../api'

interface EvalDataset {
  id: string
  name: string
  description: string
  example_count: number
  created_at: string
  updated_at: string
}

interface EvalRun {
  id: string
  dataset_name: string
  dataset_id: string
  summary: string
  status: string
  created_at: string
}

const loading = ref(false)
const datasets = ref<EvalDataset[]>([])
const evalRuns = ref<EvalRun[]>([])
const activeTab = ref('datasets')

const modalVisible = ref(false)
const form = ref({ name: '', description: '', examples: '' })
const saving = ref(false)

const runDetailVisible = ref(false)
const runDetail = ref<any>(null)

async function fetchDatasets() {
  loading.value = true
  try {
    const res = await api.get('/v1/ent/eval/datasets')
    datasets.value = res.data?.data?.datasets || []
  } catch (e: any) {
    message.error(e?.response?.data?.error || '加载失败')
  } finally {
    loading.value = false
  }
}

async function fetchRuns() {
  try {
    const res = await api.get('/v1/ent/eval/runs')
    evalRuns.value = res.data?.data?.runs || []
  } catch (e: any) {
    message.error(e?.response?.data?.error || '加载运行记录失败')
  }
}

function openCreate() {
  form.value = { name: '', description: '', examples: '' }
  modalVisible.value = true
}

async function save() {
  if (!form.value.name) {
    message.warning('请输入数据集名称')
    return
  }
  saving.value = true
  try {
    let examples = []
    try {
      examples = form.value.examples ? JSON.parse(form.value.examples) : []
    } catch {
      message.warning('示例数据格式不正确，请使用 JSON 数组')
      return
    }
    await api.post('/v1/ent/eval/datasets', {
      name: form.value.name,
      description: form.value.description,
      examples,
    })
    message.success('已创建')
    modalVisible.value = false
    fetchDatasets()
  } catch (e: any) {
    message.error(e?.response?.data?.error || '保存失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete(r: EvalDataset) {
  Modal.confirm({
    title: '删除数据集',
    content: `确认删除「${r.name}」？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await api.delete(`/v1/ent/eval/datasets/${r.id}`)
        message.success('已删除')
        fetchDatasets()
      } catch (e: any) {
        message.error(e?.response?.data?.error || '删除失败')
      }
    },
  })
}

async function viewRun(r: EvalRun) {
  try {
    const res = await api.get(`/v1/ent/eval/runs/${r.id}`)
    runDetail.value = res.data?.data
    runDetailVisible.value = true
  } catch (e: any) {
    message.error(e?.response?.data?.error || '加载运行详情失败')
  }
}

async function deleteRun(r: EvalRun) {
  Modal.confirm({
    title: '删除评估运行',
    content: `确认删除「${r.dataset_name}」的运行记录？`,
    okText: '删除',
    okType: 'danger',
    onOk: async () => {
      await api.delete(`/v1/ent/eval/runs/${r.id}`)
      message.success('已删除')
      fetchRuns()
    },
  })
}

const datasetColumns: TableColumnsType = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '示例数', dataIndex: 'example_count', key: 'example_count', width: 80 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 170, customRender: ({ text }) => new Date(text).toLocaleString('zh-CN', { hour12: false }) },
  { title: '操作', key: 'action', width: 100, fixed: 'right' },
]

const runColumns: TableColumnsType = [
  { title: '数据集', dataIndex: 'dataset_name', key: 'dataset_name', width: 200 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true },
  { title: '运行时间', dataIndex: 'created_at', key: 'created_at', width: 170, customRender: ({ text }) => new Date(text).toLocaleString('zh-CN', { hour12: false }) },
  { title: '操作', key: 'action', width: 140, fixed: 'right' },
]

onMounted(() => {
  fetchDatasets()
  fetchRuns()
})
</script>

<template>
  <div class="eval-view">
    <div class="page-header">
      <h2 class="page-title">Agent 评估系统</h2>
      <a-button type="primary" @click="openCreate">新建数据集</a-button>
    </div>

    <a-alert type="info" show-icon message="管理评估数据集、查看评估运行记录和 Prompt 版本。数据集包含输入输出示例，Python 引擎定期触发离线评估。" style="margin-bottom: 16px" />

    <a-tabs v-model:activeKey="activeTab">
      <a-tab-pane key="datasets" tab="评估数据集">
        <a-table
          :columns="datasetColumns"
          :data-source="datasets"
          :loading="loading"
          :row-key="(r: EvalDataset) => r.id"
          :pagination="false"
          size="small"
        >
          <template #emptyText><div class="empty-block">暂无数据集</div></template>
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-button type="link" size="small" danger @click="confirmDelete(record as EvalDataset)">删除</a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
      <a-tab-pane key="runs" tab="评估运行">
        <a-table
          :columns="runColumns"
          :data-source="evalRuns"
          :row-key="(r: EvalRun) => r.id"
          :pagination="false"
          size="small"
        >
          <template #emptyText><div class="empty-block">暂无运行记录</div></template>
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'action'">
              <a-button type="link" size="small" @click="viewRun(record as EvalRun)">详情</a-button>
              <a-button type="link" size="small" danger @click="deleteRun(record as EvalRun)">删除</a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>

    <a-modal v-model:open="modalVisible" title="新建评估数据集" :confirm-loading="saving" width="640" @ok="save">
      <a-form layout="vertical">
        <a-form-item label="名称">
          <a-input v-model:value="form.name" placeholder="数据集名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" />
        </a-form-item>
        <a-form-item label="示例数据 (JSON 数组)">
          <a-textarea v-model:value="form.examples" :rows="6" class="code-editor" placeholder='[{"input": "hello", "expected": "Hi there!"}]' />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="runDetailVisible" title="评估运行详情" width="800" :footer="null">
      <pre v-if="runDetail" class="run-detail-json">{{ JSON.stringify(runDetail, null, 2) }}</pre>
    </a-modal>
  </div>
</template>

<style scoped>
.eval-view { padding: 0; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { margin: 0; font-size: 18px; font-weight: 600; }
:deep(.code-editor) { font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace; font-size: 12px; }
.empty-block { text-align: center; padding: 24px; color: #999; }
.run-detail-json { background: #f5f5f5; padding: 16px; border-radius: 4px; max-height: 500px; overflow: auto; font-size: 12px; white-space: pre-wrap; }
</style>