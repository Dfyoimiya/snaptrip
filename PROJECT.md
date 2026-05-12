# Activity Agent —— 本地生活智能规划与执行系统

## 项目概述

本项目是面向美团 AI Hackathon 命题 1.6（本地场景短时活动规划与执行 Agent）的全栈解决方案，同时作为个人 Agent 开发实习项目。

**核心定位**：用户输入一句自然语言（如"今天下午有空，想和朋友出去玩"），系统通过多 Agent 协作生成可执行的时间轴方案，并自动完成 Mock 预订/下单，最终生成可分享的计划卡片。

**产品闭环**：自然语言输入 → 意图解析 → POI 检索 → 时空规划 → 自动预订 → 异常自愈 → 分享通知。

---

## 技术架构

### 全栈技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|----------|
| **Agent 框架** | Hermes Agent (NousResearch) | 通过 HTTP/ACP 协议调用，支持 Skill 自进化 |
| **LLM 网关** | OpenRouter | 统一接入 DeepSeek-V3 / Claude-3.5-Sonnet |
| **后端** | FastAPI + Pydantic v2 + SQLAlchemy 2.0 | 异步全链路，自动 Swagger 文档 |
| **数据库** | PostgreSQL 15 + pgvector | 结构化数据 + 向量记忆统一存储 |
| **缓存/队列** | Redis + Celery | 会话缓存 + 异步任务（PDF 解析、Embedding） |
| **前端** | React 18 + TypeScript + Tailwind + Vite | 三栏实时观测台布局 |
| **Mock 服务** | FastAPI 子服务 | 独立进程，模拟美团本地生活 API |
| **部署** | Docker Compose | 一键启动全栈 |
| **包管理** | uv (Python) + npm (Node) | 后端用 uv，前端用 npm |

### 架构分层

```plain
用户交互层 (React)
↓ REST / WebSocket (SSE)
API 网关层 (FastAPI)
↓ ACP / HTTP
Agent 执行层 (Master Controller)
├─ Intent Parser (意图解析)
├─ Context Loader (用户画像加载)
├─ Memory Manager (记忆增强与向量读写)
├─ Retrieval Engine (并行 POI 检索)
├─ Planning Engine (两阶段时空规划)
├─ Consensus Resolver (群体共识解析)
├─ Execution Engine (Tool DAG 编排执行)
├─ Fallback Engine (容错与局部重规划)
└─ Notify Engine (分享卡片生成)
↓ Tool Call
Mock API 层 (FastAPI 独立服务)
├─ POI 搜索
├─ 排队查询
├─ 订座/订票
└─ 下单/叫车
```
---

## 目录结构规范

项目采用 **Monorepo** 管理，前后端 + Mock 统一仓库：

