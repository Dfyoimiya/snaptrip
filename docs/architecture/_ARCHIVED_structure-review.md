# SnapTrip 项目结构审查与规范包结构定义

> **文档状态**: 已被 [`00-architecture-reference.md`](./00-architecture-reference.md) 替代。
> 本审查日期为 2026-05-19（monorepo 重构前），所描述的 `backend/app/` 单体结构已不适用。
> 当前实际目录结构见 `00-architecture-reference.md` 第 8 节。
>
> 审查日期：2026-05-19  
> 审查范围：backend / mock_server / frontend 全栈  
> 基准文档：[PROJECT.md](../../PROJECT.md)

---

## 一、现有结构总览

### Backend (`backend/app/`)

```
backend/
├── alembic/                           # 数据库迁移
│   ├── env.py
│   ├── versions/8da6e575b9c0_init.py
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI 入口 + lifespan
│   ├── celry_app.py                   # Celery 配置（⚠️ 位置不符 PROJECT.md）
│   │
│   ├── core/                          # ✅ 核心基础设施
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic-Settings
│   │   ├── constants.py               # 状态枚举 + 策略参数
│   │   ├── exception_handlers.py      # 全局异常处理器
│   │   ├── exceptions.py              # 统一异常体系 (SOCID)
│   │   ├── logging.py                 # structlog JSON 日志
│   │   ├── rate_limit.py              # Redis 限流
│   │   ├── response.py                # 统一响应格式
│   │   ├── security.py                # bcrypt + JWT 认证
│   │   └── state.py                   # Plan FSM 状态机
│   │
│   ├── db/                            # ✅ 数据库
│   │   ├── __init__.py
│   │   └── session.py                 # AsyncSession + pgvector
│   │
│   ├── models/                        # ✅ ORM 模型（9个表）
│   │   ├── __init__.py                # 统一导出
│   │   ├── base.py                    # Base + TimestampMixin + UUIDMixin
│   │   ├── checkpoint.py
│   │   ├── llm_usage_log.py
│   │   ├── plan.py
│   │   ├── plan_adjustment.py
│   │   ├── plan_slot.py
│   │   ├── poi.py
│   │   ├── refresh_token.py
│   │   ├── user_profile.py
│   │   └── users.py
│   │
│   ├── schemas/                       # ✅ Pydantic Schema（5个文件）
│   │   ├── __init__.py                # ⚠️ 空文件
│   │   ├── auth.py
│   │   ├── checkpoint.py
│   │   ├── plan.py                    # 25+ Schema 类（过于庞大）
│   │   ├── tool.py                    # Tool 注册表 + 定义
│   │   └── user.py
│   │
│   ├── api/                           # REST API
│   │   ├── __init__.py                # ⚠️ 空文件
│   │   ├── v1/
│   │   │   ├── __init__.py            # ⚠️ 空文件
│   │   │   ├── auth.py                # ✅ 认证路由
│   │   │   ├── plan.py                # ✅ LangGraph 编排入口
│   │   │   ├── session.py             # ✅ SSE 流式推送
│   │   │   └── user.py                # ✅ 用户接口
│   │
│   ├── agents/                        # LangGraph Agent 层
│   │   ├── __init__.py                # 重新导出 BaseAgent/AgentContext/AgentResult
│   │   ├── protocol.py                # BaseAgent ABC
│   │   ├── graph.py                   # StateGraph 定义（9 Node + 条件边）
│   │   ├── hub.py                     # MasterController（⚠️ 与 graph.py 并存）
│   │   ├── intent_parser.py           # LLM + 关键词降级
│   │   ├── context_loader.py          # 用户画像 DB 查询
│   │   ├── memory_manager.py          # 历史偏好聚合
│   │   ├── retrieval_engine.py        # POI 检索 + haversine
│   │   ├── planning_engine.py         # 两阶段求解器
│   │   ├── consensus_resolver.py      # ⚠️ 完全 stub
│   │   ├── execution_engine.py        # Tool DAG 编排 + Gateway 集成
│   │   ├── fallback_engine.py         # Shadow + 涟漪重排
│   │   ├── notify_engine.py           # 分享卡片生成
│   │   └── prompts/                   # Jinja2 模板
│   │       ├── intent.j2
│   │       ├── planning.j2
│   │       └── notify.j2
│   │
│   ├── services/                      # 业务服务
│   │   ├── __init__.py                # ⚠️ 空文件
│   │   ├── circuit_breaker.py         # 三态熔断器
│   │   ├── llm_gateway.py             # DeepSeek API 封装
│   │   ├── memory_service.py          # pgvector 记忆读写
│   │   ├── mock_gateway.py            # Mock API httpx 网关
│   │   ├── plan_service.py            # ⚠️ 旧版实现（已废弃，代码不一致）
│   │   ├── saga.py                    # Saga 补偿协调器
│   │   ├── tool_dag.py                # Tool DAG 执行器
│   │   └── user_service.py            # 用户服务
│   │
│   ├── adapters/                      # 高德地图适配层
│   │   ├── __init__.py
│   │   ├── amap_client.py             # 高德 HTTP 客户端
│   │   ├── base.py                    # BaseAmapAdapter
│   │   ├── registry.py                # AdapterRegistry + Router
│   │   ├── adapters/                  # ⚠️ 双层嵌套命名异味
│   │   │   ├── __init__.py
│   │   │   ├── district_adapter.py
│   │   │   ├── geocode_adapter.py
│   │   │   ├── poi_adapter.py
│   │   │   └── route_adapter.py
│   │   ├── mappers/                   # 领域映射器
│   │   │   ├── __init__.py
│   │   │   ├── geo_mapper.py
│   │   │   ├── poi_mapper.py
│   │   │   └── route_mapper.py
│   │   └── schemas/                   # 高德 API 响应 Schema
│   │       ├── __init__.py
│   │       ├── district.py
│   │       ├── geocode.py
│   │       ├── poi.py
│   │       ├── route.py
│   │       └── weather.py
│   │
│   ├── tasks/                         # Celery 异步任务
│   │   ├── __init__.py
│   │   └── plan_tasks.py
│   │
│   └── data/                          # 种子数据
│       ├── __init__.py
│       └── seed_pois.py               # 16 条 POI（⚠️ 规范要求 50 条）
│
└── tests/
    ├── conftest.py
    ├── unit/                          # 14 个单元测试文件
    ├── integration/                   # 5 个集成测试文件
    ├── contract/                      # 契约测试 + 3 个 snapshot
    └── eval/                          # 离线评估 + 2 个 golden set
```

