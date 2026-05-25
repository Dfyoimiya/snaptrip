"""Product domain DTOs — list, detail, spec, review."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from contracts.schemas.common import PaginationParams
from contracts.schemas.enums import ProductStatus


class ProductListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    merchant_id: str | None = None
    category_id: str | None = None
    keyword: str | None = None
    status: ProductStatus | None = None
    sort_field: Literal["sales", "price", "created_at"] = "sales"
    sort_order: Literal["asc", "desc"] = "desc"


class ProductResp(BaseModel):
    id: str
    merchant_id: str
    name: str
    image: str
    price: int
    original_price: int | None = None
    sales: int
    rating: float
    status: ProductStatus
    stock: int
    has_specs: bool = False
    category_name: str


class SpecValueResp(BaseModel):
    value_id: str
    value_name: str
    price_offset: int
    stock: int


class ProductSpecResp(BaseModel):
    spec_id: str
    spec_name: str
    values: list[SpecValueResp]


class ProductFlavorResp(BaseModel):
    flavor_id: str
    flavor_name: str
    extra_price: int


class ProductDetailResp(ProductResp):
    description: str
    images: list[str] = []
    specs: list[ProductSpecResp] = []
    flavors: list[ProductFlavorResp] = []
    reviews_count: int = 0
    review_avg: float = 0.0


# ── Review ──

class ReviewResp(BaseModel):
    id: str
    user_id: str
    user_nickname: str = ""
    user_avatar: str | None = None
    rating: int
    content: str
    images: list[str] = []
    created_at: str


class ReviewCreateReq(BaseModel):
    product_id: str
    order_id: str
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=500)
    images: list[str] = []


class ReviewStatsResp(BaseModel):
    avg_rating: float
    total_count: int
    distribution: dict[str, int]  # {"5": 42, "4": 18, ...}


# ── Product Create/Update (Admin) ──

class SpecCreateReq(BaseModel):
    spec_name: str
    values: list[SpecValueReq]


class SpecValueReq(BaseModel):
    value_name: str
    price_offset: int = 0
    stock: int = 999


class FlavorCreateReq(BaseModel):
    flavor_name: str
    extra_price: int = 0


class ProductCreateReq(BaseModel):
    merchant_id: str
    category_id: str
    name: str = Field(min_length=1, max_length=50)
    description: str | None = None
    image: str
    images: list[str] = []
    price: int = Field(ge=0)
    original_price: int | None = None
    stock: int = Field(default=999, ge=0)
    specs: list[SpecCreateReq] = []
    flavors: list[FlavorCreateReq] = []


class ProductUpdateReq(BaseModel):
    name: str | None = None
    description: str | None = None
    image: str | None = None
    images: list[str] | None = None
    price: int | None = None
    original_price: int | None = None
    stock: int | None = None
    category_id: str | None = None
    specs: list[SpecCreateReq] | None = None
    flavors: list[FlavorCreateReq] | None = None
