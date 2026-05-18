# 01 —— 系统架构总览

## 架构目标

构建一个**端到端的本地生活智能规划系统**，实现从自然语言输入到可执行时间轴方案的完整闭环。

**双域定位**：
- **竞赛核心**：Hackathon 命题 1.6 — 本地短时活动规划与执行 Agent（规划→预订→自愈→分享）
- **课设扩展**：传统本地生活服务 Agent 化（智能推荐、评价分析、配送调度、动态定价、质量监控）

**部署模式**：**模块化单体 + 3 进程部署**（backend :8000 / mock_server :8001 / frontend :5174），内部按目录分层，
非微服务架构。各模块直接 import，同一进程内内存传递，避免分布式复杂度。

**核心设计原则**：
- **Agent 自治**：每个 Agent 独立决策，LangGraph 图引擎负责调度
- **可观测性**：全链路 SSE 推送 + structlog JSON 结构化日志 + LangSmith 追踪
- **异常自愈**：局部失败不影响整体流程，Shadow Candidate + Ripple Reschedule 自动降级和补偿
- **Mock 解耦**：通过独立 Mock 服务模拟真实 API，开发阶段无需外部依赖
- **LLM 克制**：仅在意图解析（1 次）和规划排序（1 次）调用 LLM，其余全部纯代码

---

## 系统分层（6 层架构）

```
┌──────────────────────────────────────────────────────────────────┐
│                    前端层 (React 18 + Vite + Tailwind)             │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐        │
│  │ 计划面板  │  │ 地图视图  │  │ Agent大脑  │  │ 订单管理  │  ...   │
│  │(竞赛核心) │  │(Amap JS) │  │(思考过程)  │  │(课设扩展) │        │
│  └──────────┘  └──────────┘  └───────────┘  └──────────┘        │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST / SSE
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                  API 网关层 (FastAPI :8000)                        │
│  Auth 中间件(JWT) | Rate Limiter(Redis) | 统一响应{code,msg,data} │
│  /api/v1/plan/* (竞赛)  |  /api/v1/order/* | /api/v1/poi/* (课设) │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    编排层 (LangGraph StateGraph)                   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Agent Hub (langgraph)                     │ │
│  │  PostgresSaver(持久化) │ AgentRegistry(注册发现) │ PolicyEngine │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─── 竞赛核心 Agent 链 ───────────────────────────────────────┐ │
│  │ Intent → Context → Memory → Retrieval → Planning             │ │
│  │   → Consensus → Execution → [Fallback] → Notify              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─── 课设扩展 Agent ──────────────────────────────────────────┐ │
│  │ RecommendAgent │ ReviewAgent │ DispatchAgent                  │ │
│  │ PricingAgent   │ QualityAgent                                │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬──────────────────────────────────────┘
                            │ Tool Call
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    执行层 (Tool DAG)                               │
│  L0: search_poi | get_user_profile                               │
│  L1: check_queue | check_availability | check_child_facility     │
│       calculate_route                                            │
│  L2: book_table | book_ticket | order | deliver | ride_hail      │
│  L3: notify                                                      │
│  CircuitBreaker | RetryPolicy | Saga Compensate                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                Mock API 层 (FastAPI :8001 / 真实API)              │
│  poi | queue | booking | order | delivery | payment              │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    数据层                                         │
│  PostgreSQL 16 + pgvector(向量) | Redis 7(缓存/PubSub/限流)       │
│  MinIO(对象存储) | Celery(异步任务队列)                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 部署架构（模块化单体，3 进程）

```
                     docker compose up

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  backend :8000   │  │  mock_server:8001 │  │  frontend :5174  │
│                  │  │                  │  │                  │
│ FastAPI + Agents │  │ 模拟美团本地生活API  │  │ React SPA        │
│ LangGraph 图引擎  │  │ poi/queue/booking │  │ Amap 地图集成     │
│ Celery Worker    │  │ /order/delivery   │  │ SSE 流式渲染      │
│ ──────────────── │  │ ──────────────── │  │ ─────────────── │
│ 竞赛9Agent +     │  │ 5 Router         │  │ 三栏布局          │
│ 课设5Agent       │  │ 50条种子POI       │  │ 计划/订单/商家     │
│ 全部业务Services │  │                  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
         │                      │
         ▼                      ▼
