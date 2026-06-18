"""
【公告/通知模型】— cms_notices 表

Author: SnapTrip Team
Date: 2026-06-18
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase, SoftDeleteMixin


class CmsNotice(CommerceBase, AuditMixin, SoftDeleteMixin):
    """
    公告/通知 —— 支持定向推送（全体/C端/B端）。

    target_type:
      - ALL: 所有用户可见
      - CUSTOMER: 仅前台用户可见
      - MERCHANT: 仅后台管理员可见

    status:
      - 0: 隐藏（草稿或已下架）
      - 1: 已发布
    """

    __tablename__ = "cms_notices"

    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="公告标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="公告内容（富文本HTML）")
    target_type: Mapped[str] = mapped_column(
        String(20), default="ALL", nullable=False, comment="目标类型: ALL/CUSTOMER/MERCHANT"
    )
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="0=隐藏 1=已发布")
    publish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="发布时间")