### Mock Server (`mock_server/`)

```
mock_server/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py                     # 统一 ToolResult 响应
│   ├── core/
│   │   └── fault.py                   # 故障注入中间件
│   ├── data/
│   │   └── __init__.py                # ⚠️ 空目录（数据在顶层 data/）
│   └── routers/
│       ├── __init__.py
│       ├── delivery.py
│       ├── order.py
│       ├── poi.py
│       ├── queue.py
│       ├── route.py
│       └── weather.py
├── data/
│   └── seed_pois.json                 # 种子 POI JSON
├── Dockerfile
└── pyproject.toml
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx                        # 仅渲染 PlanPage
│   ├── index.css
│   ├── api/
│   │   └── plan.ts                    # plan API 调用
│   ├── types/
│   │   ├── plan.ts                    # Plan 类型定义
│   │   └── agent.ts                   # Agent 类型定义
│   ├── stores/
│   │   ├── planStore.ts               # Zustand 计划状态
│   │   └── agentStore.ts              # Zustand Agent 状态
│   ├── hooks/
│   │   └── usePlanSSE.ts              # SSE 流式监听
│   ├── components/
│   │   ├── agent/AgentMonitor.tsx
│   │   ├── common/InputBar.tsx
│   │   ├── map/MapView.tsx
│   │   └── plan/PlanCard.tsx, PlanTimeline.tsx, ConfirmPanel.tsx
│   └── pages/
│       └── PlanPage.tsx               # 唯一页面
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 二、问题识别

### 2.1 目录层级问题

| 问题 | 严重程度 | 说明 |
|------|:---:|------|
| `adapters/adapters/` 双层嵌套 | 🔴 高 | 命名混淆：`app/adapters/adapters/` 应改为 `app/adapters/clients/` 或取消嵌套 |
| `mock_server/app/data/` 为空 | 🟡 中 | seed_pois.json 在顶层 `data/`，与 `app/data/` 不一致 |
| `celery_app.py` 位置不当 | 🟡 中 | PROJECT.md 指定为 `app/tasks/celery_app.py`，实际在 `app/celery_app.py` |
| 课设相关目录仅有代理层 | 🟡 中 | `agents/` 缺 5 个课设 Agent；`api/v1/` 缺 poi/order/delivery/merchant |
| 前端组件目录不完整 | 🟢 低 | 缺 SlotDetail / RouteLine / POIMarker / ToolCallLog 等子组件 |

### 2.2 命名规范问题

| 问题 | 说明 |
|------|------|
| `llm_gateway.py` vs `mock_gateway.py` | 两者同为 Gateway，命名一致但 LLMGateway 内部定义了 `LLMError`（与 `exceptions.py` 中 `LLMError` 重复定义） |
| 无问题 | 其余全部符合 PEP8 小写+下划线规范 |

### 2.3 架构不一致（高优先级）

| 问题 | 说明 |
|------|------|
| **双调度入口** | `api/v1/plan.py` 直接使用 `plan_graph.ainvoke()`，`agents/hub.py` 的 `MasterController` 定义了三内核调度逻辑但未被 API 层使用。两套调度机制并存，造成维护困惑。 |
| **双状态定义** | `core/state.py` 定义 `PlanStateMachine`（含 `StateRecord`），`agents/graph.py` 定义 `PlanState` TypedDict。graph.py 用 LangGraph 的状态机，hub.py 用自己的 FSM。 |
| **双 LLM 调用路径** | `intent_parser.py` 直接 `httpx.AsyncClient` 调 DeepSeek，`llm_gateway.py` 封装了完整的重试+日志。意图解析未使用 `LLMGateway`。 |
| **`services/plan_service.py` 已废弃** | 旧版实现（注释 `# mypy: ignore-errors`），使用不存在的 `PlanSlot.time` 字段（实际 Schema 定义了 `time_range`）。应删除或标记为 `@deprecated`。 |

### 2.4 循环依赖排查

经过审查，当前各模块的 import 关系：
- `agents/*` → `protocol.py` (BaseAgent), `schemas/plan.py`, `core/config.py`, `data/seed_pois.py`
- `api/v1/plan.py` → `agents/graph.py` → 各 Agent
- `agents/graph.py` → 所有 Agent Node
- `agents/hub.py` → `core/state.py`, `schemas/checkpoint.py`

**未发现循环依赖。**

### 2.5 空包 / Stub 文件

| 文件 | 状态 | 优先级 | 建议 |
|------|------|:---:|------|
| `agents/consensus_resolver.py` | 完全 stub（单用户 always confirmed） | P1 | 实现多用户加权投票+帕累托补偿 |
| `services/__init__.py` | 空文件 | P2 | 添加模块统一导出 |
| `schemas/__init__.py` | 空文件 | P2 | 添加 Schema 统一导出 |
| `api/__init__.py` | 空文件 | P2 | 添加路由注册导出 |
| `api/v1/__init__.py` | 空文件 | P2 | 添加 v1 路由注册导出 |
| `mock_server/app/data/__init__.py` | 空目录 | P2 | 将 seed_pois.json 移入此目录或删除空目录 |

### 2.6 重复代码

