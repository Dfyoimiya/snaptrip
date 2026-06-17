# 06 —— Agent 生产化重构方案

> **文档状态**: 生产化重构设计文档（2026-05-17）。
>
> **实施进度**:
> - **Phase 1** (收敛运行入口): ✅ 已完成 — `AgentRuntime` DI 容器 + `ports/`/`adapters/` 分层 + 双模式 graph + `plan_service.py` 已移除
> - **Phase 2** (typed runtime state): ✅ 已完成 — `PlanRuntimeState` + `RuntimeEvent` 等强类型 Schema 已就位
> - **Phase 3** (统一外部出口): ✅ 已完成 — `LLMPort`/`ToolGatewayPort`/`PromptPort`/`EventSinkPort` Protocol 定义 + adapters 实现
> - **Phase 4** (confirm/fallback/checkpoint 闭环): 🚧 部分完成 — `ConfirmationState` + `CheckpointSnapshot` 已定义，共识仍为单用户模式
> - **Phase 5** (事件流与持久化): ✅ 已完成 — `MemorySaver`/`PostgresSaver` + `plan_run_events` + `RuntimeEventStore` + Redis Pub/Sub SSE
> - **Phase 6** (补生产测试): 🚧 进行中
>
> 当前实际架构见 [`00-architecture-reference.md`](./00-architecture-reference.md)。

## 目标

本方案面向 SnapTrip 当前 Agent 实现，目标不是继续扩充 Agent 数量，而是把现有链路从「可演示」收敛为「可上线、可回放、可观测、可演进」的生产级架构。

核心目标有 5 个：

1. **单一编排真相源**：只保留一套实际生效的编排内核
2. **强 Schema 契约**：所有节点输入输出可校验、可演进、可回放
3. **人机协同闭环**：确认、反对、局部修改、Fallback 形成真实重规划链路
4. **外部依赖统一出口**：LLM、DB、Mock API、事件流全部走 Port/Adapter
5. **运行可追踪**：支持持久化、幂等、审计、SSE 订阅、离线复盘

---

## 对现状的判断

当前项目已经具备较好的方向感：

- 已经引入 `LangGraph`
- 已经有 `Pydantic` Schema
- 已经区分了 `Intent / Retrieval / Planning / Execution / Fallback`
- 已经开始建设 `structlog`、`LLMGateway`、`Saga`、`Checkpoint`

但还存在 4 类关键问题：

1. **多套并行真相源**
   - `app/agents/graph.py`
   - `app/agents/hub.py`
   - `app/core/state.py`
   - `app/services/plan_service.py`

2. **状态流未闭环**
   - confirm objection 不能携带 slot 级修改意图
   - fallback 结果没有真正进入下一轮规划输入
   - checkpoint/locked slots 设计存在但未接入主链路

3. **运行时协议偏弱**
   - 节点之间大量依赖 `dict[str, Any]`
   - history 手工拼装
   - LLM 调用未统一走网关
   - SSE 重新驱动图而不是订阅真实运行事件

4. **生产保障不完整**
   - 默认 `MemorySaver`，无持久化恢复
   - 缺少幂等键、graph version、prompt version、seed
   - 测试主要覆盖 happy path，缺少 interrupt/resume/recovery/fallback exhaustion

---

## 重构原则

### 1. 编排只保留一套

生产运行只保留 `LangGraph` 一套编排内核。

- `graph.py` 成为唯一运行入口
- `hub.py` 不再参与运行时调度
- `state.py` 不再维护第二套可变 FSM
- `plan_service.py` 不再保留第二套简化规划主流程

保留策略：

- `hub.py` 中真正有价值的内容，抽成领域服务
- `state.py` 中真正有价值的内容，抽成状态规则库或 guard library
- 其余废弃实现逐步删除

### 2. 领域逻辑与编排逻辑分离

`LangGraph Node` 只负责：

- 从图状态读取输入
- 调用领域服务
- 写回标准化状态
- 记录事件和错误

领域服务负责：

- 意图解析
- 检索
- 规划求解
- 执行编排
- 局部修复

这样可以避免把业务规则写死在图节点里，后续更容易测试和复用。

### 3. 所有外部能力走 Adapter

任何会变化、会失败、会被替换的依赖，都不允许直接散落在 Agent 里：

- LLM
- Prompt 渲染
- 用户画像仓储
- 记忆仓储
- Tool Gateway
- Checkpoint 仓储
- Event Sink

### 4. 所有关键节点都要可重试、可回放、可解释

每次运行必须至少落这些信息：

