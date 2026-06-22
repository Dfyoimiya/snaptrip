"""商品评价模型 —— 用户对已购/已体验商品的星级评价与文字反馈。

知识点速查:
  - 每个用户对同一商品仅可评价一次 (UniqueConstraint)
  - 评价默认待审核 (status=0), 审核通过后前台展示
  - user_id 不加 FK 约束, 参考 UmsMemberFavorite 模式 (User 表可能在另一个 metadata 中)

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, CommerceBase, SoftDeleteMixin


class PmsProductReview(CommerceBase, AuditMixin, SoftDeleteMixin):
    """商品评价 —— 用户对商品评分+图文评价, 支持商家回复。"""

    __tablename__ = "pms_product_reviews"

    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_user_product_review"),
    )

    # ── 关联 ──
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pms_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="商品ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="关联订单ID (可选)",
    )

    # ── 评价内容 ──
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="评分: 1~5 星",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="评价文字内容",
    )
    images: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="评价图片, 逗号分隔URL",
    )
    is_anonymous: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="是否匿名评价",
    )

    # ── 状态 ──
    status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="审核状态: 0=待审核 1=通过 2=驳回",
    )

    # ── 商家回复 ──
    reply: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="商家回复内容",
    )
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="商家回复时间",
    )

    # ── 关系 ──
    product: Mapped[PmsProduct] = relationship(  # noqa: F821
        "PmsProduct",
        back_populates=None,
        lazy="selectin",
    )
