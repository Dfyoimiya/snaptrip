"""Search domain DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from contracts.schemas.common import PaginationParams


class SearchReq(BaseModel):
    q: str = Field(min_length=1, max_length=100)
    lat: float | None = None
    lng: float | None = None
    type: str | None = None  # "merchant", "product"
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class SearchResp(BaseModel):
    id: str
    type: str  # "merchant" | "product"
    name: str
    image: str | None = None
    price: int | None = None
    rating: float | None = None
    tags: list[str] = []
    distance_km: float | None = None


class HotSearchResp(BaseModel):
    keyword: str
    heat: int  # 搜索热度值


class SuggestionResp(BaseModel):
    keyword: str
    type: str  # "merchant" | "product" | "keyword"
    count: int


class SearchHistoryResp(BaseModel):
    keyword: str
    created_at: str
