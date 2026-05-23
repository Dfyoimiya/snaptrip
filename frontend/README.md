# SnapTrip Frontend

React 19 + TypeScript + Tailwind CSS v4 + Vite

## 技术栈

| 层级 | 技术 |
|------|------|
| 框架 | React 19 |
| 语言 | TypeScript 6 |
| 样式 | Tailwind CSS v4 |
| 构建 | Vite 8 |
| 状态管理 | Zustand |
| HTTP | Axios |
| 测试 | Vitest + Testing Library |

## 开发

```bash
npm install       # 安装依赖
npm run dev       # 启动开发服务器 (:5174)
npm run build     # 生产构建
npm run lint      # ESLint 检查
npm run test      # 运行测试
npm run test:watch # 测试监视模式
```

## 项目结构

```
src/
├── api/           # API 客户端
├── components/    # UI 组件
│   ├── agent/     # Agent 监控面板
│   ├── common/    # 通用组件
│   ├── map/       # 地图组件
│   └── plan/      # 计划相关组件
├── hooks/         # 自定义 Hooks (SSE 等)
├── pages/         # 页面组件
├── stores/        # Zustand 状态管理
├── types/         # TypeScript 类型定义
└── test/          # 测试文件
```

## 三栏布局

| 栏位 | 宽度 | 内容 |
|------|:---:|------|
| 左栏：地图 | 40% | POI 标记 + 路线动画 |
| 中栏：Agent | 35% | Agent 思考过程 (SSE 实时) |
| 右栏：计划 | 25% | 时间轴 + 确认面板 |
