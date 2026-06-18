"""退货原因模型 — oms_return_reasons 表

Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class OmsReturnReason(CommerceBase, AuditMixin):
    """退货原因 —— 管理员配置，用户退货时选择。"""

    __tablename__ = "oms_return_reasons"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="原因名称")
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="状态: 0=禁用 1=启用")

    def __repr__(self) -> str:
        return f"<OmsReturnReason name={self.name!r}>"
