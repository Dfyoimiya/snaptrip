"""
【优惠券 Service】— 创建/发放/领取/核销

知识点速查：
  - 乐观锁领券: UPDATE sms_coupons SET receive_count = receive_count + 1
    WHERE id = ? AND receive_count < count
    如果不加 WHERE: 高并发下可能超发(总库存 100 被领 150 次)
  - 幂等领券: 查询 history 是否存在同用户同券 → 存在则拒绝
    如果不检查: 同一用户可重复领同一张券

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.promotion import (
    CouponCreate,
    CouponHistoryResponse,
    CouponResponse,
    CouponUpdate,
)


class CouponService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 管理: CRUD ──

    async def create(self, data: CouponCreate) -> CouponResponse:
        from app.models.promotion.coupon import SmsCoupon

        c = SmsCoupon(**data.model_dump())
        self.db.add(c)
        await self.db.flush()
        await self.db.refresh(c)
        return CouponResponse.model_validate(c)

    async def update(self, coupon_id: UUID, data: CouponUpdate) -> CouponResponse:
        from app.models.promotion.coupon import SmsCoupon

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = update(SmsCoupon).where(SmsCoupon.id == coupon_id).values(**values).returning(SmsCoupon)
        result = await self.db.execute(stmt)
        c = result.scalar_one_or_none()
        if not c:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(coupon_id))
        return CouponResponse.model_validate(c)

    async def delete(self, coupon_id: UUID) -> None:
        from app.models.promotion.coupon import SmsCoupon

        c = await self.db.get(SmsCoupon, coupon_id)
        if not c:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(coupon_id))
        await self.db.delete(c)

    async def get_by_id(self, coupon_id: UUID) -> CouponResponse:
        from app.models.promotion.coupon import SmsCoupon

        c = await self.db.get(SmsCoupon, coupon_id)
        if not c:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(coupon_id))
        return CouponResponse.model_validate(c)

    async def list_admin(
        self,
        keyword: str | None = None,
        type: int | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CouponResponse], int]:
        from app.models.promotion.coupon import SmsCoupon

        base = select(SmsCoupon)
        cnt = select(func.count(SmsCoupon.id))
        if keyword:
            base = base.where(SmsCoupon.name.ilike(f"%{keyword}%"))
            cnt = cnt.where(SmsCoupon.name.ilike(f"%{keyword}%"))
        if type is not None:
            base = base.where(SmsCoupon.type == type)
            cnt = cnt.where(SmsCoupon.type == type)
        if status is not None:
            base = base.where(SmsCoupon.status == status)
            cnt = cnt.where(SmsCoupon.status == status)
        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(SmsCoupon.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [CouponResponse.model_validate(c) for c in result.scalars().all()], total

    async def get_histories(
        self, coupon_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[CouponHistoryResponse], int]:
        from app.models.promotion.coupon import SmsCouponHistory

        base = select(SmsCouponHistory).where(SmsCouponHistory.coupon_id == coupon_id)
        cnt = select(func.count(SmsCouponHistory.id)).where(SmsCouponHistory.coupon_id == coupon_id)
        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(SmsCouponHistory.receive_time.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        items = result.scalars().all()
        return [CouponHistoryResponse.model_validate(h) for h in items], total

    # ── 前台: 领券 ──

    async def list_available(self, page: int = 1, page_size: int = 20) -> tuple[list[CouponResponse], int]:
        """获取可领取的优惠券列表 —— 已启用且未超发"""
        from app.models.promotion.coupon import SmsCoupon

        base = select(SmsCoupon).where(SmsCoupon.status == 1, SmsCoupon.receive_count < SmsCoupon.count)
        cnt = select(func.count(SmsCoupon.id)).where(SmsCoupon.status == 1, SmsCoupon.receive_count < SmsCoupon.count)
        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(SmsCoupon.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [CouponResponse.model_validate(c) for c in result.scalars().all()], total

    async def claim(self, user_id: UUID, coupon_id: UUID) -> CouponHistoryResponse:
        """
        用户领取优惠券 —— 三步校验 + 乐观锁发放。

        步骤:
          1. 查询优惠券模板是否存在且启用
          2. 幂等: 检查用户是否已领取(同券+同用户)
          3. 乐观锁: UPDATE receive_count < count → +1
          4. 创建领取历史记录
        """
        from app.models.promotion.coupon import SmsCoupon, SmsCouponHistory

        # 步骤1: 查模板并锁定行 —— SELECT FOR UPDATE 防止 per_limit
        # 检查和后续 UPDATE 之间的 TOCTOU 竞态条件。
        # 同一张券的并发领券请求会在此串行化，确保 per_limit 判断是准确的。
        result = await self.db.execute(select(SmsCoupon).where(SmsCoupon.id == coupon_id).with_for_update())
        coupon = result.scalar_one_or_none()
        if not coupon or coupon.status != 1:
            from app.core.exceptions import CouponExpiredError

            raise CouponExpiredError(str(coupon_id))

        # 校验库存
        if coupon.receive_count >= coupon.count:
            from app.core.exceptions import CouponExhaustedError

            raise CouponExhaustedError(str(coupon_id))

        # 步骤2: 幂等 —— 查是否已领过（锁已持，竞态已消除）
        existing = await self.db.execute(
            select(func.count(SmsCouponHistory.id)).where(
                SmsCouponHistory.coupon_id == coupon_id,
                SmsCouponHistory.user_id == user_id,
            )
        )
        already_claimed = existing.scalar() or 0
        if coupon.per_limit > 0 and already_claimed >= coupon.per_limit:
            from app.core.exceptions import CouponAlreadyClaimedError

            raise CouponAlreadyClaimedError(str(coupon_id))

        # 步骤3: 乐观锁发放 —— receive_count < count 保证不超发
        stmt = (
            update(SmsCoupon)
            .where(SmsCoupon.id == coupon_id, SmsCoupon.receive_count < SmsCoupon.count)
            .values(
                receive_count=SmsCoupon.receive_count + 1,
                publish_count=SmsCoupon.publish_count + 1,
            )
        )
        upd = await self.db.execute(stmt)
        if upd.rowcount == 0:  # type: ignore[attr-defined]
            from app.core.exceptions import CouponExhaustedError

            raise CouponExhaustedError(str(coupon_id))

        # 步骤4: 创建历史记录
        now = datetime.now(UTC)
        expire_days = 7  # 默认有效期7天，可从配置读取
        expire_time = coupon.end_time or (now + timedelta(days=expire_days))

        history = SmsCouponHistory(
            coupon_id=coupon.id,
            user_id=user_id,
            coupon_name=coupon.name,
            coupon_type=coupon.type,
            coupon_use_type=coupon.use_type,
            coupon_amount=coupon.amount,
            coupon_min_amount=coupon.min_amount,
            use_status=0,
            receive_time=now,
            expire_time=expire_time,
        )
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return CouponHistoryResponse.model_validate(history)

    async def list_my_coupons(self, user_id: UUID, use_status: int | None = None) -> list[CouponHistoryResponse]:
        """我的优惠券 —— 按状态筛选"""
        from app.models.promotion.coupon import SmsCouponHistory

        base = select(SmsCouponHistory).where(SmsCouponHistory.user_id == user_id)
        if use_status is not None:
            base = base.where(SmsCouponHistory.use_status == use_status)
        result = await self.db.execute(base.order_by(SmsCouponHistory.receive_time.desc()))
        return [CouponHistoryResponse.model_validate(h) for h in result.scalars().all()]
