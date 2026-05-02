# Plan API

## POST /api/v1/plan/create

创建新的活动计划。

### Request

```json
{
  "user_input": "今天下午想和朋友去朝阳区逛逛，顺便吃个饭，预算300",
  "user_id": "u_001",
  "lat": 39.9219,
  "lng": 116.4435,
  "options": {
    "start_time": "2026-05-02T14:00:00",
    "end_time": "2026-05-02T18:00:00",
    "radius_km": 5.0
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_input` | string | 是 | 用户的自然语言输入 |
| `user_id` | string | 是 | 用户标识 |
| `lat` | float | 是 | 当前位置纬度 |
| `lng` | float | 是 | 当前位置经度 |
| `options.start_time` | datetime | 否 | 计划开始时间，默认当前时间后 1 小时 |
| `options.end_time` | datetime | 否 | 计划结束时间，默认 4 小时后 |
| `options.radius_km` | float | 否 | 搜索半径，默认 5.0 |

### Response (HTTP 202 Accepted)

接口立即返回 202，后续通过 SSE `/api/v1/plan/{plan_id}/stream` 获取实时结果：

```json
{
  "code": 0,
  "message": "accepted",
  "data": {
    "plan_id": "b3f1a2c4-..."
  }
}
```

### SSE Stream

建立 SSE 连接后，依次收到以下事件：

```
event: intent
data: {"intent_id": "i_001", "constraints": {"guest_count": 2, "budget": 300, "type_prefs": ["restaurant", "cafe"]}}

event: retrieval
data: {"query_id": "q_001", "poi_count": 25, "types": {"restaurant": 12, "cafe": 8, "activity": 5}}

event: planning
data: {"phase": "hard_filter", "candidates": 10}

event: planning
data: {"phase": "soft_sort", "status": "calling_llm"}

event: planning_done
data: {"plan": {"slots": [...], "total_cost": 266, "total_time": 180}}

event: execution
data: {"tool": "check_queue", "status": "running", "poi_name": "猫咪咖啡馆"}

event: execution
data: {"tool": "check_queue", "status": "success", "queue_minutes": 15}

event: execution
data: {"tool": "book_table", "status": "success", "booking_id": "bk_001"}

event: execution_done
data: {"success_count": 3, "failed_count": 0}

event: notify
data: {"card_url": "https://snaptrip.cn/cards/plan_b3f1a2c4"}

event: done
data: {"plan_id": "b3f1a2c4-..."}
```

---

## GET /api/v1/plan/{plan_id}

获取已完成的计划详情。

### Response

注意：`plans` 与 `plan_slots` 为 1:N 关系，响应中嵌套展示。

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "plan_id": "b3f1a2c4-...",
    "user_id": "u_001",
    "query_text": "今天下午想和朋友去朝阳区逛逛",
    "status": "confirmed",
    "total_cost": 266,
    "created_at": "2026-05-02T13:05:00Z",
    "slots": [
      {
        "slot_id": "s1",
        "sequence": 0,
        "time_range": ["2026-05-02T14:00:00", "2026-05-02T15:00:00"],
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
        "booking_status": "confirmed",
        "booking_id": "bk_001",
        "estimated_cost": 48
      }
    ]
  }
}
```

---

## GET /api/v1/plan/{plan_id}/status

获取计划的实时状态（适合轮询）。

### Response

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "plan_id": "b3f1a2c4-...",
    "status": "executing",
    "progress": 0.6,
    "current_step": "book_table",
    "created_at": "2026-05-02T13:05:00Z"
  }
}
```

## 状态码说明

| 状态 | 含义 |
|------|------|
| `drafting` | 意图解析中 |
| `planning` | 规划生成中 |
| `executing` | 预订执行中 |
| `confirmed` | 全部预订成功 |
| `partial_confirmed` | 部分成功，含失败项 |
| `failed` | 规划失败 |
