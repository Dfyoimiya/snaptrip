# 05 —— Agent 架构：LangGraph 驱动的三域 Agent 系统

## 总体架构

```
┌────────────── 接入层 ──────────────┐
│  POST /api/v1/plan/create          │
│  REST + SSE (astream_events)       │
└──────────────┬────────────────────┘
               │
┌──────────────▼────────────────────┐
│           编排层 (LangGraph)        │
│  ┌──────────────────────────────┐ │
│  │       Agent Hub              │ │
│  │  ├─ AgentRegistry (15 Agent) │ │
│  │  ├─ PostgresSaver (持久化)    │ │
│  │  ├─ PolicyEngine (条件路由)    │ │
│  │  └─ AgentBus (Redis Pub/Sub)  │ │
│  └──────────────────────────────┘ │
│                                    │
│  竞赛核心图 (主 StateGraph)          │
│  Intent → Context → Memory →      │
│  Retrieval → Planning →           │
│  Consensus → [Replan] → Execution │
│  → [Fallback] → Notify → DONE    │
│                                    │
│  课设扩展 Agent (独立子图/独立调用)   │
│  Recommend | Review | Dispatch    │
│  Pricing   | Quality              │
└──────────────┬────────────────────┘
               │
┌──────────────▼────────────────────┐
│            执行层                   │
│  Tool DAG 编排器 → Mock API 网关    │
│  10 个 Tool 分 4 层并行            │
│  CircuitBreaker + Saga Compensate │
└───────────────────────────────────┘
```

**关键变更**：编排层从手写 FSM（MasterController + PlanStateMachine）迁移为 LangGraph StateGraph，
通过声明式图定义替代手写状态转移矩阵，获得持久化、人机协同、流式输出等原生能力。

---

## LangGraph StateGraph 设计

### 图定义

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

class PlanState(TypedDict):
    plan_id: str
    user_input: str
    user_id: str
    lat: float
    lng: float
    status: str                       # IDLE/DRAFTING/PLANNING/CONFIRMING/EXECUTING/DONE/FAILED
    intent: IntentSchema | None
    enriched_intent: EnrichedIntent | None
    candidates: CandidatePool | None
    draft: PlanDraft | None
    execution: ExecutionResult | None
    share_card: ShareCard | None
    errors: list[AgentError]
    fallback_count: int
    locked_slots: list[int]
    checkpoint_version: int
    messages: list[dict]              # SSE 事件历史

graph = StateGraph(PlanState)

# 添加节点
graph.add_node("intent_parser", intent_parser_node)
graph.add_node("context_loader", context_loader_node)
graph.add_node("memory_manager", memory_manager_node)
graph.add_node("retrieval_engine", retrieval_engine_node)
graph.add_node("planning_engine", planning_engine_node)
graph.add_node("consensus_resolver", consensus_resolver_node)
graph.add_node("execution_engine", execution_engine_node)
graph.add_node("fallback_engine", fallback_engine_node)
graph.add_node("notify_engine", notify_engine_node)

# 添加边
graph.add_edge(START, "intent_parser")
graph.add_edge("intent_parser", "context_loader")
graph.add_edge("context_loader", "memory_manager")
graph.add_edge("memory_manager", "retrieval_engine")
graph.add_edge("retrieval_engine", "planning_engine")
graph.add_edge("planning_engine", "consensus_resolver")

# 条件边：根据用户确认结果分流
graph.add_conditional_edges(
    "consensus_resolver",
    route_consensus,
    {
        "confirmed": "execution_engine",
        "objection": "planning_engine",    # 增量重规划（带 locked_slots）
        "timeout": END,
    }
)

# 条件边：根据执行结果分流
graph.add_conditional_edges(
    "execution_engine",
    route_execution,
    {
        "full_success": "notify_engine",
        "partial_success": "fallback_engine",
        "full_failure": END,
    }
)

# 条件边：Fallback 后重试或失败
graph.add_conditional_edges(
    "fallback_engine",
    route_fallback,
    {
        "retry_planning": "planning_engine",
        "exhausted": END,
    }
)

graph.add_edge("notify_engine", END)

