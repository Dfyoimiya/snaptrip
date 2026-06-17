# 03 — 搜索与推荐系统

> **Updated**: 2026-06-17 | **Project**: SnapTrip E-Commerce Marketplace
>
> SnapTrip 搜索系统采用三路混合召回 + 个性化重排架构，推荐系统基于 4-Agent
> LangGraph 流水线实现。覆盖从用户输入到最终排名的全链路。

---

## 搜索架构总览

```
用户输入 "蓝牙耳机"
       │
       ▼
┌──────────────────────────────────────┐
│         HybridSearchService          │
│                                      │
│  1. 意图分类 (SearchIntentAgent)      │
│     transactional/navigational/      │
│     informational → 融合权重         │
│                                      │
│  2. 并发三路召回:                     │
│     ┌──────────┬──────────┬────────┐ │
│     │ ES BM25  │ pgvector │  CF    │ │
│     │ 关键词   │ 语义向量 │ 协同   │ │
│     │          │ (384d)   │ (64d)  │ │
│     └──────────┴──────────┴────────┘ │
│                                      │
│  3. 分数归一化 + 加权融合              │
│  4. 个性化 boost                     │
│  5. 去重 + 排序 → 分页返回            │
└──────────────────────────────────────┘
```

---

## 三路召回详解

### 1. ES BM25 — 关键词匹配

**文件**: `backend/app/search/client.py`

- **引擎**: Elasticsearch 8.15.3
- **索引**: 商品名称、描述、品牌、分类
- **能力**: 分词匹配、多字段加权、筛选器 (品牌/分类/价格/属性)
- **降级**: ES 不可用时自动降级到 DB ILIKE 搜索

```python
class ESSearchClient:
    async def search(keyword, filters, sort, page) → SearchResult
    async def index_product(product_id, doc)
    async def bulk_index_products(docs)
    async def health_check()  # green/yellow/red
```

### 2. pgvector 语义搜索 — 语义相似度

**文件**: `backend/app/services/vector_search_service.py`

- **维度**: 384 (HuggingFace 本地模型，替代早期 OpenAI 1536d)
- **算法**: 余弦相似度 `<=>` 操作符
- **查询方式**:
  - `search_similar_by_product(product_id)` — 相似商品推荐
  - `search_similar_by_favorites(user_id)` — 基于收藏的推荐
- **无 API 成本**: 本地模型离线推理

```sql
SELECT * FROM pms_product_embeddings
ORDER BY embedding <=> query_embedding
LIMIT 50;
```

### 3. CF 协同过滤 — 用户行为关联

**文件**: `backend/app/services/collaborative_filtering_service.py`

- **模型**: ALS (Alternating Least Squares) 隐因子模型
- **维度**: 64
- **行为加权**: view=1, add_cart=3, purchase=5
- **训练**: Celery 定时任务每 6 小时执行
- **存储**: item vectors 存 PG (`pms_product_cf_vectors`)，user vectors 存 Redis

```
User-Item 交互矩阵
  → ALS 矩阵分解
  → User Vector (64d) + Item Vector (64d)
  → 余弦相似度 → 推荐列表
```

---

## 融合与重排

### 分数归一化

三路召回分别返回不同量纲的分数，需要归一化：

```
ES BM25:      原始分数 [0, 20+]  → min-max → [0, 1]
pgvector:     余弦距离 [0, 2]    → 1 - d/2 → [0, 1]
CF:           余弦相似度 [-1, 1] → (s+1)/2 → [0, 1]
```

### 加权融合

```python
final_score = w_es * score_es + w_vec * score_vec + w_cf * score_cf

# 意图分类确定权重:
#   transactional (购买意图):  w_es=0.5, w_vec=0.2, w_cf=0.3
#   navigational (浏览意图):   w_es=0.3, w_vec=0.5, w_cf=0.2
#   informational (信息查询):  w_es=0.2, w_vec=0.6, w_cf=0.2
```

### 个性化 Boost

**文件**: `backend/app/services/search_personalization_service.py`

| 信号 | Boost | 条件 |
|------|-------|------|
| 类目偏好 | +0.15~0.20 | 用户该类目历史行为占比 > 30% |
| 价格匹配 | +0.10 | 商品价格在用户历史价格区间内 |
| 品牌偏好 | +0.05 | 用户该品牌有购买记录 |

### 多级降级

```
Level 1: ES + pgvector + CF (全量)
Level 2: ES + pgvector (CF 不可用)
Level 3: ES only (pgvector 不可用)
Level 4: DB ILIKE (ES 不可用)
```

---

## 搜索相关服务

### TrendingService — 热门检测

**文件**: `backend/app/services/trending_service.py`

