# 01 —— 系统架构总览

## 架构目标

构建一个**端到端的本地生活智能规划系统**，实现从自然语言输入到可执行时间轴方案的完整闭环。

核心设计原则：
- **Agent 自治**：每个 Agent 独立决策，Hub 负责调度
- **可观测性**：全链路 SSE 推送 + 结构化日志
- **异常自愈**：局部失败不影响整体流程，自动降级和补偿
- **Mock 解耦**：通过独立 Mock 服务模拟真实 API，开发阶段无需外部依赖

## 系统分层

```
┌─────────────────────────────────────────────┐
│             接入层 (React)                    │
│  三栏布局：地图 | Agent 大脑 | 计划卡片        │
└────────────────┬────────────────────────────┘
                 │ REST / SSE
┌────────────────▼────────────────────────────┐
│           API 网关层 (FastAPI)                │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│            编排层 (Master Controller)         │
│  State Registry (7状态FSM)                    │
│  Policy Engine (策略裁决表)                    │
│  Checkpoint Manager (Slot检查点)              │
│                                              │
│  9 Agent:                                    │
│  Intent → Context → Memory → Retrieval →     │
│  Planning → Consensus → Execution →          │
│  Fallback → Notify                           │
└────────────────┬────────────────────────────┘
                 │ Tool Call
┌────────────────▼────────────────────────────┐
│            执行层 (Tool DAG)                  │
│  L0: search_poi | get_user_profile           │
│  L1: check_queue | check_availability        │
│      check_child_facility | calculate_route  │
│  L2: book_table | book_ticket | order        │
│  L3: notify                                  │
└────────────────┬────────────────────────────┘
                 │ HTTP
┌────────────────▼────────────────────────────┐
│         Mock API 层 (FastAPI 8001)            │
│  POI 搜索 | 排队查询 | 订座/订票 | 下单        │
└─────────────────────────────────────────────┘
```

## 组件交互时序

```
用户 ──"下午想出去"──▶ Frontend
                          │
                    POST /api/v1/plan/create
                          │
                          ▼
                      FastAPI Gateway
                          │
                          ▼
                    Master Controller
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    State Registry   Policy Engine   Checkpoint Mgr
          │               │               │
          ▼               ▼               │
    ┌─────────────┐       │               │
    │ Intent      │──►  DRAFTING          │
    │ Parser      │                       │
    └──────┬──────┘                       │
           ▼                              │
    ┌───────────────┐                     │
    │ Context Loader│──►  DRAFTING        │
    └──────┬────────┘                     │
           ▼                              │
    ┌───────────────┐                     │
    │ Memory Manager│──►  DRAFTING→PLANNING│
    └──────┬────────┘                     │
           ▼                              │
    ┌─────────────────┐                   │
    │ Retrieval Engine │──► PLANNING      │
    └──────┬──────────┘                   │
           ▼                              │
    ┌──────────────────┐                  │
    │ Planning Engine   │──► CONFIRMING   │
    │ Phase1 CSP+Shadow │                  │
    │ Phase2 LLM        │                  │
    └──────┬───────────┘                  │
           ▼                              │
    ┌──────────────────┐                  │
    │ Consensus Resolver│──► EXECUTING    │
    │ (auto_confirm)    │                  │
    └──────┬───────────┘                  │
           ▼                              │
    ┌──────────────────┐                  │
    │ Execution Engine  │──► DONE/FAILED  │
    │ Tool DAG 分层并行 │                  │
    └──────┬───────────┘                  │
           │ (失败)                        │
           ▼                              │
    ┌──────────────────┐──► CONFIRMING(重入)│
    │ Fallback Engine   │                  │
    │ Shadow+Ripple     │                  │
    └──────┬───────────┘                  │
           ▼                              │
    ┌──────────────┐                      │
    │ Notify Engine│──► DONE              │
    └──────────────┘                      │
                                          │
    Frontend ◀── SSE Stream (10 events)   │
```

## 关键技术决策

| 决策 | 选型 | 理由 |
|------|------|------|
| Agent 框架 | Hermes (NousResearch) | 支持 Skill 自进化，ACP/HTTP 协议解耦 |
| 地图服务 | 高德 JS API 2.0 | 国内 POI 数据丰富，支持路径动画 |
| 语音输入 | Web Speech API → 预留第三方 | 浏览器原生，零依赖；预留讯飞/百度扩展 |
| POI 城市 | 重庆 / 上海 / 北京 | 三城风格差异大，验证跨区域能力 |
| 用户认证 | JWT + OAuth (Google/微信) | 无状态 JWT 适合容器部署 |
| LLM 网关 | OpenRouter | 统一接入 DeepSeek-V3 / Claude-3.5-Sonnet |
| Embedding | OpenAI text-embedding-3-small (1536d) | 与 pgvector vector(1536) 匹配 |
| 异步任务 | Phase 4: asyncio.create_task → Phase 6: Celery | 渐进式引入，聚焦核心链路 |
| 路线动画 | 高德 JS API 路线规划 | SSE 事件驱动地图更新 |
| 分享卡片 | Playwright HTML→截图 PNG | 复杂布局 + 微信分享兼容 |
| 数据库设计 | plans 1:N plan_slots | 分离聚合信息和单步细节 |
| 两阶段规划 | 硬约束(非LLM) + 软约束(LLM) | 可预测 + 低成本 |
| Tool 编排 | DAG + Saga | 并行执行 + 补偿事务 |
| pgvector | 统一存储向量+结构 | 同一事务，避免不一致 |

## 部署架构

```
┌──────────────────────────────────┐
│         Docker Compose            │
│                                   │
│  ┌─────────┐  ┌────────────────┐ │
│  │ Frontend│  │   Backend API  │ │
│  │  :5173  │  │     :8000      │ │
│  └─────────┘  └───────┬────────┘ │
│                       │           │
│  ┌──────────┐  ┌──────▼──────┐  │
│  │ Mock API │  │  PostgreSQL │  │
│  │  :8001   │  │    :5432    │  │
│  └──────────┘  └─────────────┘  │
│                                   │
│           ┌─────────┐             │
│           │  Redis  │             │
│           │  :6379   │             │
│           └─────────┘             │
└──────────────────────────────────┘
```

## 数据流

1. **用户请求** → Plan API 接收原始文本
2. **意图解析** → Intent Parser 输出结构化意图（人数、时间、预算、偏好）
3. **上下文加载** → Context Loader 加载用户画像 + Memory Manager 增强记忆向量
4. **POI 检索** → Retrieval Engine 并行 3 路检索获取候选池（≤50）
5. **硬约束过滤** → Planning Phase 1（纯代码 CSP）+ 同步预计算 Shadow Candidates
6. **软约束排序** → Planning Phase 2（LLM）排序并分配时隙
7. **共识确认** → Consensus Resolver 处理确认（单用户 auto_confirm）
8. **预订执行** → Execution Engine Tool DAG 4 层分层并行执行
9. **异常容错** → Fallback Engine 激活 Shadow Candidate + 涟漪重排
10. **结果输出** → Notify Engine 生成分享卡片，SSE 全链路推送
