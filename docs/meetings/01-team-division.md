# 01 —— 三人分工与接口契约

## 分工总览

```
         Person A                    Person B                    Person C
      基础设施 + 后端               Agent 智能层              前端 + Mock 体验层
    ┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
    │ Docker / Makefile│     │ Agent Hub 状态机     │     │ React 三栏布局   │
    │ FastAPI 骨架     │     │ Intent Agent        │     │ SSE 流式渲染    │
    │ DB 模型 + Alembic│     │ Planning Agent      │     │ Mock API 4路由  │
    │ Plan API 路由    │     │ Execution Agent     │     │ Seed POI 数据   │
    │ Plan Service     │     │ Prompt 模板 J2      │     │ 分享卡片组件    │
    │ Schemas 定义     │     │ Fallback + Saga     │     │ Zustand 状态    │
    │ 单测 + 集成测试  │     │ Agent 协议对接       │     │ TypeScript 类型 │
    └─────────────────┘     └─────────────────────┘     └─────────────────┘
```

## 角色职责

### Person A —— 基础设施 + 后端主管

**负责范围**：Phase 1 / Phase 2 / Phase 6

| 模块 | 文件 |
|------|------|
| Docker 基础设施 | `docker-compose.yml`, `docker-compose.override.yml` |
| 配置中心 | `backend/app/core/config.py` |
| 日志系统 | `backend/app/core/logging.py` |
| 异常体系 | `backend/app/core/exceptions.py` |
| 枚举常量 | `backend/app/core/constants.py` |
| App 入口 | `backend/app/main.py` |
| DB 会话 | `backend/app/db/session.py` |
| DB 模型 | `backend/app/models/base.py`, `user.py`, `plan.py`, `poi.py` |
| Pydantic Schema | `backend/app/schemas/plan.py`, `user.py`, `common.py` |
| API 依赖注入 | `backend/app/api/deps.py` |
| API 路由 | `backend/app/api/v1/plan.py`, `user.py`, `session.py` |
| 规划服务 | `backend/app/services/plan_service.py` |
| Agent 协议 | `backend/app/agents/protocol.py`（与 Person B 协作） |
| 测试 | `backend/tests/conftest.py`, `unit/test_plan_service.py`, `integration/test_end_to_end.py` |
| 构建脚本 | `Makefile`, `backend/pyproject.toml` |

### Person B —— Agent 智能主管

**负责范围**：Phase 4

| 模块 | 文件 |
|------|------|
| Agent Hub | `backend/app/agents/hub.py` |
| Intent Agent | `backend/app/agents/intent_agent.py` |
| Context Agent | `backend/app/agents/context_agent.py` |
| Retrieval Agent | `backend/app/agents/retrieval_agent.py` |
| Planning Agent | `backend/app/agents/planning_agent.py` |
| Execution Agent | `backend/app/agents/execution_agent.py` |
| Fallback Agent | `backend/app/agents/fallback_agent.py` |
| Notify Agent | `backend/app/agents/notify_agent.py` |
| Prompt 模板 | `backend/app/agents/prompts/intent.j2`, `planning.j2`, `execution.j2` |
| Hermes Skill | `backend/app/agents/skills/*.md` |

### Person C —— 前端 + Mock 主管

**负责范围**：Phase 3 / Phase 5

| 模块 | 文件 |
|------|------|
| Mock 入口 | `mock_server/app/main.py` |
| Mock 路由 | `mock_server/app/routers/poi.py`, `queue.py`, `booking.py`, `order.py` |
| 种子数据 | `mock_server/app/data/seed_pois.json` |
| Mock 构建 | `mock_server/pyproject.toml` |
| 前端入口 | `frontend/src/main.tsx`, `App.tsx` |
| 三栏布局 | `frontend/src/pages/Home.tsx` |
| 地图组件 | `frontend/src/components/MapView.tsx` |
| Agent 监控 | `frontend/src/components/AgentMonitor.tsx` |
| 计划卡片 | `frontend/src/components/PlanCard.tsx` |
| SSE Hook | `frontend/src/hooks/useAgentStream.ts` |
| API 封装 | `frontend/src/api/plan.ts` |
| 状态管理 | `frontend/src/stores/planStore.ts` |
| 类型定义 | `frontend/src/types/plan.ts`, `sse.ts` |
| 前端构建 | `frontend/package.json`, `tsconfig.json`, `vite.config.ts` |

