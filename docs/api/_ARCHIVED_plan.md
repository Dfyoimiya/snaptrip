# Plan API

> 最后验证: 2026-05-23 | 基于 `backend/marketplace/app/api/v1/plan.py` 实际代码

## POST /api/v1/plan/create

创建新的活动计划（Celery 异步派发）。

### Request

```json
{
  "user_input": "今天下午想和朋友去朝阳区逛逛，顺便吃个饭，预算300",
  "user_id": "u_001",
  "lat": 39.9219,
  "lng": 116.4435,
  "start_time": "2026-05-02T14:00:00",
  "end_time": "2026-05-02T18:00:00"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | string | 是 | 用户的自然语言输入 |
| `user_id` | string | 否 | 用户标识，默认 "default" |
| `lat` | float | 否 | 当前位置纬度，默认 39.9219（北京） |
| `lng` | float | 否 | 当前位置经度，默认 116.4435（北京） |
| `start_time` | datetime | 否 | 计划开始时间 |
| `end_time` | datetime | 否 | 计划结束时间 |

### Response (HTTP 202 Accepted)

接口立即返回 202，Celery 异步执行 LangGraph 图：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "plan_id": "b3f1a2c4",
    "status": "queued"
  }
}
```

---

## POST /api/v1/plan/{plan_id}/confirm

人机协同确认（Celery 异步恢复 LangGraph）。

### Request

```json
{
  "decision": "confirmed",
  "locked_slots": [0, 1],
  "rejected_slots": [],
  "instruction": "",
  "replace_only": false,
  "change_requests": []
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `decision` | string | 是 | 决策: "confirmed" / "rejected" / "partial_change" |
| `locked_slots` | int[] | 否 | 锁定的 slot index 列表 |
| `rejected_slots` | int[] | 否 | 拒绝的 slot index 列表 |
| `instruction` | string | 否 | 修改说明文本 |
| `replace_only` | bool | 否 | 是否仅替换（不重规划） |
| `change_requests` | dict[] | 否 | 结构化变更请求列表 |

### Response (HTTP 202 Accepted)

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "plan_id": "b3f1a2c4",
    "status": "accepted"
  }
}
```

### SSE Stream 示例

```
event: node_started
data: {"node_name": "intent_parser", "plan_id": "b3f1a2c4"}

event: node_succeeded
data: {"node_name": "intent_parser", "intent_id": "i_001", "constraints": {"guest_count": 2, "budget": 300}}

event: node_started
data: {"node_name": "retrieval_engine", "plan_id": "b3f1a2c4"}

event: node_succeeded
data: {"node_name": "retrieval_engine", "query_id": "q_001", "poi_count": 25}

event: node_started
data: {"node_name": "planning_engine", "plan_id": "b3f1a2c4"}

event: node_succeeded
data: {"node_name": "planning_engine", "plan": {"slots": [...], "total_cost": 266, "total_time_min": 180}}

event: interrupt_requested
data: {"node_name": "consensus_resolver", "plan_id": "b3f1a2c4", "draft": {...}}

event: interrupt_resumed
data: {"node_name": "consensus_resolver", "decision": "confirmed"}

event: tool_called
data: {"tool_name": "book_table", "slot_index": 0, "poi_name": "猫咪咖啡馆"}

event: tool_finished
data: {"tool_name": "book_table", "status": "success", "booking_id": "bk_001"}

event: plan_completed
data: {"plan_id": "b3f1a2c4", "status": "done"}
```

---

## GET /api/v1/plan/{plan_id}

获取计划详情（从 LangGraph checkpoint 读取）。

### Response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "plan_id": "b3f1a2c4",
    "query_text": "今天下午想和朋友去朝阳区逛逛",
    "status": "done",
    "total_cost": 266,
    "total_time_min": 180,
    "slots": [
      {
        "sequence": 0,
        "time_range": {"start": "2026-05-02T14:00:00", "end": "2026-05-02T15:00:00"},
        "poi": {
          "id": "p1",
          "name": "猫咪咖啡馆",
          "type": "cafe",
          "lat": 39.9220,
          "lng": 116.4440,
          "mood_tags": ["治愈", "安静"],
          "avg_price": 48,
          "rating": 4.7
        },
        "action": "arrive",
        "estimated_cost": 48
      }
    ],
    "share_card": null
  }
}
```

---

## GET /api/v1/plan/{plan_id}/status

查询 plan_run 执行状态（从 `plan_runs` 表读取）。

### Response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "plan_id": "b3f1a2c4",
    "status": "done",
    "graph_version": "3.0.0",
    "started_at": "2026-05-02T13:05:00Z",
    "completed_at": "2026-05-02T13:05:05Z"
  }
}
```

---

## GET /api/v1/plan/{plan_id}/stream

SSE 流式推送（从 `RuntimeEventStore` 读取事件）。

建立 SSE 连接后，前端依次收到事件。SSE 事件类型定义见 [`00-architecture-reference.md`](../architecture/00-architecture-reference.md#7-sse-事件类型)。

---

## 状态码说明

API 返回的 `status` 字段对应 `PlanStatus` 枚举（定义于 `snaptrip_shared/core/constants.py`）：

| 状态 | 含义 |
|------|------|
| `idle` | 初始状态 |
| `drafting` | 意图解析中 |
| `planning` | 规划生成中 |
| `confirming` | 等待用户确认（人机协同中断） |
| `executing` | 预订执行中 |
| `done` | 全部完成 |
| `failed` | 规划失败 |
