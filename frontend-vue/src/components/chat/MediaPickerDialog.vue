<script setup lang="ts">
/**
 * 从媒体库选择文件 —— agent/对话侧的媒体库联动入口。
 *
 * 数据源：GET /v1/media（与「媒体库」页面同一份 media_assets 数据）。
 * 选中后换取短时效签名 URL，并转换为 ChatAttachment 交给输入框发送。
 */
import { ref, computed, watch } from 'vue'
import { Modal, Input, Select, Table, Empty, Spin, message } from 'ant-design-vue'
import { api, resolveMediaUrl } from '../../api'
import { formatSize } from './chat-types'
import type { ChatAttachment } from './chat-types'

import { useI18n } from 'vue-i18n'
const { t } = useI18n()

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'select', attachments: ChatAttachment[]): void
}>()

interface MediaRow {
  id: string
  name: string
  type: string
  size: number
  mime_type: string
  file_url: string
}

const loading = ref(false)
const submitting = ref(false)
const rows = ref<MediaRow[]>([])
const keyword = ref('')
const typeFilter = ref<string | undefined>(undefined)
const selectedIds = ref<string[]>([])

const typeOptions = computed(() => [
  { value: 'image', label: t('图片') },
  { value: 'video', label: t('视频') },
  { value: 'audio', label: t('音频') },
  { value: 'document', label: t('文档') },
  { value: 'file', label: t('文件') },
])

const columns = computed(() => [
  { title: t('名称'), dataIndex: 'name', ellipsis: true },
  { title: t('类型'), dataIndex: 'type', width: 90 },
  {
    title: t('大小'),
    dataIndex: 'size',
    width: 110,
    customRender: ({ text }: { text: number }) => formatSize(text),
  },
])

const rowSelection = computed(() => ({
  selectedRowKeys: selectedIds.value,
  onChange: (keys: (string | number)[]) => {
    selectedIds.value = keys.map(String)
  },
}))

async function fetchRows() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: 1, page_size: 200 }
    if (keyword.value.trim()) params.search = keyword.value.trim()
    if (typeFilter.value) params.type = typeFilter.value
    const res = await api.get('/v1/media', { params })
    rows.value = (res.data?.data?.items || []) as MediaRow[]
  } catch {
    message.error(t('加载媒体库失败'))
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function handleOk() {
  const picked = rows.value.filter(r => selectedIds.value.includes(r.id))
  if (!picked.length) {
    emit('update:open', false)
    return
  }
  submitting.value = true
  try {
    const attachments: ChatAttachment[] = []
    for (const r of picked) {
      // 私有对象需换取短时效签名 URL；解析失败时回退原 file_url
      let url = r.file_url
      try {
        const signed = await resolveMediaUrl({ id: r.id, file_url: r.file_url })
        if (signed) url = signed
      } catch {
        // 静默：保留原 URL
      }
      const mime = r.mime_type || ''
      attachments.push({
        id: r.id,
        name: r.name,
        size: r.size || 0,
        mimeType: mime,
        url,
        isImage: mime.startsWith('image/') || r.type === 'image',
        isAudio: mime.startsWith('audio/') || r.type === 'audio',
      })
    }
    emit('select', attachments)
    emit('update:open', false)
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.open,
  v => {
    if (v) {
      selectedIds.value = []
      keyword.value = ''
      typeFilter.value = undefined
      void fetchRows()
    }
  },
)
</script>

<template>
  <Modal
    :open="props.open"
    :title="$t('从媒体库选取')"
    :width="720"
    :confirm-loading="submitting"
    :ok-text="$t('确定')"
    :cancel-text="$t('取消')"
    @ok="handleOk"
    @cancel="emit('update:open', false)"
  >
    <div class="picker-toolbar">
      <Input.Search
        v-model:value="keyword"
        :placeholder="$t('搜索文件名')"
        allow-clear
        @search="fetchRows"
      />
      <Select
        v-model:value="typeFilter"
        :options="typeOptions"
        :placeholder="$t('全部类型')"
        allow-clear
        style="width: 140px"
        @change="fetchRows"
      />
    </div>
    <Spin :spinning="loading">
      <Table
        row-key="id"
        size="small"
        :columns="columns"
        :data-source="rows"
        :row-selection="rowSelection"
        :pagination="{ pageSize: 8, size: 'small' }"
        :scroll="{ y: 320 }"
      >
        <template #emptyText>
          <Empty :description="$t('暂无数据')" />
        </template>
      </Table>
    </Spin>
  </Modal>
</template>

<style scoped>
.picker-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>
