# 02 — AI Agent 系统架构

> **Updated**: 2026-06-17 | **Project**: SnapTrip E-Commerce Marketplace
>
> 基于 LangGraph StateGraph 构建的 Supervisor-Specialist 多智能体对话系统，
> 配备完整的工具层（Hook链 + Saga事务 + 审计追踪）和独立的推荐子系统。

---

## 总体架构

```
                         User Message (自然语言)
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Supervisor        │
                    │  (意图分类 + 路由)     │
                    │  LLM优先 + 关键词降级  │
                    └──────┬───────────────┘
                           │ route_by_intent (8种意图)
            ┌──────────────┼──────────────┬──────────────┐
            ▼              ▼              ▼              ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ Product     │ │ Order       │ │ Customer    │ │ Marketing   │
   │ Discovery   │ │ Assistant   │ │ Service ★   │ │ Engine      │
   │ (2 tools)   │ │ (2 tools)   │ │ (14 tools)  │ │ (2 tools)   │
   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
          │               │               │               │
          └───────────────┴───────┬───────┴───────────────┘
                                  │
            ┌──────────────┬──────┴──────┬──────────────┐
            ▼              ▼             ▼              ▼
   ┌─────────────┐ ┌─────────────┐
   │ Knowledge   │ │ Admin       │     ← ReAct 循环 ──→  tools
   │ QA          │ │ Analyst     │         (tool_node)
   │ (1 tool)    │ │ (6 tools)   │
   └──────┬──────┘ └──────┬──────┘
          │               │
          └───────┬───────┘
                  │
                  ▼
         ┌──────────────┐
         │  Synthesize   │  最终回复合成
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │  Compliance   │  合规检查 (PII + 禁用词)
         └──────┬───────┘
                │
                ▼
               END
```

**核心拓扑**：`START → supervisor → route_by_intent → [Specialist ↔ tools 循环] → synthesize → compliance → END`

---

## 状态定义 (PlanState)

LangGraph StateGraph 使用 `PlanState(TypedDict)`，18 个键：

| 分组 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 对话 | `messages` | `Annotated[list, add_messages]` | 对话历史自动累加 |
| 会话 | `plan_id` / `user_id` / `session_id` | `str` | 唯一标识 |
| 路由 | `intent` | `str` | 8 种意图之一 |
| | `intent_confidence` | `float` | 置信度 0-1 |
| | `current_agent` | `str` | 当前执行的 specialist |
| 结果 | `sub_results` | `dict` | 各 specialist 汇总结果 |
| | `product_results` | `list` | 商品搜索结果 |
| | `order_detail` | `dict\|None` | 订单详情 |
| CS域 | `ticket_id` / `cs_intent` | `str` | 工单ID / CS子意图 |
| | `escalation_level` | `int` | 升级级别 |
| | `satisfaction_score` | `float` | 满意度 |
| 记忆 | `working_memory` | `dict` | 多步推理临时存储 |
| | `retry_count` | `int` | 重试计数 |
| HITL | `hitl_payload` | `dict\|None` | 人机协同负载 |
| 合规 | `compliance_passed` | `bool` | 是否通过 |
| | `compliance_violations` | `list` | 违规列表 |
| | `compliance_risk` | `str` | 风险等级 |
| 图 | `phase` / `status` | `str` | DAG 路由与状态 |

---

## Supervisor — 意图分类

**文件**: `nodes/supervisor.py`

双层策略：

### Layer 1: LLM 分类
```
SUPERVISOR_SYSTEM_PROMPT → LLM → {"intent": "...", "confidence": 0.95}
```

### Layer 2: 关键词降级（LLM 失败时）
8 种意图共 200+ 个中英文关键词，取最高命中数意图。

### 意图映射

| intent | → specialist | 说明 |
|--------|-------------|------|
| `product_search` | `product_discovery` | 商品搜索/发现 |
| `order_status` | `order_assistant` | 订单状态查询/取消 |
| `cs_after_sales` | `customer_service` | 售后问题 |
| `cs_complaint` | `customer_service` | 投诉处理 |
| `cs_inquiry` | `customer_service` | 客服咨询 |
| `coupon_inquiry` | `marketing_engine` | 优惠券/促销 |
| `admin_analytics` | `admin_analyst` | B端数据分析 |
| `general` | `knowledge_qa` | 知识库问答 |