| 重复内容 | 位置 1 | 位置 2 | 建议操作 |
|----------|--------|--------|---------|
| `haversine()` 函数 | `agents/retrieval_engine.py:34-39` | `services/plan_service.py:47-56` | 提取到 `core/utils.py` |
| `CITY_KEYWORDS` / `TYPE_KEYWORDS` / `MOOD_KEYWORDS` | `agents/intent_parser.py:29-51` | `services/plan_service.py:19-44` | 提取到 `data/keywords.py` |
| `CITY_CENTERS` | `agents/retrieval_engine.py:27-31` | `services/plan_service.py:13-17` | 提取到 `core/constants.py`（已有 `PlanStatus` 等枚举）或 `data/cities.py` |
| `parse_intent()` | `agents/intent_parser.py` (类方法) | `services/plan_service.py:59-97` (函数) | 废弃 `plan_service.py` 版本，统一使用 Agent |
| `MockAPIGateway.TOOL_ROUTES` vs `tool_dag.py TOOL_ENDPOINTS` | `services/mock_gateway.py:25-33` | `services/tool_dag.py:42-53` | 统一路由映射表，单一事实来源 |
| `LLMError` 类 | `services/llm_gateway.py:23-28` | `core/exceptions.py:194-198` | 保留 `exceptions.py` 中的版本，`llm_gateway.py` 直接引用 |

### 2.7 缺失模块（与 PROJECT.md 对照）

| 类别 | 缺失模块 | 优先级 | 备注 |
|------|---------|:---:|------|
| **Agents** | `recommend_agent.py` | P2 | 课设：智能推荐 |
| | `review_agent.py` | P2 | 课设：评价分析 |
| | `dispatch_agent.py` | P2 | 课设：配送调度 |
| | `pricing_agent.py` | P2 | 课设：动态定价 |
| | `quality_agent.py` | P2 | 课设：质量监控 |
| **Agent Prompts** | `recommend.j2` | P2 | |
| | `review.j2` | P2 | |
| **Agent Skills** | `skills/` 目录（3 个 md） | P1 | 优先级提升：skill 文件定义"触发条件/执行步骤/示例"，影响容错引擎的可阅读性 |
| **Models** | `order.py` | P2 | 课设：订单表 |
| | `delivery.py` | P2 | 课设：配送表 |
| | `review.py` | P2 | 课设：评价表 |
| **Schemas** | `poi.py` | P1 | POI 实体 Schema 独立文件（当前混在 plan.py 中） |
| | `order.py` | P2 | 课设 |
| | `delivery.py` | P2 | 课设 |
| **Services** | `poi_service.py` | P1 | POI 检索/缓存服务 |
| | `order_service.py` | P2 | 课设 |
| | `delivery_service.py` | P2 | 课设 |
| | `payment_service.py` | P2 | 课设 |
| | `notify_service.py` | P1 | 通知服务（短信/推送），当前在 notify_engine.py 中硬编码 |
| **API Routes** | `poi.py` | P1 | POI 搜索/详情 API |
| | `order.py` | P2 | 课设 |
| | `delivery.py` | P2 | 课设 |
| | `merchant.py` | P2 | 课设 |
| **API Middleware** | `api/deps.py` | P1 | FastAPI 依赖注入集中管理（get_db/get_redis/get_current_user） |
| | `api/middleware/auth.py` | P1 | JWT 验证中间件 |
| | `api/middleware/rate_limit.py` | P1 | Redis 限流中间件 |
| **Data** | `seed_users.py` | P1 | 种子用户数据 |
| **Tasks** | `notify_tasks.py` | P2 | 通知异步任务 |
| **Frontend** | `api/client.ts` | P1 | Axios 实例封装（拦截器/错误处理） |
| | `api/auth.ts` | P1 | 认证 API |
| | `hooks/useAuth.ts` | P1 | 认证 Hook |
| | `hooks/useAgentState.ts` | P1 | Agent 状态监听 Hook |
| | `stores/userStore.ts` | P1 | 用户状态 |
| | `types/order.ts` | P2 | 课设 |
| | `components/plan/SlotDetail.tsx` | P1 | Slot 详情 |
| | `components/map/RouteLine.tsx` | P1 | 路线动画 |
| | `components/map/POIMarker.tsx` | P1 | POI 标记 |
| | `components/agent/ToolCallLog.tsx` | P1 | Tool 调用日志 |
| | `components/agent/PipelineNode.tsx` | P1 | 流水线节点 |
| | `components/common/SSEStatus.tsx` | P1 | SSE 连接状态 |
| | `components/common/LoadingSpinner.tsx` | P1 | 加载动画 |
| | `pages/LoginPage.tsx` | P1 | 登录页 |
| | `pages/OrdersPage.tsx` | P2 | 课设：订单页 |
| | `pages/MerchantPage.tsx` | P2 | 课设：商家页 |
| | `components/order/` 目录 | P2 | 课设：订单组件 |
| | `components/merchant/` 目录 | P2 | 课设：商家组件 |

### 2.8 前后端对齐检查

| 后端 API | 前端调用 | 状态 |
|---------|---------|:---:|
| `POST /api/v1/plan/create` | `api/plan.ts createPlan()` | ✅ 一致 |
| `POST /api/v1/plan/{plan_id}/confirm` | `api/plan.ts confirmPlan()` | ✅ 一致 |
| `GET /api/v1/plan/{plan_id}` | `api/plan.ts getPlan()` | ✅ 一致 |
| `GET /api/v1/plan/{plan_id}/stream` | `api/plan.ts sseUrl()` | ✅ 一致 |
| `POST /api/v1/auth/*` | 无前端调用 | 🔴 缺失 |
| `GET /api/v1/user/*` | 无前端调用 | 🔴 缺失 |

**SSE 事件映射一致性：**
- 后端 `session.py` 定义 `NODE_SSE_EVENT` + `NODE_DONE_EVENT`
- 前端 `usePlanSSE.ts` 定义 `EVENT_NODE_MAP`
- ✅ 事件名称一致

### 2.9 技术债务标记

