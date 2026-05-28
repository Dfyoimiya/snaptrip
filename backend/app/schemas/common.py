"""通用 Schema —— 分页响应、基础查询参数、枚举常量。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from enum import IntEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── 分页 ──

class PaginationParams(BaseModel):
    """通用分页查询参数"""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应"""

    items: list[T] = Field(default_factory=list)
    total: int = Field(default=0)
    page: int = Field(default=1)
    page_size: int = Field(default=20)
    total_pages: int = Field(default=0)

    @classmethod
    def of(cls, items: list[T], total: int, params: PaginationParams) -> PaginatedResponse[T]:
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=(total + params.page_size - 1) // params.page_size if params.page_size > 0 else 0,
        )


# ── 通用状态枚举 ──

class PublishStatus(IntEnum):
    """通用上下架状态"""
    OFF_SHELF = 0
    ON_SHELF = 1


class VerifyStatus(IntEnum):
    """通用审核状态"""
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class SortDirection(str):
    ASC = "asc"
    DESC = "desc"


# ── 基础查询 ──

class IdRequest(BaseModel):
    """通用 ID 请求体"""
    id: str = Field(..., description="资源ID")


class BatchIdsRequest(BaseModel):
    """批量 ID 请求体"""
    ids: list[str] = Field(..., min_length=1, max_length=100, description="资源ID列表")


class StatusRequest(BaseModel):
    """通用状态修改请求"""
    status: int = Field(..., ge=0, le=1, description="状态 0=禁用 1=启用")
