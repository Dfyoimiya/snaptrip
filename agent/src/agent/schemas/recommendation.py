"""推荐系统 Pydantic Schemas。

定义推荐系统的数据模型, 参考 multi-agent-ecommerce-system 的 schemas.py 模式。

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserSegment(str, Enum):
    NEW_USER = "NEW_USER"
    ACTIVE = "ACTIVE"
    HIGH_VALUE = "HIGH_VALUE"
    PRICE_SENSITIVE = "PRICE_SENSITIVE"
    CHURN_RISK = "CHURN_RISK"


class RecommendationScene(str, Enum):
    HOMEPAGE = "homepage"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"


class RecommendationRequest(BaseModel):
    """推荐请求。"""
    user_id: str | None = Field(None, description="用户ID (登录用户)")
    session_id: str | None = Field(None, description="会话ID (匿名用户)")
    scene: RecommendationScene = Field(RecommendationScene.HOMEPAGE)
    num_items: int = Field(10, ge=1, le=50)
    product_id: str | None = Field(None, description="关联商品ID (product_detail场景)")
    context: dict[str, Any] = Field(default_factory=dict)


class RecommendationProduct(BaseModel):
    """推荐商品。"""
    product_id: str
    name: str
    category_id: str = ""
    price: float = 0.0
    brand_name: str = ""
    image_url: str = ""
    sale_count: int = 0
    stock: int = 0
    score: float = 0.0
    marketing_copy: str = ""  # 个性化文案 (由 MarketingCopyAgent 生成)


class AgentResultItem(BaseModel):
    """单个 Agent 执行结果摘要。"""
    agent_name: str
    success: bool = True
    latency_ms: float = 0.0
    confidence: float = 1.0
    error: str | None = None


class RecommendationResponse(BaseModel):
    """推荐响应。"""
    request_id: str
    user_id: str | None = None
    session_id: str | None = None
    products: list[RecommendationProduct] = Field(default_factory=list)
    copies: list[dict[str, str]] = Field(default_factory=list)
    experiment_group: str = "control"
    agent_results: dict[str, AgentResultItem] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
