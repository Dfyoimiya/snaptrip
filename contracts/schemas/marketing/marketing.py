"""Marketing domain DTOs — banner, coupon, notice."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BannerResp(BaseModel):
    id: str
    image_url: str
    link_type: str  # "product", "merchant", "url", "none"
    link_id: str | None = None
    sort_order: int = 0
    status: str  # "ACTIVE", "INACTIVE"


class BannerCreateReq(BaseModel):
    image_url: str
    link_type: str = "none"
    link_id: str | None = None
    sort_order: int = 0


class BannerUpdateReq(BaseModel):
    image_url: str | None = None
    link_type: str | None = None
    link_id: str | None = None
    sort_order: int | None = None
    status: str | None = None


class NoticeResp(BaseModel):
    id: str
    title: str
    content: str
    target_type: str  # "ALL", "CUSTOMER", "MERCHANT"
    status: str
    created_at: str


class NoticeCreateReq(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=5000)
    target_type: str = "ALL"


class CouponResp(BaseModel):
    id: str
    name: str
    discount_amount: int  # 分
    threshold_amount: int  # 分, 0=无门槛
    total_count: int
    claimed_count: int
    start_date: str
    end_date: str
    status: str


class CouponCreateReq(BaseModel):
    name: str
    discount_amount: int = Field(ge=1)
    threshold_amount: int = Field(default=0, ge=0)
    total_count: int = Field(ge=1)
    start_date: str
    end_date: str