- **存储**: Redis 时间桶 ZSET (`trending:product:{hour}`, `trending:search:{hour}`)
- **算法**: Reddit Hot 改编 — 综合热度 = 近期行为数 / (时间衰减系数 + 基准时间)
- **能力**:
  - `record_product_view(product_id)` — 写入时间桶
  - `get_trending_products(hours=24, limit=20)` — 热门商品
  - `get_hot_queries(hours=6, limit=10)` — 搜索热词

### AutocompleteService — 自动补全

**文件**: `backend/app/services/autocomplete_service.py`

- **存储**: Redis 前缀索引 (ZSET)
- **构建**: `build_index()` 离线批量 + `increment()` 在线增量
- **查询**: `suggest(prefix, limit=10)` — 前缀匹配 + 按热度排序

### SuggestionService — 搜索建议

**文件**: `backend/app/services/suggestion_service.py`

三区块并发聚合：

```
GET /portal/search/suggest?q=耳机
  ├── autocomplete → ["耳机支架", "耳机收纳盒", "耳机清洁套装"]
  ├── trending     → ["蓝牙耳机", "降噪耳机", "运动耳机"]
  └── AI suggest   → LLM 生成: ["适合通勤的降噪耳机", "200元以内高性价比"]
```

### QueryExpansionService — 查询扩展

**文件**: `backend/app/services/query_expansion_service.py`

- **方法**: LLM 离线生成同义词/关联词/上位词
- **缓存**: Redis 存储扩展结果
- **目标**: 提升头部查询的召回率

---

## 推荐系统

### 4-Agent 流水线

```
RecommendationRequest
       │
       ▼
┌─────────────────┐
│ Phase 1 (并行)   │
│ ├ UserProfile   │  用户画像分析
│ └ ProductRec    │  商品召回 (ES + CF + Hot)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Phase 2 (并行)   │
│ ├ ProductRec    │  LLM 重排 (基于用户画像)
│ └ Inventory     │  库存过滤 + 限购计算
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ filter          │  ranked ∩ available
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ MarketingCopy   │  个性化文案生成
└────────┬────────┘
         │
         ▼
   RecommendationResponse
```

### Agent 详解

#### UserProfileAgent
- **输入**: 用户行为数据 (浏览/搜索/购买/收藏)
- **输出**: `{segments, preferred_categories, rfm_score, realtime_tags}`
- **分群**: NEW_USER / ACTIVE / HIGH_VALUE / PRICE_SENSITIVE / CHURN_RISK
- **降级**: LLM 不可用时使用规则分群

#### ProductRecAgent
- **Phase 1 — 召回**: ES 语义搜索 → CF 协同过滤 → DB 热门兜底
- **Phase 2 — 重排**: LLM 基于用户画像排序，考虑多样性/新颖性
- **降级策略**: ES → CF → Hot → Mock

#### InventoryAgent
- **纯规则** (无 LLM 调用)
- 过滤下架/缺货商品
- 检查购买限制 (每人限购 N 件)
- 生成低库存预警

#### MarketingCopyAgent
- 5 种分群模板: NEW_USER / HIGH_VALUE / CHURN_RISK / PRICE_SENSITIVE / ACTIVE
- LLM 生成个性化推荐文案
- **合规过滤**: 广告法禁用词替换 (正则匹配)

---

## A/B 测试

**文件**: `backend/app/services/ab_test.py`

- **分桶**: MD5(`user_id + experiment_id`) % 100 → 0-99 桶号
- **分配**: Thompson Sampling 动态比例分配
- **分组**: Control / Treatment_A / Treatment_B ...
- **指标**: 点击率 (CTR)、转化率 (CVR)、GMV 提升

```
Experiment: "search_hybrid_weights_v2"
  Control (50%):  w_es=0.4, w_vec=0.3, w_cf=0.3
  Treatment (50%): w_es=0.3, w_vec=0.5, w_cf=0.2
```

---

## 行为追踪

**文件**: `backend/app/api/portal/behavior.py`

- **端点**: `POST /portal/behaviors` 批量上报
- **事件类型**: view / search / add_cart / purchase / favorite
- **双写**: PostgreSQL (持久化) + Redis 滑动窗口 (实时特征)
- **用途**: CF 训练数据源、用户画像、Trending 计算、个性化排序

---

## 数据流总结

```
用户行为
  ├── PostgreSQL: 持久化存储 (member_behaviors, member_search_logs)
  ├── Redis: 实时滑动窗口 (行为计数、trending、session)
  └── Celery: 每6小时 ALS CF 训练

搜索请求
  ├── Autocomplete: Redis 前缀索引
  ├── Trending: Redis 时间桶 ZSET
  ├── 混合搜索: ES + pgvector + CF 三路融合
  ├── 个性化: 用户偏好 boost
  └── A/B 测试: 分组实验

推荐请求
  ├── UserProfile: 用户特征聚合
  ├── ProductRec: 多路召回 + LLM 重排
  ├── Inventory: 库存过滤
  └── MarketingCopy: 个性化文案
```
