# SnapTrip 商品 Seed 数据说明

## 数据来源

本 seed 数据来源于 **macrozheng/mall** 开源电商项目（GitHub），经过合法获取并适配到 SnapTrip 的 PostgreSQL 数据库 schema。

- 原始项目: https://github.com/macrozheng/mall
- 数据类型: 真实电商系统示例数据（品牌、分类、商品、SKU、属性均来自真实电商场景）
- 适配方式: MySQL Long ID → PostgreSQL UUID，字段映射转换

## 数据规模

| 表名 | 数据量 | 说明 |
|------|--------|------|
| pms_brands | 12 条 | 万和、三星、华为、格力、方太、小米、OPPO、七匹狼、海澜之家、苹果、NIKE、测试品牌 |
| pms_categories | 40 条 | 覆盖 7 大一级分类（服装、手机数码、家用电器、家具家装、汽车用品、电脑办公等），含多级子分类 |
| pms_products | 20 条 | 剔除测试数据后的真实商品，包含 iPhone 14、华为 Mate 50、小米电视、海澜之家 T 恤等 |
| pms_skus | 96 条 | 每个商品平均 4-5 个 SKU 规格，含颜色、容量、尺寸等规格组合 |
| pms_product_attributes | 53 条 | 属性模板：尺寸、颜色、容量、屏幕尺寸、网络等 |
| pms_product_attribute_values | 130 条 | 商品属性实例值 |

## 覆盖的商品类别

- **手机数码**: iPhone 14、小米 12 Pro、华为 Mate 50、OPPO Reno8、Redmi K50、iPad 10.9
- **电脑办公**: 小米 Book Pro 14、三星 SSD 固态硬盘
- **家用电器**: 小米电视 4A（55/65 英寸）、万和燃气热水器
- **服装**: 海澜之家 T 恤、衬衫、外套
- **鞋靴**: 耐克 NIKE 休闲鞋、气垫鞋

## 图片资源

所有商品图片均使用 mall 项目托管在阿里云 OSS 的原始图片 URL，包括：
- 商品主图
- 商品详情页 HTML 内容中的图片
- 品牌 Logo 和 Banner

> 注意：这些图片 URL 是公开可访问的，适合用于开发和测试环境。生产环境建议下载到本地 CDN 或对象存储。

## 使用方式

### 1. 直接导入数据库

```bash
# 确保在 snaptrip 数据库上下文中
psql -h localhost -U your_user -d snaptrip_dev -f backend/snaptrip_seed_data.sql
```

### 2. 通过 Alembic 迁移执行

在 alembic 版本脚本中引用此 SQL 文件，或将其作为 `op.execute()` 的内容执行。

### 3. 注意事项

- 文件开头使用 `TRUNCATE TABLE ... CASCADE` 会清空原有数据，请谨慎执行
- 所有主键使用 **确定性 UUID**（基于 UUID5），保证重复导入不会产生重复数据
- 已自动过滤 `delete_status=1`（已删除）的商品
- 时间戳使用当前 UTC 时间

## 技术细节

### ID 映射策略

原始 mall 项目使用自增 Long ID，SnapTrip 使用 UUID。转换使用 **UUID5** 基于表名+原ID 生成确定性 UUID，确保：
- 同一来源数据多次转换结果一致
- 外键关系在转换后保持正确
- 便于增量更新和调试

### 字段映射

| mall 字段 | SnapTrip 字段 | 说明 |
|-----------|--------------|------|
| pic | default_pic / pics | 首图 + 画册合并为 pics 列表 |
| detail_html | description | 富文本详情作为商品描述 |
| sale | sale_count | 销量字段重命名 |
| recommand_status | recommend_status | 拼写差异适配 |
| sp_data (JSON) | spec (JSON) | SKU 规格 JSON 直接透传 |

## 文件位置

```
backend/snaptrip_seed_data.sql
```

---

生成时间: 2026-06-19
数据版本: mall v1.0 + SnapTrip schema v2026-06
