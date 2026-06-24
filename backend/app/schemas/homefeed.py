"""首页多维度推荐 Feed Schema。

5 种 Section:
  - guess_you_like:   "猜你喜欢" (个性化推荐, Agent pipeline)
  - trending_now:     "热门推荐" (Redis trending)
  - new_arrivals:     "新品上市" (DB 最新)
  - recently_viewed:  "浏览历史" (Redis behavior)
  - search_discovery: "搜索发现" (Redis query velocity)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, computed_field

from app.utils.display import format_sale_count


class FeedSectionType(str, Enum):
    GUESS_YOU_LIKE = "guess_you_like"
    TRENDING_NOW = "trending_now"
    NEW_ARRIVALS = "new_arrivals"
    RECENTLY_VIEWED = "recently_viewed"
    SEARCH_DISCOVERY = "search_discovery"


class FeedProduct(BaseModel):
    """推荐商品 (精简版, 用于 Feed 渲染)。"""

    product_id: str
    name: str
    price: float = 0.0
    image_url: str = ""
    brand_name: str = ""
    category_id: str = ""
    sale_count: int = 0
    stock: int = 0
    score: float = 0.0
    marketing_copy: str = ""  # 仅 guess_you_like section 有值
    promotion_price: float | None = None
    promotion_type: int = 0
    new_status: int = 0
    recommend_status: int = 0

    @computed_field
    @property
    def sale_count_display(self) -> str:
        return format_sale_count(self.sale_count)


class SearchDiscoveryItem(BaseModel):
    """搜索发现项 (渲染为可点击标签)。"""

    query: str
    count: int = 0


class FeedSection(BaseModel):
    """单个推荐板块。"""

    section_type: FeedSectionType
    title: str
    sub_title: str = ""
    products: list[FeedProduct] = Field(default_factory=list)
    suggestions: list[SearchDiscoveryItem] = Field(default_factory=list)


class HomeFeedResponse(BaseModel):
    """首页多维度推荐聚合响应。"""

    sections: list[FeedSection]
    user_id: str | None = None
    session_id: str | None = None
