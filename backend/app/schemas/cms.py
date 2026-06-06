"""
【内容域 + 统计 Pydantic Schema】

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
#  轮播图
# ============================================================================

class BannerCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    pic: str = Field(..., min_length=1, max_length=255)
    url: str | None = Field(None, max_length=500)
    sort: int = Field(default=0, ge=0)
    status: int = Field(default=1, ge=0, le=1)
    start_time: datetime | None = None
    end_time: datetime | None = None


class BannerUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    pic: str | None = Field(None, min_length=1, max_length=255)
    url: str | None = Field(None, max_length=500)
    sort: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)
    start_time: datetime | None = None
    end_time: datetime | None = None


class BannerResponse(BaseModel):
    id: UUID
    title: str
    pic: str
    url: str | None = None
    sort: int
    status: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
#  专题
# ============================================================================

class SubjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=500)
    pic: str | None = Field(None, max_length=255)
    content: str | None = None
    category_name: str | None = Field(None, max_length=100)
    status: int = Field(default=1, ge=0, le=1)
    recommend_status: int = Field(default=0, ge=0, le=1)


class SubjectUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    summary: str | None = Field(None, max_length=500)
    pic: str | None = Field(None, max_length=255)
    content: str | None = None
    category_name: str | None = Field(None, max_length=100)
    status: int | None = Field(None, ge=0, le=1)
    recommend_status: int | None = Field(None, ge=0, le=1)


class SubjectResponse(BaseModel):
    id: UUID
    title: str
    summary: str | None = None
    pic: str | None = None
    content: str | None = None
    category_name: str | None = None
    status: int
    recommend_status: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
#  帮助中心
# ============================================================================

class HelpCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    content: str | None = None
    category_name: str | None = Field(None, max_length=100)
    status: int = Field(default=1, ge=0, le=1)
    sort: int = Field(default=0, ge=0)


class HelpUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    content: str | None = None
    category_name: str | None = Field(None, max_length=100)
    status: int | None = Field(None, ge=0, le=1)
    sort: int | None = Field(None, ge=0)


class HelpResponse(BaseModel):
    id: UUID
    title: str
    content: str | None = None
    category_name: str | None = None
    status: int
    sort: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ============================================================================
#  统计看板
# ============================================================================

class DashboardOverview(BaseModel):
    """仪表盘概览 —— 今日关键指标"""
    today_order_count: int = Field(default=0, description="今日订单数")
    today_sales_amount: float = Field(default=0.0, description="今日销售额")
    today_new_member_count: int = Field(default=0, description="今日新增会员")
    total_product_count: int = Field(default=0, description="商品总数")
    on_shelf_product_count: int = Field(default=0, description="上架商品数")


class SalesStatItem(BaseModel):
    """销售额统计项"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    amount: float = Field(default=0.0)
    order_count: int = Field(default=0)


class ProductRankItem(BaseModel):
    """商品销量排行"""
    product_id: str
    product_name: str
    sale_count: int = 0
    amount: float = 0.0


class HomePageAggregation(BaseModel):
    """首页聚合数据 —— Banner + 推荐商品 + 秒杀 + 专题"""
    banners: list[BannerResponse] = Field(default_factory=list)
    new_products: list[dict] = Field(default_factory=list, description="新品推荐")
    recommend_products: list[dict] = Field(default_factory=list, description="推荐商品")
    subjects: list[SubjectResponse] = Field(default_factory=list)
