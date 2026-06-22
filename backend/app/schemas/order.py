"""
【订单域 Pydantic Schema】— 购物车 + 订单 请求/响应模型

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
#  购物车 Schema
# ============================================================================


class CartItemCreate(BaseModel):
    """加入购物车 —— 需要 product_id + sku_id + quantity"""

    product_id: UUID = Field(..., description="商品SPU ID")
    sku_id: UUID = Field(..., description="SKU ID")
    quantity: int = Field(default=1, ge=1, le=999, description="购买数量")


class CartItemUpdate(BaseModel):
    """修改购物车条目 —— quantity 或 checked"""

    quantity: int | None = Field(None, ge=1, le=999)
    checked: int | None = Field(None, ge=0, le=1)


class CartItemResponse(BaseModel):
    """购物车条目响应"""

    id: UUID
    product_id: UUID
    product_name: str
    product_pic: str | None = None
    sku_id: UUID
    sku_code: str
    spec: str
    price: Decimal
    quantity: int
    checked: int

    model_config = {"from_attributes": True}


# ============================================================================
#  订单状态常量
# ============================================================================


class OrderStatus:
    """订单状态枚举 (用常量类而非 IntEnum，因为需要跨层复用)"""

    PENDING_PAYMENT = 0  # 待付款
    PAID = 1  # 已付款
    DELIVERED = 2  # 已发货
    RECEIVED = 3  # 已收货
    COMPLETED = 4  # 已完成
    CLOSED = 5  # 已关闭
    REFUNDING = 6  # 退款中
    REFUNDED = 7  # 已退款


# 合法的状态转换映射 —— 状态机白名单
# key=当前状态, value=允许转换到的状态列表
STATUS_TRANSITIONS: dict[int, list[int]] = {
    OrderStatus.PENDING_PAYMENT: [OrderStatus.PAID, OrderStatus.CLOSED],
    OrderStatus.PAID: [OrderStatus.DELIVERED, OrderStatus.REFUNDING],
    OrderStatus.DELIVERED: [OrderStatus.RECEIVED],
    OrderStatus.RECEIVED: [OrderStatus.COMPLETED],
    OrderStatus.REFUNDING: [OrderStatus.REFUNDED, OrderStatus.CLOSED],
}


# ============================================================================
#  订单 Schema
# ============================================================================


class OrderItemResponse(BaseModel):
    """订单商品明细"""

    id: UUID
    product_id: UUID
    product_name: str
    product_pic: str | None = None
    spec: str
    sku_id: UUID
    sku_code: str
    price: Decimal
    quantity: int

    model_config = {"from_attributes": True}


class _OrderAddressMixin(BaseModel):
    """订单收货地址 + 支付公用字段 (OrderCreateFromCart / OrderCreateDirect 共用)"""

    receiver_name: str = Field(..., min_length=1, max_length=100)
    receiver_phone: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="收货人手机号",
    )
    receiver_province: str | None = Field(None, max_length=32)
    receiver_city: str | None = Field(None, max_length=32)
    receiver_region: str | None = Field(None, max_length=32)
    receiver_detail_address: str = Field(..., min_length=1, max_length=200)
    receiver_post_code: str | None = Field(None, max_length=16)
    note: str | None = Field(None, max_length=500)
    pay_type: int = Field(default=1, ge=0, le=2, description="支付方式: 0=未选 1=微信 2=支付宝")
    coupon_id: UUID | None = None


class OrderCreateFromCart(_OrderAddressMixin):
    """从购物车提交订单 —— 需要收货地址 + 勾选的购物车项ID列表"""

    cart_item_ids: list[UUID] = Field(..., min_length=1, max_length=50, description="勾选的购物车项ID")


class OrderCreateDirect(_OrderAddressMixin):
    """直接购买 (跳过购物车) —— 需要 product_id + sku_id + quantity"""

    product_id: UUID = Field(..., description="商品SPU ID")
    sku_id: UUID = Field(..., description="SKU ID")
    quantity: int = Field(default=1, ge=1, le=999, description="购买数量")


class OrderResponse(BaseModel):
    """订单列表/详情响应"""

    id: UUID
    order_sn: str
    user_id: UUID
    member_username: str
    total_amount: Decimal
    pay_amount: Decimal
    freight_amount: Decimal
    discount_amount: Decimal
    pay_type: int
    payment_time: datetime | None = None
    delivery_company: str | None = None
    delivery_sn: str | None = None
    delivery_time: datetime | None = None
    receiver_name: str
    receiver_phone: str
    receiver_province: str | None = None
    receiver_city: str | None = None
    receiver_region: str | None = None
    receiver_detail_address: str
    receiver_post_code: str | None = None
    status: int
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[OrderItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrderOperateLogResponse(BaseModel):
    """订单操作日志响应"""

    id: UUID
    operate_man: str = Field(validation_alias="operate_man")
    order_status_before: int | None = None
    order_status_after: int
    note: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    """订单详情 —— 含操作日志"""

    logs: list[OrderOperateLogResponse] = Field(default_factory=list)


class OrderListQuery(BaseModel):
    """订单列表筛选条件 (管理后台)"""

    order_sn: str | None = Field(None, max_length=64)
    status: int | None = Field(None, ge=0, le=7)
    start_time: datetime | None = None
    end_time: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class OrderDeliveryRequest(BaseModel):
    """发货请求"""

    delivery_company: str = Field(..., min_length=1, max_length=64, validation_alias="deliveryCompany")
    delivery_sn: str = Field(..., min_length=1, max_length=64, validation_alias="deliverySn")


class OrderPriceModifyRequest(BaseModel):
    """修改订单金额"""

    freight_amount: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    discount_amount: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
