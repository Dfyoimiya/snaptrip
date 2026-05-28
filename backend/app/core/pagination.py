"""通用分页工具。

用法:
    from app.core.pagination import PaginationParams, PaginatedResult

    params = PaginationParams(page=1, page_size=20)
    query = select(Product).offset(params.offset).limit(params.page_size)
    total = await db.scalar(select(func.count()).select_from(Product))
    result = PaginatedResult(
        items=products,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """分页请求参数 —— page 从 1 开始"""

    page: int = Field(default=1, ge=1, description="页码, 从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数, 最大100")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResult(BaseModel, Generic[T]):
    """分页响应 —— 泛型 items 列表 + 分页元数据"""

    items: list[T] = Field(default_factory=list, description="当前页数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页条数")
    total_pages: int = Field(default=0, description="总页数")

    @classmethod
    def create(cls, items: list[T], total: int, params: PaginationParams) -> PaginatedResult[T]:
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=ceil(total / params.page_size) if params.page_size > 0 else 0,
        )
