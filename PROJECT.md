# SnapTrip —— 本地生活智能规划与执行系统

## 项目概述

本项目是面向美团 AI Hackathon 命题 1.6（本地场景短时活动规划与执行 Agent）的全栈解决方案，
同时作为个人 Agent 开发实习项目的课设扩展。

**双域定位**：
- **竞赛核心**：接受一句自然语言目标，输出可执行的完整方案并自动完成关键下单/预订动作
- **课设扩展**：在竞赛基础上扩展传统本地生活服务 Agent 化（智能推荐、评价分析、配送调度、动态定价、质量监控）

**产品闭环**：自然语言输入 → 意图解析 → POI 检索 → 时空规划 → 自动预订 → 异常自愈 → 分享通知。

**任务背景**：
小明发消息："今天下午是空的，想和老婆孩子/朋友出去玩几个小时，别离家太远，帮我安排一下。"
- 家庭场景：孩子 5 岁，老婆最近在减肥
- 朋友场景：4 个人，2 男 2 女

系统应在几分钟内完成：规划 4-6 小时综合方案 → 查餐厅/排队/位置 → 安排活动 → 一键预订下单 → 分享计划给朋友。

---

## 技术架构

### 全栈技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|----------|
| **Agent 编排** | **LangGraph** | StateGraph + PostgresSaver + interrupt 人机协同 + astream_events 流式输出 |
| **LLM 网关** | OpenRouter | 统一接入 DeepSeek-V3 / Claude-3.5-Sonnet |
| **后端** | FastAPI + Pydantic v2 + SQLAlchemy 2.0 | 异步全链路，自动 Swagger 文档 |
| **数据库** | PostgreSQL 16 + pgvector | 结构化数据 + 向量记忆统一存储 |
| **缓存/队列** | Redis 7 + Celery 5.4 | 会话缓存 + 异步任务 + Pub/Sub AgentBus |
| **前端** | React 18 + TypeScript + Tailwind + Vite | 三栏实时观测台布局 |
| **地图** | 高德 JS API 2.0 | 国内 POI + 路径动画 + SSE 实时更新 |
| **分享卡片** | Playwright HTML → 截图 PNG | 复杂布局 + 微信分享兼容 |
| **Mock 服务** | FastAPI 独立服务 | 独立进程，模拟美团本地生活 API |
| **部署** | Docker Compose | 模块化单体，3 进程部署 |
| **包管理** | uv (Python) + npm (Node) | 后端用 uv，前端用 npm |

### 架构分层（6 层）

```
用户交互层 (React)
    ↓ REST / SSE
API 网关层 (FastAPI)
    ↓
编排层 (LangGraph StateGraph)          ← 竞赛核心 + 课设扩展
    ├─ 竞赛 Agent: Intent → Context → Memory → Retrieval → Planning
    │              → Consensus → Execution → [Fallback] → Notify
    └─ 课设 Agent: Recommend | Review | Dispatch | Pricing | Quality
    ↓ Tool Call
执行层 (Tool DAG + CircuitBreaker + Saga)
    ↓ HTTP
Mock API 层 (FastAPI :8001 / 真实 API)
    ↓
数据层 (PostgreSQL + pgvector + Redis + MinIO)
```

**部署模式**：模块化单体 + 3 进程（backend :8080 / mock_server :8001 / frontend :5174），
非微服务架构。内部按目录分层（agents / services / models / api / tasks），
各模块直接 import 通信，将来拆微服务时边界清晰、抽离代价低。

---

## 竞赛核心 vs 课设扩展

| 维度 | 竞赛核心 | 课设扩展 |
|------|---------|---------|
| **Agent** | 9 个（规划执行全链路） | +5 个（业务智能） |
| **API 路由** | plan + session | +auth/user/poi/order/delivery/merchant |
| **业务服务** | plan_service + mock_gateway + memory | +user/poi/order/delivery/payment/notify |
| **ORM 模型** | user + plan + plan_slot + poi | +order/delivery/review |
| **前端页面** | PlanPage（三栏布局） | +OrdersPage/MerchantPage/LoginPage |
| **Mock Server** | 5 Router + 50 POI | 可复用 + delivery router |
| **LLM 调用** | 2 次/请求 | 3-5 次/请求 |
| **LangGraph Node** | 9 个竞赛 Agent Node | 5 个课设 Agent（独立子图） |

---

## 目录结构

项目采用 **Monorepo** 管理：