| 债务 | 位置 | 说明 |
|------|------|------|
| `# mypy: ignore-errors` | `services/plan_service.py:1` | 废弃文件，类型不合法 |
| `gateway=None` 兼容 | `execution_engine.py:46` | 为兼容单元测试保留了本地 mock 分支 |
| 硬编码 URL | `mock_gateway.py:35` | `base_url` 默认 `http://localhost:8001`（虽有环境变量覆盖，但硬编码了 fallback） |
| Jinja2 路径 | `intent_parser.py:87` | 使用 `open("app/agents/prompts/intent.j2")` 相对路径，容器中可能失败 |
| Jinja2 路径 | `planning_engine.py:134` | 同上 |

### 2.10 Seed 数据不匹配

- `backend/app/data/seed_pois.py`: **16 条** POI（注释宣称 16 条），PROJECT.md 要求 50 条
- `mock_server/data/seed_pois.json`: 需验证条目数

---

## 三、规范包结构（Target Architecture）

### 3.1 Backend 规范结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI 入口 + lifespan + 异常注册
│   ├── celery_app.py                  # ⚠️ 应移至 tasks/celery_app.py
│   │
│   ├── core/                          # 核心基础设施（不允许业务逻辑）
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic-Settings 唯一配置来源
│   │   ├── constants.py               # 所有枚举 + 策略参数常量
│   │   ├── exceptions.py              # 统一异常体系（SnapTripException 及其子类）
│   │   ├── exception_handlers.py      # FastAPI 全局异常处理器注册
│   │   ├── logging.py                 # structlog JSON 日志工厂
│   │   ├── response.py                # 统一 API 响应 {code, message, data}
│   │   ├── security.py                # bcrypt + JWT + OAuth2 依赖
│   │   └── utils.py                   # 🆕 通用工具函数（haversine, parse_uuid 等）
│   │
│   ├── db/                            # 数据库层
│   │   ├── __init__.py
│   │   └── session.py                 # AsyncSession + async_engine + get_db 依赖
│   │
│   ├── models/                        # SQLAlchemy ORM 模型
│   │   ├── __init__.py                # 统一导出所有 Model（供 Alembic 发现）
│   │   ├── base.py                    # Base + TimestampMixin + UUIDMixin
│   │   ├── users.py                   # 用户表
│   │   ├── user_profile.py            # 用户画像表（含 preference_embedding）
│   │   ├── refresh_token.py           # 刷新令牌表
│   │   ├── plan.py                    # 计划主表
│   │   ├── plan_slot.py               # 计划时隙子表
│   │   ├── plan_adjustment.py         # 计划调整记录
│   │   ├── poi.py                     # POI 实体表（含 embedding）
│   │   ├── checkpoint.py              # 检查点表
│   │   ├── llm_usage_log.py           # LLM 用量日志表
│   │   ├── order.py                   # 🆕 课设：订单表（P2）
│   │   ├── delivery.py                # 🆕 课设：配送表（P2）
│   │   └── review.py                  # 🆕 课设：评价表（P2）
│   │
│   ├── schemas/                       # Pydantic Schema（按领域拆分，避免单文件过大）
│   │   ├── __init__.py                # 统一导出所有 Schema
│   │   ├── auth.py                    # LoginRequest / TokenResponse 等
│   │   ├── user.py                    # UserProfile / PreferenceVector 等
│   │   ├── plan.py                    # PlanCreateRequest / PlanResponse / PlanSlot 等
│   │   ├── agent.py                   # IntentSchema / EnrichedIntent / CandidatePool 等
│   │   ├── execution.py               # ExecutionResult / SlotExecutionResult / FailedSlot 等
│   │   ├── fallback.py                # ShadowCandidate / RevisedPlan / SlotDiff 等
│   │   ├── checkpoint.py              # Checkpoint / LockedSlot / TentativeSlot / ShadowSlot
│   │   ├── tool.py                    # ToolInvocation / ToolResult / ToolDefinition / TOOL_REGISTRY
│   │   ├── poi.py                     # 🆕 POI 实体 Schema（P1）
│   │   ├── order.py                   # 🆕 课设（P2）
│   │   ├── delivery.py                # 🆕 课设（P2）
│   │   └── notification.py            # ShareCard / NotificationRequest 等
│   │
│   ├── api/                           # REST API 层（薄层，仅参数校验+调用 Service）
│   │   ├── __init__.py                # 路由注册导出
│   │   ├── deps.py                    # 🆕 FastAPI 依赖注入（get_db / get_redis / get_current_user）
│   │   ├── v1/
│   │   │   ├── __init__.py            # v1 路由注册导出
│   │   │   ├── plan.py                # 计划创建/查询/确认/流式
│   │   │   ├── auth.py                # 注册/登录/刷新/登出
│   │   │   ├── user.py                # 用户画像
│   │   │   ├── poi.py                 # 🆕 POI 搜索（P1）
│   │   │   ├── order.py               # 🆕 课设（P2）
│   │   │   ├── delivery.py            # 🆕 课设（P2）
│   │   │   ├── merchant.py            # 🆕 课设（P2）
│   │   │   └── session.py             # SSE 流式推送
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py                # 🆕 JWT 验证中间件（P1）
│   │       └── rate_limit.py          # 🆕 Redis 限流中间件（P1）
│   │
│   ├── agents/                        # Agent 层（LangGraph 编排）
│   │   ├── __init__.py                # 导出 BaseAgent / AgentContext / AgentResult
│   │   ├── protocol.py                # BaseAgent ABC + AgentContext + AgentResult
│   │   ├── graph.py                   # StateGraph 定义 + Node 实现 + 条件边路由
│   │   ├── hub.py                     # ⚠️ 待废弃：MasterController（与 graph.py 二选一）
│   │   │
│   │   ├── intent_parser.py           # 意图解析（LLM + 关键词降级）
│   │   ├── context_loader.py          # 用户画像 DB 查询
│   │   ├── memory_manager.py          # 历史偏好聚合
│   │   ├── retrieval_engine.py        # POI 检索
│   │   ├── planning_engine.py         # 两阶段求解器
│   │   ├── consensus_resolver.py      # 共识解析（P1: 多用户模式）
│   │   ├── execution_engine.py        # Tool DAG 编排 + Gateway 集成
│   │   ├── fallback_engine.py         # Shadow + 涟漪重排
│   │   ├── notify_engine.py           # 分享卡片生成
│   │   │
│   │   ├── recommend_agent.py         # 🆕 课设：智能推荐（P2）
│   │   ├── review_agent.py            # 🆕 课设：评价分析（P2）
│   │   ├── dispatch_agent.py          # 🆕 课设：配送调度（P2）
│   │   ├── pricing_agent.py           # 🆕 课设：动态定价（P2）
│   │   ├── quality_agent.py           # 🆕 课设：质量监控（P2）
│   │   │
│   │   ├── prompts/                   # Jinja2 Prompt 模板
│   │   │   ├── intent.j2
│   │   │   ├── planning.j2
│   │   │   ├── notify.j2
│   │   │   ├── recommend.j2           # 🆕 课设（P2）
│   │   │   └── review.j2              # 🆕 课设（P2）
│   │   └── skills/                    # 🆕 Skill 文件（P1）
│   │       ├── plan-fallback.md       # 容错策略
│   │       ├── restaurant-recommend.md # 餐厅推荐
│   │       └── time-negotiation.md    # 时间协商
│   │
│   ├── services/                      # 业务服务层（可被多个 Agent/API 复用）
│   │   ├── __init__.py                # 统一导出所有 Service
│   │   ├── mock_gateway.py            # Mock API httpx 网关
│   │   ├── llm_gateway.py             # LLM API 封装（含重试+用量日志）
│   │   ├── memory_service.py          # pgvector 记忆读写
│   │   ├── user_service.py            # 用户 CRUD
│   │   ├── poi_service.py             # 🆕 POI 检索/缓存（P1）
│   │   ├── plan_service.py            # ⚠️ 待删除或标记 @deprecated
│   │   ├── order_service.py           # 🆕 课设（P2）
│   │   ├── delivery_service.py        # 🆕 课设（P2）
│   │   ├── payment_service.py         # 🆕 课设（P2）
│   │   ├── notify_service.py          # 🆕 通知服务（P1）
│   │   ├── circuit_breaker.py         # 三态熔断器
│   │   ├── saga.py                    # Saga 补偿协调器
│   │   └── tool_dag.py                # Tool DAG 执行器
│   │
│   ├── adapters/                      # 高德地图适配层
│   │   ├── __init__.py
│   │   ├── base.py                    # BaseAmapAdapter
│   │   ├── amap_client.py             # 高德 HTTP 客户端
│   │   ├── registry.py                # AdapterRegistry + Router
│   │   ├── clients/                   # 🏗️ 改名自 adapters/
│   │   │   ├── __init__.py
│   │   │   ├── district_adapter.py
│   │   │   ├── geocode_adapter.py
│   │   │   ├── poi_adapter.py
│   │   │   └── route_adapter.py
│   │   ├── mappers/                   # 领域映射器
│   │   │   ├── __init__.py
│   │   │   ├── geo_mapper.py
│   │   │   ├── poi_mapper.py
│   │   │   └── route_mapper.py
│   │   └── schemas/                   # 高德 API 响应 Schema
│   │       ├── __init__.py
│   │       ├── district.py
│   │       ├── geocode.py
│   │       ├── poi.py
│   │       ├── route.py
│   │       └── weather.py
│   │
│   ├── tasks/                         # Celery 异步任务
│   │   ├── __init__.py
│   │   ├── celery_app.py              # 🏗️ 从 app/celery_app.py 移入
│   │   ├── plan_tasks.py
│   │   └── notify_tasks.py            # 🆕 通知异步任务（P2）
│   │
│   └── data/                          # 种子数据 + 关键词常量
│       ├── __init__.py
│       ├── seed_pois.py               # 50 条 POI（P1: 补充至 50 条）
│       ├── seed_users.py              # 🆕 种子用户（P1）
│       ├── cities.py                  # 🆕 城市中心坐标 + 关键词映射
│       └── keywords.py                # 🆕 类型/心情/城市关键词（提取重复代码）
│
├── tests/
│   ├── conftest.py
│   ├── unit/                          # 单元测试（mock 外部依赖）
│   │   ├── test_auth.py
│   │   ├── test_dag.py
│   │   ├── test_execution_engine.py
│   │   ├── test_fallback_engine.py
│   │   ├── test_intent_parser.py
│   │   ├── test_llm_gateway.py
│   │   ├── test_memory_service.py
│   │   ├── test_mock_server.py
│   │   ├── test_planning_engine.py
│   │   ├── test_retrieval_engine.py
│   │   ├── test_state.py
│   │   ├── test_tool_dag.py
│   │   ├── test_user.py
│   │   ├── test_vector_service.py
│   │   └── adapters/
│   │       ├── test_adapters.py
│   │       ├── test_amap_client.py
│   │       ├── test_mappers.py
│   │       └── test_registry.py
│   ├── integration/                   # 集成测试（真实 DB/Redis）
│   │   ├── conftest.py
│   │   ├── test_amap_integration.py
│   │   ├── test_api.py
│   │   ├── test_auth_api.py
│   │   ├── test_plan_api.py
│   │   └── test_user_api.py
│   ├── contract/                      # 契约测试（高德 API 响应 snapshot）
│   │   ├── test_amap_schemas.py
│   │   └── snapshots/
│   └── eval/                          # 离线评估
│       ├── eval_runner.py
│       ├── golden_intent.json
│       └── golden_plan.json
│
├── alembic/
├── pyproject.toml
├── Dockerfile
└── requirements.txt
```

### 3.2 Mock Server 规范结构

```
mock_server/
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI 入口
│   ├── schemas.py                     # 统一 ToolResult 响应
│   ├── core/
│   │   └── fault.py                   # 故障注入中间件
│   ├── data/
│   │   ├── __init__.py
│   │   └── seed_pois.json             # 🏗️ 从顶层 data/ 移入
│   └── routers/
│       ├── __init__.py
│       ├── poi.py                     # GET /mock/poi/search
│       ├── queue.py                   # GET /mock/queue/{poi_id}
│       ├── booking.py                 # 🆕 POST /mock/booking/table, /ticket（从 order.py 拆分）
│       ├── order.py                   # POST /mock/order
│       ├── delivery.py                # POST /mock/delivery
│       ├── route.py                   # GET /mock/route
│       └── weather.py                 # GET /mock/weather
├── Dockerfile
└── pyproject.toml
```

### 3.3 Frontend 规范结构

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx                        # 路由配置（React Router → 多页面）
│   ├── index.css
│   ├── api/                           # API 调用层
│   │   ├── client.ts                  # 🆕 Axios 实例（拦截器/错误处理）
│   │   ├── plan.ts
│   │   ├── auth.ts                    # 🆕 认证 API
│   │   └── order.ts                   # 🆕 课设（P2）
│   ├── types/                         # TypeScript 类型定义
│   │   ├── plan.ts
│   │   ├── agent.ts
│   │   ├── auth.ts                    # 🆕 认证类型
│   │   └── order.ts                   # 🆕 课设（P2）
│   ├── stores/                        # Zustand 状态管理
│   │   ├── planStore.ts
│   │   ├── agentStore.ts
│   │   └── userStore.ts               # 🆕 用户状态
│   ├── hooks/                         # 自定义 Hooks
│   │   ├── usePlanSSE.ts
│   │   ├── useAgentState.ts           # 🆕 Agent 状态监听
│   │   └── useAuth.ts                 # 🆕 认证 Hook
│   ├── components/                    # UI 组件
│   │   ├── agent/
│   │   │   ├── AgentMonitor.tsx
│   │   │   ├── ToolCallLog.tsx        # 🆕 Tool 调用日志
│   │   │   └── PipelineNode.tsx       # 🆕 流水线节点
│   │   ├── common/
│   │   │   ├── InputBar.tsx
│   │   │   ├── SSEStatus.tsx          # 🆕 SSE 连接状态
│   │   │   └── LoadingSpinner.tsx     # 🆕 加载动画
│   │   ├── map/
│   │   │   ├── MapView.tsx
│   │   │   ├── RouteLine.tsx          # 🆕 路线动画
│   │   │   └── POIMarker.tsx          # 🆕 POI 标记
│   │   ├── plan/
│   │   │   ├── PlanCard.tsx
│   │   │   ├── PlanTimeline.tsx
│   │   │   ├── SlotDetail.tsx         # 🆕 Slot 详情
│   │   │   └── ConfirmPanel.tsx
│   │   ├── order/                     # 🆕 课设（P2）
│   │   │   ├── OrderList.tsx
│   │   │   ├── OrderDetail.tsx
│   │   │   └── DeliveryTrack.tsx
│   │   └── merchant/                  # 🆕 课设（P2）
│   │       ├── MerchantDashboard.tsx
│   │       └── MenuManager.tsx
│   └── pages/
│       ├── PlanPage.tsx
│       ├── LoginPage.tsx              # 🆕 登录页
│       ├── OrdersPage.tsx             # 🆕 课设（P2）
│       └── MerchantPage.tsx           # 🆕 课设（P2）
├── package.json
├── vite.config.ts
└── tsconfig.json
```

