# 05 —— Agent 架构：三层闭环系统

## 总体架构

```
┌────────────── 接入层 ──────────────┐
│    自然语言输入 → 状态机入口         │
└──────────────┬────────────────────┘
               │
┌──────────────▼────────────────────┐
│            编排层                   │
│  Master Controller (中央控制器)      │
│  ├─ State Registry (7 状态 FSM)     │
│  ├─ Policy Engine (策略裁决表)       │
│  ├─ Checkpoint Manager (Slot 检查点) │
│  └─ 9 Agent 调度链                  │
│  Intent → Context → Memory →       │
│  Retrieval → Planning →            │
│  Consensus → Execution → Fallback  │
│  → Notify                          │
└──────────────┬────────────────────┘
               │
┌──────────────▼────────────────────┐
│            执行层                   │
│  Tool DAG 编排器 → Mock API 网关    │
│  10 个 Tool 分 4 层并行            │
└───────────────────────────────────┘
```

---

## Master Controller 三内核

### State Registry（7 状态 FSM）

| 状态 | 标识 | 可重入 | 说明 |
|------|------|--------|------|
| `IDLE` | `idle` | 否 | 初始待命 |
| `DRAFTING` | `drafting` | 否 | 意图解析与上下文加载中 |
| `PLANNING` | `planning` | 否 | 候选检索与规划求解中 |
| `CONFIRMING` | `confirming` | **是** | 等待用户确认，可循环重入 |
| `EXECUTING` | `executing` | 否 | Tool DAG 执行中 |
| `DONE` | `done` | 是 | 完成归档 |
| `FAILED` | `failed` | 否 | 全局失败 |

**状态转移矩阵**：

```
IDLE ──[create_request]──► DRAFTING
DRAFTING ──[intent_ready]──► PLANNING
PLANNING ──[plan_draft_ready]──► CONFIRMING
CONFIRMING ──[user_confirm_all]──► EXECUTING
CONFIRMING ──[user_objection / slot_replacement]──► CONFIRMING (重入)
CONFIRMING ──[fallback_triggered]──► CONFIRMING (重入)
EXECUTING ──[execution_success]──► DONE
EXECUTING ──[execution_partial_fail + fallback_available]──► CONFIRMING
EXECUTING ──[execution_partial_fail + fallback_exhausted]──► FAILED
任意状态 ──[timeout > 300s]──► FAILED
```

**关键特性**：CONFIRMING 是**可重入状态**，通过 Incremental Replanning 循环回自身，已确认 Slot 受 Checkpoint 保护不丢失。

### Policy Engine（策略裁决表）

| 当前状态 | 输入事件 | 裁决 | 激活 Agent | 下一状态 |
|---------|---------|------|-----------|---------|
| `CONFIRMING` | stakeholder objection | slot 未锁→替换；已锁且 w<0.8→拒绝；w≥0.8→解锁+重规划 | Consensus→Planning(增量) | `CONFIRMING` |
| `CONFIRMING` | stakeholder confirm | 更新 vote_bitmap；全员→推进；超时且 ≥60%→推进 | State Registry | `EXECUTING` |
| `EXECUTING` | tool_result: failed | 有 Shadow→Fallback；无→Saga 补偿→Confirming；连续2次→FAILED | Fallback | `CONFIRMING` 或 `FAILED` |
| `EXECUTING` | tool_result: timeout | 标记 degraded→缓存兜底；缓存不可用→视同 failed | Fallback | `CONFIRMING` 或 `FAILED` |
| `PLANNING` | llm_timeout | Phase 2 超时→降级为 Phase 1 best-effort 排序 | Planning(降级) | `CONFIRMING` |

