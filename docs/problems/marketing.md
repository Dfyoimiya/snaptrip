# 推广/营销域问题清单

## 严重

### GAP-1: 优惠券结算不工作
- **文件**: `backend/app/services/order_service.py:128-129`
- **问题**: `create_from_cart()` 中 `discount_amount` 硬编码为 0.00。`coupon_id` 被存储但从不校验：不检查券归属、不过期检查、不验证门槛、不计算折扣、不创建用券记录。
- **影响**: 用户领券后在结算时完全无效。整个优惠券生命周期断在"使用"环节。

### GAP-2: 限时抢购门户端点缺失
- **问题**: `backend/app/api/portal/` 下无任何 flash 相关端点。用户无法浏览限时抢购活动、查看秒杀商品、或参与抢购。
- **影响**: 管理后台创建的秒杀活动对 C 端完全不可见。

### GAP-3: 限时抢购库存预热未实现
- **文件**: `backend/app/services/flash_service.py:160-167`
- **问题**: `SmsFlashPromotionProduct` 文档描述了"从 PmsSku 预扣库存"的设计，但 `FlashService.add_product()` 仅插入记录，不执行库存预留。
- **影响**: 秒杀库存与商品实际库存未隔离，存在超卖风险。

### GAP-4: 公告/通知系统缺失
- **问题**: 无 `SmsNotice` 模型、无管理后台公告 CRUD、无目标受众（ALL/CUSTOMER/MERCHANT）概念。`/portal/notices` 错误地复用了 `CmsHelp`（帮助文章）表。
- **影响**: 无法向用户推送系统公告。

## 中

### GAP-5: 优惠券过期无定时处理
- **文件**: `backend/app/services/coupon_service.py:221-229`
- **问题**: `SmsCouponHistory` 有过期时间字段，但无 Celery 定时任务扫描并标记过期券。`list_my_coupons()` 不过滤也不更新已过期的券。

### GAP-6: 秒杀价格未同步到商品表
- **文件**: `backend/app/models/product/product.py:95-124` vs `backend/app/models/promotion/flash.py:78`
- **问题**: `PmsProduct` 有 `promotion_price`/`promotion_type` 等字段，但与 `SmsFlashPromotionProduct` 无同步机制。秒杀价格仅存在于秒杀表。

## 低

### GAP-7: 优惠券过期天数硬编码
- **文件**: `backend/app/services/coupon_service.py:202`
- **问题**: `expire_days = 7` 硬编码，注释说"可从配置读取"但未实现。

### GAP-8: Banner 无位置字段
- **文件**: `backend/app/models/cms/content.py:24-37`
- **问题**: `CmsBanner` 无 `position` 字段，无法区分 HOME_TOP 和 HOME_MIDDLE 等位置。

### GAP-9: 首页聚合缺少板块
- **文件**: `backend/app/schemas/cms.py:148-154`
- **问题**: `HomePageAggregation` 无 flash_promotions、notices、coupons 字段。首页只返回 Banner+新品+推荐+专题。

### GAP-10: A/B 实验硬编码
- **文件**: `backend/app/services/ab_test.py:67-95`
- **问题**: 实验在 `_register_default_experiments()` 中硬编码，无管理后台动态管理端点。
