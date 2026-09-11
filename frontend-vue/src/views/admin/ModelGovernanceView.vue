<script setup lang="ts">
import AdminTabbedView from '@/components/admin/AdminTabbedView.vue'
import ModelPolicyView from './ModelPolicyView.vue'
import ModelRouterView from './ModelRouterView.vue'

// 模型管控：策略（可用模型/额度约束）+ 路由（provider 路由规则）
const tabs = [
  { key: 'policy', label: '模型策略', comp: ModelPolicyView },
  { key: 'routing', label: '模型路由', comp: ModelRouterView },
]
</script>

<template>
  <AdminTabbedView
    route-path="/admin/models"
    default-tab="policy"
    :tabs="tabs"
  />
</template>
