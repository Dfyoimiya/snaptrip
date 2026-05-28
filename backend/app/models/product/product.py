"""
【商品 SPU 模型】— pms_products 表

知识点速查：
  - SPU (Standard Product Unit): 标准化产品单元，如 "iPhone 15 Pro"
  - SKU (Stock Keeping Unit): 库存量单位，如 "iPhone 15 Pro 256GB 原色钛金属"
  - 一对多关系: 一个 Product 有多个 Sku
  - relationship + back_populates: 双向关联，ORM 自动维护两端引用
  - 为什么不把所有字段塞进一张表？宽表维护困难、索引效率低、大量NULL浪费空间
  - JSON vs JSONB: JSON 存原始文本(慢), JSONB 存解析后的二进制(快、支持索引)
    这里用 String 存 JSON 字符串是因为不需要在 DB 层做 JSON 查询

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, CommerceBase, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.product.sku import PmsSku


class PmsProduct(CommerceBase, AuditMixin, SoftDeleteMixin):
    """
    商品 SPU 表 —— 与 SKU 一对多、与品牌多对一、与分类多对一。

    关系图:
      PmsBrand (1) ──< (N) PmsProduct (1) >── (N) PmsSku
      PmsCategory (1) ──< (N) PmsProduct
    """

    __tablename__ = "pms_products"

    # ===========================================================================
    #  基本字段
    # ===========================================================================

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="商品名称",
    )
    # sub_title: 商品副标题/卖点，如「A17 Pro 芯片 | 钛金属设计」
    sub_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="商品副标题/卖点",
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="品牌ID",
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="分类ID",
    )
    # product_sn: 商品货号，用于 ERP/WMS 系统对接
    product_sn: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        comment="商品货号",
    )

    # ===========================================================================
    #  价格 (SPU 级价格是 SKU 的最低/默认价)
    # ===========================================================================
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="商品售价 (SKU最低价或默认价)",
    )
    original_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="原价/市场价 (用于划线价展示)",
    )
    promotion_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="促销价",
    )
    # promotion 的时间范围约束
    promotion_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="促销开始时间",
    )
    promotion_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="促销结束时间",
    )
    # promotion_per_limit: 每人限购数量 (0=不限购)
    promotion_per_limit: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="每人限购数量，0=不限",
    )
    # promotion_type: 促销类型 → 0=无 1=限时特惠 2=会员价 3=满减 4=阶梯价
    promotion_type: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="促销类型: 0=无 1=限时 2=会员 3=满减 4=阶梯",
    )

    # ===========================================================================
    #  库存与销量
    # ===========================================================================
    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="总库存 (SKU 库存汇总)",
    )
    sale_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="总销量",
    )

    # ===========================================================================
    #  图片 (逗号分隔的URL列表，相册形式)
    # ===========================================================================
    # 为什么用逗号分隔字符串而非 JSON 数组？
    # 前端表单通常是 <input multiple> 传逗号分隔字符串，这样存储最简单
    # 如果需要单个图片操作，应该建独立的 product_images 表
    pics: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="商品图片列表，逗号分隔的URL",
    )
    album_pics: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="画册图片，逗号分隔的URL",
    )
    # 首图 (用于列表展示, 主搜索图)
    default_pic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="默认首图URL",
    )

    # ===========================================================================
    #  描述与规格
    # ===========================================================================
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="商品描述 (富文本HTML)",
    )
    keywords: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SEO 关键词",
    )
    unit: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="计量单位: 件/箱/盒/kg",
    )
    # 重量 (g) / 体积 用于物流计算
    weight: Mapped[float | None] = mapped_column(
        nullable=True,
        comment="重量(克), 用于物流计费",
    )

    # ===========================================================================
    #  状态控制
    # ===========================================================================
    publish_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="上架状态: 0=下架 1=上架",
    )
    new_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="新品状态: 0=否 1=是",
    )
    recommend_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="推荐状态: 0=否 1=是",
    )
    preview_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="预告状态: 0=否 1=是",
    )
    verify_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="审核状态: 0=待审核 1=通过 2=驳回",
    )

    # ===========================================================================
    #  服务保证 (逗号分隔，如 "七天退换,正品保证")
    # ===========================================================================
    service_ids: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="服务保障ID列表,逗号分隔",
    )

    # ===========================================================================
    #  运费模板
    # ===========================================================================
    feight_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="运费模板ID",
    )

    # ===========================================================================
    #  关系
    # ===========================================================================
    # 为什么要用 relationship 而非每次都手动 JOIN?
    # relationship 声明后，可以通过 product.skus 直接访问，ORM 自动生成子查询
    # 如果不这样做: 每次查商品都要手动写 select(Sku).where(Sku.product_id==...)
    skus: Mapped[list[PmsSku]] = relationship(
        "PmsSku",
        back_populates=None,  # SKU 方不需要回引 Product，减少循环引用风险
        lazy="selectin",  # 一次 JOIN 加载所有 SKU，避免 N+1
        order_by="PmsSku.sale_count.desc()",  # 按销量降序，热销规格优先展示
    )

    def __repr__(self) -> str:
        return f"<PmsProduct name={self.name!r} price={self.price}>"
