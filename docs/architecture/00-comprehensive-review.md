# SnapTrip 全架构审核报告

> 日期: 2026-05-22 | 审核人: 系统架构师 | 范围: 全栈 Monorepo

---

## 一、当前项目结构 vs 目标结构

### 1.1 当前实际结构

```
snaptrip/
├── Makefile
├── docker-compose.yml                    # 7 服务编排
├── docker-compose.override.example.yml
├── docker-compose.test.yml               # 测试 DB 独立编排
├── .env.example
├── PROJECT.md                            # 项目规约
├── AGENTS.md                             # AI 协作指令
├── .pre-commit-config.yaml
├── .gitguardian.yml
├── .github/workflows/ci.yml
│
├── backend/                              # ⚠️ 巨石后端 — 包含 3 个子包
│   ├── pyproject.toml                    # snaptrip-backend (单包，非 workspace)
│   ├── uv.lock
│   ├── Dockerfile / Dockerfile.gateway / Dockerfile.worker
│   ├── alembic.ini
│   │
│   ├── marketplace/app/                  # API 网关 + 业务逻辑
│   │   ├── main.py                       # FastAPI 入口
│   │   ├── celery_app.py
│   │   ├── adapters/amap/               # 高德地图适配器
│   │   ├── api/v1/                      # REST 路由 (plan/auth/user)
│   │   ├── models/                      # ORM 模型 (9 表)
│   │   ├── schemas/                     # Pydantic Schema
│   │   └── services/                    # 业务服务
│   │
│   ├── agent_worker/app/agent/          # Agent 核心引擎
│   │   ├── graph.py                     # LangGraph 编排
│   │   ├── runtime.py                   # AgentRuntime DI 容器
│   │   ├── engines/                     # 9 个 Agent 节点
│   │   ├── adapters/                    # LLM/Marketplace/Mock 网关
│   │   ├── ports/                       # 抽象接口
│   │   ├── schemas/                     # Agent Schema
│   │   ├── state/                       # 状态构建器
│   │   ├── events/                      # 事件总线
│   │   ├── providers/                   # LLM Provider 注册
│   │   ├── prompts/                     # Jinja2 模板
│   │   └── skills/                      # Skill 定义
│   │
│   ├── shared/                          # 共享库
│   │   ├── core/                        # config/logging/exceptions/security
│   │   ├── db/                          # session/redis
│   │   └── schemas/                     # 共享 Schema
│   │
│   ├── tests/                           # 测试 (unit/integration/contract/eval)
│   ├── alembic/ + migrations/           # ⚠️ 两套迁移目录并存
│   └── scripts/
│
├── frontend/                            # ✅ 结构合理
│   ├── package.json / vite.config.ts
│   ├── src/
│   │   ├── components/{agent,common,map,plan}/
│   │   ├── hooks/usePlanSSE.ts
│   │   ├── stores/{agentStore,planStore}.ts
│   │   ├── pages/PlanPage.tsx
│   │   └── types/{agent,plan}.ts
│   └── Dockerfile
│
├── mock_server/                         # Mock 服务
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/{delivery,order,poi,queue,route,weather}.py
│   │   └── schemas.py
│   └── data/seed_pois.json
│
└── docs/
    ├── architecture/                    # 6 架构文档 + 1 结构审查
    ├── api/plan.md
    ├── meetings/                        # 3 会议记录
    └── skills/                          # 3 Skill 副本 (与 agent 中重复)
```

### 1.2 目标 Monorepo 结构