**策略参数**：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `CONFIRM_TIMEOUT` | 300s | 确认最大等待时间 |
| `OVERRIDE_THRESHOLD` | 0.8 | 高权重 stakeholder 可解锁已确认 slot |
| `FALLBACK_MAX_RETRY` | 2 | 单节点失败最多重试次数 |
| `MAJORITY_RATIO` | 0.6 | 超时后自动通过比例 |
| `EXEC_TIMEOUT_PER_TOOL` | 3s | 单个 Tool 超时 |
| `EXEC_TIMEOUT_TOTAL` | 10s | 整个 DAG 超时 |

### Checkpoint Manager（Slot 粒度检查点）

以 Slot 为最小粒度的乐观检查点：

```yaml
Checkpoint:
  plan_id: UUID
  version: int
  state: StateEnum
  locked_slots:
    - slot_index: int
      confirmed_by: [stakeholder_id]
      confirmed_at: timestamp
      booking_id: str
  tentative_slots:
    - slot_index: int
      poi_id: UUID
      start_time: datetime
      end_time: datetime
      action: str
  shadow_candidates:
    - slot_index: int
      alternative_poi_id: UUID
      prechecked: bool
```

**写入策略**：用户确认→Redis+PostgreSQL；Planning 输出→Redis；Fallback 替换→Redis+PostgreSQL；DONE→归档

**读取策略**：增量重规划时先读 Checkpoint，locked_slots 作为前缀固定值，仅替换 tentative_slots 中的目标 Slot

---

## 9 Agent 契约

| # | Agent | 输入 | 输出 | LLM? | 超时 |
|---|-------|------|------|------|------|
| 1 | **Intent Parser** | `raw_query` | `IntentSchema` | LLM | 2s |
| 2 | **Context Loader** | `IntentSchema + user_id` | `EnrichedIntent` | 否 | 500ms |
| 3 | **Memory Manager** | `EnrichedIntent` | 记忆向量 + 历史模式 | 否 | — |
| 4 | **Retrieval Engine** | `EnrichedIntent + type_prefs` | `CandidatePool (≤50)` | 否 | 1s |
| 5 | **Planning Engine** | `CandidatePool + EnrichedIntent` | `PlanDraft` | Phase1否/Phase2LLM | 3.1s |
| 6 | **Consensus Resolver** | `{votes, stakeholder_weights}` | `ConsensusDecision` | 否 | 100ms |
| 7 | **Execution Engine** | `PlanDraft` | `ExecutionResult` | 否 | 10s |
| 8 | **Fallback Engine** | `FailedSlot + Checkpoint` | `RevisedPlan + diff_patch` | 否 | 2s |
| 9 | **Notify Engine** | `PlanDraft + ExecutionResult` | `ShareCard` | 否 | 500ms |

### Agent 1: Intent Parser（意图解析器）
- **输入**：`IntentInput: {raw_query, user_lat, user_lng, timestamp, session_id}`
- **输出**：`IntentSchema: {time_window, guest_count, budget, scene_type, type_prefs, mood_prefs, implicit_constraints, city, confidence}`
- **执行**：LLM 单次调用，超时 2s 降级为关键词匹配
- **失败**：confidence < 0.6 时触发 Policy Engine 追问补全分支

### Agent 2: Context Loader（上下文加载器）
- **输入**：`IntentSchema + user_id`
- **输出**：`EnrichedIntent: IntentSchema + profile_vector + family_profile + historical_rejections + preferred_pace`
- **执行**：PostgreSQL + pgvector 查询，超时 500ms
- **失败**：返回空 profile，Planning Engine 降级为通用规划

### Agent 3: Memory Manager（记忆管理器）
- **输入**：`EnrichedIntent`
- **输出**：记忆增强向量 + 历史规划模式匹配
- **职责**：pgvector 语义检索 + Redis 会话缓存 + Skill 文件匹配
- **远期**：记忆演化 → 策略模板化 → Skill 蒸馏（Phase 2）

