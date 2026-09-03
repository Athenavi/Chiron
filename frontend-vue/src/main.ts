import { createApp } from 'vue'
import { createPinia } from 'pinia'
// antd 已按需引入（unplugin-vue-components），无需全局 app.use(Antd)
import 'ant-design-vue/dist/reset.css'
import '@fontsource-variable/geist'
import router from './router'
import App from './App.vue'
import './style.css'
import { usePerformanceMonitor } from './composables/usePerformanceMonitor'

const app = createApp(App)

// 标记应用启动
performance.mark('app-init-start')

// 初始化性能监控
const { initMonitor, mark, measure } = usePerformanceMonitor()
initMonitor()

// 全局暴露性能数据 (仅开发环境，供 DevTools 调试)
if (import.meta.env.DEV) {
  window.__ChironPerf = { mark, measure, getReport: () => usePerformanceMonitor().getReport() }
}

const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')

// 标记首次渲染完成
performance.mark('vue-first-render')
performance.mark('app-init-end')

// Lighthouse 性能评分优化标记
if (import.meta.env.PROD) {
  performance.measure('app-init-duration', 'app-init-start', 'app-init-end')
}

// PWA：生产环境注册 Service Worker（离线壳；开发环境跳过）
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
