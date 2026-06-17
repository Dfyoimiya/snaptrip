# SnapTrip Development Summary

> **Version**: 2.0 | **Date**: 2026-06-17
>
> SnapTrip 是一个 AI 驱动的全栈电商平台，集成混合搜索、个性化推荐与多智能体客服系统。

---

## 模块清单

### 后端数据模型 (`backend/app/models/`)

#### 商品域 (PMS — Product Management System)

| 表名 | 模型 | 说明 |
|------|------|------|
| `pms_products` | `PmsProduct` | 商品 SPU (名称/副标题/品牌/分类/价格/库存/图片/上下架/新品/推荐/审核) |
| `pms_skus` | `PmsSku` | 商品 SKU (规格JSON/价格/库存/锁定库存/图片) |
| `pms_brands` | `PmsBrand` | 品牌 (名称/首字母/Logo/工厂状态/显示状态) |
| `pms_categories` | `PmsCategory` | 分类树 (父级自引用/层级0-2/导航状态/图标) |
| `pms_product_attributes` | `PmsProductAttribute` | EAV 属性定义 (规格/参数类型/输入类型/筛选/搜索) |
| `pms_product_attribute_values` | `PmsProductAttributeValue` | 属性值 (商品-属性-值 关联) |
| `pms_product_embeddings` | `PmsProductEmbedding` | 语义嵌入向量 Vector(384), UNIQUE product_id |
| `pms_product_cf_vectors` | `PmsProductCFVector` | 协同过滤向量 Vector(64), UNIQUE product_id |

#### 订单域 (OMS — Order Management System)

| 表名 | 模型 | 说明 |
|------|------|------|
| `oms_orders` | `OmsOrder` | 订单 (订单号/金额/支付/快递/地址快照/状态0-7) |
| `oms_order_items` | `OmsOrderItem` | 订单明细 (商品/SKU/规格/价格/数量) |
| `oms_order_operate_logs` | `OmsOrderOperateLog` | 操作日志 (操作人/前后状态/备注) |
| `oms_cart_items` | `OmsCartItem` | 购物车 (用户/商品/SKU/数量/勾选) |
| `oms_return_applies` | `OmsReturnApply` | 退货申请 (状态:待处理/已退货/已拒绝/已退款) |
| `oms_return_reasons` | `OmsReturnReason` | 退货原因字典 |
| `oms_order_settings` | `OmsOrderSetting` | 订单配置 (超时/确认收货时限) |
| `oms_support_tickets` | `OmsSupportTicket` | 客服工单 (类型/状态/优先级/SLA时限/坐席分配) |
| `cs_conversation_messages` | `CsConversationMessage` | 客服消息 (发送方/内容类型/元数据) |

#### 会员域 (UMS — User Management System)

| 表名 | 模型 | 说明 |
|------|------|------|
| `ums_member_addresses` | `UmsMemberAddress` | 收货地址 (省市区/默认标记) |
| `ums_member_favorites` | `UmsMemberFavorite` | 收藏 (用户+商品 唯一约束) |
| `ums_member_behaviors` | `UmsMemberBehavior` | 行为埋点 (view/search/add_cart/purchase/favorite) |
| `ums_member_search_logs` | `UmsMemberSearchLog` | 搜索日志 (关键词/筛选/结果数) |
| `cs_agent_status` | `CsAgentStatus` | 坐席状态 (在线/离线/忙碌/当前工单/技能) |
| `cs_session_summaries` | `CsSessionSummary` | 客服会话摘要 (意图/情感轨迹/工具调用) |

#### 促销域 (SMS — Sales Management System)

| 表名 | 模型 | 说明 |
|------|------|------|
| `sms_coupons` | `SmsCoupon` | 优惠券模板 (类型/使用类型/金额/门槛/数量/时间/每人限领) |
| `sms_coupon_histories` | `SmsCouponHistory` | 领券/用券记录 (使用状态:未用/已用/过期) |
| `sms_flash_promotions` | `SmsFlashPromotion` | 秒杀活动 (标题/日期/状态) |
| `sms_flash_sessions` | `SmsFlashPromotionSession` | 秒杀场次 (活动/时间/状态) |
| `sms_flash_promotion_products` | `SmsFlashPromotionProduct` | 秒杀商品 (场次/商品/秒杀价/库存/限购) |

#### 内容域 (CMS — Content Management System)

| 表名 | 模型 | 说明 |
|------|------|------|
| `cms_banners` | `CmsBanner` | 首页 Banner (标题/图片/链接/排序/时间) |
| `cms_subjects` | `CmsSubject` | 专题 (标题/摘要/图片/内容/推荐状态) |
| `cms_helps` | `CmsHelp` | 帮助中心 (标题/内容/分类/状态) |
| `cs_notifications` | `CsNotification` | 客服通知 (类型/标题/内容/已读状态) |

