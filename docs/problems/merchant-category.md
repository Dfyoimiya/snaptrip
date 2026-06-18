# 商家/分类域问题清单

## 高

### GAP-1: 品牌无经纬度，无法按距离筛选
- **文件**: `backend/app/models/product/brand.py:27-84`
- **问题**: `PmsBrand` 模型无 `latitude`/`longitude` 字段。门户品牌列表 (`/portal/brands`) 不支持地理筛选。品牌详不含商品列表。
- **影响**: 无法实现"附近商家"等 LBS 功能。

### GAP-2: 品牌无软删除
- **文件**: `backend/app/models/product/brand.py:26`, `backend/app/services/brand_service.py:62-69`
- **问题**: `PmsBrand` 不继承 `SoftDeleteMixin`。删除是物理删除 (`await self.db.delete(brand)`)。关联商品的 `brand_id` 外键 `ON DELETE SET NULL`，静默丢失品牌关联。

## 中

### GAP-3: 无商家实体，品牌充当商家
- **文件**: `backend/app/models/product/brand.py:27-84`
- **问题**: 代码库无独立"商家"概念。品牌被当作商家使用，但缺少商家必要字段：营业执照、法人代表、联系方式、地址、营业时间等。

### GAP-4: 无商家状态机
- **文件**: `backend/app/models/product/brand.py:52-64`
- **问题**: 品牌仅有 `factory_status` (0/1) 和 `show_status` (0/1)。无 OPEN/CLOSED/RESTING 等商家运营状态。

### GAP-5: 无商家审核流程
- **问题**: 品牌无 `verify_status` 字段，无法实现 PENDING→APPROVED/REJECTED 审核。品牌创建即生效。

### GAP-6: 无商家自助注册
- **问题**: 无面向商家的注册入口。所有品牌由管理员在后台创建。

### GAP-7: 分类删除无安全检查
- **文件**: `backend/app/services/category_service.py:92-106`
- **问题**: 删除分类时不检查子分类数量和已分配商品数量。子分类 `parent_id` 被 SET NULL 变孤立，商品 `category_id` 被 SET NULL 变未分类。无级联处理或阻止删除逻辑。

## 低

### GAP-8: 分类无 type 字段
- **文件**: `backend/app/models/product/category.py:36-123`
- **问题**: `PmsCategory` 无 `type` 字段，无法区分 PRODUCT 和 COMBO 分类类型。

### GAP-9: 门户分类未过滤隐藏分类
- **文件**: `backend/app/api/portal/category.py:23-31`, `backend/app/services/category_service.py:121-151`
- **问题**: 端点文档声称"只返回显示状态的分类"，但 `CategoryService.list_paginated()` 不包含 `show_status` 过滤条件。

### GAP-10: 品牌详情不含商品列表
- **文件**: `backend/app/api/portal/brand.py:40-47`
- **问题**: 品牌详情端点只返回品牌本身数据，不包含关联商品、商品数量、平均评分等聚合信息。