# 编译图（带持久化）
checkpointer = PostgresSaver(conn_string=settings.DATABASE_URL)
app = graph.compile(checkpointer=checkpointer)
```

### 图可视化

```
                         ┌─────────────┐
                         │   START     │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │intent_parser│ ← LLM 调用
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │context_     │
                         │loader       │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │memory_      │
                         │manager      │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │retrieval_   │
                         │engine       │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                ┌────────┤planning_    │◄─────────────┐
                │        │engine       │               │
                │        └──────┬──────┘               │
                │               │                       │
                │        ┌──────▼──────┐               │
                │   ┌───►│consensus_   │               │
                │   │    │resolver     │               │
                │   │    └──────┬──────┘               │
                │   │           │                       │
                │   │   ┌───────┼───────┐              │
                │   │   │       │       │              │
            obj │   │   │confirm│ timeout│              │
                │   │   │       │       │              │
                │   │   │  ┌────▼──┐ ┌──▼──┐          │
                │   └───┘  │execution│ END  │          │
                │          │engine  │      │          │
                │          └───┬──┬─┘      │          │
                │   partial│   │  │full    │          │
                │   success│   │  │success │          │
                │  ┌───────▼┐  │  │        │          │
                │  │fallback│  │  │        │          │
                │  │engine  │  │  │        │          │
                │  └───┬──┬─┘  │  │        │          │
                │      │  │    │  │        │          │
                │retry │  │exhausted│      │          │
                └──────┘  │  ┌─▼──▼─┐     │          │
                          │  │ END  │     │          │
                          │  └─────┘     │          │
                          │        ┌─────▼──┐      │
                          │        │notify_ │      │
                          │        │engine  │      │
                          │        └────┬───┘      │
                          │             │           │
                          │        ┌────▼───┐      │
                          │        │  END   │      │
                          │        └────────┘      │
                          │                         │
                          └─────────────────────────┘
                                   ripple reschedule
```

### 与手写 FSM 对照

| 能力 | 手写 FSM (当前) | LangGraph |
|------|:--:|:--:|
| 状态定义 | 手写 dataclass + dict | `TypedDict` |
| 转移规则 | `TRANSITIONS` 列表 + 守卫函数 | `add_edge` / `add_conditional_edges` |
| 持久化 | 无 → 需自己对接 Redis/DB | `PostgresSaver(conn)` 一行 |
| 人机协同 | 需自己设计 wait/resume | `interrupt()` / `Command(resume=...)` |
| 流式输出 | 手动 `yield` SSE 事件 | `astream_events()` 自动追踪每个 node |
| 重试 | 无 | `node(retry=RetryPolicy(...))` |
| 并行 | `asyncio.gather` 手写 | `Send` API 原生支持 |
| 可观测 | 需集成 OpenTelemetry | LangSmith 自动追踪 |

---

## 15 Agent 分类矩阵

### 按认知层级分类

| 分类 | Agent | 归属 | LLM? | 核心职责 | 输入 | 输出 |
|------|-------|:---:|:---:|---------|------|------|
| **感知** | IntentParser | 竞赛 | ✅ | 自然语言→结构化意图 | `raw_query` | `IntentSchema` |
| **感知** | ContextLoader | 竞赛 | ❌ | 用户画像+历史偏好加载 | `IntentSchema + user_id` | `EnrichedIntent` |
| **感知** | MemoryManager | 竞赛 | ❌ | 向量记忆检索+Skill匹配 | `EnrichedIntent` | 记忆增强向量 |
| **认知** | RetrievalEngine | 竞赛 | ❌ | POI并行检索+硬约束过滤 | `EnrichedIntent` | `CandidatePool` |
| **认知** | PlanningEngine | 竞赛 | ✅ | 两阶段规划(Phase1代码+Phase2 LLM) | `CandidatePool` | `PlanDraft` |
| **认知** | RecommendAgent | 课设 | ✅ | 个性化推荐(协同过滤+语义) | `UserProfile + context` | `RecommendList` |
| **协作** | ConsensusResolver | 竞赛 | ❌ | 多利益方共识(投票+帕累托补偿) | `votes[]` | `ConsensusDecision` |
| **执行** | ExecutionEngine | 竞赛 | ❌ | Tool DAG编排+分层并行执行 | `PlanDraft` | `ExecutionResult` |
| **执行** | DispatchAgent | 课设 | ✅ | 骑手智能调度+ETA预测 | `orders[]` | `DispatchPlan` |
| **执行** | PricingAgent | 课设 | ✅ | 动态定价(供需+时段+天气) | `POI + demand` | `PriceDecision` |
| **容错** | FallbackEngine | 竞赛 | ❌ | Shadow候选+涟漪重排 | `FailedSlot + Checkpoint` | `RevisedPlan` |
| **输出** | NotifyEngine | 竞赛 | ❌ | 分享卡片生成(Playwright) | `PlanDraft + ExecutionResult` | `ShareCard` |
| **分析** | ReviewAgent | 课设 | ✅ | 评价情感分析+自动摘要 | `reviews[]` | `ReviewSummary` |
| **监控** | QualityAgent | 课设 | ❌ | 服务质量实时监控+异常告警 | `metrics[]` | `AlertDecision` |

### 竞赛核心：9 Agent 链路

| # | Agent | 超时 | 降级策略 |
|---|-------|:---:|---------|
| 1 | **Intent Parser** | 2s | LLM 超时 → 关键词匹配（confidence=0.4） |
| 2 | **Context Loader** | 500ms | 超时 → 返回空 profile |
| 3 | **Memory Manager** | — | 无历史 → 返回默认向量 |
| 4 | **Retrieval Engine** | 1s | 超时 → Redis 缓存（TTL 1h） |
| 5 | **Planning Engine** | 3.1s | Phase2 超时 → Phase1 评分排序 |
| 6 | **Consensus Resolver** | 100ms | 单用户 → auto_confirm=true |
| 7 | **Execution Engine** | 10s | 单 Tool 超时不阻塞同层 |
| 8 | **Fallback Engine** | 2s | Shadow→重检索→Saga 补偿→最多2次 |
| 9 | **Notify Engine** | 500ms | 失败不影响主流程 |

### 课设扩展：5 Agent

| # | Agent | 超时 | 降级策略 |
|---|-------|:---:|---------|
| 10 | **Recommend Agent** | 2s | LLM → 协同过滤规则 |
| 11 | **Review Agent** | 1.5s | LLM → 评分统计 |
| 12 | **Dispatch Agent** | 3s | LLM → 贪心调度 |
| 13 | **Pricing Agent** | 1s | LLM → 固定定价策略 |
| 14 | **Quality Agent** | 500ms | 规则引擎，无 LLM |

---

## Agent Node 实现规范

每个 Agent 需要改写为 LangGraph Node 函数，签名为：

```python
async def agent_node(state: PlanState) -> dict:
    """返回 PlanState 的部分更新，LangGraph 自动合并到全局状态"""
    ...
    return {"draft": draft, "checkpoint_version": state["checkpoint_version"] + 1}