---

## 四、差异报告：现有结构 vs 规范结构

### 图例

| 标记 | 含义 |
|:---:|------|
| 🏗️ | 需要移动/重命名 |
| 🆕 | 需要新建 |
| ⚠️ | 需要修改/完善 |
| 🔴 | 待废弃/删除 |
| ✅ | 已符合规范 |

### 4.1 P0 - 阻塞级别（需立即修复）

| 现有路径 | 问题 | 建议操作 |
|---------|------|---------|
| `backend/app/services/plan_service.py` | 废弃代码，使用不存在的 `PlanSlot.time` 字段，函数与 `agents/intent_parser.py` 重复 | 🔴 删除此文件 |
| `backend/app/agents/intent_parser.py:87` → `open("app/agents/prompts/intent.j2")` | 硬编码相对路径，容器中运行可能失败 | ⚠️ 改为 `Path(__file__).parent / "prompts" / "intent.j2"` |
| `backend/app/agents/planning_engine.py:134` → `open("app/agents/prompts/planning.j2")` | 同上 | ⚠️ 同上 |
| `backend/app/services/llm_gateway.py:23-28` `LLMError` | 与 `core/exceptions.py:194-198` 重复定义 | ⚠️ `llm_gateway.py` 引用 `core/exceptions.py` 中的 `LLMError` |