```plain
snaptrip/
├── Makefile                    # 统一命令入口（make dev / make up / make test-backend）
├── docker-compose.yml          # 生产/竞赛基础设施
├── docker-compose.override.yml # 本地开发覆盖（热重载）
├── .env.example                # 环境变量模板
├── README.md                   # 快速开始
│
├── backend/                    # FastAPI 核心后端
│   ├── app/
│   │   ├── main.py             # App Factory 入口（ lifespan + 路由注册）
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic-Settings 配置中心（必须 env 驱动）
│   │   │   ├── logging.py      # structlog JSON 格式
│   │   │   ├── exceptions.py   # 业务异常基类（HTTPException 子类）
│   │   │   └── constants.py    # 枚举（PlanStatus, POIType 等）
│   │   ├── api/
│   │   │   ├── deps.py         # FastAPI Dependencies（get_db / get_redis）
│   │   │   └── v1/
│   │   │       ├── plan.py     # 规划 API：POST /api/v1/plan/create, GET /api/v1/plan/{id}
│   │   │       ├── user.py     # 用户画像 API
│   │   │       └── session.py  # Agent 会话管理 + SSE 流式输出
│   │   ├── schemas/
│   │   │   ├── plan.py         # PlanCreate / PlanResponse / PlanSlot
│   │   │   ├── user.py         # UserProfile / PreferenceVector
│   │   │   └── common.py       # ResponseModel[T] 统一响应体
│   │   ├── models/
│   │   │   ├── base.py         # SQLAlchemy Base + TimestampMixin
│   │   │   ├── user.py         # 用户画像表（含 preference_vector: Vector）
│   │   │   ├── plan.py         # 计划主表 + 时隙子表
│   │   │   ├── poi.py          # POI 实体（含 mood_tags, business_hours）
│   │   │   └── knowledge_item.py # 长期记忆条目
│   │   ├── services/
│   │   │   ├── plan_service.py # 规划编排核心（两阶段算法）
│   │   │   ├── user_service.py
│   │   │   └── memory_service.py # pgvector 记忆读写
│   │   ├── agents/
│   │   │   ├── hub.py          # Agent Hub：路由分发 + 状态机管理
│   │   │   ├── intent_agent.py # 意图解析（Prompt + Schema 约束）
│   │   │   ├── planning_agent.py # 时空规划（硬约束过滤 + 软约束排序）
│   │   │   ├── execution_agent.py # Tool 调用编排（DAG + Saga）
│   │   │   └── skills/         # Hermes Skill 文件（.md）
│   │   ├── tasks/              # Celery 异步任务
│   │   │   └── plan_tasks.py   # 异步规划执行
│   │   └── db/
│   │       ├── session.py      # AsyncSession 工厂
│   │       └── migrations/     # Alembic 迁移目录
│   ├── alembic/
│   ├── tests/
│   │   ├── conftest.py         # Pytest fixtures（async_client, db_session）
│   │   ├── unit/               # 单测：Agent Prompt / 规划算法 / Tool 调用
│   │   └── integration/        # 集成：端到端规划链路
│   ├── pyproject.toml          # uv 依赖管理
│   └── Dockerfile              # 多阶段构建（development / production）
│
├── frontend/                   # React 18 + TypeScript
│   ├── src/
│   │   ├── api/                # Axios 封装 + 类型定义
│   │   ├── components/         # 原子组件（PlanCard / AgentLog / MapView）
│   │   ├── pages/              # 页面（Home / PlanDetail / AgentMonitor）
│   │   ├── stores/             # Zustand 状态管理
│   │   ├── hooks/              # useAgentStream (SSE) / usePlanState
│   │   └── types/              # 全局 TS 类型（与 backend schemas 对齐）
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts          # 代理 /api 到 localhost:8000
│
├── mock_server/                # 独立 Mock API 服务（端口 8001）
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── poi.py          # GET /mock/poi/search, GET /mock/poi/{id}
│   │   │   ├── queue.py        # GET /mock/queue/{poi_id}
│   │   │   ├── booking.py      # POST /mock/booking/table, POST /mock/booking/ticket
│   │   │   └── order.py        # POST /mock/order
│   │   └── data/               # seed_pois.json / seed_queues.json
│   └── pyproject.toml
│
└── docs/                       # 设计文档（Markdown）
├── architecture/
├── api/
└── meetings/

```
---

---

## 开发规范（强制遵守）

### 1. 代码风格

- **Python**：`ruff` 格式化，`mypy --strict` 类型检查，行宽 100
- **TypeScript**：`strict: true`，显式类型，禁止 `any`
- **提交规范**：`feat: / fix: / refactor: / test: / docs:` 前缀

### 2. 接口规范

- **统一响应体**：所有 API 返回 `ResponseModel[T]`，结构为 `{code: 0, message: "success", data: T}`
- **错误码**：`400` 业务参数错误 / `422` 校验失败 / `500` 系统错误 / `503` Agent 超时
- **流式输出**：Agent 思考过程使用 SSE，`Content-Type: text/event-stream`，事件名：`intent`, `retrieval`, `planning`, `execution`, `notify`

### 3. 数据库规范

- **命名**：表名复数 `plans`, `pois`；字段蛇形 `created_at`
- **向量字段**：使用 `pgvector` 的 `vector(1536)` 类型，命名 `embedding`
- **迁移**：任何模型变更必须通过 `alembic revision --autogenerate`，禁止手动改表

### 4. Agent 开发规范

- **Prompt 模板化**：所有 Prompt 放在 `agents/prompts/` 下，使用 Jinja2 模板，禁止硬编码字符串
- **Tool 定义**：每个 Tool 必须有 `name`, `description`, `parameters`（JSON Schema），符合 OpenAI Function Calling 规范
- **Skill 文件**：Hermes Skill 放在 `agents/skills/` 下，Markdown 格式，包含 `## 触发条件` / `## 执行步骤` / `## 示例`