┌──────────────┐       ┌──────────────┐
│ PostgreSQL 16│       │   Redis 7    │
│  :5432       │       │   :6379      │
│ pgvector     │       │ PubSub/缓存   │
└──────────────┘       └──────────────┘
```

**模块边界**：
- `backend/app/agents/` —— Agent 层，共享 Hub
- `backend/app/services/` —— 业务服务层，共享 DB 连接池 + Redis
- `backend/app/models/` —— ORM，同一套表（Alembic 迁移）
- `backend/app/api/v1/` —— 路由，同一 FastAPI app
- `backend/app/tasks/` —— Celery，同一队列

各模块间直接 import（非 HTTP 调用），将来拆微服务时边界清晰、抽离代价低。

---

## 竞赛核心 vs 课设扩展对照表

| 模块 | 竞赛核心 | 课设扩展 |
|------|:---:|:---:|
| **Agent 数量** | 9 个（规划执行全链路） | +5 个（业务智能） |
| **API 路由** | plan + session | +auth/user/poi/order/delivery/merchant |
| **业务服务** | plan_service + mock_gateway + memory | +user/poi/order/delivery/payment/notify |
| **ORM 模型** | 0 个（当前全内存）→ 需补齐 | +user/plan/poi/order/delivery/review |
| **前端页面** | PlanPage（三栏布局） | +OrdersPage/MerchantPage/LoginPage |
| **Mock Server** | 5 Router + 50 POI | 可复用 |
| **LangGraph Node** | 9 个竞赛 Agent Node | 5 个课设 Agent 作为独立子图 |
| **LLM 调用** | 2 次/请求（intent + planning） | 3-5 次/请求（recommend/review/pricing） |

---

## Agent 协作图（LangGraph StateGraph）

```
用户 ──"下午想带朋友出去玩"──► API Gateway
                                  │
                                  ▼
                          ┌───────────────┐
                          │  Agent Hub    │
                          │  (LangGraph)  │
                          │  PostgresSaver│
                          └───────┬───────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ 竞赛核心链路   │ │课设Agent │ │ 传统服务接口   │
            │ (StateGraph) │ │(独立调用) │ │ (REST API)   │
            └──────┬───────┘ └──────┬───┘ └──────┬───────┘
                   │               │             │
                   ▼               ▼             ▼
            ┌──────────────────────────────────────────┐
            │          Tool 注册表 (10+ Tools)          │
            │  search_poi | check_queue | book_table   │
            │  book_ticket | order | deliver | pay     │
            │  check_weather | get_review | calc_route │
            └────────────────────┬─────────────────────┘
                                 │
                      ┌──────────┼──────────┐
                      ▼          ▼          ▼
                 Mock API    真实API    本地计算
                 (竞赛用)    (课设)     (Haversine等)
```

---

## 组件交互时序（LangGraph 驱动）

```
用户 ──"下午想出去"──► Frontend
                          │
                    POST /api/v1/plan/create
                          │
                          ▼
                      FastAPI Gateway
                          │
                          ▼
                    AgentHub.submit(context)
                          │
                    LangGraph.astream_events()
                          │
    ┌─────────────────────┼─────────────────────────┐
    ▼                     ▼                         ▼
┌───────────┐     ┌──────────────┐         ┌──────────────┐
│intent_    │     │retrieval_    │         │planning_     │
│parser     │     │engine        │         │engine        │
│(LLM 调用) │     │(3路并行检索)  │         │(Phase1+Phase2)│
└─────┬─────┘     └──────┬───────┘         └──────┬───────┘
      │                  │                        │
      ▼                  ▼                        ▼
  AgentResult        CandidatePool            PlanDraft
  (SSE: intent)      (SSE: retrieval)         (SSE: planning_done)
                                                        │
                                          ┌─────────────▼─────────────┐
                                          │     CONFIRM 节点           │
                                          │  interrupt() 挂起等待用户   │
                                          └─────────────┬─────────────┘
                                              object│    │confirm
                                          ┌─────────▼┐   ▼
                                          │ REPLAN   │  EXECUTE
                                          │ 增量重规划 │  Tool DAG
                                          └─────┬────┘   │
                                                │   ┌────▼────┐
                                                └──►│ FALLBACK │
                                                    │ 备选重排  │
                                                    └────┬─────┘
                                                         ▼
                                                    NOTIFY → DONE
                                                         │
    Frontend ◀── SSE Stream (10 events) ◀───────────────┘
