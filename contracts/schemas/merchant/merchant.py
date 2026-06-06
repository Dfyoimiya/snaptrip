"""Merchant domain DTOs — list, detail, category."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from contracts.schemas.common import GeoPoint, PaginationParams, SortOption
from contracts.schemas.enums import AuditStatus, MerchantStatus


class MerchantListQuery(BaseModel):
    """Composite query: combine pagination, geo, category, sort, keyword, price."""

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    lat: float | None = None
    lng: float | None = None
    category_id: str | None = None
    sort_field: Literal["rating", "distance", "sales"] = "distance"
    sort_order: Literal["asc", "desc"] = "asc"
    keyword: str | None = None
    price_min: int | None = None
    price_max: int | None = None


class MerchantResp(BaseModel):
    id: str
    name: str
    logo: str
    rating: float
    sales: int
    distance_km: float | None = None
    delivery_time_min: int
    min_order_price: int
    delivery_fee: int
    tags: list[str] = []
    status: MerchantStatus
    category_name: str


class MerchantDetailResp(MerchantResp):
    description: str
    address: str
    phone: str
    open_time: str
    images: list[str] = []
    announcement: str | None = None
    audit_status: AuditStatus = AuditStatus.APPROVED


class AuditReq(BaseModel):
    status: AuditStatus
    remark: str | None = None


class StatusReq(BaseModel):
    status: MerchantStatus


# ── Category ──

class CategoryResp(BaseModel):
    id: str
    name: str
    icon: str | None = None
    type: str
    parent_id: str | None = None
    sort_order: int = 0
    children: list["CategoryResp"] = []


class CategoryTreeResp(BaseModel):
    id: str
    name: str
    icon: str | None = None
    type: str
    sort_order: int = 0
    children: list["CategoryTreeResp"] = []
    product_count: int = 0


class CategoryCreateReq(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    type: Literal["PRODUCT", "COMBO"]
    parent_id: str | None = None
    icon: str | None = None
    sort_order: int = 0


class CategoryUpdateReq(BaseModel):
    name: str | None = None
    icon: str | None = None
    sort_order: int | None = None
