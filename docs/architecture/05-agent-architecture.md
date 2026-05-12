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
│  └─ 8 Agent 调度链                  │
│  Intent → Context → Retrieval →    │
│  Planning → Execution → Fallback   │
│  Consensus → Notify                │
└──────────────┬────────────────────┘
               │
┌──────────────▼────────────────────┐
│            执行层                   │
│  Tool DAG 编排器 → Mock API 网关    │
│  10 个 Tool 分 4 层并行            │
└───────────────────────────────────┘
```

---

## 状态机

```
IDLE → DRAFTING → PLANNING → CONFIRMING → EXECUTING → DONE
                                 ↑              │
                                 │    ┌─────────┘
                                 │    ▼
                                 └────┤ (Fallback)
                                      │
                                  FAILED
```

`CONFIRMING` 为可重入状态：
- 用户异议 → Incremental Replanning → 回到 CONFIRMING
- Fallback 完成 → 回到 CONFIRMING
- 全员确认 → 进入 EXECUTING

---

## 8 Agent 拓扑

| Agent | 输入 | 输出 | LLM? | 超时 |
|-------|------|------|------|------|
| Intent Parser | raw_query | IntentSchema | LLM | 2s |
| Context Loader | IntentSchema + user_id | EnrichedIntent | 否 | 500ms |
| Retrieval Engine | EnrichedIntent | CandidatePool(≤50) | 否 | 1s |
| Planning Engine | CandidatePool | PlanDraft | Phase1:否 Phase2:LLM | 3.1s |
| Execution Engine | PlanDraft | ExecutionResult | 否 | 10s |
| Fallback Engine | FailedSlot | RevisedPlan | 否 | 2s |
| Consensus Resolver | Votes | ConsensusDecision | 否 | 100ms |
| Notify Engine | PlanDraft | ShareCard | 否 | 500ms |

---

## Tool DAG 分层

| Layer | Tools | 并行度 |
|-------|-------|--------|
| L0 | search_poi, get_user_profile | 2+ |
| L1 | check_queue, check_availability, check_child_facility, calculate_route | 4 |
| L2 | book_table, book_ticket, order | 3 |
| L3 | notify | 1 |

---

## SSE 事件流

```
intent → retrieval → planning → planning_done
→ execution → execution_done
→ [fallback → confirmation]
→ notify → done
```

---

## 核心工程机制

### 影子规划
主规划生成时，关键 Slot 并行生成 Shadow Candidate，预查可用性存入 Redis。失败时直接激活，跳过重新检索。

### 涟漪重排
局部替换 Slot 后，向下游传播时间偏移，检查营业时间冲突，递归触发二次 Fallback。

### 增量共识（单用户 Stub）
Consensus Resolver 在单用户模式下直接返回 `auto_confirm=True`，多用户模式待 Phase 2 实现。

### 技能蒸馏（远期）
历史规划经验沉淀为可复用的 Skill 模板（Markdown），存储于 `agents/skills/`。同类请求优先加载模板，LLM 从生成变为微调。

---

## 与 LLM/Agent 框架的边界

- 内部 Agent：Master Controller 内存调度，非网络
- LLM 调用：仅 Intent Parser + Planning Phase 2
- Tool 调用：httpx → Mock API (8001)
- 记忆读写：MemoryManager 统一封装
- Hermes Skill：本地文件系统替代（`agents/skills/*.md`）
