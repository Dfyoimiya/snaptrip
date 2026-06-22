"""商品评价 Service —— 评价 CRUD + 审核/回复。

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product.review import PmsProductReview
from app.schemas.review import ReviewCreate, ReviewListQuery, ReviewUpdate


class ReviewService:
    """商品评价服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 去重检查 ──

    async def get_by_user_and_product(self, user_id: uuid.UUID, product_id: uuid.UUID) -> PmsProductReview | None:
        """检查用户是否已评价过该商品（含待审核/已删除）。"""
        result = await self.db.execute(
            select(PmsProductReview).where(
                PmsProductReview.user_id == user_id,
                PmsProductReview.product_id == product_id,
                PmsProductReview.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    # ── 创建 ──

    async def create(self, user_id: uuid.UUID, data: ReviewCreate) -> PmsProductReview:
        """创建评价, 默认待审核。"""
        review = PmsProductReview(
            product_id=data.product_id,
            user_id=user_id,
            order_id=data.order_id,
            rating=data.rating,
            content=data.content,
            images=data.images,
            is_anonymous=data.is_anonymous,
            status=0,
        )
        self.db.add(review)
        await self.db.flush()
        return review

    # ── 查询 ──

    async def get_by_id(self, review_id: uuid.UUID) -> PmsProductReview | None:
        result = await self.db.execute(
            select(PmsProductReview).where(
                PmsProductReview.id == review_id,
                PmsProductReview.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_reviews(
        self, query: ReviewListQuery, viewer_user_id: uuid.UUID | None = None
    ) -> tuple[list[PmsProductReview], int]:
        """分页查询评价列表, 支持按商品/评分/状态筛选。

        当 viewer_user_id 提供时, 除已通过(status=1)的评价外, 还会包含该用户
        自己待审核(status=0)和已驳回(status=2)的评价, 确保用户提交后能看到自己的评价。
        """
        conditions = [PmsProductReview.is_deleted == False]  # noqa: E712

        if query.product_id is not None:
            conditions.append(PmsProductReview.product_id == query.product_id)
        if query.rating is not None:
            conditions.append(PmsProductReview.rating == query.rating)
        if query.status is not None and viewer_user_id is not None:
            # 公开已通过 + 用户自己的待审核/驳回
            conditions.append(
                (PmsProductReview.status == query.status)
                | (
                    PmsProductReview.status.in_([0, 2])
                    & (PmsProductReview.user_id == viewer_user_id)
                )
            )
        elif query.status is not None:
            conditions.append(PmsProductReview.status == query.status)

        count_q = select(func.count()).select_from(PmsProductReview).where(*conditions)
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        items_q = (
            select(PmsProductReview)
            .where(*conditions)
            .order_by(PmsProductReview.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        items_result = await self.db.execute(items_q)
        items = list(items_result.scalars().all())

        return items, total

    # ── 更新 ──

    async def update(
        self, review_id: uuid.UUID, user_id: uuid.UUID, data: ReviewUpdate
    ) -> PmsProductReview | None:
        """修改评价 (仅作者可改), 修改后重置为待审核。"""
        review = await self.get_by_id(review_id)
        if review is None or review.user_id != user_id:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)
        review.status = 0  # 重新审核

        await self.db.flush()
        return review

    # ── 删除 ──

    async def delete(self, review_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """软删除评价 (仅作者可删)。"""
        review = await self.get_by_id(review_id)
        if review is None or review.user_id != user_id:
            return False
        review.is_deleted = True
        await self.db.flush()
        return True

    # ── 管理员操作 ──

    async def approve(self, review_id: uuid.UUID) -> PmsProductReview | None:
        """审核通过。"""
        review = await self.get_by_id(review_id)
        if review is None:
            return None
        review.status = 1
        await self.db.flush()
        return review

    async def reject(self, review_id: uuid.UUID) -> PmsProductReview | None:
        """驳回评价。"""
        review = await self.get_by_id(review_id)
        if review is None:
            return None
        review.status = 2
        await self.db.flush()
        return review

    async def reply(
        self, review_id: uuid.UUID, reply_text: str
    ) -> PmsProductReview | None:
        """商家回复评价。"""
        review = await self.get_by_id(review_id)
        if review is None:
            return None
        review.reply = reply_text
        review.replied_at = datetime.now(UTC)
        await self.db.flush()
        return review
