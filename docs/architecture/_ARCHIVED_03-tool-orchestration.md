# 03 —— Tool 编排器（DAG + Saga）

## 设计动机

Execution Agent 需要同时调用多个外部 Mock API（查排队、订座、订票、下单），这些调用之间存在依赖关系。我们使用 **DAG + Saga** 模式来管理调用顺序和异常恢复。

## 策略分层

### 首选：Fallback（局部替换）
- 适用：单个 Tool 失败，且存在替代 POI
- 动作：保留已成功的 `book_table(A)` 和 `book_ticket(B)`，仅替换失败的 `book_table(C)` 为 `book_table(D)`
- 不触发任何 compensate

### 降级：Saga 补偿（部分回滚）
- 适用：Fallback 找不到替代，或用户点击「整体取消」
- 动作：仅回滚与失败节点同属一个「时间区块」的预订
  - 例：`book_table(C)` 失败 → 调用 `cancel_booking(C)`（若已预占）
  - 不取消：`book_table(A)`（已完成且独立）、`book_ticket(B)`（已完成且独立）

### 兜底：全局重置
- 适用：连续 2 个节点 Fallback 失败
- 动作：释放所有 held 状态预订，返回错误

## DAG 依赖图

### 依赖定义

Tool 之间的依赖关系用有向无环图（DAG）表示：

```python
TOOL_DAG = {
    # 查询层（无依赖，并行）
    "search_poi": [],
    "get_user_profile": [],
    
    # 校验层（依赖查询）
    "check_queue": ["search_poi"],
    "check_availability": ["search_poi"],
    "calculate_route": ["search_poi"],
    
    # 预订层（互相独立，可并行）
    "book_table": ["check_queue"],
    "book_ticket": ["check_availability"],
    "order": ["search_poi"],  # 下单独立，不依赖预订成功
    
    # 通知层（依赖所有预订完成）
    "notify": ["book_table", "book_ticket", "order"]
}
```

### 拓扑排序

```python
def topological_sort(dag: Dict[str, List[str]]) -> List[List[str]]:
    # 收集所有节点（包括依赖节点）
    all_nodes = set(dag.keys())
    for deps in dag.values():
        all_nodes.update(deps)
    
    # 为无 key 的依赖节点补充空依赖
    for node in all_nodes:
        if node not in dag:
            dag[node] = []
    
    remaining = set(all_nodes)
    while remaining:
        layer = {t for t in remaining if all(d not in remaining for d in dag[t])}
        layers.append(list(layer))
        remaining -= layer
    return layers

# 输出示例：
# [
#   ["search_poi", "ride_hailing"],       # Layer 0：无依赖，并行
#   ["check_queue", "check_availability"], # Layer 1：依赖 search_poi
#   ["book_table", "book_ticket"],         # Layer 2：依赖 check_*
#   ["order"]                              # Layer 3：依赖 book_*
# ]
```

### 并行执行

同层的 Tool 使用 `asyncio.gather` 并行调用：

```python
async def execute_layer(tools: List[str]) -> Dict[str, ToolResult]:
    tasks = [call_tool(tool) for tool in tools]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {tool: r for tool, r in zip(tools, results)}
```

## Saga 补偿模式

### 为什么不用分布式事务

预订场景不适合严格的 ACID 事务：
- 订座和订票是独立的 Mock 服务，不支持两阶段提交
- 全部回滚用户体验差（"前功尽弃"）
- 部分成功时，用户期望系统自动给出替代方案

### Saga 步骤定义

每个 Tool 需要实现：

```python
class Tool(BaseModel):
    name: str
    execute: Callable[..., Awaitable[ToolResult]]
    compensate: Callable[..., Awaitable[bool]]  # 返回是否成功补偿

# 示例
class BookTableTool(Tool):
    async def execute(self, poi_id, guest_count, time):
        return await mock_api.book_table(poi_id, guest_count, time)

    async def compensate(self, booking_id):
        return await mock_api.cancel_booking(booking_id)
```

### 执行流程

```
begin Saga
  ├─ Step 1: book_table(restaurant_A)  ──► Success ✓
  ├─ Step 2: book_ticket(activity_B)   ──► Success ✓
  ├─ Step 3: book_table(restaurant_C)  ──► Failed  ✗
  │
  ├─ Compensate Step 2: cancel_ticket(activity_B) ──► Success ✓
  ├─ Compensate Step 1: cancel_booking(restaurant_A) ──► Success ✓
  │
  └─ Fallback: 重新编排剩余 slots
end Saga
```

### 补偿策略

| 场景 | 补偿动作 |
|------|---------|
| 订座失败 | 取消该 slot，由 Fallback Agent 替换为其他餐厅 |
| 订票失败 | 取消已预订的该 slot 上下游，重排时间 |
| 下单失败 | 不取消预订（座位/票保留），仅提示用户手动下单 |
| 多步失败 | 执行全部补偿链，从后往前依次回滚 |

## 超时控制

```python
TOOL_TIMEOUT = 3       # 单个 Tool 超时（秒）
SAGA_TIMEOUT = 10      # 整体 Saga 超时（秒）

async def call_tool_with_timeout(tool: Tool, **kwargs) -> ToolResult:
    try:
        result = await asyncio.wait_for(tool.execute(**kwargs), timeout=TOOL_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("tool_timeout", tool=tool.name)
        return ToolResult(success=False, error="timeout")
    return result
```

## Tool 状态机

```
pending ──► running ──► success ──► committed
                │
                ├──► failed  ──► compensating ──► compensated
                │
                └──► timeout
```

## 日志规范

每个 Tool 调用必须记录结构化日志：

```python
logger.info("tool_start",   tool="book_table", poi_id="p25", saga_step=3)
logger.info("tool_success", tool="book_table", booking_id="b001", elapsed_ms=234)
logger.warning("tool_failed", tool="book_table", error="no_available_slot")
logger.info("compensate_start", step=2, tool="book_ticket")
```

## 监控指标

| 指标 | 含义 |
|------|------|
| `tool_call_duration_ms` | 单个 Tool 调用耗时 |
| `saga_total_duration_ms` | 整体 Saga 执行耗时 |
| `compensate_count` | 需要补偿的步数 |
| `fallback_rate` | 触发 Fallback Agent 的比例 |