```
snaptrip/
├── Makefile
├── docker-compose.yml
├── docker-compose.override.example.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 入口 + lifespan
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic-Settings 配置中心
│   │   │   ├── logging.py             # structlog JSON 格式日志
│   │   │   ├── exceptions.py          # 业务异常体系(SnapTripError等)
│   │   │   ├── constants.py           # 枚举(PlanStatus/POIType等) + 超时
│   │   │   ├── state.py               # PlanState TypedDict (LangGraph用)
│   │   │   └── security.py            # JWT + Prompt注入防御
│   │   │
│   │   ├── api/
│   │   │   ├── deps.py                # FastAPI 依赖注入(get_db/get_redis)
│   │   │   ├── v1/
│   │   │   │   ├── plan.py            # [竞赛] Agent 入口(提交+轮询)
│   │   │   │   ├── session.py         # [竞赛] SSE 流式推送
│   │   │   │   ├── auth.py            # 认证接口
│   │   │   │   ├── user.py            # 用户画像接口
│   │   │   │   ├── poi.py             # POI 搜索接口
│   │   │   │   ├── order.py           # [课设] 订单管理接口
│   │   │   │   ├── delivery.py        # [课设] 配送追踪接口
│   │   │   │   └── merchant.py        # [课设] 商家后台接口
│   │   │   └── middleware/
│   │   │       ├── auth.py            # JWT 验证中间件
│   │   │       └── rate_limit.py      # Redis 限流中间件
│   │   │
│   │   ├── agents/
│   │   │   ├── graph.py               # LangGraph StateGraph 定义(核心)
│   │   │   ├── protocol.py            # BaseAgent ABC + AgentResult
│   │   │   ├── hub.py                 # AgentRegistry + AgentBus
│   │   │   ├── intent_parser.py       # [竞赛] 意图解析
│   │   │   ├── context_loader.py      # [竞赛] 上下文加载
│   │   │   ├── memory_manager.py      # [竞赛] 记忆管理
│   │   │   ├── retrieval_engine.py    # [竞赛] 检索引擎
│   │   │   ├── planning_engine.py     # [竞赛] 规划引擎
│   │   │   ├── consensus_resolver.py  # [竞赛] 共识解析
│   │   │   ├── execution_engine.py    # [竞赛] 执行引擎
│   │   │   ├── fallback_engine.py     # [竞赛] 容错引擎
│   │   │   ├── notify_engine.py       # [竞赛] 通知引擎
│   │   │   ├── recommend_agent.py     # [课设] 智能推荐
│   │   │   ├── review_agent.py        # [课设] 评价分析
│   │   │   ├── dispatch_agent.py      # [课设] 配送调度
│   │   │   ├── pricing_agent.py       # [课设] 动态定价
│   │   │   ├── quality_agent.py       # [课设] 质量监控
│   │   │   ├── prompts/
│   │   │   │   ├── intent.j2
│   │   │   │   ├── planning.j2
│   │   │   │   ├── recommend.j2
│   │   │   │   └── review.j2
│   │   │   └── skills/
│   │   │       ├── plan-fallback.md
│   │   │       ├── restaurant-recommend.md
│   │   │       └── time-negotiation.md
│   │   │
│   │   ├── schemas/
│   │   │   ├── plan.py                # PlanCreate/PlanResponse/PlanSlot
│   │   │   ├── checkpoint.py          # LockedSlot/TentativeSlot/ShadowSlot
│   │   │   ├── tool.py                # ToolInvocation/ToolResult/TOOL_REGISTRY
│   │   │   ├── user.py                # UserProfile/PreferenceVector
│   │   │   ├── poi.py                 # POI 实体
│   │   │   ├── order.py               # [课设] 订单 Schema
│   │   │   ├── delivery.py            # [课设] 配送 Schema
│   │   │   └── auth.py                # Token/Login Schema
│   │   │
│   │   ├── services/
│   │   │   ├── mock_gateway.py        # Mock API httpx 网关
│   │   │   ├── memory_service.py      # pgvector 记忆读写
│   │   │   ├── tool_dag.py            # Tool DAG 调度器(保留,Engine用)
│   │   │   ├── user_service.py        # 用户服务
│   │   │   ├── poi_service.py         # POI 服务
│   │   │   ├── order_service.py       # [课设] 订单服务
│   │   │   ├── delivery_service.py    # [课设] 配送服务
│   │   │   ├── payment_service.py     # [课设] 支付服务
│   │   │   └── notify_service.py      # 通知服务(短信/推送)
│   │   │
│   │   ├── models/
│   │   │   ├── base.py                # SQLAlchemy Base + TimestampMixin
│   │   │   ├── user.py                # 用户画像表(含 preference_vector)
│   │   │   ├── plan.py                # 计划主表 + 时隙子表
│   │   │   ├── poi.py                 # POI 实体表(含 embedding)
│   │   │   ├── order.py               # [课设] 订单表
│   │   │   ├── delivery.py            # [课设] 配送表
│   │   │   └── review.py              # [课设] 评价表
│   │   │
│   │   ├── db/
│   │   │   └── session.py             # AsyncSession + pgvector 注册
│   │   │
│   │   ├── tasks/
│   │   │   ├── celery_app.py          # Celery 配置
│   │   │   ├── plan_tasks.py          # 规划异步任务
│   │   │   └── notify_tasks.py        # 通知异步任务
│   │   │
│   │   └── data/
│   │       ├── seed_pois.py           # 种子 POI 数据
│   │       └── seed_users.py          # 种子用户数据
│   │
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   │   ├── test_state.py          # FSM 状态转移测试
│   │   │   ├── test_intent.py         # 意图解析测试
│   │   │   ├── test_planning.py       # 规划算法测试
│   │   │   ├── test_tool_dag.py       # Tool DAG 测试
│   │   │   ├── test_fallback.py       # 容错测试
│   │   │   └── test_services.py       # 服务层测试
│   │   ├── integration/
│   │   │   ├── test_plan_e2e.py       # 端到端规划测试
│   │   │   ├── test_sse.py            # SSE 流测试
│   │   │   └── test_auth_flow.py      # 认证流程测试
│   │   └── eval/
│   │       ├── golden_intent.json     # 意图解析 golden set
│   │       ├── golden_plan.json       # 规划质量 golden set
│   │       └── eval_runner.py         # 评估运行器
│   │
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── plan/
│   │   │   │   ├── PlanCard.tsx       # 计划卡片
│   │   │   │   ├── PlanTimeline.tsx   # 时间轴
│   │   │   │   ├── SlotDetail.tsx     # Slot 详情
│   │   │   │   └── ConfirmPanel.tsx   # confirm/object 面板
│   │   │   ├── map/
│   │   │   │   ├── MapView.tsx        # Amap 地图
│   │   │   │   ├── RouteLine.tsx      # 路线动画
│   │   │   │   └── POIMarker.tsx      # POI 标记
│   │   │   ├── agent/
│   │   │   │   ├── AgentMonitor.tsx   # Agent 思考过程
│   │   │   │   ├── ToolCallLog.tsx    # Tool 调用日志
│   │   │   │   └── PipelineNode.tsx   # 流水线节点
│   │   │   ├── order/
│   │   │   │   ├── OrderList.tsx      # [课设] 订单列表
│   │   │   │   ├── OrderDetail.tsx    # [课设] 订单详情
│   │   │   │   └── DeliveryTrack.tsx  # [课设] 配送追踪
│   │   │   ├── merchant/
│   │   │   │   ├── MerchantDashboard.tsx
│   │   │   │   └── MenuManager.tsx
│   │   │   └── common/
│   │   │       ├── InputBar.tsx
│   │   │       ├── SSEStatus.tsx
│   │   │       └── LoadingSpinner.tsx
│   │   ├── hooks/
│   │   │   ├── usePlanSSE.ts
│   │   │   ├── useAgentState.ts
│   │   │   └── useAuth.ts
│   │   ├── stores/
│   │   │   ├── planStore.ts           # Zustand: 计划状态
│   │   │   ├── agentStore.ts          # Zustand: Agent 状态
│   │   │   └── userStore.ts           # Zustand: 用户状态
│   │   ├── api/
│   │   │   ├── client.ts              # Axios 封装
│   │   │   ├── plan.ts
│   │   │   ├── auth.ts
│   │   │   └── order.ts               # [课设]
│   │   ├── types/
│   │   │   ├── plan.ts
│   │   │   ├── agent.ts
│   │   │   └── order.ts               # [课设]
│   │   └── pages/
│   │       ├── PlanPage.tsx            # [竞赛] 主页面
│   │       ├── OrdersPage.tsx          # [课设] 订单页
│   │       ├── MerchantPage.tsx        # [课设] 商家页
│   │       └── LoginPage.tsx           # 登录页
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.ts
│
├── mock_server/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── poi.py                 # GET /mock/poi/search
│   │   │   ├── queue.py               # GET /mock/queue/{poi_id}
│   │   │   ├── booking.py             # POST /mock/booking/table, /ticket
│   │   │   ├── order.py               # [课设] POST /mock/order
│   │   │   └── delivery.py            # [课设] 配送模拟
│   │   └── data/
│   │       └── seed_pois.json         # 50 条预置 POI
│   ├── Dockerfile
│   └── pyproject.toml
│
└── docs/
    ├── architecture/
    │   ├── 01-overview.md
    │   ├── 02-planning-algorithm.md
    │   ├── 03-tool-orchestration.md
    │   ├── 04-exception-handling.md
    │   └── 05-agent-architecture.md
    ├── api/
    │   └── plan.md
    ├── meetings/
    │   ├── 01-team-division.md
    │   ├── 02-dev-timeline.md
    │   └── 03-decisions-log.md
    └── skills/
        ├── plan-fallback.md
        ├── restaurant-recommend.md
        └── time-negotiation.md
```

