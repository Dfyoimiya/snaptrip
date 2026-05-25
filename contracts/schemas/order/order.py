"""Order domain DTOs — cart, order, status."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from contracts.schemas.common import PaginationParams
from contracts.schemas.enums import OrderStatus, PayStatus


# ── Cart ──

class CartAddReq(BaseModel):
    product_id: str
    spec_value_id: str | None = None
    flavor_ids: list[str] = []
    qty: int = Field(default=1, ge=1, le=99)


class CartUpdateReq(BaseModel):
    qty: int = Field(ge=1, le=99)


class CartItemResp(BaseModel):
    item_id: str
    product_id: str
    merchant_id: str
    product_name: str
    product_image: str
    spec_text: str = ""
    flavor_text: str = ""
    price: int
    qty: int
    stock: int


# ── Order ──

class OrderItemCreateReq(BaseModel):
    cart_item_id: str | None = None
    product_id: str
    spec_value_id: str | None = None
    flavor_ids: list[str] = []
    qty: int = Field(ge=1, le=99)


class OrderCreateReq(BaseModel):
    merchant_id: str
    address_id: str
    items: list[OrderItemCreateReq]
    note: str | None = None
    coupon_id: str | None = None


class OrderListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    status: OrderStatus | None = None
    keyword: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class OrderItemResp(BaseModel):
    product_id: str
    product_name: str
    product_image: str
    spec_text: str
    flavor_text: str
    qty: int
    price: int


class OrderStatusLogResp(BaseModel):
    from_status: str | None
    to_status: str
    operator: str
    remark: str | None
    created_at: str


class OrderResp(BaseModel):
    order_id: str
    order_no: str
    merchant_id: str
    merchant_name: str
    total_price: int
    original_price: int
    status: OrderStatus
    pay_status: PayStatus
    item_count: int
    created_at: str


class OrderDetailResp(OrderResp):
    items: list[OrderItemResp] = []
    status_logs: list[OrderStatusLogResp] = []
    note: str | None = None
    contact_name: str = ""
    contact_phone: str = ""
    address_detail: str = ""


class OrderStatusFlowReq(BaseModel):
    target_status: OrderStatus
    remark: str | None = None


class CancelReq(BaseModel):
    reason: str | None = None


class OrderExportQuery(BaseModel):
    status: OrderStatus | None = None
    start_date: str | None = None
    end_date: str | None = None
