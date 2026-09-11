<script setup lang="ts">
import AdminTabbedView from '@/components/admin/AdminTabbedView.vue'
import RedisManagementView from './RedisManagementView.vue'
import DatabaseManagementView from './DatabaseManagementView.vue'

// 数据存储：Redis（Keyspace/慢日志/flush）+ 数据库（状态/查询/备份恢复/优化）
const tabs = [
  { key: 'redis', label: 'Redis', comp: RedisManagementView },
  { key: 'database', label: '数据库', comp: DatabaseManagementView },
]
</script>

<template>
  <AdminTabbedView
    route-path="/admin/datastores"
    default-tab="redis"
    :tabs="tabs"
  />
</template>