```
snaptrip/
├── pyproject.toml                       # 根: Uv workspace 定义
├── uv.lock                              # 全仓库统一锁文件
├── Makefile                             # 统一命令入口
├── taskfile.yml                         # (可选) Task 任务运行器
├── docker-compose.yml                   # 5+ 进程编排
├── .env.example
├── .pre-commit-config.yaml
│
├── frontend/                            # 进程1: 前端 (独立，不参与 Python workspace)
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── backend/                             # 进程2: Marketplace API 网关
│   ├── pyproject.toml                   # [tool.uv.sources] 引用 shared
│   ├── src/backend/
│   │   ├── main.py                      # FastAPI 入口
│   │   ├── api/v1/                      # REST 路由
│   │   ├── models/                      # ORM 模型
│   │   ├── schemas/                     # Pydantic Schema
│   │   ├── services/                    # 业务服务
│   │   └── adapters/amap/              # 高德适配器
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
│
├── agent/                               # 进程3: Agent 核心引擎
│   ├── pyproject.toml                   # [tool.uv.sources] 引用 shared
│   ├── src/agent/
│   │   ├── core/                        # graph.py, runtime.py
│   │   ├── engines/                     # 9 个 Agent 节点
│   │   ├── adapters/                    # LLM, Marketplace, Mock 网关
│   │   ├── ports/                       # 抽象接口
│   │   ├── schemas/                     # Agent 专用 Schema
│   │   ├── state/                       # 状态构建器
│   │   ├── events/                      # 事件系统
│   │   ├── providers/                   # LLM Provider
│   │   ├── prompts/                     # Jinja2 模板
│   │   ├── skills/                      # Skill 定义
│   │   └── persistence/                 # Checkpoint/Plan Run/Event
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
│
├── shared/                              # 共享库 (被 backend/agent/mock 引用)
│   ├── pyproject.toml                   # name = "snaptrip-shared"
│   └── src/snaptrip_shared/
│       ├── core/                        # config, logging, exceptions, security
│       ├── db/                          # session, redis
│       └── schemas/                     # 跨包共享 Schema
│
├── mock-services/                       # 模拟第三方服务
│   ├── mock-meituan/                    # 模拟美团 API
│   │   ├── pyproject.toml
│   │   ├── src/mock_meituan/
│   │   └── Dockerfile
│   └── mock-amap/                       # 模拟高德 API (可选)
│       ├── pyproject.toml
│       └── Dockerfile
│
├── infra/                               # 基础设施配置
│   ├── nginx/
│   ├── postgres/init.sql
│   └── redis/
│
├── alembic/                             # 统一数据库迁移
│   ├── env.py
│   └── versions/
│
└── docs/
    ├── architecture/
    ├── api/
    └── decisions/                       # ADR (替代 meetings/)
```

---

## 二、系统架构图

### 2.1 部署拓扑 (6 进程)

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Docker Network: snaptrip                       │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐                  │
│  │  frontend   │  │ marketplace  │  │ agent-worker │                  │
│  │  (Vite)     │  │ (FastAPI)    │  │ (Celery)     │                  │
│  │  :5173      │  │ :8000        │  │              │                  │
│  │             │  │              │  │ LangGraph     │                  │
│  │  React 18   │  │ JWT Auth     │  │ 9-Node Graph │                  │
│  │  TypeScript │  │ Rate Limit   │  │ + Celery Q   │                  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                │                 │                          │
│         │ REST/SSE       │                 │                          │
│         └────────┬───────┘                 │                          │
│                  │                         │                          │
│                  │  HTTP (Celery dispatch)  │                          │
│                  ├─────────────────────────┤                          │
│                  │                         │                          │
│         ┌────────┴────────┐    ┌───────────┴────────┐                 │
│         │    postgres     │    │       redis        │                 │
│         │  (pgvector:16)  │    │     (7-alpine)     │                 │
│         │  :5432          │    │  :6379             │                 │
│         │                 │    │                    │                 │
│         │  Plans/Users/   │    │  Celery Broker     │                 │
│         │  POIs/Orders    │    │  SSE Pub/Sub       │                 │
│         │  + LangGraph    │    │  Session Cache     │                 │
│         │  Checkpoint     │    │  Rate Limit        │                 │
│         └─────────────────┘    └────────────────────┘                 │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐                                  │
│  │  mock-server │  │ agent-beat   │                                  │
│  │  (FastAPI)   │  │ (Celery Beat)│                                  │
│  │  :8001       │  │              │                                  │
│  │              │  │ 定时清理      │                                  │
│  │  POI/Queue/  │  │ 孤儿资源      │                                  │
│  │  Booking/    │  └──────────────┘                                  │
│  │  Delivery    │                                                     │
│  └──────────────┘                                                     │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 逻辑分层 (6 层)