---

## 三方接口契约

并行开发的基石：三方通过契约解耦，各自独立开发，契约文件由 Person A 统一定义。

### 契约 1：Pydantic Schema（Person A 生产，Person B 消费）

```
契约文件：backend/app/schemas/plan.py
关键类型：
  PlanCreate        → Person B 的 hub.py 入口参数
  PlanConstraints   → Person B 的 intent_agent.py 输出
  PlanResponse      → Person B 的 planning_agent.py 输出
  PlanSlot          → Person B 的 execution_agent.py 输入
  ToolResult        → Person B 的 execution_agent.py 输出
```

### 契约 2：TypeScript 类型（Person C 生产，与 Person A 对齐）

```
契约文件：frontend/src/types/plan.ts, sse.ts
关键类型：
  PlanCreateRequest    ←→ PlanCreate (Pydantic)
  PlanResponse         ←→ PlanResponse (Pydantic)
  SSEEvent             ←→ SSE 事件类型联合
```

### 契约 3：Agent 协议接口（Person A 定义，Person B 实现）

```python
# backend/app/agents/protocol.py
class BaseAgent(ABC):
    """所有 Agent 的抽象基类"""
    name: str
    
    @abstractmethod
    async def execute(self, context: "AgentContext") -> "AgentResult":
        ...

class AgentContext(BaseModel):
    plan_id: UUID
    user_input: str
    constraints: PlanConstraints
    history: List[AgentResult]

class AgentResult(BaseModel):
    agent_name: str
    status: str           # success | failed | timeout
    data: dict
    error: str | None
```

### 契约 4：SSE 事件规范（Person C 定义，Person A 路由实现）

```
事件名清单（按流顺序）：
  intent | retrieval | planning | planning_done
  execution | execution_done
  fallback | notify | error | done

每个事件的 payload JSON Schema 见 docs/api/plan.md
```

### 契约 5：Mock API OpenAPI（Person C 实现，Person B 消费）

```
端点清单：
  GET  /mock/poi/search?lat=&lng=&radius=&type=&tags=
  GET  /mock/poi/{poi_id}
  GET  /mock/queue/{poi_id}
  POST /mock/booking/table
  POST /mock/booking/ticket
  POST /mock/order
```

---

## 并行开发依赖图

```
Phase 1 ● ───────────────── (ALL同步)
         │
Phase 2 ● ──────── [P_A] 独立
         │           │ 产出 schemas/ (契约1)
Phase 3 ● ── [P_C] 独立      │
         │  产出 Mock(契约5)  │
         │      │         │
Phase 4 ●      │    [P_B] ◄─┘ 消费 schemas/
         │      │     │        调用 Mock API
         │      │     │
Phase 5 ●  [P_C] ◄───┘  消费 SSE(契约4)
         │  产出前端
         │
Phase 6 ● ───────────────── (ALL联调)
```

---

## 分支策略

```
main
  ├── feat/infra-backend        (Person A)
  ├── feat/agent-layer          (Person B)  ← 依赖 feat/infra-backend 的 schemas/
  ├── feat/mock-frontend        (Person C)  ← 独立分支，不依赖其他分支
  └── feat/integration          (ALL)       ← 合并所有分支后
```

## 协作规则

1. **Schemas 先行**：Person A 在 Phase 2 结束时必须产出完整的 `schemas/*.py`
2. **Mock 优先**：Person C 在 Phase 3 结束时 Mock API 必须可用，Person B 才能开始调用
3. **每日同步**：每天结束时在 `docs/meetings/` 下追加当日进度
4. **破坏性变更**：修改契约文件时必须通知受影响方，并在 `decisions-log.md` 记录