### 4.2 P1 - 当前迭代（需尽快处理）

| 现有路径 | 问题 | 建议操作 |
|---------|------|---------|
| `backend/app/agents/` → 缺 `skills/` 目录 | Skill 文件定义了容错策略、推荐逻辑、时间协商，缺失影响 Fallback Engine 可读性 | 🆕 创建 `backend/app/agents/skills/plan-fallback.md`, `restaurant-recommend.md`, `time-negotiation.md` |
| `backend/app/agents/consensus_resolver.py` | 完全 stub，单用户 always confirmed | ⚠️ 实现多用户加权投票 + 帕累托补偿逻辑 |
| `backend/app/core/` → 缺 `utils.py` | `haversine()` 在 2 处重复定义 | 🆕 创建 `core/utils.py`，统一提取通用工具函数 |
| `backend/app/data/` → 缺 `cities.py` / `keywords.py` | 城市坐标和关键词在 2 处重复定义 | 🆕 创建 `data/cities.py` 和 `data/keywords.py`，消除重复 |
| `backend/app/data/seed_pois.py` | 仅 16 条 POI，规范要求 50 条 | ⚠️ 补充 34 条 POI：杭州、成都、广州 各约 11-12 条 |
| `backend/app/data/` → 缺 `seed_users.py` | 种子用户数据 | 🆕 创建种子用户数据 |
| `backend/app/schemas/` → 缺 `poi.py` | POI Schema 混在 `plan.py` | 🆕 拆分 `plan.py` 中的 POI 相关 Schema 到 `schemas/poi.py` |
| `backend/app/schemas/plan.py` | 包含 25+ Schema 类，过于庞大（195 行） | 🆕 按 Agent 阶段拆分：`schemas/agent.py`(Intent/Enriched/Candidate) + `schemas/execution.py` + `schemas/fallback.py` |
| `backend/app/api/deps.py` | 缺失，Dependencies 散落在 `db/session.py` | 🆕 创建集中管理的依赖注入文件 |
| `backend/app/api/middleware/auth.py` | 缺失，JWT 认证散落在 `security.py` 和 `api/v1/auth.py` | 🆕 创建 JWT 验证中间件 |
| `backend/app/api/middleware/rate_limit.py` | 缺失，限流逻辑定义在 `core/rate_limit.py` 但无中间件接入 | 🆕 创建 Redis 限流中间件 |
| `backend/app/api/v1/poi.py` | 缺失，前端无 POI 搜索入口 | 🆕 创建 POI 搜索路由 |
| `backend/app/services/poi_service.py` | 缺失 | 🆕 创建 POI 检索/缓存服务 |
| `backend/app/services/notify_service.py` | 缺失 | 🆕 创建通知服务 |
| `backend/app/agents/intent_parser.py` → LLM 调用 | 直接使用 `httpx.AsyncClient`，未通过 `LLMGateway` | ⚠️ 统一使用 `LLMGateway.chat()` |
| `frontend/src/api/client.ts` | 缺失 Axios 封装 | 🆕 创建 Axios 实例（baseURL / 拦截器 / 错误处理） |
| `frontend/src/api/auth.ts` | 缺失 | 🆕 创建认证 API |
| `frontend/src/hooks/useAuth.ts` / `useAgentState.ts` | 缺失 | 🆕 创建 Hooks |
| `frontend/src/stores/userStore.ts` | 缺失 | 🆕 创建用户状态 Store |
| `frontend/src/pages/LoginPage.tsx` | 缺失 | 🆕 创建登录页 |
| `frontend/src/components/` 缺 `SlotDetail / RouteLine / POIMarker / ToolCallLog / PipelineNode / SSEStatus / LoadingSpinner` | 缺少 UI 子组件 | 🆕 创建 7 个缺失组件 |

