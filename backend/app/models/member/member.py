"""
【会员模型】— ums_member_addresses / ums_member_favorites 表

知识点速查：
  - 地址管理: 用户可以有多个收货地址，下单时选择一个
  - 收藏夹: 用户可收藏商品，后续在会员中心查看
  - 为什么不用 user_profiles 的 JSON 字段存地址？
    JSON 字段无法建外键、无法高效按地址ID查询，且地址可能多笔
  - default_status: 用冗余标记位快速定位默认地址，避免每次都排序

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class UmsMemberAddress(CommerceBase, AuditMixin):
    """
    会员收货地址表 —— 一个用户可有多个地址，一个设为默认。
    """

    __tablename__ = "ums_member_addresses"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="收货人姓名")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, comment="收货人电话")
    province: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="省")
    city: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="市")
    region: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="区")
    detail_address: Mapped[str] = mapped_column(String(200), nullable=False, comment="详细地址")
    post_code: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="邮编")
    # default_status: 0=否 1=默认地址
    # 同用户只能有一个默认地址, 由 Service 层保证去重
    default_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="是否默认: 0=否 1=是")


class UmsMemberFavorite(CommerceBase):
    """
    会员收藏表 —— 用户收藏商品。
    使用 UniqueConstraint(user_id, product_id) 防止重复收藏。
    """

    __tablename__ = "ums_member_favorites"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_user_product_fav"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="商品ID",
    )
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="商品名称(冗余)",
    )
    product_pic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="商品图片(冗余)",
    )
    product_price: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="商品价格(冗余, 字符串避免Decimal序列化问题)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
