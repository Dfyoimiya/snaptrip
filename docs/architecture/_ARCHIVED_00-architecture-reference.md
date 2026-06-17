# SnapTrip 架构参考手册

> 日期: 2026-05-23 | 版本: 0.3.0 | 基于代码实际状态

---

## 一、整体架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          前端层 (React 19 + Vite + TypeScript)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   PlanPage   │  │   MapView    │  │ AgentMonitor │  │   InputBar   │      │
│  │  (主页面)     │  │  (Amap JS)   │  │  (思考过程)   │  │  (自然语言)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘      │
│                          Zustand Store (planStore + agentStore)               │
│                          usePlanSSE Hook (SSE EventSource)                    │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ REST / SSE (EventSource)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       API 网关层 (FastAPI :8000)                               │
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │   Plan API v1    │  │   Auth API v1    │  │   User API v1    │            │
│  │ POST /create     │  │ POST /register   │  │ GET /profile     │            │
│  │ POST /confirm    │  │ POST /login      │  │ PUT /profile     │            │
│  │ GET /{plan_id}   │  │ POST /refresh    │  │                  │            │
│  │ GET /stream (SSE)│  │ POST /logout     │  │                  │            │
│  │ GET /status      │  │                  │  │                  │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
│                                                                               │
│  中间件: CORS | JWT Auth (security.py) | Rate Limit (rate_limit.py)          │
│  异常处理: 统一响应 {code, message, data} + SOCID 异常体系                     │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ Celery Task Dispatch
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       编排层 (LangGraph StateGraph)                            │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                     AgentRuntime (DI 容器)                           │     │
│  │  gateway | event_sink | tool_adapter | cb_registry | saga           │     │
│  │  user_profile_repo | plan_repo | marketplace_client                 │     │
│  └─────────────────────────────────────────────────────────────────────┘     │
│                                                                               │
│  Mode A: 9-Node Multi-Agent (build_plan_graph)                               │
│  intent_parser → context_loader → memory_manager → retrieval_engine           │
│  → planning_engine → consensus_resolver → execution_engine                    │
│  → [fallback_engine] → notify_engine                                          │
│                                                                               │
│  Mode B: 5-Node Single-Agent (build_single_agent_graph) v3                    │
│  planner (折叠前5节点) → consensus → execution → [fallback] → notify           │
│                                                                               │
│  Checkpointer: MemorySaver (开发) / PostgresSaver (生产预留)                   │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ Tool Call
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        引擎层 (9 Engine Services)                              │
│                                                                               │
│  IntentParser    │ ContextLoader  │ MemoryManager  │ RetrievalEngine          │
│  (LLM+关键词降级) │ (用户画像加载)  │ (历史偏好聚合)  │ (Haversine+种子数据)      │
│                                                                               │
│  PlanningEngine  │ ConsensusResolver│ ExecutionEngine│ FallbackEngine          │
│  (两阶段求解器)   │ (单/多用户投票)   │ (Tool DAG v3)  │ (Shadow+Ripple+孤儿取消) │
│                                                                               │
│  NotifyEngine    │                                                           │
│  (分享卡片渲染)   │                                                           │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ HTTP (httpx)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     外部依赖层 (Mock / 真实 API)                               │
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Mock Meituan    │  │   高德地图 API    │  │   LLM Provider   │            │
│  │  (FastAPI :8001) │  │  (restapi.amap)  │  │  (OpenRouter /    │            │
│  │                  │  │                  │  │   DeepSeek/Kimi)  │            │
│  │  /poi /queue     │  │  geocode / poi   │  │                  │            │
│  │  /booking /order │  │  route / district│  │  DeepSeek-V3      │            │
│  │  /delivery /route│  │  weather         │  │  Claude-3.5       │            │
│  │  /weather        │  │                  │  │  Kimi             │            │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘            │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         数据层 (PostgreSQL + Redis)                            │
│                                                                               │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐    │
│  │  PostgreSQL 16 + pgvector       │  │  Redis 7                        │    │
│  │                                 │  │                                 │    │
│  │  业务表: users, user_profiles,  │  │  Celery Broker (queue)          │    │
│  │          plans, plan_slots,     │  │  SSE Pub/Sub (plan:{id})        │    │
│  │          plan_adjustments,      │  │  Session Cache                  │    │
│  │          pois, refresh_tokens   │  │  Rate Limit Counter             │    │
│  │                                 │  │  Execution Lock                 │    │
│  │  Agent表: checkpoints,          │  │                                 │    │
│  │           plan_runs,            │  │                                 │    │
│  │           plan_run_events,      │  │                                 │    │
│  │           runtime_checkpoints,  │  │                                 │    │
│  │           llm_usage_logs        │  │                                 │    │
│  └─────────────────────────────────┘  └─────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、部署拓扑 (6 进程)

```
                       Docker Network: snaptrip

  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  frontend    │  │ marketplace  │  │ agent-worker │
  │  (Vite)      │  │ (FastAPI)    │  │ (Celery)     │
  │  :5173       │  │ :8000        │  │              │
  │              │  │              │  │ LangGraph     │
  │  React 19    │  │ JWT + CORS   │  │ 9-Node Graph │
  │  TypeScript  │  │ Rate Limit   │  │ Celery Tasks │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                 │
         │ REST + SSE      │                 │
         └────────┬────────┘                 │
                  │                          │
                  │  HTTP (Celery dispatch)   │
                  ├──────────────────────────┤
                  │                          │
         ┌────────┴────────┐    ┌───────────┴────────┐
         │    postgres     │    │       redis        │
         │  (pgvector:16)  │    │     (7-alpine)     │
         │  :5432          │    │  :6379             │
         │                 │    │                    │
         │  12 Tables      │    │  Celery Broker     │
         │  + LangGraph    │    │  SSE Pub/Sub       │
         │  Checkpoint     │    │  Session Cache     │
         └─────────────────┘    └────────────────────┘

  ┌──────────────┐  ┌──────────────┐
  │  mock-server │  │ agent-beat   │
  │  (FastAPI)   │  │ (Celery Beat)│
  │  :8001       │  │              │
  │              │  │ 定时清理      │
  │  6 Routers   │  │ 孤儿资源      │
  └──────────────┘  └──────────────┘
```

---

## 三、后端模块图

### 3.1 包结构 (Monorepo Workspace)

