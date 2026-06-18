"""
【订单 Service】— 下单 / 支付 / 取消 / 发货 / 收货 核心业务

知识点速查：
  - 乐观锁库存扣减: UPDATE ... WHERE stock >= ? AND lock_stock < ?
    避免 SELECT → UPDATE 之间的 race condition (两个并发请求同时扣减)
    如果先 SELECT 再 UPDATE: A 查库存=10, B 查库存=10, A 减10, B 减10 → 超卖
  - 状态机: STATUS_TRANSITIONS 白名单控制合法状态变更
  - 订单编号生成: 时间戳 + 随机数，不使用自增ID (暴露订单量)

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.order import (
    STATUS_TRANSITIONS,
    OrderCreateFromCart,
    OrderDeliveryRequest,
    OrderDetailResponse,
    OrderItemResponse,
    OrderListQuery,
    OrderPriceModifyRequest,
    OrderResponse,
    OrderStatus,
)


def _generate_order_sn() -> str:
    """生成订单编号: 年月日时分秒 + 6位随机数"""
    now = datetime.now(UTC)
    ts = now.strftime("%Y%m%d%H%M%S")
    rand = str(random.randint(100000, 999999))
    return f"{ts}{rand}"


def _validate_transition(current_status: int, new_status: int) -> None:
    """校验状态转换合法性 —— 白名单机制"""
    allowed = STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        from app.core.exceptions import OrderStatusError

        raise OrderStatusError(
            order_id="",
            current_status=str(current_status),
            expected=str(allowed),
        )


class OrderService:
    """订单服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    #  创建订单 (从购物车) —— 最核心的流程
    # =========================================================================

    async def create_from_cart(self, user_id: UUID, username: str, data: OrderCreateFromCart) -> OrderDetailResponse:
        """
        从购物车创建订单。

        步骤:
          1. 加载勾选的购物车条目
          2. 校验库存 → 锁定库存 (乐观锁扣减)
          3. 计算金额 (总价 + 运费 - 优惠)
          4. 创建订单 + 订单明细
          5. 记录操作日志
          6. 清除已购购物车条目
          7. 返回订单详情
        """
        from app.models.order.cart import OmsCartItem
        from app.models.order.order import OmsOrder, OmsOrderItem, OmsOrderOperateLog
        from app.models.product.sku import PmsSku

        # 步骤1: 加载勾选条目
        result = await self.db.execute(
            select(OmsCartItem).where(
                OmsCartItem.id.in_(data.cart_item_ids),
                OmsCartItem.user_id == user_id,
                OmsCartItem.checked == 1,
            )
        )
        cart_items = result.scalars().all()
        if not cart_items:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="CART_EMPTY", message="没有可下单的商品", status_code=400)

        # 步骤2: 校验库存 + 锁定库存 (乐观锁)
        # 每个 SKU 依次扣减——为什么不用批量 UPDATE？
        # 因为每个 SKU 的库存量不同，批量 UPDATE 无法针对不同 SKU 写不同条件
        for item in cart_items:
            # 乐观锁: WHERE stock - lock_stock >= 需求量
            # 并发下保证不会超卖
            stmt = (
                update(PmsSku)
                .where(
                    PmsSku.id == item.sku_id,
                    PmsSku.stock - PmsSku.lock_stock >= item.quantity,
                )
                .values(lock_stock=PmsSku.lock_stock + item.quantity)
            )
            upd_result = await self.db.execute(stmt)
            if upd_result.rowcount == 0:  # type: ignore[attr-defined]
                # rowcount == 0 → 库存不足 (WHERE 条件不满足)
                # 这里需要回滚已锁定的库存——但由于事务未提交，回滚就是 rollback
                from app.core.exceptions import InsufficientStockError

                raise InsufficientStockError(
                    str(item.sku_id),
                    requested=item.quantity,
                )

        # 步骤3: 计算金额
        total_amount = sum((item.price * item.quantity for item in cart_items), Decimal("0.00"))
        freight_amount = Decimal("0.00")  # 简化: 后续可查询运费模板
        discount_amount = Decimal("0.00")

        # 步骤3b: 优惠券校验与折扣计算
        _coupon_history = None
        if data.coupon_id is not None:
            discount_amount, _coupon_history = await self._apply_coupon(
                user_id=user_id,
                coupon_id=data.coupon_id,
                total_amount=total_amount,
            )

        pay_amount = total_amount + freight_amount - discount_amount

        # 步骤4: 创建订单
        order = OmsOrder(
            order_sn=_generate_order_sn(),
            user_id=user_id,
            member_username=username,
            total_amount=total_amount,
            pay_amount=pay_amount,
            freight_amount=freight_amount,
            discount_amount=discount_amount,
            coupon_id=data.coupon_id,
            pay_type=data.pay_type,
            receiver_name=data.receiver_name,
            receiver_phone=data.receiver_phone,
            receiver_province=data.receiver_province,
            receiver_city=data.receiver_city,
            receiver_region=data.receiver_region,
            receiver_detail_address=data.receiver_detail_address,
            receiver_post_code=data.receiver_post_code,
            note=data.note,
            status=OrderStatus.PENDING_PAYMENT,
        )
        self.db.add(order)
        await self.db.flush()  # 获取 order.id

        # 创建订单明细
        for item in cart_items:
            order_item = OmsOrderItem(
                order_id=order.id,
                order_sn=order.order_sn,
                product_id=item.product_id,
                product_name=item.product_name,
                product_pic=item.product_pic,
                sku_id=item.sku_id,
                sku_code=item.sku_code,
                spec=item.spec,
                price=item.price,
                quantity=item.quantity,
            )
            self.db.add(order_item)

        # 步骤5: 记录操作日志
        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man=username,
                order_status_before=None,
                order_status_after=OrderStatus.PENDING_PAYMENT,
                note="用户提交订单",
            )
        )

        # 步骤6: 清除已购购物车条目
        await self.db.execute(
            delete(OmsCartItem).where(
                OmsCartItem.id.in_(data.cart_item_ids),
            )
        )

        # 步骤6b: 核销优惠券使用记录
        if _coupon_history is not None:
            from app.models.promotion.coupon import SmsCoupon

            _coupon_history.use_status = 1
            _coupon_history.use_time = datetime.now(UTC)
            _coupon_history.order_id = order.id
            _coupon_history.order_sn = order.order_sn
            await self.db.execute(
                update(SmsCoupon).where(SmsCoupon.id == data.coupon_id).values(use_count=SmsCoupon.use_count + 1)
            )

        await self.db.flush()
        return await self.get_detail(order.id, user_id=user_id)

    async def _apply_coupon(self, user_id: UUID, coupon_id: UUID, total_amount: Decimal):
        """
        优惠券校验与折扣计算。

        校验链:
          1. 优惠券模板存在且启用 (status=1)
          2. 用户已领取且未使用 (use_status=0)
          3. 未过期 (expire_time > now)
          4. 满足使用门槛 (total_amount >= min_amount)

        Returns:
            (discount_amount, SmsCouponHistory) — history 对象供调用方后续更新 use_status。
            调用方必须在订单创建后设置 use_status=1, use_time, order_id, order_sn，
            并更新 SmsCoupon.use_count。
        """
        from datetime import UTC

        from app.core.exceptions import CouponError
        from app.models.promotion.coupon import SmsCoupon, SmsCouponHistory

        # 1. 优惠券模板存在且启用
        coupon_result = await self.db.execute(
            select(SmsCoupon).where(
                SmsCoupon.id == coupon_id,
                SmsCoupon.status == 1,
            )
        )
        coupon = coupon_result.scalar_one_or_none()
        if not coupon:
            raise CouponError(
                code="COUPON_INVALID",
                message="优惠券不存在或已禁用",
                status_code=400,
            )

        # 2. 用户已领取且未使用、未过期
        now = datetime.now(UTC)
        history_result = await self.db.execute(
            select(SmsCouponHistory).where(
                SmsCouponHistory.coupon_id == coupon_id,
                SmsCouponHistory.user_id == user_id,
                SmsCouponHistory.use_status == 0,
                SmsCouponHistory.expire_time > now,
            )
        )
        history = history_result.scalars().first()
        if not history:
            raise CouponError(
                code="COUPON_NOT_AVAILABLE",
                message="优惠券未领取、已使用或已过期",
                status_code=400,
            )

        # 3. 使用门槛 (使用领取时的快照阈值)
        if total_amount < history.coupon_min_amount:
            raise CouponError(
                code="COUPON_THRESHOLD_NOT_MET",
                message=f"未满足优惠券使用门槛 (需满 {history.coupon_min_amount}，当前 {total_amount})",
                status_code=400,
            )

        # 4. 计算折扣 (使用领取时的快照金额和类型)
        if history.coupon_use_type == 1:
            # 折扣券: amount 存储折扣率 (如 80 = 打8折 = 优惠20%)
            rate = (Decimal("100") - history.coupon_amount) / Decimal("100")
            discount = (total_amount * rate).quantize(Decimal("0.01"))
        else:
            # 满减券 (use_type=0) / 立减券 (use_type=2): amount 为直接抵扣金额
            discount = min(history.coupon_amount, total_amount)

        return discount, history

    # =========================================================================
    #  支付回调
    # =========================================================================

    async def pay(
        self, order_id: UUID, user_id: UUID | None = None, pay_order_sn: str = "MOCK_PAY_SN"
    ) -> OrderDetailResponse:
        """
        订单支付 —— 支付网关回调后调用。

        状态变更: 待付款 → 已付款
        """
        from app.models.order.order import OmsOrder, OmsOrderOperateLog

        order = await self._get_order(OmsOrder, order_id, user_id=user_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        _validate_transition(order.status, OrderStatus.PAID)

        order.status = OrderStatus.PAID
        order.pay_order_sn = pay_order_sn
        order.payment_time = datetime.now(UTC)
        order.pay_type = order.pay_type or 1

        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man="system",
                order_status_before=OrderStatus.PENDING_PAYMENT,
                order_status_after=OrderStatus.PAID,
                note=f"支付成功 {pay_order_sn}",
            )
        )
        await self.db.flush()
        return await self.get_detail(order.id, user_id=user_id)

    # =========================================================================
    #  取消订单 (用户或超时)
    # =========================================================================

    async def cancel(
        self, order_id: UUID, operator: str = "user", note: str = "", user_id: UUID | None = None
    ) -> OrderDetailResponse:
        """
        取消订单 —— 恢复已锁定的库存。

        状态变更: 待付款 → 已关闭 (用户取消)
                  已付款 → 退款中 (客服介入)
        """
        from app.models.order.order import OmsOrder, OmsOrderItem, OmsOrderOperateLog
        from app.models.product.sku import PmsSku

        order = await self._get_order(OmsOrder, order_id, user_id=user_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        # 待付款 → 关闭；已付款 → 退款中
        target_status = OrderStatus.CLOSED if order.status == OrderStatus.PENDING_PAYMENT else OrderStatus.REFUNDING
        _validate_transition(order.status, target_status)

        old_status = order.status
        order.status = target_status

        # 恢复库存: 释放锁定的库存
        if old_status in (OrderStatus.PENDING_PAYMENT, OrderStatus.PAID):
            items_result = await self.db.execute(select(OmsOrderItem).where(OmsOrderItem.order_id == order_id))
            for item in items_result.scalars().all():
                await self.db.execute(
                    update(PmsSku).where(PmsSku.id == item.sku_id).values(lock_stock=PmsSku.lock_stock - item.quantity)
                )

        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man=operator,
                order_status_before=old_status,
                order_status_after=target_status,
                note=note or "取消订单",
            )
        )
        await self.db.flush()
        return await self.get_detail(order.id, user_id=user_id)

    # =========================================================================
    #  发货 (管理员)
    # =========================================================================

    async def delivery(self, order_id: UUID, data: OrderDeliveryRequest, operator: str) -> OrderDetailResponse:
        from app.models.order.order import OmsOrder, OmsOrderOperateLog

        order = await self.db.get(OmsOrder, order_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        _validate_transition(order.status, OrderStatus.DELIVERED)

        old_status = order.status
        order.status = OrderStatus.DELIVERED
        order.delivery_company = data.delivery_company
        order.delivery_sn = data.delivery_sn
        order.delivery_time = datetime.now(UTC)

        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man=operator,
                order_status_before=old_status,
                order_status_after=OrderStatus.DELIVERED,
                note=f"物流: {data.delivery_company} {data.delivery_sn}",
            )
        )
        await self.db.flush()
        return await self.get_detail(order.id)

    # =========================================================================
    #  确认收货 (用户)
    # =========================================================================

    async def confirm_receipt(self, order_id: UUID, user_id: UUID | None = None) -> OrderDetailResponse:
        from app.models.order.order import OmsOrder, OmsOrderOperateLog

        order = await self._get_order(OmsOrder, order_id, user_id=user_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        _validate_transition(order.status, OrderStatus.RECEIVED)

        old_status = order.status
        order.status = OrderStatus.RECEIVED
        order.confirm_status = 1

        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man="user",
                order_status_before=old_status,
                order_status_after=OrderStatus.RECEIVED,
                note="用户确认收货",
            )
        )
        await self.db.flush()
        return await self.get_detail(order.id, user_id=user_id)

    # =========================================================================
    #  完成订单 (已收货 → 已完成)
    # =========================================================================

    async def complete(self, order_id: UUID, user_id: UUID | None = None) -> OrderDetailResponse:
        """
        完成订单 —— 从已收货过渡到已完成。

        状态变更: RECEIVED(3) → COMPLETED(4)
        """
        from app.models.order.order import OmsOrder, OmsOrderOperateLog

        order = await self._get_order(OmsOrder, order_id, user_id=user_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        _validate_transition(order.status, OrderStatus.COMPLETED)

        old_status = order.status
        order.status = OrderStatus.COMPLETED

        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man="user" if user_id else "system",
                order_status_before=old_status,
                order_status_after=OrderStatus.COMPLETED,
                note="订单已完成",
            )
        )
        await self.db.flush()
        return await self.get_detail(order.id, user_id=user_id)

    # =========================================================================
    #  退款完成 (管理员)
    # =========================================================================

    async def refund(self, order_id: UUID, operator: str, note: str = "") -> OrderDetailResponse:
        """
        退款完成 —— 管理员确认退款。

        状态变更: REFUNDING(6) → REFUNDED(7)
        """
        from app.models.order.order import OmsOrder, OmsOrderOperateLog

        order = await self.db.get(OmsOrder, order_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        _validate_transition(order.status, OrderStatus.REFUNDED)

        old_status = order.status
        order.status = OrderStatus.REFUNDED

        self.db.add(
            OmsOrderOperateLog(
                order_id=order.id,
                operate_man=operator,
                order_status_before=old_status,
                order_status_after=OrderStatus.REFUNDED,
                note=note or "退款完成",
            )
        )
        await self.db.flush()
        return await self.get_detail(order.id)

    # =========================================================================
    #  管理员操作
    # =========================================================================

    async def admin_close(self, order_id: UUID, note: str, operator: str) -> OrderDetailResponse:
        """管理员关闭订单"""
        return await self.cancel(order_id, operator=operator, note=note)

    async def modify_address(self, order_id: UUID, **kwargs) -> OrderDetailResponse:
        """修改收货地址"""
        from app.models.order.order import OmsOrder

        order = await self.db.get(OmsOrder, order_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        for field, value in kwargs.items():
            if value is not None and hasattr(order, field):
                setattr(order, field, value)
        await self.db.flush()
        return await self.get_detail(order.id)

    async def modify_price(self, order_id: UUID, data: OrderPriceModifyRequest) -> OrderDetailResponse:
        """修改订单金额 (运费/优惠)"""
        from app.models.order.order import OmsOrder

        order = await self.db.get(OmsOrder, order_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        if data.freight_amount is not None:
            order.freight_amount = data.freight_amount
        if data.discount_amount is not None:
            order.discount_amount = data.discount_amount

        order.pay_amount = order.total_amount + order.freight_amount - order.discount_amount
        await self.db.flush()
        return await self.get_detail(order.id)

    async def remark(self, order_id: UUID, note: str) -> OrderDetailResponse:
        """添加管理员备注"""
        from app.models.order.order import OmsOrder

        order = await self.db.get(OmsOrder, order_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        order.admin_note = note
        await self.db.flush()
        return await self.get_detail(order.id)

    async def admin_delete(self, order_id: UUID) -> None:
        """软删除订单（设置 delete_status=1）"""
        from app.models.order.order import OmsOrder

        stmt = update(OmsOrder).where(OmsOrder.id == order_id, OmsOrder.delete_status == 0).values(delete_status=1)
        result = await self.db.execute(stmt)
        if result.rowcount == 0:  # type: ignore[attr-defined]
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

    # =========================================================================
    #  查询
    # =========================================================================

    async def _get_order(self, model: type, order_id: UUID, *, user_id: UUID | None = None) -> Any:
        """加载订单，若提供 user_id 则附加归属权过滤。"""
        if user_id is not None:
            result: Any = await self.db.execute(
                select(model).where(
                    model.id == order_id,  # type: ignore[attr-defined]
                    model.user_id == user_id,  # type: ignore[attr-defined]
                )
            )
            return result.scalars().first()
        return await self.db.get(model, order_id)

    async def get_detail(self, order_id: UUID, user_id: UUID | None = None) -> OrderDetailResponse:
        """订单详情 —— 含明细 + 操作日志。若提供 user_id 则校验归属权。"""
        from app.models.order.order import OmsOrder, OmsOrderItem, OmsOrderOperateLog

        order = await self._get_order(OmsOrder, order_id, user_id=user_id)
        if not order:
            from app.core.exceptions import OrderNotFoundError

            raise OrderNotFoundError(str(order_id))

        items_result = await self.db.execute(select(OmsOrderItem).where(OmsOrderItem.order_id == order_id))
        items = items_result.scalars().all()

        # 查询操作日志（按 ID 升序 = 按创建时间升序，用于时间线展示）
        logs_result = await self.db.execute(
            select(OmsOrderOperateLog)
            .where(OmsOrderOperateLog.order_id == order_id)
            .order_by(OmsOrderOperateLog.id.asc())
        )
        logs = logs_result.scalars().all()

        from app.schemas.order import OrderOperateLogResponse

        return OrderDetailResponse(
            **OrderResponse.model_validate(order).model_dump(),
            items=[OrderItemResponse.model_validate(i) for i in items],
            logs=[OrderOperateLogResponse.model_validate(log) for log in logs],
        )

    async def list_admin(self, query: OrderListQuery) -> tuple[list[OrderResponse], int]:
        """管理后台订单列表 —— 多条件筛选"""
        from app.models.order.order import OmsOrder

        base = select(OmsOrder)
        count_q = select(func.count(OmsOrder.id))

        if query.order_sn:
            base = base.where(OmsOrder.order_sn == query.order_sn)
            count_q = count_q.where(OmsOrder.order_sn == query.order_sn)
        if query.status is not None:
            base = base.where(OmsOrder.status == query.status)
            count_q = count_q.where(OmsOrder.status == query.status)
        if query.start_time:
            base = base.where(OmsOrder.created_at >= query.start_time)
            count_q = count_q.where(OmsOrder.created_at >= query.start_time)
        if query.end_time:
            base = base.where(OmsOrder.created_at <= query.end_time)
            count_q = count_q.where(OmsOrder.created_at <= query.end_time)

        # 排除已删除
        base = base.where(OmsOrder.delete_status == 0)
        count_q = count_q.where(OmsOrder.delete_status == 0)

        result = await self.db.execute(count_q)
        total = result.scalar() or 0

        result = await self.db.execute(
            base.order_by(OmsOrder.created_at.desc()).offset((query.page - 1) * query.page_size).limit(query.page_size)
        )
        orders = result.scalars().all()
        return [OrderResponse.model_validate(o) for o in orders], total

    async def list_user(
        self, user_id: UUID, status: int | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[OrderResponse], int]:
        """用户订单列表"""
        from app.models.order.order import OmsOrder

        base = select(OmsOrder).where(
            OmsOrder.user_id == user_id,
            OmsOrder.delete_status == 0,
        )
        count_q = select(func.count(OmsOrder.id)).where(
            OmsOrder.user_id == user_id,
            OmsOrder.delete_status == 0,
        )

        if status is not None:
            base = base.where(OmsOrder.status == status)
            count_q = count_q.where(OmsOrder.status == status)

        result = await self.db.execute(count_q)
        total = result.scalar() or 0

        result = await self.db.execute(
            base.order_by(OmsOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        orders = result.scalars().all()
        return [OrderResponse.model_validate(o) for o in orders], total

    # =========================================================================
    #  仪表盘统计
    # =========================================================================

    async def count_today(self) -> int:
        """今日订单数"""
        from datetime import date

        from app.models.order.order import OmsOrder

        today = date.today()
        result = await self.db.execute(
            select(func.count(OmsOrder.id)).where(
                OmsOrder.created_at >= today,
                OmsOrder.delete_status == 0,
            )
        )
        return result.scalar() or 0

    async def revenue_today(self) -> int:
        """今日销售额 (分)"""
        from datetime import date

        from app.models.order.order import OmsOrder

        today = date.today()
        result = await self.db.execute(
            select(func.coalesce(func.sum(OmsOrder.pay_amount), 0)).where(
                OmsOrder.created_at >= today,
                OmsOrder.delete_status == 0,
                OmsOrder.status != OrderStatus.CLOSED,
                OmsOrder.status != OrderStatus.PENDING_PAYMENT,
            )
        )
        return int(result.scalar() or 0)

    async def count_pending_returns(self) -> int:
        """待处理退货数"""
        from app.models.order.order import OmsOrder

        result = await self.db.execute(
            select(func.count(OmsOrder.id)).where(
                OmsOrder.status == OrderStatus.REFUNDING,
                OmsOrder.delete_status == 0,
            )
        )
        return result.scalar() or 0

    async def status_counts(self) -> list[dict]:
        """各状态订单数量统计"""
        from app.models.order.order import OmsOrder

        _status_map = {
            0: ("待付款", "warning"),
            1: ("待发货", "primary"),
            2: ("已发货", "success"),
            3: ("已收货", "info"),
            4: ("已完成", "info"),
            5: ("已关闭", "info"),
            6: ("退款中", "danger"),
            7: ("已退款", "info"),
        }

        result = await self.db.execute(
            select(OmsOrder.status, func.count(OmsOrder.id))
            .where(OmsOrder.delete_status == 0)
            .group_by(OmsOrder.status)
        )
        counts = {row[0]: row[1] for row in result.all()}

        return [
            {"label": label, "count": counts.get(status, 0), "type": tag_type}
            for status, (label, tag_type) in _status_map.items()
            if counts.get(status, 0) > 0
        ]

    async def revenue_daily_range(self, start_date: date, end_date: date) -> list[int]:
        """近N天每日销售额 (分)，按日期升序"""
        from app.models.order.order import OmsOrder

        result = await self.db.execute(
            select(
                func.date(OmsOrder.created_at),
                func.coalesce(func.sum(OmsOrder.pay_amount), 0),
            )
            .where(
                OmsOrder.created_at >= start_date,
                OmsOrder.created_at <= end_date,
                OmsOrder.delete_status == 0,
                OmsOrder.status != OrderStatus.CLOSED,
                OmsOrder.status != OrderStatus.PENDING_PAYMENT,
            )
            .group_by(func.date(OmsOrder.created_at))
            .order_by(func.date(OmsOrder.created_at))
        )
        day_map = {str(row[0]): int(row[1]) for row in result.all()}

        # Fill in all days in range
        sales = []
        d = start_date
        while d <= end_date:
            sales.append(day_map.get(d.isoformat(), 0))
            d += timedelta(days=1)
        return sales

    async def latest(self, limit: int = 5) -> list[dict]:
        """最新N条订单"""
        from app.models.order.order import OmsOrder

        _status_map = {
            0: "待付款",
            1: "待发货",
            2: "已发货",
            3: "已收货",
            4: "已完成",
            5: "已关闭",
            6: "退款中",
            7: "已退款",
        }

        result = await self.db.execute(
            select(OmsOrder).where(OmsOrder.delete_status == 0).order_by(OmsOrder.created_at.desc()).limit(limit)
        )
        orders = result.scalars().all()
        return [
            {
                "id": o.id,
                "order_sn": o.order_sn,
                "member": o.member_username,
                "amount": float(o.pay_amount),
                "status": o.status,
                "statusLabel": _status_map.get(o.status, "未知"),
            }
            for o in orders
        ]
