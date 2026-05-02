# 04 —— 异常处理与自愈机制

## 异常分类

我们将系统中可能出现的异常分为三层：

| 层级 | 异常类型 | 来源 | 示例 |
|------|---------|------|------|
| L1 参数层 | 用户输入异常 | 前端/网关校验 | 时间范围为空、人数为负数 |
| L2 业务层 | 规划执行异常 | Agent / Tool 调用 | 预订失败、LLM 超时、POI 为空 |
| L3 系统层 | 基础设施异常 | DB / Redis / Mock API | 数据库连接断开、Mock 服务宕机 |

## L1：参数层异常处理

由 FastAPI 的 Pydantic 校验自动拦截，返回统一错误响应：

```json
{
  "code": 422,
  "message": "validation_error",
  "data": {
    "errors": [
      {"field": "start_time", "message": "start_time must be in the future"},
      {"field": "guest_count", "message": "guest_count must be >= 1"}
    ]
  }
}
```

## L2：业务层异常处理

### 异常包装

所有外部调用异常统一包装为业务异常：

```python
class SnapTripError(Exception):
    """业务异常基类"""
    def __init__(self, code: str, message: str, detail: dict = None):
        self.code = code
        self.message = message
        self.detail = detail or {}

class AgentTimeoutError(SnapTripError):
    pass

class ToolExecutionError(SnapTripError):
    pass

class PlanFailureError(SnapTripError):
    pass
```

### Agent 层级异常恢复

```
Agent Hub 状态机
  │
  ├─ Intent Agent  ──失败──► 返回错误 + 引导用户重新输入
  │
  ├─ Context Agent ──失败──► 使用默认画像继续（user_prefs={}）
  │
  ├─ Retrieval Agent ──失败──► 使用缓存 POI 结果（TTL 5min）
  │
  ├─ Planning Agent ──失败──► 降级：跳过 LLM 排序，使用简单规则排序
  │
  ├─ Execution Agent ──失败──► Fallback Agent（局部重规划）
  │
  └─ Notify Agent ──失败──► 不影响主流程，异步重试
```

### Fallback Agent 策略

当 Execution Agent 中某个预订失败时，Fallback Agent 执行以下步骤：

1. **识别失败节点**：定位 DAG 中哪个 Tool 调用返回了失败
2. **标记受影响的 slots**：该 POI 的 slot + 受依赖影响的后续 slot
3. **重新检索**：以相同条件（type, budget, distance）重新搜索替代 POI
4. **局部重排**：将新 POI 替换到 time 位置，重新调用 Planning Agent（仅 LLM 排序）
5. **差异提示**：向前端推送 `fallback` SSE 事件，包含变化前后对比

```python
class FallbackAction(BaseModel):
    original_poi: str
    replacement_poi: str
    reason: str                    # "预订失败：该时段已满"
    affected_slots: List[int]      # 受影响的 slot 索引
    new_plan: PlanResponse         # 更新后的计划
```

### Mock 异常模拟

Mock 服务以 20% 概率返回预订失败，用于触发 Fallback：

```python
@app.post("/mock/booking/table")
async def book_table(request: BookingRequest):
    if random.random() < 0.2:
        return {
            "success": False,
            "reason": "该时段已满",
            "suggestion": "15:30 或 17:00 有空位"
        }
    return {"success": True, "booking_id": str(uuid4())}
```

## L3：系统层异常处理

### 数据库连接

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except SQLAlchemyError as e:
        logger.error("db_error", error=str(e))
        raise HTTPException(status_code=503, detail="database_unavailable")
```

### Redis 连接

```python
async def get_redis() -> Redis:
    try:
        return await redis_pool.acquire()
    except ConnectionError:
        logger.warning("redis_unavailable", fallback="in_memory_cache")
        return InMemoryCache()  # 降级到内存缓存
```

### 熔断器模式

对 Mock API 调用使用熔断器：

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_count = 0
        self.state = "closed"  # closed | open | half_open

    async def call(self, func, *args, **kwargs):
        if self.state == "open":
            raise ServiceUnavailableError("circuit_breaker_open")

        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            return result
        except Exception:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise
```

## SSE 事件格式

异常通过 SSE 实时推送到前端：

| 事件名 | 含义 | 数据字段 |
|--------|------|----------|
| `intent` | 意图解析完成 | `{"intent_id": "...", "constraints": {...}}` |
| `retrieval` | POI 检索完成 | `{"query": "...", "count": 25}` |
| `planning` | 规划排序中 | `{"status": "sorting", "candidates": 10}` |
| `planning_done` | 规划完成 | `{"plan": PlanResponse}` |
| `execution` | 预订执行 | `{"tool": "book_table", "status": "running"}` |
| `execution_done` | 全部预订完成 | `{"success_count": 3, "failed_count": 0}` |
| `fallback` | 触发降级 | `FallbackAction` |
| `notify` | 分享卡片生成 | `{"card_url": "https://..."}` |
| `error` | 异常 | `{"code": 500, "message": "agent_timeout"}` |
| `done` | 流程结束 | `{"plan_id": "..."}` |

## 错误码规范

| 状态码 | 场景 |
|--------|------|
| 400 | 业务参数错误 |
| 422 | Pydantic 校验失败 |
| 500 | 系统内部错误 |
| 503 | Agent 调用超时 |
| 504 | Mock API 熔断开启 |