```
snaptrip/                          # uv workspace root
├── pyproject.toml                 # [tool.uv.workspace] members = [...]
├── uv.lock                        # 全仓库统一锁文件
│
├── shared/                        # snaptrip-shared (被所有 Python 包引用)
│   └── snaptrip_shared/
│       ├── core/   config | constants | exceptions | exception_handlers
│       │           logging | rate_limit | response | security
│       ├── db/     session (AsyncEngine) | redis (连接池)
│       └── schemas/  plan (共享 Pydantic Schema)
│
├── agent/                         # snaptrip-agent (Agent 核心引擎)
│   └── src/agent/
│       ├── graph.py               # LangGraph 双模式编排 (9-node / 5-node)
│       ├── runtime.py             # AgentRuntime DI 容器
│       ├── protocol.py            # BaseAgent ABC + AgentContext + AgentResult
│       ├── engines/               # 9 个 Agent 节点实现
│       ├── adapters/              # LLM | Marketplace | Mock | Prompt
│       ├── ports/                 # 抽象接口 (依赖反转)
│       ├── schemas/               # Agent 专用 Schema
│       ├── state/                 # 状态构建/转换/修复
│       ├── events/                # Redis Pub/Sub + EventStore
│       ├── providers/             # LLM Provider (DeepSeek/Kimi/OpenRouter)
│       ├── prompts/               # Jinja2 模板 (intent/planning/notify)
│       ├── skills/                # Skill Markdown 定义
│       ├── services/              # AgentService + LLMGateway
│       ├── memory/                # pgvector 记忆服务
│       ├── checkpointer/          # LangGraph checkpointer builder
│       └── tasks/                 # Celery 异步任务
│
├── backend/                       # snaptrip-backend (API 网关 + 业务层)
│   ├── marketplace/app/
│   │   ├── main.py                # FastAPI 入口 + lifespan
│   │   ├── celery_app.py          # Celery 配置
│   │   ├── api/v1/                # REST 路由 (plan/auth/user)
│   │   ├── models/                # SQLAlchemy ORM (12 表)
│   │   ├── schemas/               # Pydantic 请求/响应 Schema
│   │   ├── services/              # 业务服务 (user)
│   │   ├── adapters/amap/         # 高德地图适配器
│   │   └── data/                  # 种子数据
│   ├── alembic/                   # 数据库迁移
│   └── tests/                     # unit + integration + contract + eval
│
├── mock-services/                 # 模拟第三方服务
│   └── mock-meituan/              # 模拟美团 API (:8001)
│
├── frontend/                      # React 19 SPA (独立于 Python workspace)
│
├── docs/                          # 项目文档
├── docker-compose.yml             # 7 服务编排
├── Makefile                       # Unix 命令入口
└── Taskfile.yml                   # 跨平台命令入口
```

### 3.2 依赖关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                         frontend                                │
│  depends_on: (none)                                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP REST + SSE
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         backend                                │
│  depends_on: agent, shared, mock-services                      │
│  imports:   agent.graph, agent.services, agent.adapters        │
│             marketplace.app.models, marketplace.app.api        │
│             snaptrip_shared.core, snaptrip_shared.db           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Python import
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                          agent                                  │
│  depends_on: shared                                            │
│  imports:   snaptrip_shared.core.config, .constants            │
│             snaptrip_shared.schemas.plan                       │
│             marketplace.app.data.seed_pois (循环依赖 ⚠️)       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Python import
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         shared                                  │
│  depends_on: (none — 最底层)                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、Agent 模块图

### 4.1 Agent 运行时架构

```
                         ┌─────────────────────┐
                         │    AgentRuntime     │
                         │    (DI Container)   │
                         ├─────────────────────┤
                         │ gateway             │──► MockAPIGateway
                         │ event_sink          │──► RuntimeEventStore
                         │ tool_adapter        │──► ToolAdapter
                         │ cb_registry         │──► CircuitBreakerRegistry
                         │ idempotency         │──► IdempotencyService
                         │ saga                │──► SagaCoordinator
                         │ confirmator         │──► PhysicalConfirmator
                         │ redis               │──► Redis Client
                         │ marketplace_client  │──► MarketplaceClient
                         │ user_profile_repo   │──► UserProfileRepository
                         │ plan_repo           │──► PlanRepository
                         │ memory              │──► MemoryService
                         └─────────────────────┘
                                  │
                                  ▼
              ┌───────────────────────────────────────┐
              │         CompiledStateGraph             │
              │                                       │
              │  Mode A: build_plan_graph()            │
              │  ┌─────┐   ┌─────┐   ┌─────┐         │
              │  │intent│──►│ctx  │──►│mem  │         │
              │  └─────┘   └─────┘   └─────┘         │
              │     │                     │            │
              │     ▼                     ▼            │
              │  ┌─────┐   ┌─────┐   ┌─────┐         │
              │  │retr │──►│plan │──►│cons │         │
              │  └─────┘   └─────┘   └──┬──┘         │
              │                         │            │
              │            ┌────────────┼──────┐     │
              │            ▼            ▼      ▼     │
              │       ┌──────┐    ┌──────┐  ┌──┐    │
              │       │ exec │───►│ fall │  │END│    │
              │       └──┬───┘    └──┬───┘  └──┘    │
              │          │           │               │
              │          ▼           ▼               │
              │       ┌──────┐   ┌──────┐           │
              │       │notify│   │ END  │           │
              │       └──┬───┘   └──────┘           │
              │          │                           │
              │          ▼                           │
              │       ┌──────┐                       │
              │       │ END  │                       │
              │       └──────┘                       │
              │                                       │
              │  Mode B: build_single_agent_graph()   │
              │  ┌──────┐   ┌──────┐   ┌──────┐     │
              │  │planner│──►│consensus│─►│exec │     │
              │  └──────┘   └──────┘   └──┬───┘     │
              │                            │         │
              │              ┌─────────────┼───┐     │
              │              ▼             ▼   ▼     │
              │         ┌──────┐    ┌──────┐ ┌──┐   │
              │         │notify│    │fallback│ │END│  │
              │         └──────┘    └──────┘ └──┘   │
              └───────────────────────────────────────┘
```

### 4.2 9 个竞赛核心 Agent