```

---

## 关键技术决策

| 决策 | 选型 | 理由 |
|------|------|------|
| Agent 框架 | **LangGraph** (替代 Hermes) | 原生 StateGraph + PostgresSaver + interrupt 人机协同 + astream_events 流式输出 |
| 地图服务 | 高德 JS API 2.0 | 国内 POI 数据丰富，支持路径动画 |
| 语音输入 | Web Speech API → 预留第三方 | 浏览器原生，零依赖；预留讯飞/百度扩展 |
| POI 城市 | 重庆 / 上海 / 北京 | 三城风格差异大，验证跨区域能力 |
| 用户认证 | JWT + OAuth (Google/微信) | 无状态 JWT 适合容器部署 |
| LLM 网关 | OpenRouter | 统一接入 DeepSeek-V3 / Claude-3.5-Sonnet |
| Embedding | OpenAI text-embedding-3-small (1536d) | 与 pgvector vector(1536) 匹配 |
| 异步任务 | Celery + Redis | 异步任务重试/持久化/监控 |
| 路线动画 | 高德 JS API 路线规划 | SSE 事件驱动地图更新 |
| 分享卡片 | Playwright HTML→截图 PNG | 复杂布局 + 微信分享兼容 |
| 数据库设计 | plans 1:N plan_slots | 分离聚合信息和单步细节 |
| 两阶段规划 | 硬约束(非LLM) + 软约束(LLM) | 可预测 + 低成本 |
| Tool 编排 | DAG + Saga | 并行执行 + 补偿事务 |
| pgvector | 统一存储向量+结构 | 同一事务，避免不一致 |
| 架构模式 | **模块化单体 + 3 进程** | 避免分布式复杂度，目录分层清晰，将来可拆微服务 |
| 可观测性 | structlog + LangSmith | JSON 结构化日志 + Agent 全链路自动追踪 |
| 安全 | JWT + Prompt 注入防御 + Rate Limit | 认证/防注入/限流三件套 |

---

## 数据流（端到端）

1. **用户请求** → Plan API 接收原始文本
2. **意图解析** → Intent Parser (LLM) 输出结构化意图（人数、时间、预算、偏好）
3. **上下文加载** → Context Loader 加载用户画像 (pgvector) + Memory Manager 增强记忆向量
4. **POI 检索** → Retrieval Engine 并行 3 路检索获取候选池（≤50）
   - 3 路并行：活动 / 餐饮 / 额外
   - 超时 1s，降级为 Redis 缓存（TTL 1h）
5. **硬约束过滤** → Planning Phase 1（纯代码 CSP）+ 同步预计算 Shadow Candidates
   - Haversine 距离过滤 ≤15km | 营业时间校验 | 预算约束 | 类型匹配
   - Shadow 预查可用性存入 Checkpoint
6. **软约束排序** → Planning Phase 2（LLM）排序并分配时隙
   - 超时 3s，降级为 Phase 1 评分排序
7. **共识确认** → Consensus Resolver（纯代码）等待用户确认
   - `interrupt()` 挂起，SSE 推送前端，用户 confirm/object 后 `resume`
8. **预订执行** → Execution Engine Tool DAG 4 层分层并行执行
   - 层内 `asyncio.gather` 并行，层间顺序
   - 单 Tool 3s / 总 DAG 10s 超时
9. **异常容错** → Fallback Engine 激活 Shadow Candidate + 涟漪重排
   - 优先 Shadow 缓存 → 局部重检索 → Saga 补偿
   - 最多 2 次 Fallback，超限 → FAILED
10. **结果输出** → Notify Engine 生成分享卡片，Playwright 渲染 PNG