3 个 CS 子意图均路由到 `customer_service` 节点。

---

## Specialist 节点

所有 Specialist 继承 `BaseSpecialist` 模板基类，统一模式：

```python
class BaseSpecialist:
    node_name: str          # 节点名
    system_prompt: str      # 系统提示词
    tools: list[dict]       # 可用工具 (OpenAI function-calling 格式)
    phase_name: str         # 阶段名
    temperature: float = 0.3
    max_retries: int = 3    # 指数退避重试 (1s, 2s, 4s)

    async def execute(state) -> dict:
        # 1. 检查 adapter
        # 2. 重试守卫
        # 3. _build_messages(state) → OpenAI dict 格式
        # 4. _call_with_backoff → LLM 调用
        # 5. 返回 state update
```

### 6 个 Specialist 详情

| Specialist | 工具数 | 职责 | 特殊行为 |
|-----------|--------|------|---------|
| **ProductDiscovery** | 2 | 商品搜索/发现，按预算/品类/品牌过滤 | — |
| **OrderAssistant** | 2 | 订单状态/详情查询、配送追踪、取消订单 | — |
| **CustomerService** | 14 | 全场景售后 + 情感感知 | **重写 _build_messages()**: 注入情感上下文到 system prompt |
| **MarketingEngine** | 2 | 优惠券/促销查询 | — |
| **KnowledgeQA** | 1 | 知识库问答 (支付/账户/取消/保险/签证) | — |
| **AdminAnalyst** | 6 | B端数据分析 (销售/库存/会员/趋势) | **只读**: system prompt 禁止声称管理/创建/删除操作 |

---

## CustomerService — 情感感知客服

系统中最复杂的节点（14 个工具），集成情感检测：

```
用户消息
  ├── detect_emotion(text) → (emotion, confidence)
  │     5种情感: angry / frustrated / anxious / satisfied / neutral
  │     80+ 中英文关键词
  │
  ├── detect_emotion_trajectory(messages, window=5)
  │     最近 5 轮情感变化轨迹 → "angry→calm", "frustrated→satisfied"
  │
  └── emotion_to_tone_hint(emotion)
        → 注入 system prompt:
          "当前用户情绪: angry (置信度 0.85)
           语气调整: 优先安抚、主动道歉、加速处理"
```

---

## 辅助节点

### Synthesize — 最终合成
**文件**: `nodes/synthesize.py`

读取完整对话历史（用户/工具/LLM），调用 LLM 生成最终回复，提取 `answer` + `highlights` 字段，格式化为 Markdown。

### Compliance — 合规检查
**文件**: `nodes/compliance.py`

两阶段设计（当前 Phase 1）：
- **PII 扫描**: 手机号 (`1[3-9]\d{9}`)、邮箱、身份证、银行卡号
- **禁用词**: "保证收益"、"稳赚不赔"、"零风险"等 12 个广告法/金融合规术语
- **性能**: 纯正则，< 2ms
- **非阻断式**: 违规被记录到 state，但响应仍返回用户

---

## 工具系统

### 架构分层

```
LLM (tool_use)
  → ToolHarness.execute(name, args, session_ctx)  ← 唯一执行入口
    │
    ├── PreHook 链:
    │   AuthHook → RateLimitHook → TraceBeginHook → TxBeginHook
    │
    ├── SmartDayBaseTool._arun(args)
    │   └── httpx.AsyncClient → MARKETPLACE_URL REST API
    │
    ├── ErrorHook: ErrorAuditHook (异常时)
    │
    └── PostHook 链:
        CompRegHook → AuditLogHook → TraceEndHook → AlertHook → SpendGuardHook
```

### Hook 链详解

| Hook | 阶段 | 职责 |
|------|------|------|
| `AuthHook` | Pre | 写操作需要 `user_id` |
| `RateLimitHook` | Pre | 令牌桶，30次/分钟/工具 |
| `TraceBeginHook` | Pre | 记录开始时间戳和 span_id |
| `TxBeginHook` | Pre | 绑定/创建事务上下文 |
| `CompRegHook` | Post | 注册补偿动作到 CompensationRegistry |
| `AuditLogHook` | Post | 写入 SHA-256 哈希链审计 |
| `TraceEndHook` | Post | 记录执行延迟 |
| `AlertHook` | Post | 延迟 >30s 或错误时告警 |
| `SpendGuardHook` | Post | 跟踪累计费用 |
| `ErrorAuditHook` | Error | 工具异常时记录审计 |