### 4.3 P2 - 后续迭代

| 现有路径 | 问题 | 建议操作 |
|---------|------|---------|
| `backend/app/agents/` → 缺 5 个课设 Agent | 课设扩展：recommend / review / dispatch / pricing / quality | 🆕 课设阶段创建 |
| `backend/app/agents/prompts/` → 缺 2 个 j2 | recommend.j2 / review.j2 | 🆕 课设阶段创建 |
| `backend/app/models/` → 缺 3 个 ORM | order / delivery / review | 🆕 课设阶段创建 |
| `backend/app/schemas/` → 缺 2 个 Schema | order / delivery | 🆕 课设阶段创建 |
| `backend/app/services/` → 缺 3 个 Service | order / delivery / payment | 🆕 课设阶段创建 |
| `backend/app/api/v1/` → 缺 3 个路由 | order / delivery / merchant | 🆕 课设阶段创建 |
| `backend/app/tasks/` → 缺 `notify_tasks.py` | 通知异步任务 | 🆕 课设阶段创建 |
| `frontend/src/pages/` → 缺 OrdersPage / MerchantPage | 课设页面 | 🆕 课设阶段创建 |
| `frontend/src/types/order.ts` | 缺失 | 🆕 课设阶段创建 |
| `frontend/src/api/order.ts` | 缺失 | 🆕 课设阶段创建 |
| `frontend/src/components/order/` / `merchant/` | 缺失 | 🆕 课设阶段创建 |

### 4.4 架构修改（需讨论）

| 现有路径 | 问题 | 建议操作 |
|---------|------|---------|
| `backend/app/celery_app.py` | 位于 `app/` 根，PROJECT.md 指定为 `app/tasks/celery_app.py` | 🏗️ 移入 `app/tasks/celery_app.py`，更新 Docker compose 和 Makefile |
| `backend/app/agents/hub.py` | MasterController 与 graph.py 双调度并存 | ⚠️ 统一到 LangGraph StateGraph 调度，hub.py 标记 @deprecated |
| `backend/app/core/state.py` | PlanStateMachine 与 LangGraph 状态机并存 | ⚠️ 讨论：是否完全由 LangGraph 管理状态 |
| `backend/app/adapters/adapters/` | 双层嵌套命名异味 | 🏗️ 重命名为 `adapters/clients/` |
| `mock_server/app/data/` | 空目录 | 🏗️ 将顶层 `data/seed_pois.json` 移入此目录 |
| `backend/app/services/mock_gateway.py` vs `tool_dag.py` | 两套 Tool 路由映射表（路径不一致） | ⚠️ 统一路由定义，推荐以 gateway 为单一事实来源 |
| `backend/app/schemas/__init__.py` | 空文件 | ⚠️ 添加 Schema 统一导出 |
| `backend/app/services/__init__.py` | 空文件 | ⚠️ 添加 Service 统一导出 |
| `backend/app/api/__init__.py` / `v1/__init__.py` | 空文件 | ⚠️ 添加路由注册导出 |

---

## 五、迁移脚本