---

## 核心模块实现指南

### 模块 1：规划服务（Plan Service）—— 两阶段算法

**文件**：`backend/app/services/plan_service.py`

**要求**：
1. **Phase 1（硬约束过滤）**：纯代码逻辑，非 LLM。输入候选 POI 池，按营业时间、地理半径、容量、预算过滤，输出精简候选集（≤10 个）。
2. **Phase 2（软约束排序）**：调用 Planning Agent（LLM）。输入精简候选集 + 用户偏好，输出带时间轴的计划。LLM 只负责排序和组合，不负责可行性验证。
3. **输出 Schema**：必须返回 `PlanResponse`，包含 `slots: List[PlanSlot]`，每个 slot 有 `time`, `poi`, `action`, `booking_status`, `estimated_cost`。

### 模块 2：Agent Hub —— 路由与状态机

**文件**：`backend/app/agents/hub.py`

**要求**：
1. 维护 Plan 状态机：`drafting → planning → executing → confirmed → done | failed`
2. 串行调度 Agent：Intent → Context → Retrieval → Planning → Execution → Notify
3. 并行优化：Retrieval Agent 内部可并行查景点/餐厅/活动（通过 `asyncio.gather`）
4. 异常捕获：任一 Agent 失败时，进入 `Fallback Agent`，执行局部重规划

### 模块 3：Tool 编排器 —— DAG + Saga

**文件**：`backend/app/agents/execution_agent.py`

**要求**：
1. **DAG 定义**：用字典定义 Tool 依赖图，如 `{"book_table": ["check_queue"], "check_queue": ["search_poi"]}`
2. **并行执行**：无依赖的 Tool 同时调用（如同时查 3 家餐厅排队）
3. **Saga 事务**：每个 Tool 有 `compensate` 方法。若 `book_table` 失败，已成功的 `book_ticket` 不取消，仅重排下游
4. **超时控制**：单个 Tool 调用超时 3 秒，整体规划超时 10 秒

### 模块 4：Mock API 服务

**文件**：`mock_server/app/routers/*.py`

**要求**：
1. **POI 检索**：支持按 `lat/lng/radius/type/tags` 过滤，返回 3-5 个 Mock POI
2. **排队查询**：返回随机排队时间（0-60min），热门商户概率性 >40min
3. **预订接口**：20% 概率返回失败（`success: false, reason: "该时段已满"`），用于演示异常自愈
4. **数据种子**：启动时从 `data/seed_pois.json` 加载 50 个预置 POI（覆盖餐饮/景点/活动/咖啡馆）

---

## 数据库设计（核心表）

### `users` 用户画像表
```sql
id UUID PK
name TEXT
preference_vector VECTOR(1536)  -- pgvector，跨会话记忆
family_profile JSONB            -- {child_age: 5, diet: "低卡", allergens: ["花生"]}
created_at TIMESTAMP
```

### `plans` 计划主表（1:N plan_slots）
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
```sql
-- plans 计划主表（存聚合信息）
id UUID PK
user_id UUID FK → users.id
status VARCHAR(20)              -- drafting / planning / executing / confirmed / failed
query_text TEXT                 -- 用户原始自然语言输入
total_cost INT
created_at TIMESTAMP

-- plan_slots 时隙子表（存单步细节）
id UUID PK
plan_id UUID FK → plans.id
poi_id UUID FK → pois.id
time_range TSTZRANGE            -- PostgreSQL 时间范围类型
action VARCHAR(50)              -- arrive / book_table / book_ticket / order
booking_status VARCHAR(20)      -- pending / held / confirmed / failed
estimated_cost INT
sequence INT                    -- 排序
```