#### RBAC 与基础设施

| 表名 | 模型 | 说明 |
|------|------|------|
| `ums_roles` | `Role` | 角色 (名称唯一/描述/状态/排序) |
| `ums_permissions` | `Permission` | 权限 (名称/资源/方法/状态) |
| `ums_role_permissions` | `RolePermission` | 角色-权限关联 |
| `ums_user_roles` | `UserRole` | 用户-角色关联 |
| `ums_menus` | `Menu` | 菜单树 (父级/标题/图标/隐藏/层级) |
| `ums_resource_categories` | `ResourceCategory` | 资源分类 |
| `ums_resources` | `Resource` | 资源 (分类/名称/URL) |
| `ums_role_menus` | `RoleMenu` | 角色-菜单关联 |
| `ums_role_resources` | `RoleResource` | 角色-资源关联 |
| `plan_runs` | — | Agent 计划执行记录 |
| `plan_run_events` | — | Agent 运行时事件日志 |
| `llm_usage_logs` | `LLMUsageLog` | LLM 调用用量与成本 |

---

### API 路由

#### 管理后台路由 (18 个模块)

| 路由文件 | 前缀 | 核心端点 |
|---------|------|---------|
| `product.py` | `/admin/products` | CRUD + 上下架/新品/推荐/审核/SKU库存/ES同步 |
| `brand.py` | `/admin/brands` | CRUD + 分页 + 全部启用列表 + 状态 |
| `category.py` | `/admin/categories` | CRUD + 树形 + 分页 + 状态/排序 |
| `attribute.py` | `/admin/product-attributes` | CRUD + 属性分类管理 |
| `order.py` | `/admin/orders` | 列表/详情 + 关闭/发货/改地址/改价格/备注/删除 |
| `coupon.py` | `/admin/coupons` | 模板CRUD + 领取/使用记录 |
| `member.py` | `/admin/members` | 列表/详情 + 启用/封禁 |
| `dashboard.py` | `/admin/dashboard` | 仪表盘聚合: 今日订单/营收/热销TOP5/7天趋势 |
| `flash.py` | `/admin/flash-promotions` | 活动-场次-商品 三层管理 |
| `cms.py` | `/admin/cms` | Banner/专题/帮助CRUD + 统计报表 |
| `customer_service.py` | `/admin/cs` | 工单管理/聊天SSE/坐席状态/通知/客服统计 |
| `menu.py` | `/menu` | 菜单树形CRUD |
| `resource.py` | `/resourceCategory` + `/resource` | 资源分类CRUD + 资源CRUD |
| `role.py` | `/role` | 角色CRUD + 菜单/资源分配 |
| `ums_admin.py` | `/admin` | 管理员CRUD + 角色分配 |
| `order_setting.py` | `/admin/order-settings` | 订单全局配置 |
| `return_apply.py` | `/admin/return-applies` | 退货申请列表/详情/状态更新/批量删除 |
| `return_reason.py` | `/admin/return-reasons` | 退货原因CRUD + 批量状态 |

#### 前台商城路由 (15 个模块)

| 路由文件 | 前缀 | 核心端点 |
|---------|------|---------|
| `product.py` | `/portal/products` | 混合搜索 + 详情 + 分类浏览 |
| `cart.py` | `/portal/cart` | 购物车CRUD + 幂等加购 + 勾选/清空 |
| `order.py` | `/portal/orders` | 下单 + 列表/详情 + 取消/支付/确认收货 |
| `member.py` | `/portal/member` | 个人信息 + 地址CRUD + 收藏管理 |
| `coupon.py` | `/portal/coupons` | 可领券列表 + 领券 + 我的券 |
| `home.py` | `/portal/home` | 首页聚合: Banner+新品+推荐+专题 |
| `homefeed.py` | `/portal/home/feed` | 5数据源并发: 猜你喜欢/热门/新品/历史/搜索发现 |
| `brand.py` | `/portal/brands` | 品牌列表/详情 |
| `category.py` | `/portal/categories` | 分类列表/树 |
| `behavior.py` | `/portal/behaviors` | 用户行为埋点 (双写PG+Redis) |
| `notice.py` | `/portal/notices` | 公告/帮助列表/详情 |
| `recommendation.py` | `/portal/recommendations` | 个性化推荐 (4-Agent流水线) |
| `search_suggest.py` | `/portal/search` | 搜索建议 (autocomplete+trending+AI) |
| `customer_service.py` | `/portal/cs` | 智能客服: 退货/退款/物流/投诉/工单/补偿/聊天SSE |

---

### Service 层 (25+ 服务)

#### 核心业务服务

