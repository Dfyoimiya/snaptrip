"""
【商品分类模型】— pms_categories 表

知识点速查：
  - adjacency_list pattern (邻接表): 用 parent_id 自引用实现树形结构
  - self-referential relationship: SQLAlchemy 中模型可以关联自己
  - lazy="selectin": 预加载策略，一次查询加载所有子分类，避免 N+1 问题

设计决策 —— 为什么用邻接表而非物化路径或嵌套集？
  1. 分类层级通常 ≤3 层，邻接表查询性能完全够用
  2. 移动节点只需改 parent_id，物化路径需要更新所有子节点路径
  3. 嵌套集写入成本高，电商分类变更频率低但偶尔需要调整
  如果不这样：用物化路径 (ltree) 查询更快但修改成本高，引入了 PostgreSQL 特有扩展

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, CommerceBase

if TYPE_CHECKING:
    # TYPE_CHECKING 块中的 import 只在静态分析时生效，运行时不会循环导入
    # 如果不这样做：Python 运行时会因为循环 import 导致 ImportError
    pass


class PmsCategory(CommerceBase, AuditMixin):
    """
    商品分类表 —— 通过 parent_id 实现无限层级树。

    树形示例:
        电子数码 (level=0, parent_id=NULL)
          ├─ 手机通讯 (level=1)
          │   ├─ 智能手机 (level=2)
          │   └─ 功能机   (level=2)
          └─ 电脑 (level=1)
    """

    __tablename__ = "pms_categories"

    # ── 核心字段 ──
    name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="分类名称",
    )
    # parent_id 允许 NULL (顶级分类) → 表设计中 NULL 是合法状态，不需要默认值
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pms_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="父分类ID，NULL 表示顶级分类",
    )
    level: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("level >= 0 AND level <= 2", name="ck_pms_categories_level_range"),
        default=0,
        nullable=False,
        comment="层级: 0=一级 1=二级 2=三级 (DB CHECK: 0-2)",
    )
    sort: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="排序值，越小越靠前",
    )
    # nav_status: 是否在导航栏显示，icon 用于前端导航图标
    type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
        comment="分类类型: PRODUCT/COMBO",
    )
    nav_status: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="是否在导航栏显示: 1=是 0=否",
    )
    show_status: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="是否显示: 1=显示 0=隐藏",
    )
    icon: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="分类图标URL",
    )
    keywords: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SEO 关键词",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="分类描述",
    )

    # ── 自引用关系 ──
    # relationship() 不写 secondary 就是普通外键关系
    # remote_side=[id] 告诉 SQLAlchemy: "parent_id 指向的是 id 列"
    # 不指定 remote_side: SQLAlchemy 会反向理解，把 parent_id 当作"被引用"的列
    parent: Mapped[PmsCategory | None] = relationship(
        "PmsCategory",
        back_populates="children",
        remote_side="PmsCategory.id",
        lazy="selectin",  # 一次 JOIN 加载，避免查每个子分类时再发 SQL
    )
    children: Mapped[list[PmsCategory]] = relationship(
        "PmsCategory",
        back_populates="parent",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PmsCategory name={self.name!r} level={self.level}>"
