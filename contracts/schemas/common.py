"""Shared base models: unified response envelope, pagination, geo."""

from __future__ import annotations

import time
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """Unified response wrapper. Every endpoint returns this shape."""

    code: int = 0
    message: str = "success"
    data: T | None = None
    timestamp: int = Field(default_factory=lambda: int(time.time()))


class PaginationParams(BaseModel):
    """Offset-based pagination params (page/size)."""

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class CursorParams(BaseModel):
    """Cursor-based pagination for infinite-feed scenarios."""

    cursor: str | None = None
    size: int = Field(default=20, ge=1, le=50)


class PageResult(BaseModel, Generic[T]):
    """Paginated response body."""

    page: int
    size: int
    total: int
    pages: int
    list: list[T]


class GeoPoint(BaseModel):
    """WGS84 coordinate."""

    lng: float
    lat: float


class SortOption(BaseModel):
    """Reusable sort component."""

    field: str = "distance"
    order: str = "asc"  # "asc" | "desc"
