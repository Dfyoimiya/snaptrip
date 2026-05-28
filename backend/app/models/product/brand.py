"""
【商品品牌模型】— pms_brands 表

知识点速查：
  - SQLAlchemy 2.0 Mapped 类型: str | None 表示可为 NULL 的列
  - String vs Text: String 用于有限长度, Text 用于大文本(无长度限制)
  - index=True: 为列创建 B-Tree 索引, 加速 WHERE/ORDER BY 查询

设计决策 —— 为什么品牌不关联分类？
  brand 和 category 是多对多关系，通过 pms_product 间接关联
  每个商品有 brand_id 和 category_id，查询 "品牌 A 下的所有分类" 通过 product 聚合即可
  如果直接建多对多中间表: 维护成本高 (新品上线需同时维护中间表)，实际查询场景极少

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class PmsBrand(CommerceBase, AuditMixin):
    """
    商品品牌表。
    品牌独立于分类存在，通过商品的 brand_id 字段与商品关联。
    """

    __tablename__ = "pms_brands"

    # ── 核心字段 ──
    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="品牌名称",
    )
    # first_letter: 按首字母分组检索 (A-Z)，前端常做字母索引导航
    first_letter: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        comment="品牌首字母",
    )
    sort: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="排序值",
    )
    # factory_status: mall 中表示"是否为品牌制造商" → 1 代表品牌直营可选
    factory_status: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="品牌制造商状态: 1=是 0=否",
    )
    show_status: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="显示状态: 1=显示 0=隐藏",
    )

    # ── 媒体与描述 ──
    logo: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="品牌Logo URL",
    )
    big_pic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="品牌专区大图",
    )
    brand_story: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="品牌故事",
    )

    def __repr__(self) -> str:
        return f"<PmsBrand name={self.name!r}>"