### Saga 事务

**三阶段协调器** (`SagaCoordinator`):

```
Phase 1: RESERVE  → 软预留 (reserve_only=True)
Phase 2: CONFIRM  → 硬提交 (reserve_only=False)
Phase 3: ROLLBACK → 失败时通过 CompensationRegistry 逆序补偿
```

- 当前 Saga 工具: `cancel_order`
- **CompensationRegistry**: LIFO 补偿栈，支持 action_id 去重，最多 3 次重试

### 防篡改审计

```
AuditStore:
  Entry1 → SHA-256 → Entry2 → SHA-256 → Entry3 → ...
  (每条携带前一条的 hash, verify_chain() 可检测回溯篡改)
```

### Model 降级链

```
LangChainAdapter._call_with_fallback_stream():
  1. deepseek-v4-pro (default)
  2. deepseek-v4-flash (fallback 1)
  3. kimi-k2.6        (fallback 2)
  4. kimi-k2.5        (fallback 3)

每级最多 3 次 tenacity 指数退避重试 (1s, 2s, 4s)
```

---

## 推荐子系统

独立的 4-Agent 流水线，与主 DAG 并行运行：

```
UserProfile → ProductRec (召回) → ProductRec (重排) → Inventory → MarketingCopy
    │               │                    │               │            │
    └─ 用户画像 ────┴─ ES+CF+Hot ───────┴─ LLM排序 ─────┴─ 库存过滤 ─┴─ 文案生成
```

| Agent | LLM依赖 | 职责 |
|-------|---------|------|
| `SearchIntentAgent` | 可选，规则优先 | 区分 transactional/navigational/informational |
| `UserProfileAgent` | 可选，规则兜底 | 用户分群 + 类目偏好 + RFM 评分 |
| `ProductRecAgent` | Phase 2 可选 | Phase1召回 (ES+CF+热门) + Phase2 LLM重排 |
| `InventoryAgent` | 无 (纯规则) | 过滤缺货/下架，计算限购，低库存预警 |
| `MarketingCopyAgent` | 是 | 5种分群模板 + LLM文案 + 广告法合规过滤 |

两种编排方式：LangGraph 图编排 + Supervisor 纯函数编排，灵活切换。

---

## 事件总线 (RedisEventBus)

双写模式：
1. **SQL 持久化** → `plan_run_events` 表 (保证不丢)
2. **Redis Pub/Sub** → `plan:{plan_id}:events` 频道 (SSE 实时推送)
3. Redis 失败降级为纯 SQL，不阻塞图执行

---

## 目录结构

```
agent/src/agent/
├── graph.py              # 主图编排 (build_graph)
├── runtime.py            # AgentRuntime DI 容器
├── tool_node.py          # 工具调度节点
├── utils.py              # 共享工具函数
├── nodes/
│   ├── base.py           # BaseSpecialist 模板基类
│   ├── supervisor.py     # 意图分类 + 路由
│   ├── product_discovery.py / order_assistant.py
│   ├── customer_service.py / marketing_engine.py
│   ├── knowledge_qa.py / admin_analyst.py
│   ├── synthesize.py / compliance.py / emotion.py / trace.py
│   └── recommendation/   # 推荐子图
├── tools/
│   ├── bootstrap.py      # 工具注册工厂
│   ├── auth.py           # JWT ContextVar
│   ├── registry/         # ToolRegistry + ToolManifest
│   ├── harness/          # ToolHarness + SessionContext + Hooks
│   ├── transaction/      # Saga + Compensation
│   ├── tracing/          # AuditStore + ToolTracer
│   └── implementations/  # 20 个工具实现 + admin/
├── events/redis_bus.py   # RedisEventBus
├── ports/                # LLMPort / EventSinkPort / RepoPort
├── adapters/
│   ├── langchain_adapter.py  # LLM 适配器
│   └── persistence/          # SQL 持久化适配器
├── services/
│   ├── agent.py           # AgentService (图执行封装)
│   └── llm_gateway.py     # LLM 用量日志
└── schemas/              # PlanState / RuntimeEvent / Recommendation
```
