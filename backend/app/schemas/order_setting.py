"""
【订单设置 / 退货原因 / 退货申请 Pydantic Schema】

Author: SnapTrip Team
Date: 2026-06-15
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
#  订单设置 Schema
# ============================================================================

class OrderSettingResponse(BaseModel):
    """订单设置响应"""
    id: UUID | str
    flash_order_overtime: int
    normal_order_overtime: int
    confirm_overtime: int
    finish_overtime: int
    comment_overtime: int

    model_config = {"from_attributes": True}


class OrderSettingUpdate(BaseModel):
    """更新订单设置 —— 所有字段可选"""
    flash_order_overtime: int | None = Field(None, ge=1)
    normal_order_overtime: int | None = Field(None, ge=1)
    confirm_overtime: int | None = Field(None, ge=1)
    finish_overtime: int | None = Field(None, ge=1)
    comment_overtime: int | None = Field(None, ge=1)


# ============================================================================
#  退货原因 Schema
# ============================================================================

class ReturnReasonCreate(BaseModel):
    """创建退货原因"""
    name: str = Field(..., min_length=1, max_length=100, description="原因名称")
    sort: int = Field(default=0, ge=0, description="排序")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0=禁用 1=启用")


class ReturnReasonUpdate(BaseModel):
    """更新退货原因 —— 所有字段可选"""
    name: str | None = Field(None, min_length=1, max_length=100)
    sort: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)


class ReturnReasonResponse(BaseModel):
    """退货原因响应"""
    id: UUID | str
    name: str
    sort: int
    status: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============================================================================
#  退货申请 Schema
# ============================================================================

class ReturnApplyResponse(BaseModel):
    """退货申请响应"""
    id: UUID | str
    order_id: UUID | None = None
    product_id: UUID | str | None = None
    order_sn: str | None = None
    member_username: str | None = None
    return_amount: Decimal | float
    return_name: str | None = None
    return_phone: str | None = None
    status: int
    handle_time: datetime | None = None
    product_pic: str | None = None
    product_name: str | None = None
    product_brand: str | None = None
    product_attr: str | None = None
    product_count: int
    product_real_price: Decimal | float
    reason: str | None = None
    description: str | None = None
    proof_pics: str | None = None
    handle_note: str | None = None
    handle_man: str | None = None
    receive_man: str | None = None
    receive_time: datetime | None = None
    receive_note: str | None = None
    company_address_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReturnApplyUpdateStatus(BaseModel):
    """更新退货申请状态"""
    status: int = Field(..., ge=0, le=3, description="处理状态: 0=待处理 1=已退货 2=已拒绝 3=已退款")
    handle_note: str | None = Field(None, max_length=1000, description="处理备注")
    handle_man: str | None = Field(None, max_length=100, description="处理人")
    receive_man: str | None = Field(None, max_length=100, description="收货人")
    receive_note: str | None = Field(None, max_length=1000, description="收货备注")
    return_amount: Decimal | float | None = Field(None, description="退款金额")
    company_address_id: int | None = Field(None, description="公司地址ID")