---

## 开发规范（强制遵守）

### 1. 代码风格
- **Python**：`ruff` 格式化，`mypy --strict` 类型检查，行宽 120
- **TypeScript**：`strict: true`，显式类型，禁止 `any`
- **提交规范**：`feat: / fix: / refactor: / test: / docs:` 前缀

### 2. 接口规范
- **统一响应体**：所有 API 返回 `{code: 0, message: "success", data: T}`
- **错误码**：`400` 业务参数 / `422` 校验失败 / `500` 系统错误 / `503` Agent 超时 / `504` 熔断开启
- **流式输出**：SSE 10 种事件，LangGraph `astream_events()` 自动生成

### 3. 数据库规范
- **命名**：表名复数 `plans`, `pois`；字段蛇形 `created_at`
- **向量字段**：`pgvector` 的 `vector(1536)` 类型，命名 `embedding`
- **迁移**：Alembic `revision --autogenerate`，禁止手动改表

### 4. Agent 开发规范
- **Node 签名**：`async def node(state: PlanState) -> dict`，返回部分更新
- **Prompt 模板化**：Jinja2 模板，放在 `agents/prompts/`，禁止硬编码
- **Tool 定义**：每个 Tool 有 `name`, `dependencies`, `is_idempotent`, `timeout_ms`
- **Skill 文件**：Markdown 格式，`## 触发条件` / `## 执行步骤` / `## 示例`
- **LLM 调用**：仅 Intent Parser + Planning Phase 2 调用，其余纯代码
- **异常处理**：所有外部调用 try/except，包装为业务异常
- **结构化日志**：`logger.info("event", key=value)` 格式

