# C 端布局重构计划 — 参考淘宝 Mac 桌面端设计

## 背景

淘宝于 2025 年 4-5 月先后推出了 Windows 和 macOS 桌面版客户端（基于 Electron），主打 **大屏购物体验** 和 **AI 导购深度集成**。其核心 UI 模式值得参考：

- 左侧持久化图标导航栏（类桌面应用）
- 浏览器风格多标签页浏览
- 右侧可折叠对比托盘 + 浏览历史
- AI 导购作为主内容区独立页面（非浮动面板）
- 响应式自适应网格（1024px–2560px）
- Pinterest 风格"发现好物"信息流
- 沉浸式全屏商品图片浏览

## 当前布局 vs 目标布局

```
当前（顶部导航中心）                      目标（桌面应用三栏）
┌────────────────────────┐           ┌────┬──────────────────────┬────┐
│ TopBar                 │           │    │  [Tab1][Tab2][Tab3]  │    │
├────────────────────────┤           │    ├──────────────────────┤    │
│ HeaderSearch + TabBar  │           │    │                      │    │
├────────────────────────┤           │ 左 │    Main Content      │ 右 │
│ Nav (顶部导航)          │           │ 侧 │    (产品/搜索/       │ 侧 │
├────────────────────────┤           │ 边 │     AI导购/对比)     │ 边 │
│ Main (max-w-1240px)    │           │    │                      │    │
├────────────────────────┤           │    │                      │    │
│ Footer                 │           │    │                      │    │
└────────────────────────┘           └────┴──────────────────────┴────┘

居中布局，顶部操作繁重              充分利用宽屏，信息密度更高
```

## 分阶段实施

### Phase 1: 核心布局重构

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 1.1 | **LeftSidebar 组件** | `components/layout/LeftSidebar.vue` | 图标+文字导航，~64px(收起)/~200px(展开)，hover 展开/锁定，底部用户入口 |
| 1.2 | **AppLayout 重写** | `components/layout/AppLayout.vue` | CSS Grid 三栏 `grid-template-columns: auto 1fr auto`，移除顶部多层结构 |
| 1.3 | **RightSidebar 组件** | `components/layout/RightSidebar.vue` | 浏览历史 + 商品对比托盘，可折叠，缩略图列表 |
| 1.4 | **TabBar 增强** | `components/layout/TabBar.vue` | 溢出左右滚动箭头、固定标签、图标显示 |
| 1.5 | **Layout Store** | `stores/layout.ts` | 管理侧栏展开/折叠、右侧栏状态、对比托盘数据 |

### Phase 2: 功能迁移

| # | 任务 | 说明 |
|---|------|------|
| 2.1 | **搜索入口迁移** | 从 HeaderSearch 移至左侧栏（图标模式收起，展开模式搜索栏） |
| 2.2 | **导航项迁移** | 首页/全部商品/品牌/新品/热门/帮我挑 → 左侧图标导航 |
| 2.3 | **用户入口整合** | 登录/注册/购物车/会员中心 → 左侧栏底部用户区 |
| 2.4 | **TopBar 废弃** | TopBar 功能移入左侧栏，组件保留或移除 |
| 2.5 | **Footer 精简** | 缩小高度，仅保留关键链接 |

### Phase 3: AI 导购 & 对比

| # | 任务 | 文件 | 说明 |
|---|------|------|------|
| 3.1 | **AI 面板嵌入主区域** | `ShoppingGuideView.vue` 改造 | 从浮动面板 → 主内容区独立页，支持分屏：产品左 + AI 右 |
| 3.2 | **商品对比** | `ProductCompare.vue` *新建* | 横向对比表 3-5 列，AI 总结建议 |
| 3.3 | **发现好物** | `DiscoveryView.vue` *新建* | Pinterest 瀑布流，AI 主题卡片，路由 `/discover` |

### Phase 4: 大屏适配

| # | 任务 | 说明 |
|---|------|------|
| 4.1 | **响应式网格** | `max-w-1240px` → 自适应 `minmax(0, 1fr)`，支持 1024px–2560px |
| 4.2 | **沉浸式图片浏览** | 商品大图全屏 overlay（Teleport），缩放+轮播 |
| 4.3 | **窄屏降级** | <1024px 回退移动端竖版布局（顶部导航 + 抽屉菜单） |

## 技术方案

| 层 | 方案 |
|----|------|
| **布局** | CSS Grid 三列，左侧 `sticky top-0 h-screen overflow-y-auto`，主区域 `overflow-y: auto`，右侧 `sticky top-0` 可折叠 |
| **状态** | 新建 `layoutStore` (Pinia)，管理侧栏状态、对比托盘；复用 `tabStore`、`shoppingGuideStore` |
| **样式** | 纯 Tailwind CSS，不引入第三方 UI 库 |
| **兼容** | 不改变现有 Pinia stores 接口；路由结构尽量保持；现有页面组件内部不改动 |

## 涉及文件清单

```
mall-web/src/
├── App.vue                              # 修改：新布局结构
├── components/layout/
│   ├── AppLayout.vue                    # ★ 重写：三栏 Grid
│   ├── LeftSidebar.vue                  # ★ 新建
│   ├── RightSidebar.vue                 # ★ 新建
│   ├── TabBar.vue                       # 增强
│   ├── HeaderSearch.vue                 # 改造：融入侧栏
│   ├── TopBar.vue                       # 可能废弃
├── components/product/
│   ├── ProductCompare.vue               # ★ 新建
├── views/
│   ├── ShoppingGuideView.vue            # 改造：分屏布局
│   ├── DiscoveryView.vue                # ★ 新建
├── stores/
│   ├── layout.ts                        # ★ 新建
├── router/index.ts                      # 添加 /discover 路由
```

## 执行策略

4 个 sub-agent 并行推进 Phase 1-3：

| Agent | 职责 |
|-------|------|
| **Agent 1** — 核心布局 | LeftSidebar + AppLayout 重写 + layout store |
| **Agent 2** — 右侧面板 | RightSidebar + ProductCompare |
| **Agent 3** — AI & 发现 | ShoppingGuideView 改造 + DiscoveryView 新建 |
| **Agent 4** — 组件适配 | TabBar 增强 + HeaderSearch 改造 + TopBar 处理 |

Phase 4（大屏适配）在前三阶段完成后单独推进。
