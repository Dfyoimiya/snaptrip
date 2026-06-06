"""
【优惠券模型】— sms_coupons / sms_coupon_histories 表

知识点速查：
  - 优惠券类型: 全场券(category_id=NULL)  vs  品类券(category_id 有值)
  - 优惠券使用门槛: min_amount(最低消费) 达到后才可抵扣
  - per_limit: 每人限领数量，0=不限
  - 为什么领券记录独立建表？
    管理员创建"券模板"(SmsCoupon) → 用户领取产生"券实例"(SmsCouponHistory)
    如果不用两表: 无法追溯"谁领了哪张券、何时使用、是退款还是用于下单"

设计决策 —— count/publish_count/receive_count/use_count 四个计数字段
  count: 发放总量
  publish_count: 已发放数量(领券时 +1)
  receive_count: 已领取数量
  use_count: 已使用数量
  为什么要单独存计数？COUNT(*) 在高并发下性能差，冗余汇总字段以写换读

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, CommerceBase


class SmsCoupon(CommerceBase, AuditMixin):
    """
    优惠券模板 —— 管理员创建，用户领取后生成 SmsCouponHistory。

    类型说明:
      type=0 全场券(所有商品可用)
      type=1 品类券(指定分类可用)
      type=2 品牌券(指定品牌可用)

    优惠类型:
      use_type=0 满减(满X减Y)
      use_type=1 折扣(满X打Y折)
      use_type=2 立减(无门槛减Y)
    """

    __tablename__ = "sms_coupons"

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="优惠券名称")
    type: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="类型: 0=全场 1=品类 2=品牌")
    use_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="优惠类型: 0=满减 1=折扣 2=立减")
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="优惠金额(满减/立减时) 或 折扣率(折扣时)"
    )
    min_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False, comment="使用门槛最低消费"
    )
    # 分类/品牌券的关联ID (全场券为 NULL)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="品类券关联分类ID")
    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="品牌券关联品牌ID")

    # 总量与领取
    count: Mapped[int] = mapped_column(Integer, nullable=False, comment="发放总量")
    publish_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="已发放数量(领券时+1)")
    receive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="已领取数量")
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="已使用数量")
    per_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="每人限领数量, 0=不限")

    # 有效期
    start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="有效期开始(NUL=领取时计算)"
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="有效期结束")

    # 启用状态
    status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="状态: 0=禁用 1=启用")

    # 领取规则
    member_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="可领取会员等级: 0=不限")
    note: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="优惠券说明")


class SmsCouponHistory(CommerceBase):
    """
    优惠券领取/使用记录 —— 每个用户领取一张券生成一条记录。

    状态流: 0=未使用 → 1=已使用 → 2=已过期
    """

    __tablename__ = "sms_coupon_histories"

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sms_coupons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="优惠券ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, comment="用户ID")

    # 冗余快照(优惠券可能被修改，历史记录保留领取时的信息)
    coupon_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="优惠券名称(快照)")
    coupon_type: Mapped[int] = mapped_column(Integer, nullable=False)
    coupon_use_type: Mapped[int] = mapped_column(Integer, nullable=False)
    coupon_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    coupon_min_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # 使用状态
    use_status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="0=未使用 1=已使用 2=已过期")
    use_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="使用时间")
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, comment="关联订单ID")
    order_sn: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联订单编号")

    # 领取时间
    receive_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="领取时间")
    expire_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="过期时间")