| # | Agent | 文件 | LLM | 超时 | 输入 | 输出 | 降级策略 |
|---|-------|------|:---:|:----:|------|------|---------|
| 1 | IntentParser | `engines/intent_parser.py` | Y | 8s | `user_input` | `IntentSchema` | 关键词匹配 (confidence=0.4) |
| 2 | ContextLoader | `engines/context_loader.py` | N | 500ms | `user_id` | `EnrichedIntent` | 空 profile |
| 3 | MemoryManager | `engines/memory_manager.py` | N | — | `EnrichedIntent` | `MemoryFeatures` | 默认向量 |
| 4 | RetrievalEngine | `engines/retrieval_engine.py` | N | 1s | `EnrichedIntent` | `CandidatePool` | 最近5个POI兜底 |
| 5 | PlanningEngine | `engines/planning_engine.py` | Y | 8s | `CandidatePool` | `PlanDraft` | Phase1评分排序 |
| 6 | ConsensusResolver | `engines/consensus_resolver.py` | N | 100ms | `PlanDraft` | `Confirmation` | 单用户auto_confirm |
| 7 | ExecutionEngine | `engines/execution_engine.py` | N | 10s | `PlanDraft` | `ExecutionResult` | 部分成功降级 |
| 8 | FallbackEngine | `engines/fallback_engine.py` | N | 2s | `FailedSlot` | `RevisedPlan` | Shadow→重检索→最多2次 |
| 9 | NotifyEngine | `engines/notify_engine.py` | N | 500ms | `PlanDraft` | `ShareCard` | 失败不影响主流程 |

### 4.3 Port/Adapter 架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         ports/ (抽象接口)                         │
│                                                                   │
│  LLMPort          → chat_json(prompt, model, timeout, temp)      │
│  PromptPort       → render(template_name, context) → str         │
│  ToolGatewayPort  → call/call_idempotent/cancel/query_status     │
│  EventSinkPort    → emit(event: RuntimeEvent)                    │
│  UserProfileRepositoryPort → get_profile(user_id)                │
│  PlanRepositoryPort        → get_user_history(user_id)            │
│  CheckpointRepositoryPort  → save/load_latest                    │
│  RuntimeEventRepositoryPort → append/list_by_plan/get_events_after│
└──────────────────────────┬───────────────────────────────────────┘
                           │ implements
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                       adapters/ (具体实现)                        │
│                                                                   │
│  LLMAdapter              → OpenRouter / DeepSeek / Kimi          │
│  JinjaPromptAdapter      → Jinja2 模板引擎                       │
│  MockAPIGateway          → httpx → mock-server :8001             │
│  MockToolGatewayAdapter  → 本地 mock tool                        │
│  MarketplaceClient       → httpx → marketplace :8000             │
│                                                                   │
│  persistence/checkpoint.py    → runtime_checkpoints 表           │
│  persistence/plan.py          → plans 表                         │
│  persistence/plan_run.py      → plan_runs 表                     │
│  persistence/runtime_event.py → plan_run_events 表               │
│  persistence/user_profile.py  → user_profiles 表                 │
└──────────────────────────────────────────────────────────────────┘
```

### 4.4 Engine 内部调用链 (9-Node 模式)

```
Node: intent_parser
  IntentParser.execute(ctx)
    ├── LLM: chat_json(prompt="intent.j2", model=deepseek, temp=0.3)
    │   └── 超时/失败 → _parse_via_keywords() (置信度 0.4)
    └── → AgentResult(data={"intent": IntentSchema})

Node: context_loader
  ContextLoader.execute(ctx)
    ├── UserProfileRepositoryPort.get_profile(user_id)
    │   └── SELECT * FROM user_profiles WHERE user_id = ?
    └── → AgentResult(data={"enriched_intent": EnrichedIntent})

Node: memory_manager
  MemoryManager.execute(ctx)
    ├── PlanRepositoryPort.get_user_history(user_id)
    ├── 聚合历史偏好统计 (MemoryFeatures)
    └── → AgentResult(data={"enriched_intent": enhanced, "memory_features": ...})

Node: retrieval_engine
  RetrievalEngine.execute(ctx)
    ├── 从 SEED_POIS 按城市筛选
    ├── haversine() 距离过滤 (≤15km)
    ├── 按类型分组，偏好类型优先 TOP 5
    └── → AgentResult(data={"candidate_pool": CandidatePool(≤20)})

Node: planning_engine
  PlanningEngine.execute(ctx)
    ├── Phase1: _phase1_hard_filter (纯代码, ≤50ms)
    │   ├── 类型匹配 ±5分 | 预算约束 -3分 | 距离加权 | 心情标签 +2分
    │   └── 排序取 TOP 10
    ├── Phase2: _phase2_llm_sort (LLM, ≤8s)
    │   ├── Jinja2 渲染 planning.j2
    │   ├── LLM chat_json(temp=0.5, max_tokens=1024)
    │   └── 超时 → _phase2_fallback_sort (评分+心情排序)
    ├── _generate_slots(): 最多4个Slot, 均匀分配时间, 预计算Shadow
    └── → AgentResult(data={"draft": PlanDraft})

Node: consensus_resolver
  ConsensusResolver.execute(ctx)
    ├── 预算冲突检测 → objection
    ├── 时间重叠检测 → objection
    ├── 多用户投票 (预留框架)
    └── → interrupt({draft, message, suggested_decision})
        等待 POST /confirm → Command(resume={...})

Node: execution_engine
  ExecutionEngine.execute(ctx)
    ├── v3: Redis Session锁 + User锁
    ├── v3: _execute_dag() 分层并行
    │   ├── L0: search_poi × N → asyncio.gather
    │   ├── L1: check_queue / check_availability / calculate_route
    │   ├── L2: book_table / book_ticket / order (物理操作)
    │   └── L3: notify
    ├── v3: 每Tool: CB检查→幂等→调用→Saga记录→UNKNOWN确认
    ├── 失败 → Saga.compensate() 逆序补偿
    └── → AgentResult(data={"execution": ExecutionResult, "execution_state": ...})

Node: fallback_engine
  FallbackEngine.execute(ctx)
    ├── Shadow缓存优先 → _find_alternative() 读shadow_id
    ├── 无Shadow → _retrieve_alternative() 同类型随机
    ├── v3: _cancel_orphan_booking() — 取消被替换POI的确认预订
    ├── _ripple_reschedule() — 向下游传播时间偏移
    ├── v3: Saga.compensate_for_tool() — 定向补偿
    └── → AgentResult(data={"revised_plan": RevisedPlan})