- `run_id`
- `plan_id`
- `thread_id`
- `graph_version`
- `prompt_version`
- `model_name`
- `request_hash`
- `seed`
- `state_snapshot`
- `node_events`

---

## 目标架构

### 总览

```
Frontend
  -> REST create/confirm/query
  -> SSE subscribe

FastAPI API Layer
  -> PlanApplicationService
  -> AgentRuntime

AgentRuntime (唯一编排真相源)
  -> LangGraph Graph
  -> Checkpoint Store
  -> Event Store

Domain Services
  -> Intent Domain
  -> Context Domain
  -> Memory Domain
  -> Retrieval Domain
  -> Planning Domain
  -> Execution Domain
  -> Replan Domain
  -> Notification Domain

Ports
  -> LLMPort
  -> PromptPort
  -> ToolGatewayPort
  -> UserProfileRepoPort
  -> PlanRepoPort
  -> CheckpointRepoPort
  -> EventSinkPort

Adapters
  -> OpenRouterLLMAdapter
  -> JinjaPromptAdapter
  -> Postgres*Repository
  -> MockAPIGatewayAdapter
  -> SSE/EventStore Adapter
```

### 运行链路

```
create_plan
  -> build request envelope
  -> graph invoke
  -> interrupt on confirm
  -> resume with user decision
  -> execution / fallback / replan
  -> notify
  -> persist final state
  -> stream events from event store
```

---

## 新目录设计

推荐在 `backend/app/` 下按下面结构重组：

```text
backend/app/
├── main.py
├── api/
│   └── v1/
│       ├── plan.py
│       ├── session.py
│       ├── auth.py
│       └── user.py
│
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── constants.py
│   ├── errors.py
│   ├── response.py
│   └── telemetry.py
│
├── agent_runtime/
│   ├── graph.py
│   ├── state.py
│   ├── registry.py
│   ├── events.py
│   ├── policies.py
│   ├── checkpointing.py
│   └── nodes/
│       ├── intent_node.py
│       ├── context_node.py
│       ├── memory_node.py
│       ├── retrieval_node.py
│       ├── planning_node.py
│       ├── confirm_node.py
│       ├── execution_node.py
│       ├── fallback_node.py
│       └── notify_node.py
│
├── domain/
│   ├── intent/
│   │   ├── service.py
│   │   ├── parser.py
│   │   └── rules.py
│   ├── context/
│   │   └── service.py
│   ├── memory/
│   │   └── service.py
│   ├── retrieval/
│   │   ├── service.py
│   │   └── ranking.py
│   ├── planning/
│   │   ├── service.py
│   │   ├── solver.py
│   │   ├── scoring.py
│   │   └── slot_builder.py
│   ├── execution/
│   │   ├── service.py
│   │   ├── dag.py
│   │   ├── compensation.py
│   │   └── policies.py
│   ├── replan/
│   │   ├── service.py
│   │   ├── checkpoint.py
│   │   └── diff.py
│   └── notification/
│       └── service.py
│
├── ports/
│   ├── llm.py
│   ├── prompt.py
│   ├── tools.py
│   ├── repositories.py
│   └── events.py
│
├── adapters/
│   ├── llm/
│   │   └── openrouter.py
│   ├── prompt/
│   │   └── jinja.py
│   ├── tools/
│   │   └── mock_gateway.py
│   ├── persistence/
│   │   ├── plan_repository.py
│   │   ├── user_profile_repository.py
│   │   ├── checkpoint_repository.py
│   │   └── run_event_repository.py
│   └── events/
│       └── sse_sink.py
│
├── schemas/
│   ├── api/
│   │   ├── plan.py
│   │   └── common.py
│   ├── agent/
│   │   ├── runtime.py
│   │   ├── state.py
│   │   ├── events.py
│   │   └── checkpoint.py
│   ├── domain/
│   │   ├── intent.py
│   │   ├── planning.py
│   │   ├── execution.py
│   │   ├── replan.py
│   │   └── poi.py
│   └── tool.py
│
├── services/
│   ├── plan_application_service.py
│   └── llm_gateway.py
│
├── models/
├── db/
├── tasks/
└── data/
```

---

## 模块职责

### `agent_runtime/`

只负责运行时编排。

- 图定义
- 条件路由
- interrupt/resume
- checkpoint 读写
- node lifecycle event 写入

### `domain/`

只负责业务规则。

- 不依赖 FastAPI
- 不依赖 LangGraph
- 不直接依赖 HTTP API 细节

### `ports/`

定义边界接口。