| 服务 | 核心职责 |
|------|---------|
| `ProductService` | 商品 SPU+SKU+属性值一体化管理，ES 索引同步 |
| `OrderService` | 订单全生命周期: 乐观锁库存扣减、状态机校验、金额计算、操作日志、仪表盘统计 |
| `CartService` | 购物车 CRUD，幂等加购 (同 SKU 累加数量) |
| `MemberService` | 会员地址管理、收藏管理、管理员查询/封禁 |
| `BrandService` | 品牌 CRUD + 多条件筛选 |
| `CategoryService` | 分类 CRUD + 递归树形结构 |
| `CouponService` | 优惠券模板 CRUD、乐观锁领券、幂等防重复 |
| `FlashService` | 秒杀活动-场次-商品三层管理 |
| `CmsService` | Banner/专题/帮助 CRUD |
| `StatsService` | 仪表盘统计报表 + 首页聚合数据 |

#### 搜索与推荐服务

| 服务 | 核心职责 |
|------|---------|
| `HybridSearchService` | ES BM25 + pgvector + CF 三路召回融合，意图分类确定权重，分数归一化，个性化 boost，多级降级 |
| `VectorSearchService` | pgvector 余弦相似度查询 (384d语义向量) |
| `CollaborativeFilteringService` | ALS 隐因子模型训练/推理 (64d)，行为加权 |
| `TrendingService` | Redis 时间桶 ZSET 实时 trending，Reddit Hot 改编算法 |
| `AutocompleteService` | Redis 前缀索引自动补全，离线批量 + 在线增量 |
| `SuggestionService` | 搜索建议编排: autocomplete + trending + AI 并发聚合 |
| `QueryExpansionService` | LLM 离线查询扩展 + Redis 缓存 |
| `SearchPersonalizationService` | 偏好boost: 类目+0.15~+0.20，价格+0.10 |

#### 基础设施服务

| 服务 | 核心职责 |
|------|---------|
| `MemoryService` | Redis 封装: 会话状态、行为记录、滑动窗口、缓存、用户画像 |
| `FeatureService` | 多数据源用户特征聚合 (Redis实时窗口 + PG收藏/订单RFM) |
| `ABTestEngine` | MD5 一致性哈希分桶 + Thompson Sampling 动态分配 |
| `MetricsCollector` | Agent 调用指标 + 业务事件追踪 |

---

### 异步任务 (`backend/app/tasks/`)

| 任务 | 文件 | 频率 | 功能 |
|------|------|------|------|
| `auto_cancel_expired_orders` | `order_tasks.py` | 每分钟 | 取消超时未支付订单，释放锁定库存 |
| `auto_confirm_receipt_orders` | `order_tasks.py` | 每天凌晨2点 | 自动确认收货 (发货超15天) |
| `sync_all_products_to_es` | `index_tasks.py` | 定时/手动 | 全量同步 ES 索引 |
| `sync_product_to_es_by_id` | `index_tasks.py` | 按需 | 单商品增量 ES 同步 |
| `train_cf_model` | `cf_tasks.py` | 每6小时 | ALS 训练协同过滤模型 (64d) |
| `check_sla_deadlines` | `sla_tasks.py` | 每60秒 | 客服 SLA 监控 (critical 15min/urgent 1h/normal 4h) |
| `cleanup_stale_agents` | `sla_tasks.py` | 每120秒 | 清理超5分钟无心跳的离线坐席 |

---

### AI Agent 系统 (`agent/src/agent/`)

#### 图编排与运行时

| 文件 | 说明 |
|------|------|
| `graph.py` | LangGraph StateGraph 主图定义 (Supervisor + 6 Specialist + tools + synthesize + compliance) |
| `runtime.py` | `AgentRuntime` DI 容器 (llm_adapter/event_bus/harness/session_ctx) |
| `tool_node.py` | 工具调度节点 (标准/Saga/HITL 三类分发) |
| `utils.py` | 共享工具函数 (消息格式转换/JSON解析/JWT透传) |

#### 6 个 Specialist 节点

| 节点 | 文件 | 工具数 | 职责 |
|------|------|--------|------|
| `ProductDiscoveryNode` | `nodes/product_discovery.py` | 2 | 商品搜索/发现 (search_products, get_product_detail) |
| `OrderAssistantNode` | `nodes/order_assistant.py` | 2 | 订单查询/取消 (query_order, cancel_order) |
| `CustomerServiceNode` | `nodes/customer_service.py` | 14 | 全场景售后 + 情感感知 |
| `MarketingEngineNode` | `nodes/marketing_engine.py` | 2 | 优惠券/促销查询 |
| `KnowledgeQANode` | `nodes/knowledge_qa.py` | 1 | 知识库问答 |
| `AdminAnalystNode` | `nodes/admin_analyst.py` | 6 | B端数据分析 (只读) |

