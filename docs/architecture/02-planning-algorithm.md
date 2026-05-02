# 02 —— 两阶段规划算法

## 设计动机

将规划分为两个阶段的目的：

- **Phase 1（硬约束过滤）**：确定性规则，不使用 LLM，保证结果可预测、低成本。解决"能不能去"的问题。
- **Phase 2（软约束排序）**：使用 LLM 对候选集进行语义理解和偏好匹配，解决"怎么安排更爽"的问题。

> 原则：LLM 只负责排序和组合，不负责可行性验证。

## Phase 1：硬约束过滤（非 LLM）

### 输入

```python
candidates: List[POI]              # Retrieval Agent 返回的候选池
constraints: PlanConstraints        # 从 Intent Agent 解析出的约束
```

`PlanConstraints` 结构：

```python
class PlanConstraints(BaseModel):
    lat: float              # 用户位置纬度
    lng: float              # 用户位置经度
    radius_km: float = 5.0  # 搜索半径
    start_time: datetime
    end_time: datetime
    budget: int             # 总预算（元）
    guest_count: int        # 人数
    type_prefs: List[str]   # ["restaurant", "activity"]
```

### 过滤规则

| 规则 | 条件 | 动作 |
|------|------|------|
| 地理半径 | POI 到用户距离 > `radius_km` | 排除 |
| 营业时间 | POI 营业时段不与 `[start_time, end_time]` 相交 | 排除 |
| 容量限制 | POI 容量 < `guest_count` | 排除 |
| 预算约束 | POI `avg_price * guest_count > budget * 0.6` | 降级（标记 need_check） |
| 类型匹配 | POI `type` 不在 `type_prefs` | 降级（排在候选集末尾） |

### 输出

```python
filtered: List[POI]  # <=10 个，按"完美匹配 > 预算降级 > 类型降级"排序
```

### 伪代码

```python
async def hard_filter(candidates, constraints):
    filtered = []
    for poi in candidates:
        dist = haversine((poi.lat, poi.lng), (constraints.lat, constraints.lng))
        if dist > constraints.radius_km:
            continue
        if not is_open_during(poi.business_hours, constraints.start_time, constraints.end_time):
            continue
        if poi.capacity and poi.capacity < constraints.guest_count:
            continue
        score = score_poi_match(poi, constraints)
        filtered.append((poi, score))

    filtered.sort(key=lambda x: -x[1])
    return [p for p, _ in filtered[:10]]
```

## Phase 2：软约束排序（LLM）

### Prompt 模板结构

使用 Jinja2 模板 (`backend/app/agents/prompts/planning.j2`)：

```jinja2
你是一个本地生活规划助手。请根据用户偏好和候选 POI 列表，生成一个下午的活动计划。

## 用户偏好
{{ user_preferences }}

## 时间窗口
{{ start_time }} ~ {{ end_time }}

## 候选 POI 列表
{% for poi in candidates %}
- {{ poi.name }} ({{ poi.type }}, 评分 {{ poi.rating }}, 人均 {{ poi.avg_price }}元)
  标签: {{ poi.mood_tags | join(', ') }}
  位置: {{ poi.distance }}km
{% endfor %}

## 生成要求
1. 严格按时间顺序排列，每个活动分配一个具体的开始时间
2. 考虑活动之间的移动时间（每公里 5 分钟）
3. 活动和用餐交替，避免连续 3 个以上同类型
4. 总费用不超过 {{ budget }} 元
5. 以 JSON 格式输出结果
```

### Schema 约束输出

LLM 必须返回符合以下 Pydantic Schema 的 JSON：

```python
# 预算约束修复
MAX_SINGLE_NODE_RATIO = 0.5  # 单节点不超过总预算 50%，保证至少 2 个节点
if poi.avg_price * guest_count > budget * MAX_SINGLE_NODE_RATIO:
    mark_downgrade("budget_high")

# 容量兜底
effective_capacity = poi.capacity or 999
if effective_capacity < guest_count:
    continue

# PlanSlot.time 修复
class PlanSlot(BaseModel):
    start_time: datetime  # 内部用 datetime
    # API 输出时序列化为 "14:00"
    
    @property
    def time(self) -> str:
        return self.start_time.strftime("%H:%M")

class PlanResponse(BaseModel):
    plan_id: UUID
    slots: List[PlanSlot]
    total_cost: int
    total_time: int         # 总耗时（分钟）
```

### 输出示例

```json
{
  "plan_id": "b3f1a...",
  "slots": [
    {
      "time": "14:00",
      "poi_id": "p1",
      "poi_name": "猫咪咖啡馆",
      "action": "arrive",
      "estimated_cost": 48,
      "confidence": 0.92
    },
    {
      "time": "15:00",
      "poi_id": "p10",
      "poi_name": "手工陶艺坊",
      "action": "book_ticket",
      "estimated_cost": 128,
      "confidence": 0.85
    },
    {
      "time": "16:30",
      "poi_id": "p25",
      "poi_name": "川味小馆",
      "action": "book_table",
      "estimated_cost": 90,
      "confidence": 0.78
    }
  ],
  "total_cost": 266,
  "total_time": 180
}
```

## 错误处理

| 场景 | 处理策略 |
|------|----------|
| LLM 返回格式错误 | 重试 2 次，仍失败则使用 best-effort 解析 |
| Phase 1 返回空结果 | 扩大 `radius_km` 到 10km 重试，仍为空则提示用户 |
| Phase 2 超时 (>5s) | 直接返回 Phase 1 的 TOP N 作为简单排序结果 |

## 性能指标

| 指标 | Phase 1 | Phase 2 | 合计 |
|------|---------|---------|------|
| 耗时 | <50ms | <3s | <3.1s |
| 调 LLM | 否 | 是（1 次） | 1 次 |
| 可确定性 | 100% | 受温度参数影响 | — |