### Agent 4: Retrieval Engine（检索引擎）
- **输入**：`EnrichedIntent + type_prefs`
- **输出**：`CandidatePool: {candidates: List[POI], total, query_id}`
- **执行**：内部 3 路 `asyncio.gather` 并行检索（活动/餐饮/额外）
- **超时**：1s，超时使用 Redis 缓存结果（TTL 1h）

### Agent 5: Planning Engine（规划引擎）
- **输入**：`CandidatePool + EnrichedIntent`
- **输出**：`PlanDraft: {plan_id, slots, total_cost, total_time, confidence, version}`
- **执行**：Phase 1 硬约束 CSP（纯代码 ≤50ms）+ Phase 2 软约束 LLM（≤3s）
- **降级**：Phase 2 超时 → Phase 1 TOP-N 简单排序（评分降序+距离升序加权）
- **Shadow**：Phase 1 同步预计算 Shadow Candidates 存入 Checkpoint

### Agent 6: Consensus Resolver（共识解析器）
- **输入**：`{plan_id, votes[], stakeholder_weights[]}`
- **输出**：`ConsensusDecision: {status: confirmed | revised, revised_constraints, diff_slots}`
- **执行**：加权投票 + 锁定覆盖检测 + 帕累托补偿计算（纯代码）
- **当前**：单用户模式 stub（auto_confirm=true）

### Agent 7: Execution Engine（执行引擎）
- **输入**：`PlanDraft + confirmed_slots`
- **输出**：`ExecutionResult: {success_map, failed_slots, booking_ids, layer_timings}`
- **执行**：Tool DAG 分层并行 + asyncio.gather per layer
- **超时**：单 Tool 3s / 总 DAG 10s，单 Tool 超时不阻塞同层
- **依赖感知**：上游 Tool 失败时下游依赖跳过（skipped_due_to_dep_failure）

### Agent 8: Fallback Engine（容错引擎）
- **输入**：`failed_slot + original_constraints + checkpoint`
- **输出**：`RevisedPlan: PlanDraft + diff_patch{added, removed, modified}`
- **执行**：先读 Shadow Candidate 缓存 → 未命中则局部重检索 → 涟漪重排
- **超时**：2s，超时返回 diff_patch=null → Policy Engine 路由至 Saga 补偿或 FAILED
- **递归**：涟漪重排触发下游营业时间冲突时，递归执行二次 Fallback

### Agent 9: Notify Engine（输出封装引擎）
- **输入**：`PlanDraft + ExecutionResult`
- **输出**：`ShareCard: {url, message, ics_event}`
- **执行**：Jinja2 模板渲染

---

## 执行层 Tool DAG

### Tool 注册表（10 个 Tool）

| Layer | Tool | 依赖 | 幂等 | 超时 | Mock 失败率 |
|-------|------|------|------|------|------------|
| L0 | `search_poi` | 无 | 是 | 1.5s | 0% |
| L0 | `get_user_profile` | 无 | 是 | 0.5s | 0% |
| L1 | `check_queue` | `search_poi` | 是 | 1s | 0% |
| L1 | `check_availability` | `search_poi` | 是 | 1s | 0% |
| L1 | `check_child_facility` | `search_poi` | 是 | 0.8s | 0% |
| L1 | `calculate_route` | `search_poi` | 是 | 0.8s | 0% |
| L2 | `book_table` | `check_queue, check_availability` | 否 | 2s | 20% |
| L2 | `book_ticket` | `check_availability` | 否 | 2s | 10% |
| L2 | `order` | `search_poi` | 否 | 1.5s | 5% |
| L3 | `notify` | `book_table, book_ticket, order` | 是 | 1s | 0% |

### 分层执行示例（家庭场景 3 slots）