- 领域层依赖 port
- adapter 实现 port

### `adapters/`

接外部系统。

- OpenRouter
- Jinja2 prompt
- Postgres
- Mock server
- SSE/event store

### `schemas/`

强制分层管理 schema。

- `api`：接口入参与返回
- `agent`：运行时状态、事件、checkpoint
- `domain`：业务实体和值对象

---

## 关键 Schema 设计

下面给出建议的关键 schema 草图。

### 1. Request Envelope

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PlanRequestEnvelope(BaseModel):
    request_id: str
    plan_id: str
    session_id: str
    user_id: str
    user_input: str
    lat: float
    lng: float
    created_at: datetime
    idempotency_key: str
    graph_version: str
    client_version: str | None = None
    debug: bool = False
```

作用：

- 统一入口请求
- 支持幂等与回放
- 绑定 graph version

### 2. Runtime State

```python
from typing import Literal

from pydantic import BaseModel, Field


PlanRuntimeStatus = Literal[
    "created",
    "drafting",
    "planning",
    "confirming",
    "executing",
    "repairing",
    "done",
    "failed",
]


class PlanRuntimeState(BaseModel):
    request: PlanRequestEnvelope
    status: PlanRuntimeStatus = "created"

    intent: IntentResult | None = None
    context_profile: ContextProfile | None = None
    memory_features: MemoryFeatures | None = None
    candidate_pool: CandidatePool | None = None
    draft: PlanDraft | None = None
    confirmation: ConfirmationState | None = None
    execution: ExecutionState | None = None
    repair: RepairState | None = None
    notification: NotificationState | None = None

    locked_slots: list[int] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)
    event_ids: list[str] = Field(default_factory=list)
    seed: int = 0
```

作用：

- 替代零散 `dict[str, Any]`
- 让图状态可校验、可恢复、可演进

### 3. Intent Result

```python
class IntentResult(BaseModel):
    city: str | None = None
    guest_count: int = 2
    budget: int | None = None
    scene_type: str = "solo"
    type_prefs: list[str] = Field(default_factory=list)
    mood_prefs: list[str] = Field(default_factory=list)
    time_window: TimeRange | None = None
    implicit_constraints: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    source: Literal["llm", "keyword", "hybrid"] = "keyword"
    prompt_version: str | None = None
    model_name: str | None = None
```

新增重点：

- `source`
- `prompt_version`
- `model_name`

### 4. Candidate Pool

```python
class CandidateReason(BaseModel):
    poi_id: str
    recall_source: Literal["city_filter", "memory_boost", "fallback", "manual"]
    score: float
    matched_constraints: list[str] = Field(default_factory=list)


class CandidatePool(BaseModel):
    query_id: str
    candidates: list[POI] = Field(default_factory=list)
    reasons: list[CandidateReason] = Field(default_factory=list)
    total: int = 0
```

作用：

- 支撑解释性
- 支撑 rerank/fallback 分析

### 5. Plan Draft

```python
class SlotAlternative(BaseModel):
    poi_id: str
    prechecked: bool = False
    score: float = 0.0


class PlanSlot(BaseModel):
    sequence: int
    poi: POI
    time_range: TimeRange
    action: str
    estimated_cost: int = 0
    move_time_min: int = 0
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)
    alternatives: list[SlotAlternative] = Field(default_factory=list)


class PlanDraft(BaseModel):
    draft_id: str
    plan_id: str
    version: int
    slots: list[PlanSlot] = Field(default_factory=list)
    total_cost: int = 0
    total_time_min: int = 0
    confidence: float = 0.0
    solver_version: str
    seed: int
```

把原来的 `shadow_id` 升级成 `alternatives[]`，避免只能表达一个替代候选。

### 6. Confirmation State

```python
class UserChangeRequest(BaseModel):
    slot_index: int | None = None
    instruction: str = ""
    replace_only: bool = False


class ConfirmationState(BaseModel):
    status: Literal["pending", "confirmed", "rejected", "partial_change"] = "pending"
    locked_slots: list[int] = Field(default_factory=list)
    rejected_slots: list[int] = Field(default_factory=list)
    user_change_requests: list[UserChangeRequest] = Field(default_factory=list)
    confirmed_at: datetime | None = None
```

作用：

- 让“反对”从布尔信号升级成结构化修改意图

### 7. Execution State

```python
class ToolExecutionRecord(BaseModel):
    invocation_id: str
    slot_index: int
    tool_name: str
    layer: int
    status: Literal["success", "failure", "timeout", "skipped"]
    error_code: str | None = None
    error_message: str | None = None
    booking_id: str | None = None
    latency_ms: int = 0
    depends_on: list[str] = Field(default_factory=list)


