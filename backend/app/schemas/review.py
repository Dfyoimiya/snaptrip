"""商品评价 Schema —— 创建/更新/响应/列表查询。

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── 创建 ──

class ReviewCreate(BaseModel):
    product_id: uuid.UUID = Field(..., description="商品ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1~5 星")
    content: str | None = Field(None, description="评价文字内容")
    images: str | None = Field(None, description="评价图片, 逗号分隔URL")
    is_anonymous: bool = Field(default=False, description="是否匿名评价")
    order_id: uuid.UUID | None = Field(None, description="关联订单ID")


# ── 更新 ──

class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5, description="评分 1~5 星")
    content: str | None = Field(None, description="评价文字内容")
    images: str | None = Field(None, description="评价图片, 逗号分隔URL")
    is_anonymous: bool | None = Field(None, description="是否匿名评价")


# ── 响应 ──

class ReviewResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    product_id: uuid.UUID
    user_id: uuid.UUID
    order_id: uuid.UUID | None = None
    rating: int
    content: str | None = None
    images: str | None = None
    is_anonymous: bool = False
    status: int = 0
    reply: str | None = None
    replied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


# ── 列表查询 ──

class ReviewListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    product_id: uuid.UUID | None = Field(None, description="按商品筛选")
    rating: int | None = Field(None, ge=1, le=5, description="按评分筛选")
    status: int | None = Field(default=1, description="审核状态: 0=待审核 1=通过 2=驳回, 默认1仅展示通过")


# ── 评价资格校验 ──


class ReviewEligibilityResponse(BaseModel):
    """用户是否有资格评价某商品。"""

    eligible: bool = Field(..., description="是否有资格评价")
    order_id: str | None = Field(None, description="关联订单编号(有资格时返回)")
    reason: str | None = Field(None, description="无资格原因")
    already_reviewed: bool = Field(default=False, description="是否已评价过")


# ── 评价统计 ──


class ReviewStatsResponse(BaseModel):
    """商品评价聚合统计。"""

    product_id: uuid.UUID = Field(..., description="商品ID")
    average_rating: float = Field(..., description="平均评分, 保留1位小数")
    total_count: int = Field(..., description="评价总数")
    distribution: dict[int, int] = Field(..., description="1~5星各数量, e.g. {5:10, 4:5, 3:2, 2:0, 1:1}")


# ── 管理员专用 ──

class ReviewReplyCreate(BaseModel):
    reply: str = Field(..., min_length=1, description="商家回复内容")