---

## 数据库设计（核心表）

### `users` 用户画像表
```sql
id UUID PK
name TEXT
preference_vector VECTOR(1536)    -- pgvector, 跨会话记忆
family_profile JSONB              -- {child_age: 5, diet: "低卡", allergens: ["花生"]}
created_at TIMESTAMP
```

### `plans` 计划主表 + `plan_slots` 时隙子表（1:N）
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
                        │ shadow_poi_id   │ → pois.id (备选)
                        └─────────────────┘
```

### `pois` POI 实体表
```sql
id UUID PK
name TEXT
type VARCHAR(50)              -- restaurant / cafe / attraction / activity
lat FLOAT, lng FLOAT
city VARCHAR(20)              -- 北京 / 上海 / 重庆
mood_tags TEXT[]              -- GIN 索引: {安静, 亲子, 治愈, 热闹}
business_hours TSTZRANGE[]
avg_price INT
rating FLOAT
capacity INT
embedding VECTOR(1536)
```

### `orders` 订单表 (课设)
```sql
id UUID PK
user_id UUID FK → users.id
plan_id UUID FK → plans.id
poi_id UUID FK → pois.id
type VARCHAR(20)              -- food_delivery / table_booking / ticket / ride
status VARCHAR(20)            -- pending / confirmed / delivering / completed / cancelled
amount INT
created_at TIMESTAMP
```

### `deliveries` 配送表 (课设)
```sql
id UUID PK
order_id UUID FK → orders.id
rider_id UUID
status VARCHAR(20)            -- assigned / picking_up / in_transit / delivered
current_lat FLOAT
current_lng FLOAT
eta INT                       -- 预计到达秒数
created_at TIMESTAMP
```

### `reviews` 评价表 (课设)
```sql
id UUID PK
user_id UUID FK → users.id
poi_id UUID FK → pois.id
order_id UUID FK → orders.id
rating INT                   -- 1-5
content TEXT
sentiment VARCHAR(10)        -- positive / neutral / negative
embedding VECTOR(1536)
created_at TIMESTAMP
```

---

## 前端核心组件规范

### 三栏布局
| 栏位 | 宽度 | 内容 | 实时更新 |
|------|:---:|------|---------|
| **左栏：地图** | 40% | 用户位置 + POI 气泡 + 渐变路线动画 | Agent 每步更新 |
| **中栏：Agent 大脑** | 35% | Agent 节点状态 + Tool 调用日志（终端风格） | SSE 流式 |
| **右栏：计划卡片** | 25% | 时间轴 + 费用 + 一键确认 + 分享 | 最终确认后生成 |

### 关键交互
1. 输入区：大字输入框，支持语音/文字，下方显示解析出的约束标签（可点击修改）
2. 流式加载：点击生成后，右栏先显示骨架时间轴（2 秒内），再逐步填充详情
3. 人机协同：Consensus 节点触发 interrupt 时，右栏弹出 ConfirmPanel（confirm/object 按钮）
4. 异常演示：Mock 触发预订失败时，右栏弹出「差异对比卡片」，高亮变化项
5. 分享卡片：确认后生成手机比例的卡片，Playwright 渲染 PNG

---

## 开发阶段（9 周 × 5 天 = 45 天）

| 阶段 | 周次 | 竞赛核心 | 课设扩展 | 基础设施 |
|------|:---:|---------|---------|---------|
| W1 | 1 | — | — | config/logging/exception/security + DB + Alembic + LangGraph 图定义 |
| W2 | 2 | 9 Agent 改写为 LangGraph Node | — | Hub + ToolReg + SkillStore |
| W3 | 3 | Mock Server 5 Router + ExecutionEngine 接入 Gateway | — | Saga补偿 + CircuitBreaker |
| W4 | 4 | PlanPage 全功能 + SSE interrupt | LoginPage + Auth | JWT + 限流 |
| W5 | 5 | 测试(单元+集成+eval) | — | CI + 离线评估 runner |
| W6 | 6 | — | Recommend/Review Agent + Order/Delivery API | 前端订单页 + 商家后台 |
| W7 | 7 | — | Dispatch/Pricing/Quality Agent | 配送追踪 + 支付服务 |
| W8 | 8 | 全链路联调 | 全链路联调 | 性能优化 + 文档 |
| W9 | 9 | 提交准备 | 提交准备 | 架构文档 + 演示准备 |

---

## 协作指令

当要求 AI 基于本文档进行开发时，按以下优先级执行：

### 阶段 1：基础设施
1. 创建 `backend/app/core/config.py`（Pydantic-Settings）
2. 创建 `backend/app/core/logging.py`（structlog JSON）
3. 创建 `backend/app/core/exceptions.py`（业务异常体系）
4. 创建 `backend/app/core/security.py`（JWT + Prompt 注入防御）
5. 创建 ORM 模型 + `db/session.py`（AsyncSession + pgvector）
6. 初始化 Alembic 并生成首版迁移（users, plans, plan_slots, pois）

### 阶段 2：LangGraph 图 + Agent 重构
1. 创建 `backend/app/agents/graph.py`（StateGraph 定义 + conditional_edges）
2. 9 个竞赛 Agent 改写为 Node 函数（签名 `state → dict`）
3. 创建 AgentRegistry + AgentBus
4. 接入 PostgresSaver

### 阶段 3：Mock 服务 + 执行层
1. 完善 Mock Server 5 个 Router + 50 条 seed POI
2. ExecutionEngine 接入 MockAPIGateway（移除本地 mock）
3. 实现 CircuitBreaker + Saga Compensate

### 阶段 4：前端 + SSE
1. 前端计划三栏布局 + SSE 10 种事件渲染
2. 实现 ConfirmPanel（interrupt 人机协同）
3. JWT 认证 + 限流中间件

### 阶段 5：测试 + 评估
1. 单元测试（状态机、意图解析、规划算法、Tool DAG）
2. 集成测试（端到端规划链路、SSE 流）
3. 离线评估（golden_intent.json + golden_plan.json）

### 阶段 6：课设扩展
1. 5 个课设 Agent 实现
2. 订单/配送/支付/商家后台 API + 前端页面
3. 课设文档

### 代码生成原则
- **先 Schema 后实现**：所有函数必须先有 Pydantic / TypeScript 类型定义
- **禁止硬编码**：配置走 config.py，Prompt 走模板文件，数据走 seed 文件
- **异步优先**：数据库、HTTP 调用全部使用 async/await
- **错误处理**：所有外部调用必须 try/except，包装为业务异常
- **结构化日志**：`logger.info("event", key=value)` 格式
