"""
【购物车模型】— oms_cart_items 表

知识点速查：
  - 购物车为何不存 Redis 而存 DB？
    用户登录/退出后购物车数据不丢失，支持多端同步(PC/App/小程序)
    如果存 Redis: 需要额外做 Redis→DB 持久化，且多端同步复杂
  - 为什么不建 Cart 主表（只有 CartItem）？
    购物车本质是"用户商品集合"，不需要 Cart 作为容器；
    CartItem 直接关联 user_id 和 product_id 即可

设计决策 —— quantity 为何存 DB 而非实时计算？
  购物车的核心操作是增/删/改数量，直接存 quantity 字段
  修改数量 = UPDATE quantity，查询 = SELECT quantity
  如果不存: 每次查询要 COUNT 用户的所有 cart_item（随商品数线性增长）

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommerceBase


class OmsCartItem(CommerceBase):
    """
    购物车条目表。
    每个用户对每个 SKU 有且仅有一条购物车记录，重复添加同类商品只更新数量。
    """

    __tablename__ = "oms_cart_items"

    # ── 用户标识 ──
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="用户ID (关联 users 表)",
    )

    # ── 商品关联 ──
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="商品SPU ID",
    )
    # product_name / product_pic: 冗余存储，避免查购物车时 JOIN product 表
    # 为什么冗余？购物车是高频查询场景，WHERE user_id + 不JOIN 是最快的
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="商品名称(冗余)",
    )
    product_pic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="商品图片(冗余)",
    )

    # ── SKU 关联 ──
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="SKU ID",
    )
    sku_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SKU编码(冗余)",
    )
    spec: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="规格描述(冗余)，如 黑色/128GB",
    )

    # ── 价格与数量 ──
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="加入时单价",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="购买数量",
    )

    # ── 勾选状态 ──
    checked: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="是否选中: 1=是 0=否",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<OmsCartItem user={self.user_id} sku={self.sku_code} qty={self.quantity}>"