class ExecutionState(BaseModel):
    run_id: str
    status: Literal["full_success", "partial_success", "full_failure"]
    tool_records: list[ToolExecutionRecord] = Field(default_factory=list)
    confirmed_bookings: dict[int, str] = Field(default_factory=dict)
    failed_slot_indices: list[int] = Field(default_factory=list)
    total_elapsed_ms: int = 0
```

重点变化：

- 失败与超时统一纳入状态机语义
- 不再依赖模糊的 `dict` 嵌套

### 8. Repair / Replan State

```python
class SlotDiff(BaseModel):
    slot_index: int
    old_poi_id: str
    new_poi_id: str
    old_poi_name: str
    new_poi_name: str
    time_shift_min: int = 0


class CheckpointSnapshot(BaseModel):
    version: int
    locked_slots: list[int] = Field(default_factory=list)
    mutable_slots: list[int] = Field(default_factory=list)
    draft: PlanDraft


class RepairState(BaseModel):
    retry_count: int = 0
    checkpoint: CheckpointSnapshot | None = None
    revised_draft: PlanDraft | None = None
    diffs: list[SlotDiff] = Field(default_factory=list)
    exhausted: bool = False
```

重点变化：

- repair 的产物直接是 `revised_draft`
- 下一轮 planning 明确读取 checkpoint 与 mutable window

### 9. Agent Error

```python
class AgentError(BaseModel):
    code: str
    message: str
    node_name: str
    retryable: bool = False
    detail: dict[str, str] = Field(default_factory=dict)
```

不要再只用字符串异常信息。

### 10. Runtime Event

```python
class RuntimeEvent(BaseModel):
    event_id: str
    run_id: str
    plan_id: str
    node_name: str
    event_type: Literal[
        "node_started",
        "node_succeeded",
        "node_failed",
        "interrupt_requested",
        "interrupt_resumed",
        "tool_called",
        "tool_finished",
        "plan_completed",
    ]
    timestamp: datetime
    payload: dict = Field(default_factory=dict)
```

SSE 应该从这个事件模型出发，而不是重新跑图。

---

## Port 设计

### LLM Port

```python
from typing import Protocol


class LLMPort(Protocol):
    async def chat_json(
        self,
        *,
        prompt: str,
        model_alias: str,
        timeout_s: float,
        temperature: float,
    ) -> dict: ...
```

### Prompt Port

```python
class PromptPort(Protocol):
    async def render(self, template_name: str, context: dict) -> str: ...
```

### Tool Gateway Port

```python
class ToolGatewayPort(Protocol):
    async def call(self, tool_name: str, params: dict) -> dict: ...
```

### Repository Ports

```python
class UserProfileRepositoryPort(Protocol):
    async def get_profile(self, user_id: str) -> UserProfileDTO | None: ...


class CheckpointRepositoryPort(Protocol):
    async def save(self, checkpoint: CheckpointSnapshot) -> None: ...
    async def load_latest(self, plan_id: str) -> CheckpointSnapshot | None: ...
```

---

## 节点设计建议

每个 Node 统一遵循下面模式：

```python
async def planning_node(state: PlanRuntimeState) -> dict:
    logger.info("agent_node_start", node="planning_node", plan_id=state.request.plan_id)

    try:
        draft = await planning_service.create_draft(
            intent=state.intent,
            context_profile=state.context_profile,
            memory_features=state.memory_features,
            candidate_pool=state.candidate_pool,
            locked_slots=state.locked_slots,
            seed=state.seed,
        )
        return {
            "draft": draft.model_dump(),
            "status": "confirming",
        }
    except DomainError as exc:
        return {
            "status": "failed",
            "errors": [AgentError(
                code=exc.code,
                message=str(exc),
                node_name="planning_node",
                retryable=exc.retryable,
            ).model_dump()],
        }
