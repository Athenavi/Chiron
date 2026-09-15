<script setup lang="ts">
import AdminTabbedView from '@/components/admin/AdminTabbedView.vue'
import RolesView from './RolesView.vue'
import GroupsView from './GroupsView.vue'

import { useI18n } from 'vue-i18n'
const { t } = useI18n()
// 权限与组织：角色 + 群组（同为 admin 权限域、同为 CRUD 型页面）
const tabs = [
  { key: 'roles', label: t('角色'), comp: RolesView },
  { key: 'groups', label: t('群组'), comp: GroupsView },
]
</script>

<template>
  <AdminTabbedView
    route-path="/admin/access"
    default-tab="roles"
    :tabs="tabs"
  />
</template>
