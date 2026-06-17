"""用户行为追踪模型 — ums_member_behaviors / ums_member_search_logs 表。

为个性化推荐提供行为数据基础:
  - ums_member_behaviors: 浏览/搜索/加购/购买/收藏等事件流水
  - ums_member_search_logs: 用户搜索历史（关键词+筛选条件）

设计决策:
  - 使用 CommerceBase (UUID主键) + AuditMixin (created_at) 与现有模型一致
  - behavior_type 用字符串枚举而非外键, 方便扩展新行为类型
  - metadata JSON 字段存扩展信息 (停留时长/来源页面/设备等)
  - user_id 可为空, 支持匿名用户行为追踪 (通过 session_id 关联)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class UmsMemberBehavior(CommerceBase, AuditMixin):
    """会员行为事件表 —— 记录用户在C端的所有可观测行为。

    支持的行为类型 (behavior_type):
      - view: 浏览商品详情
      - search: 执行搜索
      - add_cart: 加入购物车
      - purchase: 完成购买
      - favorite: 收藏商品

    metadata JSON 示例:
      {"duration_ms": 3500, "source": "homepage", "device": "mobile"}
    """

    __tablename__ = "ums_member_behaviors"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="用户ID (匿名用户为空)"
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="匿名会话ID"
    )
    behavior_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True,
        comment="行为类型: view/search/add_cart/purchase/favorite"
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="关联对象ID (如product_id)"
    )
    item_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="对象类型: product/category/brand/coupon"
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, nullable=True, comment="扩展信息 (时长/来源/设备等)"
    )


class UmsMemberSearchLog(CommerceBase, AuditMixin):
    """会员搜索日志表 —— 记录用户在C端的搜索行为。

    注意: updated_at 在此表中无实际用途 (搜索日志不可修改),
    但继承 AuditMixin 保持模型一致性。
    """

    __tablename__ = "ums_member_search_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="用户ID (匿名用户为空)"
    )
    session_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="匿名会话ID"
    )
    keyword: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="搜索关键词"
    )
    filters: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="筛选条件 (category_id/brand_id/price_range等)"
    )
    result_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="搜索结果数量"
    )
