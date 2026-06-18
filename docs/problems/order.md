# 订单域问题清单

## 严重

### GAP-1: 支付纯粹是 Mock
- **文件**: `backend/app/services/order_service.py:194`
- **问题**: `pay()` 直接标记已付款，`pay_order_sn = "MOCK_PAY_SN"`。无支付网关对接，无支付回调接口。
- **影响**: 任何认证用户可调用支付接口，无需真实付款即完成订单。

### GAP-2: 优惠券结算完全不工作
- **文件**: `backend/app/services/order_service.py:128-129`
- **问题**: `create_from_cart()` 中 `discount_amount = Decimal("0.00")`，注释 `# 简化: 后续 Phase 4 优惠券计算`。`coupon_id` 存储了但不校验归属、不过期检查、不计算折扣、不创建 `SmsCouponHistory` 记录。
- **影响**: 用户即使在结算时使用优惠券也完全不会生效。

### GAP-3: 已签收→已完成 转换缺失
- **文件**: `backend/app/schemas/order.py:67-73`, `backend/app/services/order_service.py`
- **问题**: `STATUS_TRANSITIONS` 定义了 `RECEIVED: [COMPLETED]`，但无 `complete()` 服务方法、无 API 端点。Celery 任务 `auto_confirm_receipt_orders` 仅转到 RECEIVED 不转到 COMPLETED。
- **影响**: 订单永远无法到达"已完成"状态。

## 高

### GAP-4: 退款中→已退款 转换缺失
- **文件**: `backend/app/services/order_service.py`
- **问题**: `STATUS_TRANSITIONS` 定义了 `REFUNDING: [REFUNDED, CLOSED]`，但无 `refund()` 方法和端点。`cancel()` 将已支付订单转为 REFUNDING，但无人能完成退款。
- **影响**: 退款流程有头无尾。

### GAP-5: 订单详情不返回操作日志
- **文件**: `backend/app/services/order_service.py:422`, `backend/app/schemas/order.py:143`
- **问题**: `get_detail()` 只查 `OmsOrderItem`，不查 `OmsOrderOperateLog`。`OrderDetailResponse` 无 `logs` 字段。但前端类型定义 (`frontend/src/types/order.d.ts:33`) 期望 `historyList`。
- **影响**: 前后端契约不一致，操作历史在前端不可见。

### GAP-6: 退款申请审核不联动订单状态
- **文件**: `backend/app/api/admin/return_apply.py:97`
- **问题**: `PATCH /admin/return-applies/{apply_id}/status` 更新退款申请状态但不改变 `OmsOrder.status`。退款申请标记为"已退款"时订单状态未同步。

## 中

### GAP-7: confirm_receipt 缺乏幂等检查
- **文件**: `backend/app/services/order_service.py:320`
- **问题**: 设置 `confirm_status = 1` 前未检查是否已为 1。

### GAP-8: 定时任务硬编码状态值
- **文件**: `backend/app/tasks/order_tasks.py:50,58`
- **问题**: 直接使用魔法数字 `order.status == 0`、`order.status = 5` 而非 `OrderStatus` 常量。

## 低

### GAP-9: auto_confirm_day 字段未被使用
- **文件**: `backend/app/models/order/order.py:188`
- **问题**: `OmsOrder` 有 `auto_confirm_day` 字段但 Celery 任务使用全局配置 `ORDER_AUTO_CONFIRM_DAYS`，忽略逐订单配置。
