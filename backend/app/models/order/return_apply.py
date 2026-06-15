"""退货申请模型 — oms_return_applies 表

Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class OmsReturnApply(CommerceBase, AuditMixin):
    """退货申请 —— 用户提交退货后管理员审核处理。"""

    __tablename__ = "oms_return_applies"

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True, comment="关联订单ID"
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="商品ID"
    )
    order_sn: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="订单编号"
    )
    member_username: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="会员用户名"
    )
    return_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), comment="退款金额"
    )
    return_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="退货人姓名"
    )
    return_phone: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="退货人电话"
    )
    status: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, index=True,
        comment="处理状态: 0=待处理 1=已退货 2=已拒绝 3=已退款",
    )
    handle_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="处理时间"
    )
    product_pic: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="商品图片"
    )
    product_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="商品名称"
    )
    product_brand: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="商品品牌"
    )
    product_attr: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="销售属性"
    )
    product_count: Mapped[int] = mapped_column(
        Integer, default=1, comment="退货数量"
    )
    product_real_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), comment="商品实际价格"
    )
    reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="退货原因"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="问题描述"
    )
    proof_pics: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="凭证图片(逗号分隔)"
    )
    handle_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="处理备注"
    )
    handle_man: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="处理人"
    )
    receive_man: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="收货人"
    )
    receive_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="收货时间"
    )
    receive_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="收货备注"
    )
    company_address_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="公司地址ID"
    )

    def __repr__(self) -> str:
        return f"<OmsReturnApply order_sn={self.order_sn!r} status={self.status}>"