```

**规范**：
- Node 函数**不直接修改 state**，返回 dict 由 LangGraph 合并
- 所有外部调用（LLM/DB/HTTP）必须 try/except，异常写入 `state["errors"]`
- 关键节点使用 `RetryPolicy`：`graph.add_node("...", agent_node, retry=RetryPolicy(max_attempts=2))`
- 人机协同节点使用 `interrupt()`：在 Consensus Resolver 处挂起等待用户

---

## Agent 通信协议

```
┌───────────────────────────────────────────────────────────────┐
│                     Agent 通信层                               │
│                                                               │
│  竞赛核心 Agent:                                               │
│    同进程内存传递 (Pydantic 对象, 零序列化)                      │
│    PlanState → node → dict update → PlanState                 │
│                                                               │
│  课设扩展 Agent:                                               │
│    AgentBus (Redis Pub/Sub) 异步通信                           │
│    {                                                          │
│      "correlation_id": "uuid",     ← 全链路追踪                │
│      "source_agent": "planning_engine",                       │
│      "target_agent": "recommend_agent",                       │
│      "event_type": "request_recommendation",                  │
│      "payload": { ... },                                      │
│      "timestamp": "2026-05-17T10:00:00Z"                      │
│    }                                                          │
│                                                               │
│  传统服务调用:                                                  │
│    REST/HTTP (httpx AsyncClient)                              │
│    Mock API (:8001) 或 真实 API                               │
│                                                               │
│  前端实时推送:                                                  │
│    SSE (sse-starlette) 或 astream_events()                    │
│    10 种事件类型: intent/retrieval/planning/planning_done/    │
│    execution/execution_done/fallback/consensus/notify/done    │
└───────────────────────────────────────────────────────────────┘
```

---

## Agent 注册与发现（AgentRegistry）

```python
class AgentRegistry:
    """Agent 注册中心，管理 15 Agent 的生命周期和元数据"""

    _registry: dict[str, AgentMeta] = {}

    def register(self, name: str, node: Callable, meta: AgentMeta):
        self._registry[name] = meta

    def get_node(self, name: str) -> Callable:
        return self._nodes[name]

    def list_by_category(self, category: AgentCategory) -> list[str]:
        """按分类查询：PERCEPTION / COGNITION / COLLABORATION / EXECUTION / FALLBACK / OUTPUT / ANALYSIS / MONITOR"""
        return [n for n, m in self._registry.items() if m.category == category]

    def list_by_domain(self, domain: str) -> list[str]:
        """按域查询：competition / curriculum"""
        return [n for n, m in self._registry.items() if m.domain == domain]