| 层级 | Tool 调用 | 并行度 | 预计耗时 |
|------|----------|--------|---------|
| L0 | `search_poi`(绘本馆), `search_poi`(餐厅), `search_poi`(蛋糕店), `get_user_profile` | 4 | ~200ms |
| L1 | `check_queue`(餐厅), `check_availability`(绘本馆), `check_child_facility`(绘本馆), `calculate_route`(咖啡→绘本馆) | 4 | ~300ms |
| L2 | `book_table`(餐厅), `book_ticket`(绘本馆), `order`(蛋糕→餐厅) | 3 | ~500ms |
| L3 | `notify`(分享卡片) | 1 | ~100ms |

---

## 核心工程机制

### 影子规划（Shadow Planning）
主规划生成时，关键 Slot 并行生成 Shadow Candidate，预查可用性存入 Checkpoint。失败时直接激活，跳过重新检索。

### 涟漪重排（Ripple Rescheduling）
局部替换 Slot 后，向下游传播时间偏移，检查营业时间冲突，递归触发二次 Fallback。

### 增量共识（Incremental Consensus）
加权投票 + 锁定覆盖检测 + 帕累托补偿计算。当前单用户 stub（auto_confirm），多用户 Phase 2。

### 记忆演化与技能蒸馏（Memory Evolution）
历史规划经验 → 策略模板 → Skill 文件（Markdown）→ LLM 从生成变为微调。Phase 2 实现。

### 分层超时控制
- 单 Tool：3s，超时不阻塞同层其他 Tool
- 单层：5s（含并行聚合）
- 总 DAG：10s

### 轻量熔断
快速失败 + 缓存兜底。超时后尝试 stale cache（TTL 1h），不可用则标记失败。

---

## 分层超时示例

```
per_tool_ms: 3000          # 单个 Tool
per_layer_ms: 5000         # 单层（含并行聚合）
total_dag_ms: 10000        # 整个 DAG
fallback_to_cache_ms: 500  # 超时后缓存兜底最长时间
```

---

## SSE 事件流（10 种）

```
intent → retrieval → planning → planning_done
→ execution → execution_done
→ [fallback → confirmation]
→ notify → done
```

| 事件 | 状态 | 含义 |
|------|------|------|
| `intent` | DRAFTING | Intent Parser 完成约束提取 |
| `retrieval` | DRAFTING→PLANNING | Retrieval Engine 返回候选池 |
| `planning` | PLANNING | Planning Engine 执行中 |
| `planning_done` | PLANNING→CONFIRMING | 规划草案就绪 |
| `execution` | CONFIRMING→EXECUTING | Tool DAG 执行中 |
| `execution_done` | EXECUTING | 全部 Tool 完成 |
| `fallback` | EXECUTING→CONFIRMING | Fallback Engine 局部替换 |
| `consensus` | CONFIRMING | Consensus Resolver 投票更新 |
| `notify` | DONE | Notify Engine 分享链路 |
| `done` | DONE | 全流程结束 |

---

## 执行层与编排层边界

| 方向 | 编排层→执行层 | 执行层→编排层 |
|------|-------------|-------------|
| **数据** | `PlanDraft` | `ExecutionResult`(含 failed_slots + Shadow Candidate) |
| **触发** | Policy Engine 状态→EXECUTING | Tool DAG 完成或超时 |
| **异常** | 不干预执行过程 | failed_slots 非空→Fallback Engine 接管 |
| **超时** | 设置 total_dag_ms=10000 | 超时返回 partial_success 或 full_failure |

**关键约束**：执行层**无状态**（Stateless），所有状态维护在编排层 State Registry。

---

## 与外部 LLM/Agent 框架的集成边界

```
SnapTrip Backend (FastAPI)
  ├─ 内部 Agent：Master Controller 内存调度，非网络调用
  ├─ LLM 调用：仅 Intent Parser + Planning Phase 2 → OpenRouter → DeepSeek-V3 / Claude
  ├─ Tool 调用：httpx → Mock API (8001)
  ├─ 记忆读写：Memory Manager → Redis / PostgreSQL / FileSystem
  └─ Hermes Skill：本地文件系统替代 (agents/skills/*.md)，ACP 协议预留
```
