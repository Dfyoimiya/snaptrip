"""
【订单模型】— oms_orders / oms_order_items / oms_order_operate_logs 表

知识点速查：
  - 订单状态机: 待付款→已付款→已发货→已收货→已完成 (正向)
                待付款→已关闭 (取消) / 已付款→退款中→已退款 (逆向)
  - 为什么要拆 Order 和 OrderItem？
    一个订单包含多个商品 (如 iPhone + AirPods)，每个商品独立记录
    如果塞进一张表: 重复存储收货地址/支付信息，违背数据库范式
  - 操作日志 (OrderOperateLog): 记录订单每个状态变更的操作人、时间、备注
    如果不记录: 出问题时无法追溯是谁关闭的订单、何时修改的价格

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditMixin, CommerceBase

# ============================================================================
#  订单主表
# ============================================================================

class OmsOrder(CommerceBase, AuditMixin):
    """
    订单表 —— 一个订单对应一个用户、一个收货地址。

    关系:
      OmsOrder 1 ── N OmsOrderItem (订单商品明细)
      OmsOrder 1 ── N OmsOrderOperateLog (操作日志)

    状态机:
      PENDING_PAYMENT (待付款)
        ├──→ PAID (已付款) ──→ DELIVERED (已发货) ──→ RECEIVED (已收货) ──→ COMPLETED (已完成)
        └──→ CLOSED (已关闭)

      PAID → REFUNDING (退款中) → REFUNDED (已退款)
    """

    __tablename__ = "oms_orders"

    # ── 订单编号 (对外展示) ──
    order_sn: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="订单编号，如 202605261530001234",
    )

    # ── 用户 ──
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="用户ID",
    )
    member_username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="用户名(冗余，方便后台展示)",
    )

    # ── 金额 ──
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="订单总金额(商品总价)",
    )
    pay_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="实付金额(= total_amount - discount + freight)",
    )
    freight_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="运费",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="优惠金额(促销/优惠券)",
    )
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="使用的优惠券ID",
    )

    # ── 支付 ──
    pay_type: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="支付方式: 0=未支付 1=微信 2=支付宝",
    )
    payment_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="支付时间",
    )
    pay_order_sn: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="支付流水号(第三方返回)",
    )

    # ── 物流 ──
    delivery_company: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="物流公司",
    )
    delivery_sn: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="物流单号",
    )
    delivery_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="发货时间",
    )

    # ── 收货信息 (订单快照——下单后地址不可变) ──
    # 为什么不直接用用户地址表 ID 关联？
    # 用户可能删除旧地址，但订单必须保留历史收货信息
    # 所以订单一创建就把地址拍平存储
    receiver_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="收货人姓名",
    )
    receiver_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="收货人电话",
    )
    receiver_province: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="省",
    )
    receiver_city: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="市",
    )
    receiver_region: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="区",
    )
    receiver_detail_address: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="详细地址",
    )
    receiver_post_code: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="邮编",
    )

    # ── 状态 ──
    # status: 订单状态——状态机的核心字段
    # 0=待付款 1=已付款 2=已发货 3=已收货 4=已完成 5=已关闭 6=退款中 7=已退款
    status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
        comment="订单状态: 0=待付款 1=已付款 2=已发货 3=已收货 4=已完成 5=已关闭 6=退款中 7=已退款",
    )
    auto_confirm_day: Mapped[int] = mapped_column(
        Integer,
        default=15,
        nullable=False,
        comment="自动确认收货天数(发货后N天自动确认)",
    )
    confirm_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="确认收货状态: 0=未确认 1=已确认",
    )
    delete_status: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="删除状态: 0=未删除 1=已删除(用户删除,逻辑删除)",
    )

    # ── 备注 ──
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="订单备注(用户填写)",
    )
    admin_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="管理员备注",
    )

    # ── 关联 ──
    items: Mapped[list[OmsOrderItem]] = relationship(
        "OmsOrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",  # 删除订单时级联删除明细
    )

    def __repr__(self) -> str:
        return f"<OmsOrder sn={self.order_sn} status={self.status}>"


# ============================================================================
#  订单商品明细
# ============================================================================

class OmsOrderItem(CommerceBase):
    """
    订单商品明细 —— 订单中每个 SKU 对应一条记录。

    为什么冗余 product_name/sku_code 而非 JOIN？
    下单后商品可能改名/下架，但订单需要保留交易当时的商品信息（订单快照）
    """

    __tablename__ = "oms_order_items"

    # ── 关联 ──
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("oms_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="订单ID",
    )
    order_sn: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="订单编号(冗余, 方便查询)",
    )

    # ── 商品快照 ──
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="商品SPU ID",
    )
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="商品名称(快照)",
    )
    product_pic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="商品图片(快照)",
    )

    # ── SKU 快照 ──
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="SKU ID",
    )
    sku_code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SKU编码(快照)",
    )
    spec: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="规格描述(快照)",
    )

    # ── 价格 ──
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="成交单价",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="购买数量",
    )

    # ── 关联 ──
    order: Mapped[OmsOrder] = relationship("OmsOrder", back_populates="items")

    def __repr__(self) -> str:
        return f"<OmsOrderItem sku={self.sku_code} qty={self.quantity}>"


# ============================================================================
#  操作日志
# ============================================================================

class OmsOrderOperateLog(CommerceBase):
    """
    订单操作日志 —— 记录订单每个状态变更的操作。

    为什么单独建表而非在 Order 表加 JSON 字段？
    JSON 字段可以做审计，但:
      1. 不支持高效按时间/操作人查询
      2. 日志量可能很大 (一个订单可能有 10+ 次操作)，JSON 字段膨胀
      3. 独立表支持按操作人索引 → "查管理员 A 今天关闭了多少订单" 只需一次索引扫描
    """

    __tablename__ = "oms_order_operate_logs"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="订单ID",
    )
    operate_man: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="操作人: 用户名/系统",
    )
    order_status_before: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="操作前状态",
    )
    order_status_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="操作后状态",
    )
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="操作备注",
    )

    def __repr__(self) -> str:
        return f"<OmsOrderOperateLog order={self.order_id} {self.order_status_before}→{self.order_status_after}>"
