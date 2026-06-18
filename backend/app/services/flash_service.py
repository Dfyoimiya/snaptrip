"""
【秒杀 Service】— 活动/场次/商品管理 + 库存预热

Author: SnapTrip Team
Date: 2026-05-26 / 2026-06-18
"""

from __future__ import annotations

from datetime import UTC, datetime
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

        # ── 场次结束时释放未售出的秒杀库存 ──
        if status == 2:
            await self.release_flash_stock(session_id)

        return FlashSessionResponse.model_validate(s)

    # ── 秒杀商品 ──

    async def add_product(self, data: FlashProductCreate) -> FlashProductResponse:
        """添加秒杀商品，同时从 PmsSku 预扣库存（库存预热）。

        使用乐观锁：UPDATE PmsSku SET stock = stock - :qty, lock_stock = lock_stock + :qty
        WHERE id = :sku_id AND stock - lock_stock >= :qty

        只有当可用库存（stock - lock_stock）足够时才允许预扣。
        """
        from app.core.exceptions import InsufficientStockError
        from app.models.product.sku import PmsSku
        from app.models.promotion.flash import SmsFlashPromotionProduct

        qty = data.flash_stock
        sku_id = data.sku_id

        # ── 乐观锁扣减 SKU 库存 ──
        result = await self.db.execute(
            update(PmsSku)
            .where(
                PmsSku.id == sku_id,
                PmsSku.stock - PmsSku.lock_stock >= qty,
            )
            .values(
                stock=PmsSku.stock - qty,
                lock_stock=PmsSku.lock_stock + qty,
            )
            .returning(PmsSku.id)
        )
        if result.scalar_one_or_none() is None:
            # 获取当前库存用于报错详情
            sku = await self.db.get(PmsSku, sku_id)
            available = (sku.stock - sku.lock_stock) if sku else 0
            raise InsufficientStockError(
                sku_id=str(sku_id),
                available=available,
                requested=qty,
            )

        p = SmsFlashPromotionProduct(**data.model_dump())
        self.db.add(p)
        await self.db.flush()
        await self.db.refresh(p)
        return FlashProductResponse.model_validate(p)

    async def release_flash_stock(self, session_id: UUID) -> None:
        """场次结束时释放未售出的秒杀库存回 PmsSku。

        将每个秒杀商品的 flash_stock（剩余库存）归还给对应的 PmsSku：
         - PmsSku.stock += flash_stock
         - PmsSku.lock_stock -= flash_stock

        注意：这里只归还"剩余"库存（flash_stock 字段），已卖出的部分不再归还。
        """
        from app.models.product.sku import PmsSku
        from app.models.promotion.flash import SmsFlashPromotionProduct

        # 查询该场次所有秒杀商品（仅取还有剩余库存的）
        products_result = await self.db.execute(
            select(SmsFlashPromotionProduct).where(
                SmsFlashPromotionProduct.session_id == session_id,
                SmsFlashPromotionProduct.flash_stock > 0,
            )
        )
        flash_products = products_result.scalars().all()

        for fp in flash_products:
            await self.db.execute(
                update(PmsSku)
                .where(PmsSku.id == fp.sku_id)
                .values(
                    stock=PmsSku.stock + fp.flash_stock,
                    lock_stock=PmsSku.lock_stock - fp.flash_stock,
                )
            )

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
            base.order_by(SmsFlashPromotionProduct.sort.asc()).offset((page - 1) * page_size).limit(page_size)
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

    # ── 前台 Portal 查询 ──

    async def list_active_portal_promotions(self) -> list[FlashPromotionResponse]:
        """前台：列出当前活跃的秒杀活动（status=1，在有效时间范围内）。"""
        from app.models.promotion.flash import SmsFlashPromotion

        now = datetime.now(UTC)
        result = await self.db.execute(
            select(SmsFlashPromotion)
            .where(
                SmsFlashPromotion.status == 1,
                SmsFlashPromotion.start_date <= now,
                SmsFlashPromotion.end_date >= now,
            )
            .order_by(SmsFlashPromotion.start_date.asc())
        )
        return [FlashPromotionResponse.model_validate(p) for p in result.scalars().all()]

    async def list_active_portal_sessions(self, promotion_id: UUID) -> list[FlashSessionResponse]:
        """前台：列出活动下进行中的场次（status=1）。"""
        from app.models.promotion.flash import SmsFlashPromotionSession

        result = await self.db.execute(
            select(SmsFlashPromotionSession)
            .where(
                SmsFlashPromotionSession.promotion_id == promotion_id,
                SmsFlashPromotionSession.status == 1,
            )
            .order_by(SmsFlashPromotionSession.start_time.asc())
        )
        return [FlashSessionResponse.model_validate(s) for s in result.scalars().all()]

    async def list_active_portal_products(self, session_id: UUID) -> list[dict]:
        """前台：列出场次下的秒杀商品，包含 flash_price 和剩余 flash_stock。

        返回 dict 列表，比 FlashProductResponse 多了 flash_stock 作为 countdown 剩余库存。
        """
        from app.models.promotion.flash import SmsFlashPromotionProduct

        result = await self.db.execute(
            select(SmsFlashPromotionProduct)
            .where(
                SmsFlashPromotionProduct.session_id == session_id,
                SmsFlashPromotionProduct.flash_stock > 0,
            )
            .order_by(SmsFlashPromotionProduct.sort.asc())
        )
        products = result.scalars().all()
        return [
            {
                "id": str(p.id),
                "session_id": str(p.session_id),
                "product_id": str(p.product_id),
                "sku_id": str(p.sku_id),
                "flash_price": float(p.flash_price),
                "flash_stock": p.flash_stock,
                "flash_limit": p.flash_limit,
                "sort": p.sort,
            }
            for p in products
        ]
