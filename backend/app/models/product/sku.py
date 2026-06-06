"""
【SKU 库存模型】— pms_skus 表

知识点速查：
  - SKU = Stock Keeping Unit (库存量单位)，是商品的可购买最小单元
    例如: iPhone 15 (SPU) → 128GB 黑色 (SKU) / 256GB 白色 (SKU)
  - SPU = Standard Product Unit，对应 pms_products 表
  - 为什么要拆 SPU 和 SKU？同一商品不同规格的价格/库存/图片都可能不同
    如果不分拆: 一个商品表搞定一切，会导致大量冗余字段和库存管理混乱
  - Decimal vs Float: 金额必须用 Numeric/Decimal，Float 有精度问题
    如果不这样: 1.03 - 0.42 用 Float 可能得到 0.6100000000000001，财务对账会出错

设计决策 —— lock_stock 字段的作用？
  锁库存 = 用户下单但未付款时预占的数量，防止超卖
  实际可用库存 = stock - lock_stock
  如果不设锁库存: 高并发下可能出现 100 件库存被 200 人下单成功

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommerceBase


class PmsSku(CommerceBase):
    """
    SKU 表 —— 与 Product 一对多。
    一个商品 (SPU) 可以有多个 SKU (不同颜色/尺码/套餐)。
    """

    __tablename__ = "pms_skus"

    # ── 关联字段 ──
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pms_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="商品ID (关联 pms_products.id)",
    )
    # ── SKU 规格描述 ──
    sku_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SKU 编码, 如 IP15-BLK-128",
    )
    spec: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="规格 JSON 字符串, 如 {\"color\":\"黑色\",\"storage\":\"128GB\"}",
    )

    # ── 价格与库存 (金额类字段必须用 Numeric 而非 Float) ──
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),  # 总共10位, 小数2位 → 最大 99999999.99
        nullable=False,
        comment="售价",
    )
    promotion_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="促销价 (NULL 表示无促销)",
    )
    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="库存数量",
    )
    low_stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="预警库存 (低于此值触发补货提醒)",
    )
    lock_stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="锁定库存 (已下单未付款预占)",
    )

    # ── 图片 ──
    pic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SKU 图片 (不同规格可能有不同图片)",
    )

    # ── 销售数据 ──
    sale_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="销量 (用于排序和展示)",
    )

    def __repr__(self) -> str:
        return f"<PmsSku code={self.sku_code!r} price={self.price}>"
