# 商品域问题清单

## 严重

### GAP-1: ES 同步 brand_name / category_name 为空
- **文件**: `backend/app/services/product_service.py:439-440`
- **问题**: `_sync_product_to_es()` 硬编码 `"brand_name": ""`, `"category_name": ""`，从未从数据库查询填充，但 ES mapping 声明这些字段为可搜索字段。
- **影响**: 品牌名、分类名在 ES 搜索中完全不工作，ES `multi_match` 中包含这些字段但始终为空。
- **修复方向**: 在 `_sync_product_to_es()` 中 JOIN 查询 brand 和 category 表，填入实际名称。

### GAP-2: 排序 "new" 引用不存在的 publish_time
- **文件**: `backend/app/search/client.py:186`
- **问题**: `sort_by == "new"` 使用 `publish_time` 字段排序，但 `_sync_product_to_es()` 从未填充该字段。
- **影响**: 按"最新"排序静默失败。

## 高

### GAP-3: SKU 创建后无法增删改
- **文件**: `backend/app/api/admin/product.py:202-244`
- **问题**: `PUT /admin/products/{id}/skus` 仅支持更新单个 SKU 的 stock 值。无法新增 SKU、删除 SKU、修改 SKU 价格/编码/规格。
- **影响**: 管理员无法在商品创建后管理 SKU 配置，任何变更需删除重建商品。

## 中

### GAP-4: 商品属性值创建后无法修改
- **文件**: `backend/app/services/product_service.py:85-91`
- **问题**: 属性值仅在 `POST` 创建时写入。`PUT /admin/products/{id}` 不更新 `PmsProductAttributeValue`。无单独端点增删改属性值。
- **影响**: 无法修改已有商品的属性值。

## 低

### GAP-5: 死代码 — ProductService.list_portal() 从未被调用
- **文件**: `backend/app/services/product_service.py:301-358`
- **问题**: `list_portal()` 方法定义了但无任何路由调用。门户浏览走 HybridSearchService，其中 `_filter_only()` 和 `_db_ilike_fallback()` 重复了相同逻辑。

### GAP-6: `_sync_product_to_es` 私有函数被外部导入
- **文件**: `backend/app/api/admin/product.py:257`
- **问题**: 以 `_` 前缀命名的私有函数被路由文件直接导入使用，违反 PEP 8 约定。

### GAP-7: 商品审核拒绝无理由字段
- **文件**: `backend/app/models/product/product.py:216-221`
- **问题**: `verify_status` 支持 0=pending/1=approved/2=rejected，但 `PmsProduct` 无字段存储拒绝原因。

### GAP-8: 批量状态更新绕过服务层
- **文件**: `backend/app/api/admin/product.py:151-161`
- **问题**: `PATCH /admin/products/batch-status` 使用原生 SQL 直接更新，绕过 `toggle_status()` → 不触发 ES 同步。
- **影响**: 批量上下架后 ES 索引不同步。

### GAP-9: ProductResponse 不含 brand_name / category_name
- **文件**: `backend/app/schemas/product.py:297-332`
- **问题**: 管理后台商品列表返回 `brand_id`/`category_id` (UUID)，前端需额外请求解析名称。
