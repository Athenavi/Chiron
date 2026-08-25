# Chiron Frontend

Chiron 平台的 Vue 3 前端，提供对话、Agent、工作流、知识库、管理后台等完整 UI。

## 技术栈

- **框架:** Vue 3 (Composition API, `<script setup>`)
- **语言:** TypeScript
- **构建:** Vite 8
- **状态管理:** Pinia
- **路由:** Vue Router
- **测试:** Vitest
- **Lint:** ESLint + eslint-plugin-vue

## 目录结构

```
src/
├── api/          # API 请求封装
├── assets/       # 静态资源
├── components/   # 通用组件
│   ├── chat/     # 对话相关组件
│   ├── common/   # 通用 UI 组件
│   ├── home/     # 首页组件
│   └── memory/   # 记忆相关组件
├── composables/  # 组合式函数
├── router/       # 路由配置
├── stores/       # Pinia 状态
├── types/        # TypeScript 类型定义
├── utils/        # 工具函数
└── views/        # 页面视图
    ├── admin/    # 管理后台页面
    └── ...
```

## 开发

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 类型检查
pnpm vue-tsc --noEmit -p tsconfig.app.json

# Lint
pnpm lint

# 测试
pnpm test

# 构建
pnpm build
```

## 环境要求

- Node.js 22+
- pnpm (任意版本)