#### 辅助节点

| 节点 | 文件 | 职责 |
|------|------|------|
| `supervisor_node` | `nodes/supervisor.py` | 意图分类 (LLM优先 + 关键词降级, 8种意图) |
| `synthesize_node` | `nodes/synthesize.py` | 最终回复合成 |
| `compliance_node` | `nodes/compliance.py` | 合规检查 (PII + 禁用词, 非阻断式) |
| `emotion.py` | `nodes/emotion.py` | 情感检测 (5种情感 + 多轮轨迹) |

#### 推荐子图 (`nodes/recommendation/`)

| 组件 | 文件 | 职责 |
|------|------|------|
| `build_recommendation_graph` | `graph.py` | 推荐 LangGraph 子图构建 |
| `SearchIntentAgent` | `search_intent.py` | 搜索意图分类 (transactional/navigational/informational) |
| `UserProfileAgent` | `user_profile.py` | 用户画像分析 (分群/类目偏好/RFM) |
| `ProductRecAgent` | `product_rec.py` | 两阶段推荐: 召回 (ES+CF+热门) + LLM重排 |
| `InventoryAgent` | `inventory.py` | 库存检查 (纯规则, 无LLM) |
| `MarketingCopyAgent` | `marketing_copy.py` | 个性化文案生成 + 广告法合规过滤 |

#### 工具系统

| 组件 | 文件 | 说明 |
|------|------|------|
| `ToolHarness` | `tools/harness/harness.py` | 工具执行唯一入口，Hook 链编排 |
| `ToolRegistry` | `tools/registry/registry.py` | 线程安全注册表，支持热重载 |
| `SessionContext` | `tools/harness/context.py` | 会话级上下文 |
| `SagaCoordinator` | `tools/transaction/saga.py` | Saga 三阶段协调器 |
| `CompensationRegistry` | `tools/transaction/compensation.py` | LIFO 补偿栈 |
| `AuditStore` | `tools/tracing/audit_log.py` | SHA-256 防篡改审计链 |

#### 20 个工具实现

**C 端基础 (6 个)**:

| 工具 | 文件 | 读写 |
|------|------|------|
| `search_products` | `implementations/search_products.py` | 读 |
| `get_product_detail` | `implementations/get_product_detail.py` | 读 |
| `query_order` | `implementations/query_order.py` | 读 |
| `cancel_order` | `implementations/cancel_order.py` | 写 (Saga) |
| `get_coupons` | `implementations/get_coupons.py` | 读 |
| `search_knowledge` | `implementations/search_knowledge.py` | 读 |

**C 端客服 (8 个)**:

| 工具 | 文件 | 读写 |
|------|------|------|
| `check_return_eligibility` | `implementations/check_return_eligibility.py` | 读 |
| `submit_return_request` | `implementations/submit_return_request.py` | 写 |
| `query_refund_status` | `implementations/query_refund_status.py` | 读 |
| `check_logistics` | `implementations/check_logistics.py` | 读 |
| `validate_order_complaint` | `implementations/validate_order_complaint.py` | 读 |
| `create_support_ticket` | `implementations/create_support_ticket.py` | 写 |
| `issue_compensation_coupon` | `implementations/issue_compensation_coupon.py` | 写 |
| `save_session_summary` | `implementations/save_session_summary.py` | 写 |

**B 端管理 (6 个, 全部只读)**:

| 工具 | 文件 |
|------|------|
| `get_sales_report` | `implementations/admin/get_sales_report.py` |
| `get_low_stock_alert` | `implementations/admin/get_low_stock_alert.py` |
| `get_order_trends` | `implementations/admin/get_order_trends.py` |
| `get_member_insights` | `implementations/admin/get_member_insights.py` |
| `generate_product_desc` | `implementations/admin/generate_product_desc.py` |
| `analyze_coupon_effect` | `implementations/admin/analyze_coupon_effect.py` |

---

## 统计

| 指标 | 数量 |
|------|------|
| **后端 API 路由文件** | 33 (18 admin + 15 portal) |
| **后端 Service 文件** | 25+ |
| **数据库表** | 40+ (6 大域: PMS/OMS/UMS/SMS/CMS/CS) |
| **Agent Specialist 节点** | 6 |
| **Agent 推荐子图节点** | 5 |
| **Agent 工具实现** | 20 (14 C端 + 6 B端) |
| **Celery 任务类型** | 7 (订单/索引/CF/SLA) |
| **LLM 模型** | 4 (DeepSeek V4 Pro/Flash + Kimi K2.6/K2.5) |
| **Docker 服务** | 8 |
| **Monorepo 包** | 4 (backend/agent/shared/contracts) |