```

统一要求：

- 入参读取 typed state
- 输出写回 typed state 对应字段
- 日志统一
- 错误统一落 `AgentError`

---

## 人机协同闭环设计

### create 阶段

`planning_node -> confirm_node -> interrupt`

前端展示：

- 草案
- slot 列表
- 替代候选
- 可修改说明

### confirm 阶段

前端提交结构化决策：

```json
{
  "decision": "partial_change",
  "locked_slots": [0, 1],
  "rejected_slots": [2],
  "change_requests": [
    {
      "slot_index": 2,
      "instruction": "不要排队太久，换成更适合带孩子的活动",
      "replace_only": true
    }
  ]
}
```

### graph 路由

- `confirmed` -> `execution_node`
- `partial_change` -> `planning_node`
- `rejected` -> `planning_node`
- `cancelled` -> `failed`

### planning 输入

重新规划时必须读：

- `locked_slots`
- `rejected_slots`
- `change_requests`
- 最近 checkpoint
- 上一版 draft

这样才是真正的局部重规划，不是重新随机出一版。

---

## SSE 设计

现状中的 `/stream` 不应重新驱动 graph。

正确方案：

1. graph 运行时把 `RuntimeEvent` 写入 event sink
2. API `/stream` 按 `plan_id` 或 `run_id` 订阅 event sink
3. 前端只消费真实事件

事件映射建议：

- `node_started` -> `intent/retrieval/planning/execution/fallback/notify`
- `interrupt_requested` -> `consensus`
- `tool_called` -> `tool_start`
- `tool_finished` -> `tool_done`
- `plan_completed` -> `done`

---

## 持久化设计

至少新增 3 类持久化对象：

1. `plan_runs`
   - 记录一次完整运行
2. `plan_checkpoints`
   - 记录每次可恢复状态
3. `plan_run_events`
   - 记录 node/tool 事件

建议最小表结构：

```text
plan_runs
- id
- plan_id
- thread_id
- graph_version
- request_payload
- final_status
- seed
- created_at

plan_checkpoints
- id
- plan_id
- run_id
- version
- state_json
- created_at

plan_run_events
- id
- plan_id
- run_id
- node_name
- event_type
- payload_json
- created_at
```

---

## 迁移路线

### Phase 1：收敛运行入口

目标：只保留一套实际执行主线

- `plan.py` API 只走 `agent_runtime.graph`
- 标记 `hub.py`、`plan_service.py` 为 deprecated
- 把旧 FSM 逻辑移到 `agent_runtime/policies.py`

### Phase 2：引入 typed runtime state

目标：去掉运行时 `dict[str, Any]`

- 新建 `schemas/agent/state.py`
- Node 逐个迁移
- history 不再手工拼，改为显式字段读写

### Phase 3：统一外部出口

目标：清理散落依赖

- `IntentParser` 改走 `LLMGateway`
- `PlanningEngine` 改走 `LLMGateway`
- prompt 统一走 `PromptPort`
- Tool 调用统一走 `ToolGatewayPort`

### Phase 4：接通 confirm/fallback/checkpoint 闭环

目标：实现真正局部重规划

- 引入 `ConfirmationState`
- 引入 `CheckpointSnapshot`
- Fallback 直接生成 `revised_draft`
- planning 支持 `locked_slots + mutable window`

### Phase 5：接事件流与持久化

目标：支持中断恢复和真实 SSE

- MemorySaver -> Postgres Saver
- 新增 `plan_run_events`
- `/stream` 只订阅事件

### Phase 6：补生产测试

必须新增：

- interrupt/resume
- fallback exhaustion
- service restart recovery
- duplicate request idempotency
- deterministic replay by seed
- tool timeout / partial success / compensation

---

## 建议删除或降级的旧实现

### 直接废弃

- `app/services/plan_service.py`
  - 与 Agent 主链重复
  - 继续保留只会扩大分叉

### 降级为参考实现或规则库

- `app/agents/hub.py`
  - 其中 checkpoint 思路可以迁移
  - 不应继续作为第二套 orchestrator

- `app/core/state.py`
  - guard 规则可迁移
  - 不应继续作为第二套运行状态机

---

## 最终预期收益

完成这轮重构后，SnapTrip 的 Agent 架构会获得 7 个生产级能力：

1. **单一主链路**：排查和演进成本显著降低
2. **可恢复**：服务重启后仍能 resume
3. **可回放**：同输入可复盘同一运行
4. **可解释**：知道为什么选这个 POI、为什么替换
5. **可观测**：前端看到的就是运行时真实事件
6. **可扩展**：后续加 `Recommend/Review/Pricing` 不会继续污染主链
7. **可测试**：domain service 与 graph runtime 可以分层验证

---

## 结论

SnapTrip 现阶段最重要的不是再增加 Agent，而是完成一次**运行时收敛**：

- 收敛编排
- 收敛状态
- 收敛外部依赖出口
- 收敛事件与持久化

只要这四件事先做好，后续无论是竞赛演示、课设扩展还是真实 API 替换，都会稳定很多。
