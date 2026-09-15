<script setup lang="ts">
/**
 * 语言切换器。
 *
 * 显示各语言的**母语名**（简体中文 / English / العربية）而不是当前界面语言的译名 ——
 * 用户在看不懂当前界面语言时，仍能找到自己的语言。
 *
 * 切换动作由 setLocale() 统一处理：写 localStorage、更新 <html lang/dir>、
 * 同步 dayjs；antd 组件库语言经 App.vue 的 ConfigProvider 自动跟随。
 */
import { useI18n } from 'vue-i18n'
import { LANGUAGES } from '../../i18n/languages'
import { setLocale } from '../../i18n'

const { t, locale } = useI18n()

const options = LANGUAGES.map(l => ({ value: l.code, label: l.nativeName }))

function onChange(value: unknown): void {
  setLocale(String(value))
}
</script>

<template>
  <a-select
    :value="locale"
    :options="options"
    :aria-label="t('common.language')"
    size="small"
    class="language-switcher"
    @change="onChange"
  />
</template>

<style scoped>
/* 逻辑属性：min-inline-size 在 RTL 下同样按"行内方向"生效，避免物理宽度假设 */
.language-switcher {
  min-inline-size: 7.5rem;
}
</style>