```bash
#!/bin/bash
# SnapTrip 目录结构规范化迁移脚本
# 运行方式: bash scripts/migrate-structure.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== SnapTrip Structure Migration ==="

# ─── 新建目录 ────────────────────────────────────

mkdir -p "$ROOT/backend/app/core"               # 已存在
mkdir -p "$ROOT/backend/app/api/middleware"
mkdir -p "$ROOT/backend/app/agents/skills"
mkdir -p "$ROOT/backend/app/adapters/clients"
mkdir -p "$ROOT/backend/app/schemas"            # 已存在

echo "✓ 目录创建完成"

# ─── 新建文件 ────────────────────────────────────

# P1: utilities
cat > "$ROOT/backend/app/core/utils.py" << 'PYEOF'
"""通用工具函数 —— haversine 距离计算与 UUID 解析。"""

from __future__ import annotations

import math
import uuid


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间大圆距离 (km)。"""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_uuid(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        return None
PYEOF

# P1: cities data
cat > "$ROOT/backend/app/data/cities.py" << 'PYEOF'
"""城市中心坐标 + 关键词映射。"""
from __future__ import annotations

CITY_CENTERS: dict[str, tuple[float, float]] = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "重庆": (29.5630, 106.5516),
}

CITY_KEYWORDS: dict[str, list[str]] = {
    "北京": ["北京", "朝阳", "海淀", "东城", "西城", "三里屯", "国贸", "簋街", "故宫",
              "长城", "天安门", "颐和园", "鸟巢", "王府井", "后海", "798"],
    "上海": ["上海", "浦东", "静安", "徐汇", "外滩", "新天地", "陆家嘴", "迪士尼",
              "南京路", "城隍庙", "武康路", "法租界"],
    "重庆": ["重庆", "渝中", "江北", "南岸", "洪崖洞", "解放碑", "磁器口", "南山",
              "火锅", "朝天门", "观音桥"],
}
PYEOF

# P1: keywords data
cat > "$ROOT/backend/app/data/keywords.py" << 'PYEOF'
"""类型/心情关键词映射表。"""
from __future__ import annotations

TYPE_KEYWORDS: dict[str, list[str]] = {
    "restaurant": ["吃", "饭", "餐厅", "火锅", "烤鸭", "川菜", "本帮菜", "聚餐", "晚饭", "午饭", "美食"],
    "cafe": ["咖啡", "下午茶", "奶茶", "猫咖", "喝茶", "甜点", "甜品"],
    "attraction": ["逛", "景点", "博物馆", "公园", "打卡", "拍照", "夜景", "古镇", "故宫"],
    "activity": ["玩", "运动", "骑行", "游乐", "乐园", "手工", "陶艺"],
}

MOOD_KEYWORDS: dict[str, list[str]] = {
    "安静": ["安静", "清净", "放松", "休息"],
    "热闹": ["热闹", "嗨", "氛围好", "人气"],
    "浪漫": ["浪漫", "约会", "情侣"],
    "文艺": ["文艺", "小众", "艺术"],
    "亲子": ["带娃", "亲子", "小孩", "孩子"],
    "治愈": ["治愈", "温暖", "舒服"],
    "辣": ["辣", "麻辣", "重口味"],
    "拍照": ["拍照", "出片", "好看"],
}
PYEOF

echo "✓ 新建文件完成"

# ─── 移动 celery_app.py ──────────────────────────

if [ -f "$ROOT/backend/app/celery_app.py" ] && [ ! -f "$ROOT/backend/app/tasks/celery_app.py" ]; then
    mv "$ROOT/backend/app/celery_app.py" "$ROOT/backend/app/tasks/celery_app.py"
    echo "✓ celery_app.py → app/tasks/"
fi

# ─── 重命名 adapters/adapters/ → adapters/clients/ ─

if [ -d "$ROOT/backend/app/adapters/adapters" ] && [ ! -d "$ROOT/backend/app/adapters/clients" ]; then
    mv "$ROOT/backend/app/adapters/adapters" "$ROOT/backend/app/adapters/clients"
    echo "✓ adapters/adapters/ → adapters/clients/"
fi

# ─── 移除废弃文件 ────────────────────────────────

if [ -f "$ROOT/backend/app/services/plan_service.py" ]; then
    rm "$ROOT/backend/app/services/plan_service.py"
    echo "✓ 删除废弃 plan_service.py"
fi

echo ""
echo "=== 迁移完成 ==="
echo "请手动执行后续操作:"
echo "  1. 更新 adapters/__init__.py 和 clients/ 中的 import 路径"
echo "  2. 更新 docker-compose.yml 中 celery command 路径"
echo "  3. 将 agents/intent_parser.py 和 retrieval_engine.py 中的"
echo "     haversine/CITY_KEYWORDS 引用改为 core/utils.py 和 data/"
echo "  4. 将 mock_server/data/seed_pois.json 移至 mock_server/app/data/"
echo "  5. 运行 ruff check + mypy 确保无引用断裂"
```

---

## 六、各包职责说明

| 包路径 | 职责 | 依赖方向 |
|--------|------|---------|
| `core/` | 配置中心、异常体系、常量枚举、安全、日志、限流、通用工具 | 无（最底层） |
| `db/` | 数据库引擎、会话工厂、get_db 依赖 | → core.config |
| `models/` | SQLAlchemy ORM 表定义（纯声明，无业务逻辑） | → core (constants) |
| `schemas/` | Pydantic 数据校验 Schema（API 入参/出参 + Agent 合约） | → 无（纯数据） |
| `data/` | 种子数据、城市/关键词常量 | → schemas |
| `adapters/` | 高德地图 API 适配（HTTP Client + Adapter + Mapper + Schema） | → core.config |
| `services/` | 业务逻辑层（可被 API 和 Agent 复用） | → models, schemas, core |
| `agents/` | LangGraph Agent 编排（9 个竞赛 Agent + 5 个课设 Agent） | → services, schemas, data, core |
| `api/` | FastAPI 路由（薄层，参数校验 + 调用 service 或 graph） | → agents.graph, services, schemas |
| `tasks/` | Celery 异步任务（后台通知/数据同步） | → services, models |

**核心原则**：`core → models/schemas → services → agents/api`，禁止反向依赖。

---

## 七、总结

| 指标 | 数值 |
|------|:---:|
| 规范要求总文件数（竞赛+课设） | ~110 |
| 现有文件数 | ~94 |
| P0 阻塞问题 | 4 |
| P1 需尽快处理 | 23 |
| P2 后续迭代 | 17 |
| Stub 文件 | 1（consensus_resolver）+ 5 个空 `__init__.py` |
| 废弃文件 | 1（plan_service.py） |
| 重复代码块 | 7 处 |
| 整体完成度 | 竞赛核心 70%，课设扩展 0% |
