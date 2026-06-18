"""
【秒杀模型】— sms_flash_promotions / sms_flash_sessions / sms_flash_promotion_products 表

知识点速查：
  - 秒杀 = 活动(promotion) → 场次(session) → 商品(product)
    三层嵌套设计: 一个活动可有多场(如10点场/14点场)，每场有多个商品
  - 秒杀库存预热: 秒杀开始前将库存从 PmsSku 预扣到 flash_promotion_product.stock
    开始后直接从 flash_promotion_product 扣减，避免秒杀流量打到主库存表
    如果不预热: 秒杀10万QPS直接打到 pms_skus 表，主库会挂

设计决策 —— 为什么商品关联用独立表而非直接在 Product 表加字段？
  一个商品可以参加多次秒杀(不同时间段)，如果加字段需要多个冗余列
  独立关联表支持: 同一商品在不同场次有不同秒杀价格/库存

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class SmsFlashPromotion(CommerceBase, AuditMixin):
    """
    秒杀活动 —— 例如"618年中大促"。
    一个活动包含多个场次(SmsFlashPromotionSession)。
    """

    __tablename__ = "sms_flash_promotions"

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="活动标题")
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="活动开始日期")
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="活动结束日期")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="0=未开始 1=进行中 2=已结束")
    note: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="活动备注")


class SmsFlashPromotionSession(CommerceBase, AuditMixin):
    """
    秒杀场次 —— 例如活动"618大促"下的"10点场"、"14点场"。
    每场有独立的开始/结束时间。
    """

    __tablename__ = "sms_flash_sessions"

    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sms_flash_promotions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属活动ID",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="场次名称,如 10点场")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="场次开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="场次结束时间")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="0=未开始 1=进行中 2=已结束")


class SmsFlashPromotionProduct(CommerceBase):
    """
    秒杀商品关联 —— 将商品关联到秒杀场次，设置秒杀价格和库存。
    """

    __tablename__ = "sms_flash_promotion_products"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sms_flash_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="场次ID",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="商品ID",
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="SKU ID",
    )
    flash_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="秒杀价格")
    flash_stock: Mapped[int] = mapped_column(Integer, nullable=False, comment="秒杀库存")
    flash_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="每人限购数量")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
