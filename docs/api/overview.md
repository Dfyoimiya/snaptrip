# API 总览

> 最后更新: 2026-06-17

SnapTrip 后端 API 分为两大域：**管理后台 (Admin)** 和 **前台商城 (Portal)**。所有 API 统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

---

## 管理后台 API (`/api/v1/admin/*`)

所有管理后台接口需要 JWT 认证 (`Authorization: Bearer <token>`)，基于 RBAC 角色权限控制。

### 商品管理 (PMS)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/products` | GET | 商品分页列表 (多条件筛选) |
| `/admin/products` | POST | 创建商品 (SPU+SKU+属性值) |
| `/admin/products/{id}` | GET | 商品详情 |
| `/admin/products/{id}` | PUT | 更新商品 |
| `/admin/products/{id}` | DELETE | 删除商品 |
| `/admin/products/{id}/status` | PATCH | 上下架切换 |
| `/admin/products/batch-status` | PATCH | 批量上下架 |
| `/admin/products/{id}/new` | PATCH | 新品标记 |
| `/admin/products/{id}/recommend` | PATCH | 推荐标记 |
| `/admin/products/{id}/verify` | PATCH | 审核 (0待审核/1通过/2驳回) |
| `/admin/products/{id}/skus` | PUT | 更新 SKU 库存 |
| `/admin/products/{id}/sync-es` | POST | 同步到 Elasticsearch |
| `/admin/brands` | GET/POST | 品牌列表/创建 |
| `/admin/brands/{id}` | GET/PUT/DELETE | 品牌详情/更新/删除 |
| `/admin/brands/all` | GET | 全部启用品牌 (下拉选择) |
| `/admin/categories` | GET/POST | 分类列表/创建 |
| `/admin/categories/{id}` | GET/PUT/DELETE | 分类详情/更新/删除 |
| `/admin/categories/tree` | GET | 分类树形结构 |
| `/admin/product-attributes` | GET/POST | 属性列表/创建 |
| `/admin/product-attributes/{id}` | GET/PUT/DELETE | 属性详情/更新/删除 |
| `/admin/product-attributes/categories` | GET/POST | 属性分类管理 |

### 订单管理 (OMS)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/orders` | GET | 订单分页列表 (多条件筛选) |
| `/admin/orders/{id}` | GET | 订单详情 |
| `/admin/orders/{id}/close` | POST | 管理关闭订单 |
| `/admin/orders/{id}/delivery` | POST | 发货 |
| `/admin/orders/{id}/modify-address` | POST | 修改收货地址 |
| `/admin/orders/{id}/modify-price` | POST | 修改订单价格 |
| `/admin/orders/{id}/remark` | POST | 添加备注 |
| `/admin/orders/{id}` | DELETE | 软删除订单 |
| `/admin/return-applies` | GET/DELETE | 退货申请列表/批量删除 |
| `/admin/return-applies/{id}` | GET | 退货申请详情 |
| `/admin/return-applies/{id}/status` | PATCH | 更新退货状态 |
| `/admin/return-reasons` | GET/POST/DELETE | 退货原因 CRUD |
| `/admin/order-settings/{id}` | GET/PUT | 订单配置 (超时/确认时限) |

### 促销管理 (SMS)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/coupons` | GET/POST | 优惠券列表/创建 |
| `/admin/coupons/{id}` | GET/PUT/DELETE | 优惠券详情/更新/删除 |
| `/admin/coupons/{id}/histories` | GET | 领取/使用记录 |
| `/admin/flash-promotions` | GET/POST | 秒杀活动 CRUD |
| `/admin/flash-promotions/sessions` | GET/POST | 场次 CRUD |
| `/admin/flash-promotions/products` | GET/POST | 秒杀商品 CRUD |

### 会员管理 (UMS)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/members` | GET | 会员分页列表 |
| `/admin/members/{id}` | GET | 会员详情 |
| `/admin/members/{id}/status` | PATCH | 启用/封禁 |

### 智能客服管理 (CS Admin)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/cs/tickets` | GET | 工单列表 |
| `/admin/cs/tickets/{id}` | GET/PUT | 工单详情/更新 |
| `/admin/cs/tickets/{id}/assign` | PATCH | 指派坐席 |
| `/admin/cs/tickets/{id}/resolve` | PATCH | 解决工单 |
| `/admin/cs/tickets/{id}/messages` | GET/POST | 聊天消息 |
| `/admin/cs/chat/{ticket_id}` | GET | SSE 聊天流 |
| `/admin/cs/agent/status` | GET/PUT | 坐席状态管理 |
| `/admin/cs/notifications` | GET | 通知列表 |
| `/admin/cs/notifications/read` | PUT | 批量已读 |
| `/admin/cs/stats` | GET | 客服统计 |

### 内容管理 (CMS)

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/cms/banners` | GET/POST | Banner CRUD |
| `/admin/cms/subjects` | GET/POST | 专题 CRUD |
| `/admin/cms/helps` | GET/POST | 帮助中心 CRUD |

### 仪表盘

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin/dashboard` | GET | 今日订单/营收/热销TOP5/7天趋势/最新订单 |

### RBAC 权限

