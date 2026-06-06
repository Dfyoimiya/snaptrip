"""
【营销域 Pydantic Schema】— 优惠券 + 秒杀 请求/响应模型

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# ============================================================================
#  优惠券 Schema
# ============================================================================

class CouponCreate(BaseModel):
    """创建优惠券模板"""
    name: str = Field(..., min_length=1, max_length=100)
    type: int = Field(default=0, ge=0, le=2, description="0=全场 1=品类 2=品牌")
    use_type: int = Field(default=0, ge=0, le=2, description="0=满减 1=折扣 2=立减")
    amount: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    min_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    category_id: UUID | None = None
    brand_id: UUID | None = None
    count: int = Field(..., ge=1, description="发放总量")
    per_limit: int = Field(default=1, ge=0, description="每人限领,0=不限")
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: int = Field(default=1, ge=0, le=1)
    member_level: int = Field(default=0, ge=0)
    note: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("开始时间必须早于结束时间")
        return self


class CouponUpdate(BaseModel):
    """编辑优惠券 —— 全字段可选"""
    name: str | None = Field(None, min_length=1, max_length=100)
    type: int | None = Field(None, ge=0, le=2)
    use_type: int | None = Field(None, ge=0, le=2)
    amount: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    min_amount: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    count: int | None = Field(None, ge=1)
    per_limit: int | None = Field(None, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: int | None = Field(None, ge=0, le=1)
    note: str | None = Field(None, max_length=200)


class CouponResponse(BaseModel):
    """优惠券模板详情"""
    id: UUID
    name: str
    type: int
    use_type: int
    amount: Decimal
    min_amount: Decimal
    category_id: UUID | None = None
    brand_id: UUID | None = None
    count: int
    publish_count: int
    receive_count: int
    use_count: int
    per_limit: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: int
    note: str | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class CouponHistoryResponse(BaseModel):
    """领券/使用记录"""
    id: UUID
    coupon_id: UUID
    user_id: UUID
    coupon_name: str
    coupon_amount: Decimal
    coupon_min_amount: Decimal
    use_status: int
    use_time: datetime | None = None
    order_id: UUID | None = None
    order_sn: str | None = None
    receive_time: datetime
    expire_time: datetime
    model_config = {"from_attributes": True}


# ============================================================================
#  秒杀 Schema
# ============================================================================

class FlashPromotionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    start_date: datetime
    end_date: datetime
    note: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date >= self.end_date:
            raise ValueError("活动开始日期必须早于结束日期")
        return self


class FlashPromotionUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: int | None = Field(None, ge=0, le=2)
    note: str | None = Field(None, max_length=500)


class FlashPromotionResponse(BaseModel):
    id: UUID
    title: str
    start_date: datetime
    end_date: datetime
    status: int
    note: str | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class FlashSessionCreate(BaseModel):
    promotion_id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=100)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("场次开始时间必须早于结束时间")
        return self


class FlashSessionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    start_time: datetime | None = None
    end_time: datetime | None = None


class FlashSessionResponse(BaseModel):
    id: UUID
    promotion_id: UUID
    name: str
    start_time: datetime
    end_time: datetime
    status: int
    model_config = {"from_attributes": True}


class FlashProductCreate(BaseModel):
    session_id: UUID = Field(...)
    product_id: UUID = Field(...)
    sku_id: UUID = Field(...)
    flash_price: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2)
    flash_stock: int = Field(..., ge=1, description="秒杀库存")
    flash_limit: int = Field(default=1, ge=1)
    sort: int = Field(default=0, ge=0)


class FlashProductResponse(BaseModel):
    id: UUID
    session_id: UUID
    product_id: UUID
    sku_id: UUID
    flash_price: Decimal
    flash_stock: int
    flash_limit: int
    sort: int
    model_config = {"from_attributes": True}
