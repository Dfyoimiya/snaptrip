# 餐饮推荐

## 触发条件

- 用户提到吃饭、就餐、聚餐、餐厅、午饭、晚饭、下午茶、咖啡
- 意图解析结果显示 `type_prefs` 包含 `restaurant` 或 `cafe`
- Planning Agent 需要根据用户口味匹配候选餐厅

## 执行步骤

1. 从 Intent Agent 获取用户偏好标签（口味、菜系、预算、氛围）
2. 查询 POI 向量数据库，使用 `user.prefererence_vector` 做语义检索
3. 硬过滤：营业时间、距离、人均消费
4. 软排序：偏好匹配度 > 评分 > 距离
5. 返回 TOP 3 候选餐厅给 Planning Agent

## 示例

### 输入
> "想吃川菜，两个人，人均100左右，最好在朝阳大悦城附近"

### 输出
```json
{
  "candidates": [
    {
      "name": "眉州东坡",
      "type": "restaurant",
      "cuisine": "川菜",
      "avg_price": 95,
      "rating": 4.6,
      "distance_km": 0.8,
      "mood_tags": ["热闹", "家庭友好"]
    },
    {
      "name": "麻辣诱惑",
      "type": "restaurant",
      "cuisine": "川菜",
      "avg_price": 110,
      "rating": 4.4,
      "distance_km": 1.2,
      "mood_tags": ["热闹", "年轻化"]
    }
  ]
}
```
