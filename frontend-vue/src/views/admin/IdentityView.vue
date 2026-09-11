<script setup lang="ts">
import AdminTabbedView from '@/components/admin/AdminTabbedView.vue'
import OAuthProvidersView from './OAuthProvidersView.vue'
import PrivacyView from './PrivacyView.vue'

// 认证与防护：三方登录与人机验证 + 隐私模式管控（同属"准入与合规"配置域）
const tabs = [
  { key: 'oauth', label: '三方登录与人机验证', comp: OAuthProvidersView },
  { key: 'privacy', label: '隐私模式管控', comp: PrivacyView },
]
</script>

<template>
  <AdminTabbedView
    route-path="/admin/identity"
    default-tab="oauth"
    :tabs="tabs"
  />
</template>
