"""
【商品属性模型】— pms_product_attributes / pms_product_attribute_values 表

知识点速查：
  - EAV 模式 (Entity-Attribute-Value): 属性不写死在列中，而是存入行
    例如: "手机"分类有"屏幕尺寸/电池容量"属性，"衣服"分类有"尺码/材质"属性
  - 为什么不直接在 Product 表加列？
    每个分类的属性差异巨大，加列会导致: (a) 几百列且大部分为 NULL (b) 新增分类要改表结构
  - PmsProductAttribute: 定义"某分类下有哪些属性" (模板)
  - PmsProductAttributeValue: 记录"某个商品的属性值" (实例)

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import CommerceBase


class PmsProductAttribute(CommerceBase):
    """
    商品属性参数表 —— 定义每个商品分类下有哪些属性。
    例如: 分类"手机"下定义属性 → 屏幕尺寸、电池容量、CPU型号
    """

    __tablename__ = "pms_product_attributes"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="商品分类ID",
    )
    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="属性名称, 如 屏幕尺寸",
    )
    # type: 0=规格(影响SKU) 1=参数(纯展示)
    # 规格属性参与 SKU 生成, 如「颜色:黑色 存储:128GB」→ 一个 SKU
    # 参数属性不参与 SKU, 如「上市时间:2024年」
    attr_type: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="属性类型: 0=规格 1=参数",
    )
    # input_type: 输入类型 → 0=手动录入 1=列表单选 2=列表多选
    input_type: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="输入类型: 0=手动 1=单选 2=多选",
    )
    # input_list: 可选值列表, input_type=1/2 时使用, 逗号分隔
    input_list: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="可选值列表，逗号分隔",
    )
    sort: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="排序值",
    )
    # filter_type: 是否支持筛选 → 0=否 1=是
    filter_type: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="是否支持筛选: 0=否 1=是",
    )
    # search_type: 是否支持搜索 → 0=否 1=是
    search_type: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="是否支持搜索: 0=否 1=是",
    )
    # related_status: 是否关联(用于前端判断是否为同属性) → 0=否 1=是
    related_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="是否关联: 0=否 1=是",
    )
    # hand_add_status: 是否支持手动新增 → 0=否 1=是
    hand_add_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="是否支持手动新增: 0=否 1=是",
    )


class PmsProductAttributeValue(CommerceBase):
    """
    商品属性值表 —— 记录每个商品的具体属性值。
    例如: 商品"iPhone 15 Pro" → 屏幕尺寸:6.1英寸, CPU:A17 Pro
    """

    __tablename__ = "pms_product_attribute_values"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="商品ID",
    )
    attribute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="属性ID (关联 pms_product_attributes.id)",
    )
    # value: 属性值，如规格属性的可选值或参数属性的手动录入值
    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="属性值",
    )
