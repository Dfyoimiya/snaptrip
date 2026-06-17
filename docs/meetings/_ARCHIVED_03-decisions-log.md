# 03 —— 架构决策记录 (ADR)

本文件记录所有关键技术决策及其理由，供后续开发追溯。

格式：`ADR-xxx` + 日期 + 状态 + 决策 + 替代方案 + 影响

---

## ADR-001：Agent 框架选型

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：使用 Hermes Agent（NousResearch）开源框架，通过 ACP/HTTP 协议调用
- **理由**：Hermes 支持 Skill 自进化机制，符合项目长期演进需求；ACP 协议标准化，Agent 间解耦
- **替代方案**：自建轻量 Hub（无 Skill 自进化，但实现简单）
- **降级策略**：若 Hermes 集成复杂度超预期（>Day 4），先自建 Hub 完成核心流程，Hermes 作为扩展项
- **影响**：`backend/app/agents/` 下所有 Agent 实现需遵循 ACP 协议

---

## ADR-002：地图服务选型

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：使用高德 JS API 2.0
- **理由**：国内 POI 数据最丰富；支持路径规划动画；有免费开发配额
- **替代方案**：Mapbox GL JS（国际化好但国内数据弱）/ Leaflet + OSM（免费但无路径动画）
- **降级策略**：若高德 Key 未就绪，前端 MapView 支持 Leaflet 降级模式（静态标记，无动画）
- **影响**：`frontend/src/components/MapView.tsx`

---

## ADR-003：语音输入方案

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：Phase 1-6 使用 Web Speech API（浏览器原生），预留第三方扩展接口
- **理由**：Web Speech API 零依赖、零成本；Chrome 支持良好；Hackathon 演示够用
- **未来扩展**：讯飞 / 百度语音 SDK 通过抽象接口接入
- **影响**：`frontend/src/components/InputBar.tsx`

---

## ADR-004：POI 种子数据城市

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：预设 POI 覆盖 3 个城市：重庆、上海、北京
- **分布**：每个城市约 16-17 个 POI，涵盖餐饮/景点/活动/咖啡馆
- **理由**：多城市验证跨区域规划能力；三城风格差异大（重庆山地/上海都市/北京历史），丰富演示效果
- **影响**：`mock_server/app/data/seed_pois.json`

---

## ADR-005：用户认证方案

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：JWT + OAuth 2.0（Google / 微信），使用 FastAPI-Users 库
- **理由**：JWT 无状态，适合 Docker 部署；微信 OAuth 是目标准入，Google OAuth 是通用备选
- **实现节奏**：Phase 2 先 mock user（通过 header `X-User-Id`），Phase 5-6 接入真实 OAuth
- **影响**：`backend/app/api/deps.py`（get_current_user）、`backend/app/models/user.py`

---

## ADR-006：Embedding 模型

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：使用 OpenAI text-embedding-3-small（1536 维）
- **理由**：PROJECT.md 定义 `vector(1536)` 与此模型匹配；通过 OpenRouter 统一调用，不依赖 OpenAI 直接 API
- **注意事项**：需要 `OPENROUTER_API_KEY` 配置，embedding 请求也走 OpenRouter
- **影响**：`backend/app/services/memory_service.py`、`backend/app/models/user.py`、`backend/app/models/poi.py`

---

## ADR-007：异步任务队列

- **日期**：2026-05-03
- **状态**：分阶段
- **Phase 4 决策**：使用 `asyncio.create_task` 处理后台任务（PDF 解析、Embedding 生成）
- **Phase 6 决策**：替换为 Celery + Redis 正式方案
- **理由**：Phase 4 聚焦核心链路，减少基础设施复杂度；Phase 6 引入 Celery 获得重试、监控、持久化能力
- **降级策略**：若 Celery 集成不顺，可保留 asyncio 方案并将任务状态写入 Redis
- **影响**：`backend/app/tasks/plan_tasks.py`

---

## ADR-008：前端路线动画

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：使用高德 JS API 2.0 的路线规划和动画能力
- **实现**：每个 SSE `execution_done` 事件触发地图更新，绘制用户位置到下一个 POI 的渐变路线
- **降级策略**：Leaflet 模式下使用静态折线 + CSS 流动动画模拟
- **影响**：`frontend/src/components/MapView.tsx`

---

## ADR-009：分享卡片生成

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：服务端生成图片，使用 Playwright 渲染 HTML → 截图 PNG
- **理由**：Playwright 支持复杂布局（与前端一致的 CSS）；生成的图片便于微信分享
- **替代方案**：Pillow 直接绘图（简单但布局能力弱）/ 前端 html2canvas 截图（依赖客户端环境）
- **降级策略**：若 Playwright 集成困难，先用 Jinja2 渲染纯文本摘要
- **影响**：`backend/app/agents/notify_agent.py`、`backend/app/tasks/card_render.py`

---

## ADR-010：数据库表设计

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：`plans` 与 `plan_slots` 为 1:N 关系

```
┌─────────────┐         ┌─────────────────┐
│   plans     │ 1    N  │   plan_slots    │
├─────────────┤◄────────┼─────────────────┤
│ id (PK)     │         │ id (PK)         │
│ user_id     │         │ plan_id (FK)    │ → plans.id
│ status      │         │ poi_id (FK)     │ → pois.id
│ query_text  │         │ time_range      │
│ total_cost  │         │ action          │
│ created_at  │         │ booking_status  │
└─────────────┘         │ estimated_cost  │
                        │ sequence        │
                        └─────────────────┘
```

- **理由**：分离计划级和时隙级数据；`plans` 存聚合信息，`plan_slots` 存单步细节；符合第三范式
- **原设计问题**：PROJECT.md 中 `plans` 表自引用 `plan_id FK`，字段混乱
- **影响**：`backend/app/models/plan.py`、`backend/app/schemas/plan.py`、Alembic 迁移

---

## ADR-011：SSE 连接管理

- **日期**：2026-05-03
- **状态**：已确认
- **决策**：使用 Redis Pub/Sub 作为 SSE 事件总线
- **理由**：SSE 路由与 Agent 执行在不同协程/进程，需要消息中间件解耦；Redis 已在项目中使用
- **流程**：Agent 执行 → `redis.publish(f"plan:{plan_id}", event)` → SSE 路由订阅并转发
- **降级策略**：单进程模式下使用 `asyncio.Queue` 直接转发
- **影响**：`backend/app/api/v1/session.py`