@dataclass
class AgentMeta:
    name: str
    category: AgentCategory      # 认知层级
    domain: str                  # competition | curriculum
    uses_llm: bool
    timeout_ms: int
    retry_max: int = 0
    is_stub: bool = False        # TODO: 待实现
```

---

## 执行层 Tool DAG

### Tool 注册表（10 个 Tool）

| Layer | Tool | 依赖 | 幂等 | 超时 | Mock 失败率 | 领域 |
|-------|------|------|------|------|------------|:---:|
| L0 | `search_poi` | 无 | 是 | 1.5s | 0% | 竞赛 |
| L0 | `get_user_profile` | 无 | 是 | 0.5s | 0% | 竞赛 |
| L1 | `check_queue` | `search_poi` | 是 | 1s | 0% | 竞赛 |
| L1 | `check_availability` | `search_poi` | 是 | 1s | 0% | 竞赛 |
| L1 | `check_child_facility` | `search_poi` | 是 | 0.8s | 0% | 竞赛 |
| L1 | `calculate_route` | `search_poi` | 是 | 0.8s | 0% | 竞赛 |
| L2 | `book_table` | `check_queue, check_availability` | 否 | 2s | 20% | 竞赛 |
| L2 | `book_ticket` | `check_availability` | 否 | 2s | 10% | 竞赛 |
| L2 | `order` | `search_poi` | 否 | 1.5s | 5% | 竞赛 |
| L2 | `deliver` | `order` | 否 | 2s | 5% | 课设 |
| L2 | `ride_hail` | `calculate_route` | 否 | 1.5s | 5% | 课设 |
| L3 | `notify` | `book_table, book_ticket, order` | 是 | 1s | 0% | 竞赛 |

### 分层执行示例（家庭场景 3 slots）

| 层级 | Tool 调用 | 并行度 | 预计耗时 |
|------|----------|--------|---------|
| L0 | `search_poi`(绘本馆), `search_poi`(餐厅), `search_poi`(蛋糕店), `get_user_profile` | 4 | ~200ms |
| L1 | `check_queue`(餐厅), `check_availability`(绘本馆), `check_child_facility`(绘本馆), `calculate_route`(家→绘本馆) | 4 | ~300ms |
| L2 | `book_table`(餐厅), `book_ticket`(绘本馆), `order`(蛋糕→餐厅) | 3 | ~500ms |
| L3 | `notify`(分享卡片) | 1 | ~100ms |

---

## 核心工程机制

### 影子规划（Shadow Planning）
主规划生成时，关键 Slot 并行生成 Shadow Candidate（替代 POI），预查可用性存入 Checkpoint。
执行失败时直接激活 Shadow，跳过重新检索，降低 Fallback 延迟。

### 涟漪重排（Ripple Rescheduling）
局部替换 Slot 后，向下游传播时间偏移，检查营业时间冲突，递归触发二次 Fallback。
若涟漪超出营业时间窗口，触发全局重规划（回到 Planning Engine）。

### 增量共识（Incremental Consensus）
加权投票 + 锁定覆盖检测 + 帕累托补偿计算。
- Phase 1（当前）：单用户模式 auto_confirm
- Phase 2（未来）：多 stakeholder 加权投票，`OVERRIDE_THRESHOLD=0.8` 可解锁已确认 slot

### 人机协同中断（Human-in-the-Loop）
通过 LangGraph `interrupt()` 原语实现：
```python
def consensus_resolver_node(state: PlanState) -> dict:
    if state.get("user_decision") is None:
        # 挂起，等待用户输入
        user_input = interrupt({
            "event": "consensus",
            "draft": state["draft"],
            "message": "请确认或修改计划"
        })
        return {"user_decision": user_input}
    return state