```
┌──────────────────────────────────────────────────────────────────┐
│  L6 前端层    │ React 18 + Vite + Tailwind + Amap JS 2.0         │
│              │ 三栏布局: Map(40%) | Agent Monitor(35%) | Plan(25%)│
├──────────────────────────────────────────────────────────────────┤
│  L5 API网关   │ FastAPI :8000                                    │
│              │ JWT Auth | Rate Limiter | CORS | SSE Streaming    │
├──────────────────────────────────────────────────────────────────┤
│  L4 编排层    │ LangGraph StateGraph                             │
│              │ Intent → Context → Memory → Retrieval → Planning  │
│              │ → Consensus → Execution → [Fallback] → Notify     │
│              │ PostgresSaver (持久化) | interrupt() (人机协同)    │
├──────────────────────────────────────────────────────────────────┤
│  L3 引擎层    │ 9 Engine Services                                │
│              │ IntentParser | ContextLoader | MemoryManager      │
│              │ RetrievalEngine | PlanningEngine | ConsensusResolver│
│              │ ExecutionEngine | FallbackEngine | NotifyEngine   │
├──────────────────────────────────────────────────────────────────┤
│  L2 执行层    │ Tool DAG + CircuitBreaker + Saga Compensate      │
│              │ L0: search_poi, get_profile                       │
│              │ L1: check_queue, check_availability, calc_route   │
│              │ L2: book_table, book_ticket, order, ride_hail     │
│              │ L3: notify                                        │
├──────────────────────────────────────────────────────────────────┤
│  L1 数据层    │ PostgreSQL 16 (pgvector) + Redis 7 + MinIO       │
│              │ pgvector: 用户向量记忆, POI embedding             │
│              │ Redis: Celery Broker + SSE Pub/Sub + Cache        │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 Agent 调度架构 (LangGraph)

```
                        ┌─────────┐
                        │  START  │
                        └────┬────┘
                             │
                        ┌────▼────┐
                        │ intent  │ LLM 调用 #1 (DeepSeek-V3 via OpenRouter)
                        │ parser  │ 输出: IntentSchema (who/where/when/what/pref)
                        └────┬────┘
                             │
                        ┌────▼────┐
                        │ context │ DB 查询 user_profile + preference_vector
                        │ loader  │
                        └────┬────┘
                             │
                        ┌────▼────┐
                        │ memory  │ pgvector 相似度检索历史偏好
                        │ manager │ 输出: MemoryFeatures
                        └────┬────┘
                             │
                        ┌────▼────┐
                        │retrieval│ haversine 过滤 + pgvector 语义搜索
                        │ engine  │ 输出: CandidatePool (top-N POI per slot)
                        └────┬────┘
                             │
                        ┌────▼────┐
                        │planning │ Phase 1: 硬约束过滤 (纯代码)
                        │ engine  │ Phase 2: 软约束排序 (LLM #2)
                        └────┬────┘
                             │
                        ┌────▼────┐
                        │consensus│ interrupt() → 人机确认
                        │resolver │ ◄── POST /confirm (resume graph)
                        └───┬─┬───┘
                   confirmed │ │ objection/timeout
                             │ └──────┐
                        ┌────▼────┐  │ (replan with locked_slots)
                        │execution│  │
                        │ engine  │  │
                        └───┬─┬───┘  │
                   success │ │ fail │
                           │ └──┐   │
                        ┌──▼──┐│   │
                        │notify││   │
                        └──┬──┘│   │
                           │   │   │
                        ┌──▼───▼───▼──┐
                        │  fallback   │ 局部重试 + Shadow POI 替换
                        │  engine     │
                        └──────┬──────┘
                               │
                           ┌───▼───┐
                           │  END  │
                           └───────┘
```


---

## 三、数据流图

### 3.1 主流程数据流 (Plan Creation → SSE Streaming)

```
User (Browser)                    Marketplace (FastAPI)              Agent Worker (Celery)
     │                                    │                               │
     │  POST /api/v1/plan/create          │                               │
     │  {query, lat, lng, user_id}        │                               │
     │ ─────────────────────────────────► │                               │
     │                                    │                               │
     │                                    │  submit_plan.delay(plan_id)   │
     │                                    │ ─────────────────────────────►│
     │  202 Accepted {plan_id}            │                               │
     │ ◄───────────────────────────────── │                               │
     │                                    │                               │
     │  GET /api/v1/plan/{id}/stream      │                               │
     │ ─────────────────────────────────► │                               │
     │                                    │  Redis Pub/Sub subscribe      │
     │                                    │  channel: plan:{plan_id}      │
     │                                    │                               │
     │                                    │                               │  ┌─────────────────────┐
     │                                    │                               │  │ LangGraph invoke()   │
     │                                    │                               │  │                     │
     │                                    │                               │  │ intent_parser       │
     │                                    │                               │  │   → LLM call #1     │
     │                                    │                               │  │   → IntentSchema    │
     │                                    │                               │  │                     │
     │                                    │         Redis Publish         │  │ context_loader      │
     │  SSE: event=intent                 │ ◄─────────────────────────────│  │   → UserProfile     │
     │  data:{IntentSchema}               │                               │  │                     │
     │ ◄───────────────────────────────── │                               │  │ memory_manager      │
     │                                    │                               │  │   → MemoryFeatures  │
     │                                    │         Redis Publish         │  │                     │
     │  SSE: event=retrieval              │ ◄─────────────────────────────│  │ retrieval_engine    │
     │  data:{candidate_count: 15, ...}   │                               │  │   → CandidatePool   │
     │ ◄───────────────────────────────── │                               │  │                     │
     │                                    │                               │  │ planning_engine     │
     │                                    │         Redis Publish         │  │   → Phase1 (code)   │
     │  SSE: event=planning               │ ◄─────────────────────────────│  │   → Phase2 (LLM #2) │
     │  data:{PlanDraft}                  │                               │  │   → PlanDraft       │
     │ ◄───────────────────────────────── │                               │  │                     │
     │                                    │                               │  │ consensus_resolver  │
     │                                    │         Redis Publish         │  │   → interrupt()     │
     │  SSE: event=pending_confirmation   │ ◄─────────────────────────────│  │   → AWAIT RESUME    │
     │  data:{PlanDraft}                  │                               │  │                     │
     │ ◄───────────────────────────────── │                               │  └─────────────────────┘
     │                                    │                               │
     │  POST /api/v1/plan/{id}/confirm    │                               │
     │  {action: "confirm", slots: [...]} │                               │
     │ ─────────────────────────────────► │                               │
     │                                    │  resume graph with confirm    │
     │                                    │ ─────────────────────────────►│
     │                                    │                               │  ┌─────────────────────┐
     │                                    │                               │  │ execution_engine    │
     │                                    │         Redis Publish         │  │   → Tool DAG        │
     │  SSE: event=execution              │ ◄─────────────────────────────│  │   → booking results │
     │  data:{slot_id, booking_status}    │                               │  │                     │
     │ ◄───────────────────────────────── │                               │  │ notify_engine       │
     │                                    │                               │  │   → ShareCard       │
     │                                    │         Redis Publish         │  │                     │
     │  SSE: event=done                   │ ◄─────────────────────────────│  │                     │
     │  data:{PlanResponse}               │                               │  └─────────────────────┘
     │ ◄───────────────────────────────── │                               │
```

### 3.2 SSE 事件类型 (10 种)

| 事件 | 触发节点 | 数据载荷 | 前端处理 |
|------|---------|---------|---------|
| `intent` | IntentParser | IntentSchema | 显示约束标签 |
| `context` | ContextLoader | UserProfile | 更新用户信息 |
| `memory` | MemoryManager | MemoryFeatures | 显示偏好匹配 |
| `retrieval` | RetrievalEngine | {candidate_count, poi_count} | 地图标记候选 POI |
| `planning` | PlanningEngine | PlanDraft | 渲染时间轴 |
| `planning_done` | PlanningEngine | PlanDraft (final) | 时间轴完成 |
| `pending_confirmation` | ConsensusResolver | PlanDraft | 弹出确认面板 |
| `execution` | ExecutionEngine | {slot_id, booking_status} | 更新预订状态 |
| `execution_done` | ExecutionEngine | ExecutionResult | 预订完成标记 |
| `notify` | NotifyEngine | ShareCard | 显示分享卡片 |
| `done` | END | PlanResponse | 计划完成 |
| `error` | Any Node | AgentError | 错误提示 |

### 3.3 持久化数据流 (Checkpoint → Recovery)

```
LangGraph Node 执行
     │
     ├── state: PlanState (TypedDict)
     │     └── PostgresSaver.write_checkpoint()
     │           │
     │           ▼
     │     ┌──────────────────┐
     │     │ langgraph_       │
     │     │ checkpoints      │  ← LangGraph 框架表
     │     │ (checkpoint_id,   │
     │     │  thread_id,       │
     │     │  state_blob JSON) │
     │     └──────────────────┘
     │
     ├── RuntimeEventStore.append()
     │     │
     │     ▼
     │     ┌──────────────────┐
     │     │ plan_run_events  │  ← 审计日志 (自定义)
     │     │ (plan_run_id,     │
     │     │  event_type,      │
     │     │  payload JSON,    │
     │     │  created_at)      │
     │     └──────────────────┘
     │
     └── AgentResult (graph 返回值)
           │
           ▼
     ┌──────────────────┐
     │ plan_runs        │  ← 运行记录 (自定义)
     │ (plan_run_id,     │
     │  plan_id FK,      │
     │  status,           │
     │  started_at,       │
     │  completed_at)     │
     └──────────────────┘
```


---

## 四、模块详细说明

### 4.1 Frontend (`frontend/`) — 状态: ✅ 良好

| 子模块 | 文件 | 职责 | 状态 |
|--------|------|------|:----:|
| Pages | `PlanPage.tsx` | 三栏布局主页面, SSE 事件驱动 | ✅ |
| Components/plan | `PlanCard.tsx`, `PlanTimeline.tsx`, `ConfirmPanel.tsx` | 计划卡片、时间轴、确认面板 | ✅ |
| Components/map | `MapView.tsx` | 高德地图 + POI 气泡 + 路线动画 | ✅ |
| Components/agent | `AgentMonitor.tsx` | Agent 思考过程/节点状态可视化 | ✅ |
| Components/common | `InputBar.tsx` | 自然语言输入框 + 约束标签 | ✅ |
| Hooks | `usePlanSSE.ts` | SSE 流订阅 + 状态更新 | ✅ |
| Stores | `planStore.ts`, `agentStore.ts` | Zustand 状态管理 | ✅ |
| API | `plan.ts` | Axios REST 封装 | ✅ |
| Types | `plan.ts`, `agent.ts` | TypeScript 类型定义 | ✅ |

**缺失项** (PROJECT.md 规划但未实现):
- `SlotDetail.tsx`, `RouteLine.tsx`, `POIMarker.tsx` — 地图组件细化
- `ToolCallLog.tsx`, `PipelineNode.tsx`, `SSEStatus.tsx`, `LoadingSpinner.tsx` — Agent 监视器细化
- `OrdersPage.tsx`, `MerchantPage.tsx`, `LoginPage.tsx` — 课设页面
- `useAgentState.ts`, `useAuth.ts` — 额外 Hooks
- `userStore.ts` — 用户状态 Store

### 4.2 Marketplace (`backend/marketplace/`) — 状态: ⚠️ 需重构

| 子模块 | 文件 | 职责 | 状态 |
|--------|------|------|:----:|
| Entry | `main.py` | FastAPI 应用入口, lifespan | ✅ |
| API v1 | `auth.py`, `plan.py`, `session.py`, `user.py` | REST 路由 | ✅ 基本功能 |
| Models | `plan.py`, `plan_slot.py`, `poi.py`, `users.py`, `user_profile.py` 等 | SQLAlchemy ORM (9 表) | ✅ |
| Schemas | `auth.py`, `user.py` | Pydantic 请求/响应 Schema | ⚠️ 过少 (plan Schema 在 shared) |
| Services | `user_service.py` | 业务逻辑 | ⚠️ 单薄 (仅有 user) |
| Adapters/Amap | `client.py`, `poi_adapter.py`, `geocode_adapter.py`, `route_adapter.py` 等 | 高德地图 API 封装 | ✅ 完整 |
| Tasks | `celery_app.py` | Celery 配置 | ✅ |
| Data | `seed_pois.py` | POI 种子数据 | ✅ |

**问题**:
1. `celery_app.py` 属于 marketplace 但 Celery worker 实际在 agent_worker — 位置歧义
2. `services/` 仅含 `user_service.py`，PROJECT.md 规划的 poi_service, order_service 等未实现
3. Schema 分散在 marketplace/schemas/ 和 shared/schemas/ 两处

### 4.3 Agent Worker (`backend/agent_worker/`) — 状态: ⚠️ 核心完整但需分离

| 子模块 | 文件 | 职责 | 状态 |
|--------|------|------|:----:|
| Core | `graph.py` | LangGraph StateGraph 定义 (双模式: 9-node / 5-node) | ✅ v3 |
| Core | `runtime.py` | AgentRuntime DI 容器 (Phase 1 重构成果) | ✅ |
| Core | `protocol.py` | AgentResult, BaseAgent ABC | ✅ |
| Engines | `intent_parser.py`, `context_loader.py`, `memory_manager.py`, `retrieval_engine.py`, `planning_engine.py`, `consensus_resolver.py`, `execution_engine.py`, `fallback_engine.py`, `notify_engine.py` | 9 个 Agent 节点实现 | ✅ |
| Adapters | `llm.py`, `marketplace.py`, `mock_gateway.py`, `mock_tool_gateway.py`, `prompt.py` | 外部依赖适配器 | ✅ Phase 1 |
| Ports | `events.py`, `llm.py`, `prompt.py`, `repositories.py`, `tools.py` | 抽象接口 (依赖反转) | ✅ Phase 1 |
| State | `builder.py`, `preconfirm.py`, `postconfirm.py`, `response.py`, `events.py` | 状态构建/转换辅助 | ✅ |
| Schemas | `state.py`, `events.py`, `llm.py`, `runtime.py`, `tool.py`, `tool_provider.py`, `checkpoint.py` | Agent 专用 Pydantic Schema | ✅ |
| Providers | `base.py`, `deepseek.py`, `kimi.py`, `openrouter.py`, `registry.py` | LLM Provider 实现 | ✅ |
| Events | `redis_bus.py`, `store.py` | Redis Pub/Sub 事件总线 + 持久化 | ✅ |
| Memory | `service.py` | pgvector 记忆服务 | ✅ |
| Persistence | `checkpoint.py`, `plan.py`, `plan_run.py`, `runtime_event.py`, `user_profile.py` | 数据持久化适配器 | ✅ |
| Models | `checkpoint.py`, `plan_run.py`, `plan_run_event.py`, `runtime_checkpoint.py`, `llm_usage_log.py` | Agent 专用 ORM 模型 | ✅ |
| Prompts | `intent.j2`, `planning.j2`, `notify.j2` | Jinja2 Prompt 模板 | ✅ |
| Skills | `plan-fallback.md`, `restaurant-recommend.md`, `time-negotiation.md` | Skill 定义 | ✅ |

**架构亮点** (Phase 1 重构成果):
- AgentRuntime DI 容器 — 统一管理所有依赖, 支持 mock 替换
- Port/Adapter 分离 — `ports/` 定义抽象, `adapters/` 实现具体
- 双模式 graph — `build_plan_graph` (9-node) / `build_single_agent_graph` (5-node v3)

**问题**: `agent_worker/` 嵌套在 `backend/` 下，与 marketplace 共享 pyproject.toml, 无法独立版本控制

### 4.4 Shared (`backend/shared/`) — 状态: ✅ 但位置不当

| 子模块 | 文件 | 职责 | 状态 |
|--------|------|------|:----:|
| Core | `config.py` | Pydantic-Settings 配置中心 | ✅ |
| Core | `exceptions.py` | 业务异常体系 (SnapTripError 等) | ✅ |
| Core | `exception_handlers.py` | FastAPI 全局异常处理器 | ✅ |
| Core | `logging.py` | structlog JSON 日志 | ✅ |
| Core | `security.py` | JWT + bcrypt + Prompt 注入防御 | ✅ |
| Core | `response.py` | 统一 API 响应格式 | ✅ |
| Core | `rate_limit.py` | Redis 限流 | ✅ |
| Core | `constants.py` | 枚举 + 策略参数 | ✅ |
| DB | `session.py`, `redis.py` | AsyncSession + Redis 客户端 | ✅ |
| Schemas | `plan.py` | 跨包共享 Pydantic Schema | ✅ |

**问题**: 当前在 `backend/shared/`, 作为 monorepo 顶级包应该提到根级

### 4.5 Mock Server (`mock_server/`) — 状态: ✅ 基础可用

| 子模块 | 文件 | 职责 | 状态 |
|--------|------|------|:----:|
| Entry | `main.py` | FastAPI mock 服务入口 | ✅ |
| Routers | `poi.py`, `queue.py`, `route.py`, `weather.py`, `order.py`, `delivery.py` | 6 个 Mock 路由 | ✅ |
| Schemas | `schemas.py` | Mock 数据 Schema | ✅ |
| Data | `seed_pois.json` | 50 条预置 POI 数据 | ✅ |
| Core | `fault.py` | 故障注入 (模拟超时/错误) | ✅ |

### 4.6 Tests (`backend/tests/`) — 状态: ⚠️ 覆盖不均

| 目录 | 文件数 | 测试范围 | 状态 |
|------|:---:|------|:----:|
| `unit/` | 22 | Agent engines, services, adapters, state, events | ✅ 核心覆盖 |
| `integration/` | 6 | E2E plan, auth API, user API, Amap | ⚠️ 需 mock 服务 |
| `contract/` | 1 + 3 snapshots | Amap schema 快照测试 | ✅ |
| `eval/` | 1 runner + 2 golden | 离线评估 | ⚠️ 基础框架 |

**缺失**: `consensus_resolver` (完全 stub) 无测试；`conftest.py` fixture 覆盖不足

### 4.7 Docs (`docs/`) — 状态: ⚠️ 部分过时 (详见第五节)


---

## 五、Docs 文档审核

### 5.1 文档清单评估

| 文件 | 行数 | 内容 | 状态 | 建议 |
|------|:---:|------|:----:|------|
| `docs/architecture/01-overview.md` | 267 | 6 层架构总览、技术选型表 | ⚠️ 部分过时 | 更新部署模式描述 |
| `docs/architecture/02-planning-algorithm.md` | 182 | 两阶段规划算法 | ✅ 最新 | 保留 |
| `docs/architecture/03-tool-orchestration.md` | 187 | Tool DAG + Saga | ⚠️ 部分过时 | 更新为 ExecutionEngine 实现 |
| `docs/architecture/04-exception-handling.md` | 182 | 异常处理体系 | ✅ 最新 | 保留 |
| `docs/architecture/05-agent-architecture.md` | 502 | LangGraph 15 Agent 设计 | ⚠️ 描述理想态 | 标注已实现 vs 规划中 |
| `docs/architecture/06-agent-production-refactor.md` | 934 | 生产化重构方案 | ⚠️ 设计文档 | 标注 Phase 1 已完成 |
| `docs/architecture/structure-review.md` | 878 | 结构审查 + 迁移计划 | ⚠️ 设计文档 | 与本次重构对齐后归档 |
| `docs/api/plan.md` | 163 | Plan API 规范 | ⚠️ 可能过时 | 对比实际路由验证 |
| `docs/meetings/01-team-division.md` | 195 | 团队分工 | ❌ 已过时 | **建议删除或归档** |
| `docs/meetings/02-dev-timeline.md` | 187 | 10 天开发时间线 | ❌ 已过时 | **建议删除或归档** |
| `docs/meetings/03-decisions-log.md` | 147 | 11 条 ADR | ⚠️ 混合 | 提取 ADR 到 `docs/decisions/` |
| `docs/skills/plan-fallback.md` | 57 | Skill 定义 | ⚠️ 副本 | 与 `agent/skills/` 重复 |
| `docs/skills/restaurant-recommend.md` | 46 | Skill 定义 | ⚠️ 副本 | 与 `agent/skills/` 重复 |
| `docs/skills/time-negotiation.md` | 41 | Skill 定义 | ⚠️ 副本 | 与 `agent/skills/` 重复 |
| `frontend/README.md` | 73 | Vite 模板 | ❌ 无用 | 替换为项目前端说明 |

### 5.2 清理建议

```
保留 (7 文件):
  docs/architecture/01-overview.md          → 更新后保留
  docs/architecture/02-planning-algorithm.md → 保留
  docs/architecture/03-tool-orchestration.md → 更新后保留
  docs/architecture/04-exception-handling.md → 保留
  docs/architecture/05-agent-architecture.md → 标注实现状态后保留
  docs/api/plan.md                          → 验证更新后保留
  docs/architecture/00-comprehensive-review.md → 本次审核报告 (新增)

归档/删除 (9 文件):
  docs/meetings/01-team-division.md         → 删除 (历史规划)
  docs/meetings/02-dev-timeline.md          → 删除 (历史规划)
  docs/skills/plan-fallback.md              → 删除 (以 agent/skills/ 为准)
  docs/skills/restaurant-recommend.md       → 删除 (以 agent/skills/ 为准)
  docs/skills/time-negotiation.md           → 删除 (以 agent/skills/ 为准)
  frontend/README.md                        → 重写为项目前端文档

迁移 (2 文件):
  docs/meetings/03-decisions-log.md         → docs/decisions/ADR.md
  docs/architecture/06-agent-production-refactor.md → 添加状态标注
  docs/architecture/structure-review.md     → 标注"已被 00-comprehensive-review 替代"
```

---

## 六、基础配置审核

### 6.1 开发环境

| 配置项 | 当前状态 | 跨平台兼容 | 建议 |
|--------|---------|:---------:|------|
| Python 包管理 | `uv` (backend + mock_server 各自 pyproject.toml) | ✅ Mac/Linux/Windows | 统一 workspace |
| Node 包管理 | `npm` (frontend/package.json) | ✅ | 考虑 pnpm 提速 |
| 环境变量 | `.env.example` (56 行, 完整) | ✅ | 添加 Windows 注释 |
| Pre-commit | `.pre-commit-config.yaml` (ruff + 通用 hooks) | ✅ | 添加 prettier for frontend |
| Makefile | `make` (26 targets, 分工清晰) | ⚠️ Mac/Linux | 添加 `taskfile.yml` for Windows |
| Git | `.gitignore` (3 个: 根/backend/frontend) | ✅ | 合并为单一 .gitignore |
| Docker Dev | `docker-compose.override.example.yml` (bind mount + hot reload) | ✅ | 注意 Windows 文件权限 |

**关键缺失**:
- **无根 `pyproject.toml`** — uv workspace 未配置，backend 和 mock_server 各自独立
- **无 `.python-version`** — 未锁定 Python 版本 (仅 pyproject.toml `requires-python = ">=3.11"`)
- **前端 `.gitignore` 独立** — 应合并到根 `.gitignore`

### 6.2 测试环境

| 配置项 | 当前状态 | 评估 |
|--------|---------|:---:|
| 测试数据库 | `docker-compose.test.yml` (postgres:5433, redis:6380) | ✅ 独立端口 |
| 测试环境变量 | Makefile `TEST_ENV` 硬编码 | ⚠️ 应改为 `.env.test` |
| CI 测试 | `.github/workflows/ci.yml` (services + uv + pytest) | ✅ 完整 |
| 测试 fixture | `tests/conftest.py`, `tests/integration/conftest.py` | ⚠️ 需文档化 |
| Mock 服务 | CI 中 nohup 启动 mock_server | ⚠️ 不够健壮 |
| 覆盖率 | pytest-cov → codecov | ✅ |

**CI 配置分析** (`.github/workflows/ci.yml`):
```
Jobs:
  lint-backend    — ruff check + mypy (uv sync)
  lint-frontend   — tsc --noEmit (npm)
  test-backend    — postgres + redis services, alembic upgrade, pytest unit/integration
  
✅ 优点:
  - 使用 astral-sh/setup-uv@v3 (官方 action)
  - concurrency 控制避免重复运行
  - 服务健康检查完整
  
⚠️ 改进:
  - mock_server 启动用 nohup + sleep loop, 建议用 docker compose
  - 缺少 test-frontend job (无 vitest/jest 配置)
  - 缺少 docker build 验证 (确保镜像可构建)
```

### 6.3 生产环境

| 配置项 | 当前状态 | 评估 |
|--------|---------|:---:|
| Dockerfile 多阶段构建 | `base → development/production` | ✅ |
| 非 root 用户 | `appuser` (production stage) | ✅ |
| 健康检查 | 所有容器均有 healthcheck | ✅ |
| 密钥管理 | 环境变量 `${VAR:?required}` | ✅ |
| 数据库迁移 | 容器启动自动 alembic upgrade head | ✅ |
| 日志 | structlog JSON 格式 | ✅ |
| 资源限制 | **未配置** | ❌ 缺 `deploy.resources.limits` |

**docker-compose.yml 进程清单**:
```
1. postgres      — pgvector/pgvector:pg16    :5432
2. redis         — redis:7-alpine            :6379
3. marketplace   — FastAPI + Celery Beat     :8080→:8000
4. agent-worker  — Celery Worker (LangGraph) 无端口
5. agent-beat    — Celery Beat Scheduler     无端口
6. mock-server   — FastAPI Mock              :8001 (profiles: dev, full)
7. frontend      — Vite Dev Server           :5174→:5173 (profiles: dev, full)
```

### 6.4 跨平台问题

| 问题 | 影响平台 | 严重度 | 解决方案 |
|------|:--------:|:-----:|---------|
| Makefile 仅 Unix | Windows | 中 | 提供 `taskfile.yml` 或 `justfile` |
| Docker bind mount 权限 | Windows (WSL2) | 低 | 文档说明 WSL2 要求 |
| `uv sync` 在 CI 中的缓存 | 全部 | 低 | 添加 `cache: pip` 或 uv cache |
| `#!/bin/bash` shebang | Windows | 低 | 所有脚本保持 POSIX |
| 路径分隔符 `/` vs `\` | Windows | 低 | Docker 内统一 Linux 容器 |

---

## 七、重构实施计划

### 7.1 优先级矩阵

| 优先级 | 任务 | 影响范围 | 风险 |
|:------:|------|:-------:|:---:|
| **P0** | 创建根 `pyproject.toml` uv workspace | backend, mock_server | 低 |
| **P0** | 提取 `shared/` 到根级 | 全栈引用路径 | 中 |
| **P0** | 拆分 `backend/` → `backend/` + `agent/` | Dockerfile, CI, import | 高 |
| **P1** | 重命名 `mock_server/` → `mock-services/` | docker-compose, CI | 低 |
| **P1** | 创建 `infra/` — 提取 nginx, postgres, redis 配置 | docker-compose | 低 |
| **P1** | 合并 `.gitignore` | 无 | 低 |
| **P1** | 合并 `alembic/` + `migrations/` 两套目录 | DB 迁移 | 中 |
| **P1** | 清理过时文档 | 无 | 低 |
| **P2** | 添加 `taskfile.yml` for Windows | CI | 低 |
| **P2** | 添加 `.env.test` 替代 Makefile 硬编码 | 测试 | 低 |
| **P2** | Docker Compose resource limits | 生产 | 低 |
| **P2** | 添加前端测试框架 (vitest) | CI | 低 |

### 7.2 迁移步骤 (P0+P1 详细)

**Step 1: 创建根 workspace**
```bash
# 在根目录创建 pyproject.toml 定义 uv workspace
# [tool.uv.workspace]
# members = ["backend", "agent", "shared", "mock-services/*"]
```

**Step 2: 提取 shared/**
```bash
mkdir -p shared/src/snaptrip_shared
mv backend/shared/core shared/src/snaptrip_shared/
mv backend/shared/db shared/src/snaptrip_shared/
mv backend/shared/schemas shared/src/snaptrip_shared/
# 更新 backend/pyproject.toml 和新增 agent/pyproject.toml 中添加
# [tool.uv.sources]
# snaptrip-shared = { workspace = true }
```

**Step 3: 拆分 backend/ → backend/ + agent/**
```bash
mkdir -p agent/src/agent
mv backend/agent_worker/app/agent/* agent/src/agent/
# 更新 Docker 构建上下文
# 更新 CI workflows
```

**Step 4: 清理 imports**
```python
# 从: from agent_worker.app.agent.engines import ...
# 到: from agent.engines import ...
# 从: from shared.core.config import settings
# 到: from snaptrip_shared.core.config import settings
```

---

## 八、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|:----:|:----:|------|
| import 断裂 (重构后) | 高 | 高 | CI 全量测试 + `scripts/migrate_imports.py` |
| Docker 构建上下文变化 | 中 | 中 | 逐步迁移, 保留旧 Dockerfile 至验证通过 |
| 两套 alembic 合并冲突 | 中 | 高 | 生成新合并 migration, 保留两套至 CI 通过 |
| `agent_worker/` 有 Celery 依赖 | 低 | 中 | agent/ 需保留 celery 依赖 (worker 运行环境) |
| 文档与代码不一致 | 中 | 低 | 归档历史文档, 标注文档状态 |

