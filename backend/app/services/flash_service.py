"""
【秒杀 Service】— 活动/场次/商品管理

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.promotion import (
    FlashProductCreate,
    FlashProductResponse,
    FlashProductUpdate,
    FlashPromotionCreate,
    FlashPromotionResponse,
    FlashPromotionUpdate,
    FlashSessionCreate,
    FlashSessionResponse,
    FlashSessionUpdate,
)


class FlashService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 活动 ──

    async def create_promotion(self, data: FlashPromotionCreate) -> FlashPromotionResponse:
        from app.models.promotion.flash import SmsFlashPromotion

        p = SmsFlashPromotion(**data.model_dump())
        self.db.add(p)
        await self.db.flush()
        await self.db.refresh(p)
        return FlashPromotionResponse.model_validate(p)

    async def update_promotion(self, promo_id: UUID, data: FlashPromotionUpdate) -> FlashPromotionResponse:
        from app.models.promotion.flash import SmsFlashPromotion

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = (
            update(SmsFlashPromotion)
            .where(SmsFlashPromotion.id == promo_id)
            .values(**values)
            .returning(SmsFlashPromotion)
        )
        result = await self.db.execute(stmt)
        p = result.scalar_one_or_none()
        if not p:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(promo_id))
        return FlashPromotionResponse.model_validate(p)

    async def delete_promotion(self, promo_id: UUID) -> None:
        from app.models.promotion.flash import SmsFlashPromotion

        p = await self.db.get(SmsFlashPromotion, promo_id)
        if not p:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(promo_id))
        await self.db.delete(p)

    async def list_promotions(self, page: int = 1, page_size: int = 20) -> tuple[list[FlashPromotionResponse], int]:
        from app.models.promotion.flash import SmsFlashPromotion

        cnt = await self.db.execute(select(func.count(SmsFlashPromotion.id)))
        total = cnt.scalar() or 0
        result = await self.db.execute(
            select(SmsFlashPromotion)
            .order_by(SmsFlashPromotion.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [FlashPromotionResponse.model_validate(p) for p in result.scalars().all()], total

    async def list_sessions(self, promo_id: UUID | None = None) -> list[FlashSessionResponse]:
        """列出所有场次，或按活动ID筛选"""
        from app.models.promotion.flash import SmsFlashPromotionSession

        base = select(SmsFlashPromotionSession)
        if promo_id:
            base = base.where(SmsFlashPromotionSession.promotion_id == promo_id)
        result = await self.db.execute(base.order_by(SmsFlashPromotionSession.start_time.asc()))
        return [FlashSessionResponse.model_validate(s) for s in result.scalars().all()]

    # ── 场次 ──

    async def create_session(self, data: FlashSessionCreate) -> FlashSessionResponse:
        from app.models.promotion.flash import SmsFlashPromotionSession

        s = SmsFlashPromotionSession(**data.model_dump())
        self.db.add(s)
        await self.db.flush()
        await self.db.refresh(s)
        return FlashSessionResponse.model_validate(s)

    async def update_session(self, session_id: UUID, data: FlashSessionUpdate) -> FlashSessionResponse:
        from app.models.promotion.flash import SmsFlashPromotionSession

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = (
            update(SmsFlashPromotionSession)
            .where(SmsFlashPromotionSession.id == session_id)
            .values(**values)
            .returning(SmsFlashPromotionSession)
        )
        result = await self.db.execute(stmt)
        s = result.scalar_one_or_none()
        if not s:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(session_id))
        return FlashSessionResponse.model_validate(s)

    async def delete_session(self, session_id: UUID) -> None:
        from app.models.promotion.flash import SmsFlashPromotionSession

        s = await self.db.get(SmsFlashPromotionSession, session_id)
        if not s:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(session_id))
        await self.db.delete(s)

    async def toggle_session_status(self, session_id: UUID, status: int) -> FlashSessionResponse:
        from app.models.promotion.flash import SmsFlashPromotionSession

        stmt = (
            update(SmsFlashPromotionSession)
            .where(SmsFlashPromotionSession.id == session_id)
            .values(status=status)
            .returning(SmsFlashPromotionSession)
        )
        result = await self.db.execute(stmt)
        s = result.scalar_one_or_none()
        if not s:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(session_id))
        return FlashSessionResponse.model_validate(s)

    # ── 秒杀商品 ──

    async def add_product(self, data: FlashProductCreate) -> FlashProductResponse:
        from app.models.promotion.flash import SmsFlashPromotionProduct

        p = SmsFlashPromotionProduct(**data.model_dump())
        self.db.add(p)
        await self.db.flush()
        await self.db.refresh(p)
        return FlashProductResponse.model_validate(p)

    async def list_products(
        self, session_id: UUID | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[FlashProductResponse], int]:
        """分页列出秒杀商品，按 session_id 筛选"""
        from app.models.promotion.flash import SmsFlashPromotionProduct

        base = select(SmsFlashPromotionProduct)
        cnt_q = select(func.count(SmsFlashPromotionProduct.id))
        if session_id:
            base = base.where(SmsFlashPromotionProduct.session_id == session_id)
            cnt_q = cnt_q.where(SmsFlashPromotionProduct.session_id == session_id)
        cnt_result = await self.db.execute(cnt_q)
        total = cnt_result.scalar() or 0
        result = await self.db.execute(
            base.order_by(SmsFlashPromotionProduct.sort.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [FlashProductResponse.model_validate(p) for p in result.scalars().all()], total

    async def update_product(self, product_id: UUID, data: FlashProductUpdate) -> FlashProductResponse:
        """编辑秒杀商品（flash_price / flash_stock / flash_limit / sort）"""
        from app.models.promotion.flash import SmsFlashPromotionProduct

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = (
            update(SmsFlashPromotionProduct)
            .where(SmsFlashPromotionProduct.id == product_id)
            .values(**values)
            .returning(SmsFlashPromotionProduct)
        )
        result = await self.db.execute(stmt)
        fp = result.scalar_one_or_none()
        if not fp:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))
        return FlashProductResponse.model_validate(fp)

    async def delete_product(self, product_id: UUID) -> None:
        from app.models.promotion.flash import SmsFlashPromotionProduct

        fp = await self.db.get(SmsFlashPromotionProduct, product_id)
        if not fp:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))
        await self.db.delete(fp)
