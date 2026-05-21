# 计划降级（Fallback）

## 触发条件

- Execution Agent 预订失败（任一 Tool 返回 `success: false`）
- Mock API 返回 `"该时段已满"` 或类似失败信息
- Agent 超时或 Mock API 熔断器开启

## 执行步骤

1. 定位失败节点：解析 `ToolResult` 中的错误信息
2. 识别受影响的 slots：
   - 直接失败的 slot（当前 POI）
   - 下游依赖 slot（如后续就餐依赖于前一个活动）
3. 搜索替代 POI：
   - 使用相同的约束条件（type, distance, budget）
   - 调用 Retrieval Agent 重新搜索该区域
4. 局部重规划：
   - 用新 POI 替换失败 slot
   - 调整受影响 slot 的时间
   - 重新检查移动时间和营业时间
5. 前端通知：
   - SSE 推送 `fallback` 事件
   - 渲染「差异对比卡片」

## 示例

### 场景
用户计划：猫咪咖啡馆(14:00) → 手工陶艺坊(15:00) → 川味小馆(16:30)

预订结果：手工陶艺坊→成功 ✓，川味小馆→失败 ✗（"该时段已满"）

### Fallback 输出
```json
{
  "original_poi": "川味小馆",
  "replacement_poi": "云南小厨",
  "reason": "预订失败：该时段已满",
  "affected_slots": [2],
  "new_plan": {
    "slots": [
      {"time": "14:00", "poi_name": "猫咪咖啡馆", "action": "arrive"},
      {"time": "15:00", "poi_name": "手工陶艺坊", "action": "book_ticket"},
      {"time": "16:30", "poi_name": "云南小厨", "action": "book_table"}
    ]
  }
}
```

### SSE 推送
```
event: execution
data: {"tool": "book_table", "status": "failed", "poi_name": "川味小馆", "reason": "该时段已满"}

event: fallback
data: {"original_poi": "川味小馆", "replacement_poi": "云南小厨", "reason": "预订失败：该时段已满"}
```