### `pois` POI 实体表
```sql
id UUID PK
name TEXT
type VARCHAR(50)                -- restaurant / activity / cafe / attraction
lat FLOAT, lng FLOAT
mood_tags TEXT[]                  -- GIN 索引数组：{安静, 亲子, 治愈, 热闹}
business_hours TSTZRANGE[]
avg_price INT
rating FLOAT
embedding VECTOR(1536)           -- 用于语义检索和跨课程关联
```
## 前端核心组件规范
### 三栏布局
| 栏位              | 宽度  | 内容                           | 实时更新       |
| --------------- | --- | ---------------------------- | ---------- |
| **左栏：地图**       | 40% | 用户位置 + POI 气泡 + 渐变路线动画       | Agent 每步更新 |
| **中栏：Agent 大脑** | 35% | Agent 节点状态 + Tool 调用日志（终端风格） | SSE 流式     |
| **右栏：计划卡片**     | 25% | 时间轴 + 费用 + 一键确认 + 分享         | 最终确认后生成    |
### 关键交互
1. 输入区：大字输入框，支持语音/文字，下方显示解析出的约束标签（可点击修改）
2. 流式加载：点击生成后，右栏先显示骨架时间轴（2 秒内），再逐步填充详情
3. 异常演示：Mock 触发预订失败时，右栏弹出「差异对比卡片」，高亮变化项
4. 分享卡片：确认后生成手机比例的卡片，含「发给朋友」按钮，模拟微信对话框
---
## OpenCode 协作指令
当用户要求你基于本文档进行开发时，请按以下优先级执行： 
### 阶段1：基础设施（第 1 次交互）
1. 创建 docker-compose.yml + docker-compose.override.yml + .env.example
2. 创建 backend/pyproject.toml（uv + FastAPI 依赖）
3. 创建 frontend/package.json（React + Vite + Tailwind）
4. 创建 mock_server/pyproject.toml
5. 创建 Makefile（含 make dev / make init / make test-backend）
6. 确保 make init 可执行（复制 .env、安装依赖）
### 阶段 2：后端骨架（第 2 次交互）
1. 创建 backend/app/core/config.py（Pydantic-Settings）
2. 创建 backend/app/core/logging.py（structlog JSON）
3. 创建 backend/app/main.py（App Factory + lifespan + 路由注册）
4. 创建 backend/app/db/session.py（asyncpg + AsyncSessionLocal）
5. 创建 backend/app/models/base.py（SQLAlchemy Base + TimestampMixin）
6. 初始化 Alembic：alembic init alembic
7. 创建第一个迁移：生成 users, plans, plan_slots, pois 表
### 阶段 3：Mock 服务（第 3 次交互）
1. 创建 mock_server/app/main.py
2. 创建 4 个 Router：poi.py, queue.py, booking.py, order.py
3. 创建 mock_server/app/data/seed_pois.json（50 条预置数据）
4. 确保 Mock 服务在 localhost:8001 可访问，Swagger 文档正常
### 阶段 4：Agent 层（第 4 次交互）
1. 创建 backend/app/agents/hub.py（状态机 + Agent 调度）
2. 创建 backend/app/agents/intent_agent.py（Prompt + 意图解析）
3. 创建 backend/app/agents/planning_agent.py（两阶段规划封装）
4. 创建 backend/app/agents/execution_agent.py（Tool DAG + Saga）
5. 创建 backend/app/agents/prompts/ 下的 Jinja2 模板
### 阶段 5：前端骨架（第 5 次交互）
1. 创建 frontend/src/main.tsx + App.tsx
2. 创建三栏布局组件：MapView, AgentMonitor, PlanCard
3. 实现 SSE Hook：useAgentStream（EventSource 封装）
4. 实现 Plan API 调用：createPlan, getPlan
5. 确保前端代理 /api 到 localhost:8000
### 阶段 6：集成与测试（第 6 次交互）
1. 确保 make dev 一键启动全栈（DB + Redis + Backend + Frontend + Mock）
2. 编写 tests/unit/test_plan_service.py（测试硬约束过滤逻辑）
3. 编写 tests/integration/test_end_to_end.py（测试完整规划链路）
4. 生成 README.md（快速开始指南）
### 代码生成原则
- 先写接口（Schema），再写实现：所有函数必须先有 Pydantic / TypeScript 类型定义
- 禁止硬编码：配置走 config.py，Prompt 走模板文件，数据走 seed 文件
- 异步优先：数据库、HTTP 调用全部使用 async/await
- 错误处理：所有外部调用必须 try/except，包装为业务异常
- 日志：关键节点必须 logger.info("plan_created", plan_id=..., user_id=...)

