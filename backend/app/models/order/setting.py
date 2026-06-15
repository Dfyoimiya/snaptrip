"""订单设置模型 — oms_order_settings 表

存储订单超时等全局配置，单行数据（id=固定值）。
Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class OmsOrderSetting(CommerceBase, AuditMixin):
    """订单全局设置 —— 单行配置表。"""

    __tablename__ = "oms_order_settings"

    flash_order_overtime: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False,
        comment="秒杀订单超时(分钟)",
    )
    normal_order_overtime: Mapped[int] = mapped_column(
        Integer, default=120, nullable=False,
        comment="普通订单超时(分钟)",
    )
    confirm_overtime: Mapped[int] = mapped_column(
        Integer, default=15, nullable=False,
        comment="发货后自动确认收货(天)",
    )
    finish_overtime: Mapped[int] = mapped_column(
        Integer, default=7, nullable=False,
        comment="交易完成后关闭(天)",
    )
    comment_overtime: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False,
        comment="完成评价期限(天)",
    )

    def __repr__(self) -> str:
        return f"<OmsOrderSetting id={self.id}>"