Node: notify_engine
  NotifyEngine.execute(ctx)
    ├── _build_message() — 生成文字摘要
    ├── _render_card() — Jinja2渲染 notify.j2
    └── → AgentResult(data={"share_card": ShareCard})
```

---

## 五、数据流图

### 5.1 主流程 (Plan Creation → SSE Streaming)

```
User (Browser)                  Marketplace (FastAPI)              Agent Worker (Celery)
     │                                  │                               │
     │ POST /api/v1/plan/create         │                               │
     │ {user_input, lat, lng, user_id}  │                               │
     │ ────────────────────────────────►│                               │
     │                                  │                               │
     │                                  │ 1. build_initial_state()      │
     │                                  │ 2. SQLPlanRunRepo.insert()    │
     │                                  │ 3. celery_submit.delay()      │
     │  202 {plan_id, status: "queued"} │ ─────────────────────────────►│
     │ ◄─────────────────────────────── │                               │
     │                                  │                               │
     │ GET /api/v1/plan/{id}/stream     │                               │
     │ ────────────────────────────────►│                               │
     │                                  │  Redis Pub/Sub subscribe      │
     │                                  │  channel: plan:{plan_id}      │
     │                                  │                               │  ┌─────────────────────┐
     │                                  │                               │  │ AgentService.invoke()│
     │                                  │                               │  │                     │
     │                                  │                               │  │ intent_parser       │
     │                                  │                               │  │   → LLM #1          │
     │                                  │       Redis Publish           │  │   → IntentSchema    │
     │  SSE: event=intent               │ ◄─────────────────────────────│  │                     │
     │ ◄─────────────────────────────── │                               │  │ context_loader      │
     │                                  │                               │  │   → UserProfile     │
     │                                  │       Redis Publish           │  │                     │
     │  SSE: event=context              │ ◄─────────────────────────────│  │ memory_manager      │
     │ ◄─────────────────────────────── │                               │  │   → MemoryFeatures  │
     │                                  │                               │  │                     │
     │                                  │       Redis Publish           │  │ retrieval_engine    │
     │  SSE: event=retrieval            │ ◄─────────────────────────────│  │   → CandidatePool   │
     │ ◄─────────────────────────────── │                               │  │                     │
     │                                  │                               │  │ planning_engine     │
     │                                  │       Redis Publish           │  │   → Phase1 (code)   │
     │  SSE: event=planning_done        │ ◄─────────────────────────────│  │   → Phase2 (LLM #2) │
     │ ◄─────────────────────────────── │                               │  │   → PlanDraft       │
     │                                  │                               │  │                     │
     │                                  │                               │  │ consensus_resolver  │
     │                                  │       Redis Publish           │  │   → interrupt()     │
     │  SSE: event=interrupt_requested  │ ◄─────────────────────────────│  │   → AWAIT RESUME    │
     │ ◄─────────────────────────────── │                               │  └─────────────────────┘
     │                                  │                               │
     │ POST /api/v1/plan/{id}/confirm   │                               │
     │ {decision, locked_slots, ...}    │                               │
     │ ────────────────────────────────►│                               │
     │                                  │  celery_confirm.delay()      │
     │  202 {status: "accepted"}        │ ─────────────────────────────►│
     │ ◄─────────────────────────────── │                               │  ┌─────────────────────┐
     │                                  │                               │  │ AgentService.resume()│
     │                                  │                               │  │                     │
     │                                  │                               │  │ execution_engine    │
     │                                  │       Redis Publish           │  │   → Tool DAG (v3)   │
     │  SSE: event=execution            │ ◄─────────────────────────────│  │   → booking results │
     │ ◄─────────────────────────────── │                               │  │                     │
     │                                  │                               │  │ [fallback_engine]   │
     │                                  │       Redis Publish           │  │   → Shadow替换      │
     │  SSE: event=fallback             │ ◄─────────────────────────────│  │                     │
     │ ◄─────────────────────────────── │                               │  │                     │
     │                                  │                               │  │ notify_engine       │
     │                                  │       Redis Publish           │  │   → ShareCard       │
     │  SSE: event=done                 │ ◄─────────────────────────────│  │                     │
     │ ◄─────────────────────────────── │                               │  └─────────────────────┘
```

### 5.2 持久化数据流 (Checkpoint + Event)

```
LangGraph Node 执行
     │
     ├── state: PlanState (TypedDict)
     │     └── MemorySaver.put() (开发) / PostgresSaver (生产)
     │           │
     │           ▼
     │     ┌──────────────────────┐
     │     │ langgraph_checkpoints│  ← LangGraph 框架表 (开发中)
     │     └──────────────────────┘
     │
     ├── RuntimeEventStore.append()
     │     │
     │     ▼
     │     ┌──────────────────┐
     │     │ plan_run_events  │  ← 审计日志
     │     │ (event_id,       │
     │     │  run_id,         │
     │     │  plan_id,        │
     │     │  node_name,      │
     │     │  event_type,     │
     │     │  payload_json,   │
     │     │  created_at)     │
     │     └──────────────────┘
     │
     └── AgentResult → graph最终状态
           │
           ▼
     ┌──────────────────┐
     │ plan_runs        │  ← 运行记录
     │ (run_id,         │
     │  plan_id FK,     │
     │  thread_id,      │
     │  graph_version,  │
     │  final_status,   │
     │  seed,           │
     │  created_at)     │
     └──────────────────┘
```

### 5.3 v3 执行安全管道 (Single Tool)

```
_execute_single_tool(slot_index, tool, meta, slot, context)
  │
  ├─ ToolAdapter 不存在? → 旧版路径 (gateway / mock)
  │
  └─ ToolAdapter 存在 → v3 安全管道:
       │
       ├─ 1. 双层熔断检查
       │     L1 Provider: cb_registry.is_open(tool, provider)
       │     L2 Tool:     cb_registry.is_open(tool)
       │     → 熔断打开 → ToolResult(CIRCUIT_OPEN)
       │
       ├─ 2. 构建参数
       │     _build_tool_params(slot, context)
       │     根据 tool action 填充 poi_id, guest_count, time_slot 等
       │
       ├─ 3. 幂等键生成 (仅物理操作)
       │     key = idempotent:{plan_id}:{tool}:{poi_id}:{slot_index}
       │
       ├─ 4. ToolAdapter.call(tool, params, idempotency_key)
       │     → ToolProviderResult {status, booking_ref, physical_state, ...}
       │
       ├─ 5. 熔断器反馈
       │     success/degraded → on_success()
       │     failure          → on_failure()
       │
       ├─ 6. Saga 记录 (物理操作成功)
       │     saga.record_step(SagaStep{step_id, tool, booking_ref, ...})
       │
       ├─ 7. UNKNOWN 异步确认
       │     physical_state == UNKNOWN → confirmator.schedule_confirmation()
       │
       └─ 8. 结果转换
            ToolProviderResult → ToolResult
```

---

## 六、数据库表 (ERD)

### 6.1 完整表结构

```
                         ┌─────────────────────┐
                         │       users         │
                         ├─────────────────────┤
                         │ id (PK, UUID)       │
                         │ email (UNIQUE)      │
                         │ hashed_password     │
                         │ oauth_provider      │
                         │ is_active           │
                         │ created_at          │
                         └──────┬──────┬───────┘
                                │      │
                    ┌───────────┘      └──────────────┐
                    │ 1:1                              │ 1:N
                    ▼                                  ▼
     ┌──────────────────────┐            ┌─────────────────────┐
     │    user_profiles     │            │       plans         │
     ├──────────────────────┤            ├─────────────────────┤
     │ user_id (PK,FK)      │            │ id (PK, UUID)       │
     │ nickname             │            │ user_id (FK)        │
     │ avatar_url           │            │ title               │
     │ preferences (JSON)   │            │ status              │
     │ travel_style         │            │ date_range (DATERANGE)
     │ preference_embedding │            │ group_type          │
     │   VECTOR(1536)       │            │ created_at          │
     │ home_address (JSON)  │            └──────┬──────┬───────┘
     │ updated_at           │                   │      │
     └──────────────────────┘         ┌─────────┘      └─────────────┐
                                      │ 1:N             1:N          │ 1:N
                                      ▼                 ▼            ▼
                         ┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
                         │   plan_slots    │ │  checkpoints │ │plan_adjustments  │
                         ├─────────────────┤ ├──────────────┤ ├──────────────────┤
                         │ id (PK, UUID)   │ │ id (PK, UUID)│ │ id (PK, UUID)    │
                         │ plan_id (FK)    │ │ plan_id (FK) │ │ plan_id (FK)     │
                         │ poi_id (STRING) │ │ version      │ │ trigger_reason   │
                         │ time_start      │ │ slots_snapshot│ │ original_slots   │
                         │ time_end        │ │   (JSON)     │ │ adjusted_slots   │
                         │ slot_status     │ │ consensus_   │ │ user_confirmed   │
                         │ booking_ref     │ │   status     │ │ created_at       │
                         │ buffer_minutes  │ │ created_at   │ └──────────────────┘
                         │ actual_end      │ └──────────────┘
                         └─────────────────┘

     ┌──────────────────┐   ┌─────────────────────┐   ┌──────────────────┐
     │       pois       │   │   refresh_tokens    │   │  llm_usage_logs  │
     ├──────────────────┤   ├─────────────────────┤   ├──────────────────┤
     │ id (PK, UUID)    │   │ id (PK, UUID)       │   │ id (PK, UUID)    │
     │ name             │   │ user_id (FK)        │   │ model_name       │
     │ lat              │   │ token_hash          │   │ provider         │
     │ lng              │   │ expires_at          │   │ prompt_tokens    │
     │ category         │   │ created_at          │   │ completion_tokens│
     │ tags (JSON)      │   └─────────────────────┘   │ latency_ms       │
     │ avg_rating       │                             │ cost_usd         │
     │ metadata (JSON)  │                             │ endpoint         │
     │ embedding        │                             │ created_at       │
     │   VECTOR(1536)   │                             └──────────────────┘
     │ group_suitability│
     │   (JSON)         │
     │ created_at       │
     └──────────────────┘

     ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
     │      plan_runs       │  │   plan_run_events    │  │ runtime_checkpoints  │
     ├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
     │ id (PK, UUID)        │  │ id (PK, UUID)        │  │ id (PK, UUID)        │
     │ run_id (UNIQUE)      │  │ event_id (UNIQUE)    │  │ plan_id              │
     │ plan_id              │  │ run_id               │  │ run_id               │
     │ thread_id            │  │ plan_id              │  │ version              │
     │ graph_version        │  │ node_name            │  │ state_json (JSON)    │
     │ request_payload(JSON)│  │ event_type           │  │ created_at           │
     │ final_status         │  │ payload_json (JSON)  │  └──────────────────────┘
     │ seed                 │  │ created_at           │
     │ debug                │  └──────────────────────┘
     │ error_message        │
     │ created_at           │
     └──────────────────────┘
```

### 6.2 表统计

| 表名 | 类型 | 索引数 | 用途 |
|------|:---:|:---:|------|
| `users` | 业务 | 1 (email unique) | 用户账户 |
| `user_profiles` | 业务 | 0 (PK only) | 用户画像 + pgvector偏好向量 |
| `plans` | 业务 | 3 (user_id, status, date_range) | 计划主表 |
| `plan_slots` | 业务 | 2 (plan_id, poi_id) | 计划时段子表 |
| `plan_adjustments` | 业务 | 0 | 计划调整审计记录 |
| `pois` | 业务 | 1 (category) | POI实体 + pgvector嵌入 |
| `refresh_tokens` | 业务 | 1 (token_hash) | JWT刷新令牌 |
| `checkpoints` | Agent | 1 (plan_id) | 计划检查点 |
| `plan_runs` | Agent | 3 (run_id unique, plan_id, thread_id) | 执行运行记录 |
| `plan_run_events` | Agent | 5 (event_id unique, run_id, plan_id, node_name, event_type) | 运行时事件审计 |
| `runtime_checkpoints` | Agent | 2 (plan_id, run_id) | 运行时快照 |
| `llm_usage_logs` | Agent | 0 | LLM调用用量日志 |

### 6.3 pgvector 向量字段

| 表 | 字段 | 维度 | 用途 |
|----|------|:---:|------|
| `user_profiles` | `preference_embedding` | 1536 | 用户偏好语义向量 |
| `pois` | `embedding` | 1536 | POI特征语义向量 |

---

## 七、SSE 事件类型

| # | 事件名 | 触发节点 | 数据载荷 | 前端处理 |
|---|--------|---------|---------|---------|
| 1 | `node_started` | 每个节点开始 | `{node_name}` | AgentMonitor 状态更新 |
| 2 | `node_succeeded` | 每个节点完成 | `{node_name, payload}` | 节点完成标记 |
| 3 | `node_failed` | 节点出错 | `{node_name, error}` | 错误提示 |
| 4 | `interrupt_requested` | ConsensusResolver | `{draft, message, suggested_decision}` | 弹出确认面板 |
| 5 | `interrupt_resumed` | 用户确认后 | `{decision}` | 关闭确认面板 |
| 6 | `tool_called` | ExecutionEngine | `{tool_name, slot_index}` | 工具执行中 |
| 7 | `tool_finished` | ExecutionEngine | `{tool_name, status, booking_id}` | 工具完成 |
| 8 | `plan_completed` | NotifyEngine | `{status: "done"}` | 计划完成 |

---

## 八、项目详细目录（精确到每一个文件）

```
snaptrip/
├── .claude/
│   ├── agents/
│   │   ├── agent-core-engineer.md          # Agent 核心工程师专用 agent
│   │   └── qa-pytest-tester.md             # QA pytest 测试专用 agent
│   └── settings.local.json                 # Claude Code 本地设置
│
├── .github/
│   ├── dependabot.yml                      # 依赖自动更新配置
│   └── workflows/
│       └── ci.yml                          # CI 流水线 (lint + test)
│
├── .ruff_cache/                            # Ruff 缓存
├── .env                                    # 环境变量（不提交）
├── .env.example                            # 环境变量模板
├── .env.test                               # 测试环境变量
├── .gitignore
├── .gitguardian.yml                        # GitGuardian 密钥检测
├── .pre-commit-config.yaml                 # Pre-commit hooks
│
├── pyproject.toml                          # Uv workspace 根定义
├── uv.lock                                 # 全仓库统一锁文件
├── Makefile                                # Unix 命令入口
├── Taskfile.yml                            # 跨平台 Task 任务运行器
├── docker-compose.yml                      # 7 服务编排
├── docker-compose.override.yml             # 本地覆盖（不提交）
├── docker-compose.override.example.yml     # 本地覆盖模板
├── docker-compose.test.yml                 # 测试 DB 编排
│
├── README.md                               # 项目说明
├── PROJECT.md                              # 项目规约（含开发规范）
├── AGENTS.md                               # AI 协作指令
│
├── shared/                                 # 共享库 (snaptrip-shared)
│   ├── pyproject.toml
│   └── snaptrip_shared/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py                   # Pydantic-Settings 配置中心
│       │   ├── constants.py                # 枚举 + 策略参数 (PlanStatus/SceneType/...)
│       │   ├── exceptions.py               # 统一异常体系 (SOCID: SnapTripException子类)
│       │   ├── exception_handlers.py        # FastAPI 全局异常处理器
│       │   ├── logging.py                  # structlog JSON 格式日志
│       │   ├── rate_limit.py               # Redis 滑动窗口限流
│       │   ├── response.py                 # 统一 API 响应 {code, message, data}
│       │   └── security.py                 # bcrypt + JWT + Prompt 注入防御
│       ├── db/
│       │   ├── __init__.py
│       │   ├── session.py                  # AsyncSession + async_engine + get_db
│       │   └── redis.py                    # Redis 连接池 + 客户端
│       └── schemas/
│           ├── __init__.py
│           └── plan.py                     # 共享 Pydantic Schema (PlanDraft/POI/ExecutionResult/...)
│
├── agent/                                  # Agent 核心引擎 (snaptrip-agent)
│   ├── pyproject.toml
│   └── src/agent/
│       ├── __init__.py
│       ├── graph.py                        # LangGraph 双模式编排 (9-node / 5-node v3)
│       ├── runtime.py                      # AgentRuntime DI 容器
│       ├── protocol.py                     # BaseAgent ABC + AgentContext + AgentResult
│       ├── engines/
│       │   ├── __init__.py
│       │   ├── intent_parser.py            # LLM + 关键词降级意图解析
│       │   ├── context_loader.py           # 用户画像 DB 查询
│       │   ├── memory_manager.py           # 历史偏好聚合 (MemoryFeatures)
│       │   ├── retrieval_engine.py         # Haversine + 种子数据 POI 检索
│       │   ├── planning_engine.py          # 两阶段求解器 (Phase1 代码 + Phase2 LLM)
│       │   ├── consensus_resolver.py       # 单/多用户共识协商
│       │   ├── execution_engine.py         # Tool DAG v3 (熔断+幂等+Saga+确认)
│       │   ├── fallback_engine.py          # Shadow+Ripple+孤儿取消
│       │   └── notify_engine.py            # 分享卡片渲染
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── llm.py                      # LLMAdapter (OpenRouter/DeepSeek/Kimi)
│       │   ├── marketplace.py              # MarketplaceClient → marketplace :8000
│       │   ├── mock_gateway.py             # MockAPIGateway (httpx) → mock-server :8001
│       │   ├── mock_tool_gateway.py        # MockToolGatewayAdapter (本地 mock)
│       │   ├── prompt.py                   # JinjaPromptAdapter (Jinja2 渲染)
│       │   └── persistence/
│       │       ├── __init__.py
│       │       ├── checkpoint.py           # 检查点持久化适配器
│       │       ├── plan.py                 # Plan 持久化适配器
│       │       ├── plan_run.py             # PlanRun 持久化适配器
│       │       ├── runtime_event.py        # RuntimeEvent 持久化适配器
│       │       └── user_profile.py         # UserProfile 持久化适配器
│       ├── ports/
│       │   ├── __init__.py
│       │   ├── events.py                   # EventSinkPort (抽象事件发射器)
│       │   ├── llm.py                      # LLMPort (抽象 LLM 调用)
│       │   ├── prompt.py                   # PromptPort (抽象模板渲染)
│       │   ├── repositories.py             # UserProfile/Plan/Checkpoint/RuntimeEvent Repository Ports
│       │   └── tools.py                    # ToolGatewayPort (抽象工具网关)
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── checkpoint.py               # CheckpointSnapshot
│       │   ├── events.py                   # RuntimeEvent
│       │   ├── llm.py                      # LLMResult
│       │   ├── runtime.py                  # PlanRuntimeState
│       │   ├── state.py                    # ExecutionState, ToolExecutionRecord, RepairState
│       │   ├── tool.py                     # TOOL_REGISTRY, ToolDefinition, ToolResult, ToolInvocation
│       │   └── tool_provider.py            # ToolProviderResult, PhysicalActionState, SagaStep
│       ├── state/
│       │   ├── __init__.py
│       │   ├── builder.py                  # build_initial_runtime_state
│       │   ├── events.py                   # build_runtime_event
│       │   ├── preconfirm.py               # 确认前状态构建 (context_from_state 等)
│       │   ├── postconfirm.py              # 确认后状态构建 (confirmation_from_resume 等)
│       │   └── response.py                 # state_to_response (PlanState → PlanResponse)
│       ├── events/
│       │   ├── __init__.py
│       │   ├── redis_bus.py                # Redis Pub/Sub 事件总线
│       │   └── store.py                    # RuntimeEventStore (事件存储)
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                     # LLMProvider 基类
│       │   ├── deepseek.py                 # DeepSeek API 实现
│       │   ├── kimi.py                     # Kimi (Moonshot) API 实现
│       │   ├── openrouter.py               # OpenRouter API 实现
│       │   └── registry.py                 # Provider 注册表
│       ├── services/
│       │   ├── __init__.py
│       │   ├── agent.py                    # AgentService (封装 CompiledGraph)
│       │   └── llm_gateway.py              # LLMGateway (统一 LLM 入口)
│       ├── skills/
│       │   ├── __init__.py                 # Skill 加载 + 匹配逻辑
│       │   ├── plan-fallback.md            # 容错策略 Skill
│       │   ├── restaurant-recommend.md     # 餐厅推荐 Skill
│       │   └── time-negotiation.md         # 时间协商 Skill
│       ├── prompts/
│       │   ├── __init__.py
│       │   ├── intent.j2                   # 意图解析 Prompt 模板
│       │   ├── planning.j2                 # 规划排序 Prompt 模板
│       │   └── notify.j2                   # 分享卡片渲染模板
│       ├── memory/
│       │   ├── __init__.py
│       │   └── service.py                  # MemoryService (pgvector 记忆读写)
│       ├── checkpointer/
│       │   ├── __init__.py
│       │   └── builder.py                  # Checkpointer 构建器
│       ├── models/
│       │   ├── __init__.py
│       │   ├── checkpoint.py               # Checkpoint ORM
│       │   ├── plan_run.py                 # PlanRun ORM
│       │   ├── plan_run_event.py           # PlanRunEvent ORM
│       │   ├── runtime_checkpoint.py       # RuntimeCheckpoint ORM
│       │   └── llm_usage_log.py            # LLMUsageLog ORM
│       └── tasks/
│           ├── __init__.py
│           └── plan_tasks.py               # Celery 异步任务 (submit_plan / confirm_plan)
│
├── backend/                                # API 网关 + 业务层 (snaptrip-backend)
│   ├── pyproject.toml
│   ├── Dockerfile.gateway                  # Marketplace 网关镜像
│   ├── Dockerfile.worker                   # Agent Worker 镜像
│   ├── .dockerignore
│   ├── alembic.ini
│   ├── init.sql                            # 数据库初始化 SQL
│   │
│   ├── marketplace/app/
│   │   ├── __init__.py
│   │   ├── main.py                         # FastAPI 入口 + lifespan + 异常注册
│   │   ├── celery_app.py                   # Celery 配置
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── plan.py                 # Plan API (create/confirm/get/status/stream)
│   │   │       ├── session.py              # SSE 流式推送路由
│   │   │       ├── auth.py                 # 认证路由 (register/login/refresh/logout)
│   │   │       └── user.py                 # 用户画像路由
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # Base + TimestampMixin + UUIDMixin
│   │   │   ├── users.py                    # users 表
│   │   │   ├── user_profile.py             # user_profiles 表 (含 preference_embedding)
│   │   │   ├── plan.py                     # plans 表
│   │   │   ├── plan_slot.py                # plan_slots 表
│   │   │   ├── plan_adjustment.py          # plan_adjustments 表
│   │   │   ├── poi.py                      # pois 表 (含 embedding)
│   │   │   └── refresh_token.py            # refresh_tokens 表
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                     # Auth 请求/响应 Schema
│   │   │   └── user.py                     # User 请求/响应 Schema
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── user_service.py             # 用户业务服务
│   │   ├── adapters/
│   │   │   └── amap/                       # 高德地图适配器
│   │   │       ├── __init__.py
│   │   │       ├── base.py                 # BaseAmapAdapter
│   │   │       ├── client.py               # Amap HTTP 客户端
│   │   │       ├── district_adapter.py     # 行政区划查询
│   │   │       ├── geo_mapper.py           # 地理坐标映射
│   │   │       ├── geocode_adapter.py      # 地理编码
│   │   │       ├── poi_adapter.py          # POI 搜索
│   │   │       ├── poi_mapper.py           # POI 数据映射
│   │   │       ├── registry.py             # AdapterRegistry
│   │   │       ├── route_adapter.py         # 路线规划
│   │   │       ├── route_mapper.py          # 路线映射
│   │   │       └── schemas/
│   │   │           ├── __init__.py
│   │   │           ├── district.py
│   │   │           ├── geocode.py
│   │   │           ├── poi.py
│   │   │           ├── route.py
│   │   │           ├── types.py
│   │   │           └── weather.py
│   │   └── data/
│   │       ├── __init__.py
│   │       └── seed_pois.py                # 种子 POI 数据 (16 条)
│   │
│   ├── alembic/
│   │   ├── env.py                          # Alembic 环境配置
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 36fc7e368593_create_schemas_agent_marketplace_.py
│   │       └── 7c7974cb12bd_create_tables.py
│   │
│   ├── scripts/
│   │   └── __init__.py
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                     # 全局 fixture
│       ├── unit/
│       │   ├── __init__.py
│       │   ├── adapters/
│       │   │   ├── __init__.py
│       │   │   ├── test_adapters.py
│       │   │   ├── test_amap_client.py
│       │   │   ├── test_mappers.py
│       │   │   └── test_registry.py
│       │   ├── test_agent_service.py
│       │   ├── test_auth.py
│       │   ├── test_cross_process_sse.py
│       │   ├── test_event_store.py
│       │   ├── test_execution_engine.py
│       │   ├── test_fallback_engine.py
│       │   ├── test_graph_runtime_state.py
│       │   ├── test_intent_parser.py
│       │   ├── test_llm_gateway.py
│       │   ├── test_marketplace_client.py
│       │   ├── test_memory_service.py
│       │   ├── test_mock_server.py
│       │   ├── test_phase1_di.py
│       │   ├── test_plan_api_async.py
│       │   ├── test_plan_tasks.py
│       │   ├── test_planning_engine.py
│       │   ├── test_postconfirm_state.py
│       │   ├── test_redis_event_bus.py
│       │   ├── test_response_state.py
│       │   ├── test_retrieval_engine.py
│       │   ├── test_user.py
│       │   └── test_vector_service.py
│       ├── integration/
│       │   ├── __init__.py
│       │   ├── conftest.py
│       │   ├── test_amap_integration.py
│       │   ├── test_api.py
│       │   ├── test_auth_api.py
│       │   ├── test_plan_api.py
│       │   └── test_user_api.py
│       ├── contract/
│       │   ├── test_amap_schemas.py
│       │   └── snapshots/
│       │       ├── amap_geocode.json
│       │       ├── amap_poi_search.json
│       │       └── amap_route_walking.json
│       └── eval/
│           ├── __init__.py
│           ├── eval_runner.py
│           ├── golden_intent.json
│           └── golden_plan.json
│
├── mock-services/                          # 模拟第三方服务
│   └── mock-meituan/
│       ├── pyproject.toml
│       ├── Dockerfile
│       └── app/
│           ├── __init__.py
│           ├── main.py                     # FastAPI Mock 入口 (:8001)
│           ├── schemas.py                  # 统一 ToolResult 响应
│           ├── core/
│           │   └── fault.py                # 故障注入 (X-Force-Fail, X-Simulate-Delay)
│           ├── data/
│           │   └── __init__.py
│           └── routers/
│               ├── __init__.py
│               ├── delivery.py             # /mock/delivery
│               ├── order.py                # /mock/order
│               ├── poi.py                  # /mock/poi/search
│               ├── queue.py                # /mock/queue/{poi_id}
│               ├── route.py                # /mock/route
│               └── weather.py              # /mock/weather
│       └── data/
│           └── seed_pois.json              # 50条预置POI
│
├── frontend/                               # React 19 SPA
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   ├── eslint.config.js
│   ├── index.html
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .gitignore
│   ├── README.md
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   └── src/
│       ├── main.tsx                        # React 入口
│       ├── App.tsx                         # 路由配置
│       ├── index.css                       # Tailwind 全局样式
│       ├── assets/
│       │   ├── hero.png
│       │   ├── react.svg
│       │   └── vite.svg
│       ├── api/
│       │   └── plan.ts                     # Plan API 调用封装
│       ├── types/
│       │   ├── plan.ts                     # Plan 类型定义
│       │   └── agent.ts                    # Agent 类型定义
│       ├── stores/
│       │   ├── planStore.ts                # Zustand 计划状态管理
│       │   └── agentStore.ts               # Zustand Agent 状态管理
│       ├── hooks/
│       │   └── usePlanSSE.ts               # SSE 流式监听 Hook
│       ├── components/
│       │   ├── agent/
│       │   │   └── AgentMonitor.tsx        # Agent 节点状态可视化
│       │   ├── common/
│       │   │   └── InputBar.tsx            # 自然语言输入框
│       │   ├── map/
│       │   │   └── MapView.tsx             # 高德地图容器
│       │   └── plan/
│       │       ├── PlanCard.tsx            # 计划卡片
│       │       ├── PlanTimeline.tsx        # 时间轴展示
│       │       └── ConfirmPanel.tsx        # 人机确认面板
│       ├── pages/
│       │   └── PlanPage.tsx                # 三栏布局主页面
│       └── test/
│           ├── App.test.tsx                # App 组件测试
│           └── setup.ts                    # 测试环境配置
│
└── docs/                                   # 项目文档
    ├── architecture/
    │   ├── 00-architecture-reference.md    # ★ 本文件 — 架构参考手册
    │   ├── 00-comprehensive-review.md      # 全架构审核报告 (2026-05-22)
    │   ├── 01-overview.md                  # 系统架构总览
    │   ├── 02-planning-algorithm.md        # 规划算法详解
    │   ├── 03-tool-orchestration.md        # Tool 编排设计
    │   ├── 04-exception-handling.md        # 异常处理体系
    │   ├── 05-agent-architecture.md        # Agent 架构设计
    │   ├── 06-agent-production-refactor.md # 生产化重构方案
    │   └── structure-review.md             # 结构审查 + 迁移计划
    ├── api/
    │   └── plan.md                         # Plan API 文档
    └── meetings/
        └── 03-decisions-log.md             # 架构决策记录 (ADR)
```

---

## 九、关键技术决策 (ADR 摘要)

| # | 决策 | 选型 | 理由 |
|---|------|------|------|
| 1 | Agent 框架 | **LangGraph** | StateGraph + PostgresSaver + interrupt + astream_events |
| 2 | 地图服务 | 高德 JS API 2.0 | 国内 POI 数据丰富，支持路径动画 |
| 3 | LLM 网关 | **OpenRouter** | 统一接入 DeepSeek-V3 / Claude-3.5-Sonnet / Kimi |
| 4 | Embedding | OpenAI text-embedding-3-small (1536d) | 与 pgvector vector(1536) 匹配 |
| 5 | 用户认证 | JWT + bcrypt + OAuth2 | 无状态 JWT 适合容器部署 |
| 6 | 异步队列 | Celery + Redis | 异步任务重试/持久化/监控 |
| 7 | 部署模式 | **模块化单体 + 6 进程** | 避免分布式复杂度，目录分层清晰 |
| 8 | 架构模式 | **Port/Adapter** | 依赖反转，Agent 通过抽象接口调用外部依赖 |
| 9 | 规划算法 | 两阶段：硬约束(纯代码) + 软约束(LLM) | 可预测 + 低成本 |
| 10 | Tool 编排 | **DAG + Saga** | 分层并行执行 + 补偿事务 |
| 11 | 数据库 | plans 1:N plan_slots | 分离聚合信息与单步细节 |
| 12 | 计划 | pgvector 统一存储向量 | 同一事务，避免不一致 |