| 路由 | 方法 | 说明 |
|------|------|------|
| `/admin` | GET/POST | 管理员列表/注册 |
| `/admin/{id}` | POST/PUT/DELETE | 管理员更新/角色分配/删除 |
| `/role/listAll` | GET | 全部角色 |
| `/role/list` | GET | 角色分页列表 |
| `/role/create|update|delete` | POST | 角色 CRUD |
| `/role/listMenu/{id}` | GET | 角色菜单 |
| `/role/listResource/{id}` | GET | 角色资源 |
| `/role/allocMenu` | POST | 分配菜单 |
| `/role/allocResource` | POST | 分配资源 |
| `/menu/treeList` | GET | 菜单树 |
| `/menu/list/{parent_id}` | GET | 子菜单列表 |
| `/menu/create|update/{id}|delete/{id}` | POST | 菜单 CRUD |
| `/resourceCategory` | GET/POST | 资源分类 CRUD |
| `/resource` | GET/POST | 资源 CRUD |

---

## 前台商城 API (`/api/v1/portal/*`)

部分接口匿名可访问 (首页、商品浏览等)，用户相关接口需要 JWT 认证。

### 商品浏览

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/products` | GET | 否 | 混合搜索 (ES+向量+CF) |
| `/portal/products/{id}` | GET | 否 | 商品详情 |
| `/portal/products/category/{id}` | GET | 否 | 按分类浏览 |
| `/portal/brands` | GET | 否 | 品牌列表 |
| `/portal/brands/{id}` | GET | 否 | 品牌详情 |
| `/portal/categories` | GET | 否 | 分类列表 |
| `/portal/categories/tree` | GET | 否 | 分类树 |

### 首页与推荐

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/home` | GET | 否 | 首页聚合 (Banner+新品+推荐+专题) |
| `/portal/home/feed` | GET | 否 | 5数据源并发: 猜你喜欢+热门+新品+历史+发现 |
| `/portal/recommendations` | POST | 否 | 个性化推荐 (4-Agent流水线) |
| `/portal/recommendations/home` | GET | 否 | 首页快捷推荐 |

### 搜索

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/search/suggest` | GET | 否 | 搜索建议 (autocomplete+trending+AI) |
| `/portal/search/suggest/generate` | POST | 否 | 离线生成 AI 搜索建议 |

### 购物车与订单

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/cart` | GET | 是 | 购物车列表 |
| `/portal/cart` | POST | 是 | 添加商品 (幂等: 同SKU累加) |
| `/portal/cart/{id}` | PUT | 是 | 更新数量 |
| `/portal/cart/{id}` | DELETE | 是 | 删除商品 |
| `/portal/cart` | DELETE | 是 | 清空购物车 |
| `/portal/cart/{id}/checked` | PATCH | 是 | 切换勾选 |
| `/portal/orders` | POST | 是 | 从购物车创建订单 |
| `/portal/orders` | GET | 是 | 订单列表 |
| `/portal/orders/{id}` | GET | 是 | 订单详情 |
| `/portal/orders/{id}/cancel` | POST | 是 | 取消订单 |
| `/portal/orders/{id}/pay` | POST | 是 | 支付 |
| `/portal/orders/{id}/confirm-receipt` | POST | 是 | 确认收货 |

### 会员中心

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/member/profile` | GET/PUT | 是 | 个人信息 |
| `/portal/member/addresses` | GET/POST | 是 | 地址列表/创建 |
| `/portal/member/addresses/{id}` | PUT/DELETE | 是 | 地址更新/删除 |
| `/portal/member/favorites` | GET/POST/DELETE | 是 | 收藏管理 |

### 优惠券

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/coupons/available` | GET | 是 | 可领取券列表 |
| `/portal/coupons/{id}/claim` | POST | 是 | 领券 |
| `/portal/coupons/mine` | GET | 是 | 我的券 (按用途状态筛选) |

### 智能客服

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/cs/orders/{id}/return-eligibility` | GET | 是 | 退货资格校验 |
| `/portal/cs/orders/{id}/return` | POST | 是 | 提交退货申请 |
| `/portal/cs/orders/{id}/refund-status` | GET | 是 | 退款进度查询 |
| `/portal/cs/orders/{id}/logistics` | GET | 是 | 物流查询 |
| `/portal/cs/orders/{id}/validate-complaint` | GET | 是 | 投诉验证 |
| `/portal/cs/tickets` | GET/POST | 是 | 工单列表/创建 |
| `/portal/cs/tickets/{id}` | GET | 是 | 工单详情 |
| `/portal/cs/tickets/{id}/messages` | GET/POST | 是 | 工单消息 |
| `/portal/cs/chat` | POST | 是 | AI Agent 对话 |
| `/portal/cs/chat/{ticket_id}` | GET | 是 | SSE 聊天流 |
| `/portal/cs/compensate` | POST | 是 | 补偿优惠券 |
| `/portal/cs/sessions/summarize` | POST | 是 | 会话摘要 |
| `/portal/cs/sessions/history` | GET | 是 | 会话历史 |
| `/portal/cs/sessions/{id}` | GET | 是 | 会话详情 |

### 其他

| 路由 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/portal/notices` | GET | 否 | 公告/帮助列表 |
| `/portal/notices/{id}` | GET | 否 | 公告/帮助详情 |
| `/portal/behaviors` | POST | 否 | 用户行为埋点上报 |

---

## 认证

- **JWT 双令牌**：Access Token (15min) + Refresh Token (7天)
- **Token 刷新**：`POST /api/v1/auth/refresh`
- **注册**：`POST /api/v1/auth/register`
- **登录**：`POST /api/v1/auth/login`

## SSE 事件流

AI Agent 执行过程通过 SSE (Server-Sent Events) 实时推送：

```
event: node_started      → {node_name, plan_id}
event: node_succeeded    → {node_name, ...results}
event: tool_called       → {tool_name, args}
event: tool_finished     → {tool_name, status, result}
event: message           → {content, sender}
event: plan_completed    → {plan_id, status}
```