```
前端通过 SSE 收到 `interrupt` 事件后展示 ConfirmPanel，
用户点击确认/反对后，通过 `thread.update_state` 或 REST API 推送 `Command(resume=...)`。

### 记忆演化与技能蒸馏（Memory Evolution）
历史规划经验 → 策略模板 → Skill 文件（Markdown）→ 从 LLM 生成为微调。
- Phase 1（当前）：Memory Manager stub
- Phase 2（未来）：pgvector 语义检索 + Skill 文件静态匹配

### 分层超时控制
- 单 Tool：3s，超时不阻塞同层其他 Tool
- 单层：5s（含并行聚合）
- 总 DAG：10s，超时返回 `partial_success` 或 `full_failure`

### 熔断器（CircuitBreaker）
- 连续 5 次失败 → `circuit_open`，后续直接跳过
- 成功后 `failure_count` 归零
- 不实现完整三态（Closed/Open/Half-Open），采用单向打开 + 手动恢复

---

## SSE 事件流（10 种）

| 事件 | 状态 | 含义 | 数据字段 |
|------|------|------|----------|
| `intent` | DRAFTING | Intent Parser 完成约束提取 | `{"intent_id": "...", "constraints": {...}}` |
| `retrieval` | DRAFTING→PLANNING | Retrieval Engine 返回候选池 | `{"query": "...", "count": 25}` |
| `planning` | PLANNING | Planning Engine 执行中 | `{"status": "sorting", "candidates": 10}` |
| `planning_done` | PLANNING→CONFIRMING | 规划草案就绪 | `{"plan": PlanResponse}` |
| `consensus` | CONFIRMING | Consensus Resolver 等待/完成 | `{"decision": "pending"|"confirmed"|"objection"}` |
| `execution` | CONFIRMING→EXECUTING | Tool DAG 执行中（逐工具） | `{"tool": "book_table", "status": "running"}` |
| `execution_done` | EXECUTING | 全部 Tool 完成 | `{"success_count": 3, "failed_count": 0}` |
| `fallback` | EXECUTING→CONFIRMING | Fallback Engine 局部替换 | `{"original": "...", "replacement": "..."}` |
| `notify` | DONE | Notify Engine 分享链路 | `{"card_url": "https://..."}` |
| `done` | DONE | 全流程结束 | `{"plan_id": "..."}` |

**LangGraph 实现**：使用 `astream_events()` 替代手动 SSE 拼接：
```python
async for event in graph.astream_events(initial_state, config, version="v2"):
    if event["event"] == "on_chain_end":
        yield _sse(event["name"], event["data"]["output"])
```

---

## 执行层与编排层边界

| 方向 | 编排层→执行层 | 执行层→编排层 |
|------|-------------|-------------|
| **通信** | LangGraph 状态传递 | node 更新 PlanState |
| **数据** | `PlanDraft` (含 slots + shadow) | `ExecutionResult` (含 failed_slots + booking_ids) |
| **触发** | graph 执行到 execution_engine node | Tool DAG 分层执行完毕 |
| **异常** | 不干预执行过程 | failed_slots 非空 → conditional_edges 路由到 Fallback |
| **超时** | 设置 total_dag_ms=10000 | 超时返回 `partial_success` 或 `full_failure` |
| **重试** | LangGraph RetryPolicy 控制 node 级别 | Tool 级别 CircuitBreaker 控制 |

**关键约束**：
- 编排层有状态（PlanState 持久化到 PostgresSaver）
- 执行层无状态（Tool DAG 调用 Mock API，不保留本地状态）
- 编排层通过 conditional_edges 决定执行后的路由（full_success → Notify | partial → Fallback | full_failure → END）

---

## 与外部 LLM/Agent 框架的集成边界

```
SnapTrip Backend (FastAPI + LangGraph)
  │
  ├─ Agent 编排：LangGraph StateGraph (内存调度，非网络调用)
  │   ├─ PostgresSaver：状态持久化到 PostgreSQL
  │   └─ astream_events()：自动生成 SSE 流，无需手动拼接
  │
  ├─ LLM 调用：仅 Intent Parser + Planning Phase 2
  │   ├─ 通过 OpenRouter 统一接入
  │   ├─ 模型：DeepSeek-V3 / Claude-3.5-Sonnet
  │   └─ 超时 2-3s，降级为纯代码规则
  │
  ├─ Tool 调用：httpx → Mock API (:8001)
  │   ├─ ExecutionEngine 通过 MockAPIGateway 调用
  │   ├─ CircuitBreaker + RetryPolicy
  │   └─ Mock 失败率模拟异常自愈
  │
  ├─ 记忆读写：Memory Manager → PostgreSQL (pgvector) + Redis
  │   ├─ pgvector: 语义检索 (embedding cosine similarity)
  │   └─ Redis: 会话缓存 + Pub/Sub AgentBus
  │
  ├─ Skill 文件：本地文件系统 (agents/skills/*.md)
  │   ├─ 格式：## 触发条件 / ## 执行步骤 / ## 示例
  │   └─ Hermes ACP 协议预留（Phase 2）
  │
  └─ 课设 Agent：通过 AgentBus (Redis Pub/Sub) 异步解耦
      ├─ Recommend / Review / Dispatch / Pricing / Quality
      └─ 独立子图或独立函数调用
```
