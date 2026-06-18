"""推荐系统 Pydantic Schemas (Backend)。

与 agent/src/agent/schemas/recommendation.py 对齐,
作为 API Request/Response 的独立定义。

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecommendationScene(str, Enum):
    HOMEPAGE = "homepage"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"


class RecommendationRequest(BaseModel):
    user_id: str | None = Field(None)
    session_id: str | None = Field(None)
    scene: str = Field("homepage")
    num_items: int = Field(10, ge=1, le=50)
    product_id: str | None = Field(None)
    context: dict[str, Any] = Field(default_factory=dict)


class RecommendationProduct(BaseModel):
    product_id: str
    name: str
    category_id: str = ""
    price: float = 0.0
    brand_name: str = ""
    image_url: str = ""
    sale_count: int = 0
    stock: int = 0
    score: float = 0.0
    marketing_copy: str = ""


class AgentResultItem(BaseModel):
    agent_name: str
    success: bool = True
    latency_ms: float = 0.0
    confidence: float = 1.0
    error: str | None = None


class RecommendationResponse(BaseModel):
    request_id: str
    user_id: str | None = None
    session_id: str | None = None
    products: list[RecommendationProduct] = Field(default_factory=list)
    copies: list[dict] = Field(default_factory=list)
    experiment_group: str = "control"
    agent_results: dict[str, AgentResultItem] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
