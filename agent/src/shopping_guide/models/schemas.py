"""Pydantic data models for the shopping guide multi-agent system.

Adapted from refer/multi-agent-ecommerce-system with SnapTrip-specific fields.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserSegment(str, Enum):
    NEW_USER = "new_user"
    ACTIVE = "active"
    HIGH_VALUE = "high_value"
    PRICE_SENSITIVE = "price_sensitive"
    CHURN_RISK = "churn_risk"


class UserProfile(BaseModel):
    user_id: str
    age: int | None = None
    gender: str | None = None
    city: str | None = None
    segments: list[UserSegment] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    preferred_brands: list[str] = Field(default_factory=list)
    price_range: tuple[float, float] = (0.0, 10000.0)
    recent_views: list[str] = Field(default_factory=list)
    recent_purchases: list[str] = Field(default_factory=list)
    rfm_score: dict[str, float] = Field(default_factory=dict)
    real_time_tags: dict[str, Any] = Field(default_factory=dict)


class Product(BaseModel):
    product_id: str
    name: str
    category: str = ""
    category_name: str = ""
    price: float = 0.0
    original_price: float = 0.0
    description: str = ""
    brand: str = ""
    brand_name: str = ""
    seller_id: str = ""
    stock: int = 0
    sale_count: int = 0
    tags: list[str] = Field(default_factory=list)
    score: float = 0.0
    image_url: str = ""
    images: list[str] = Field(default_factory=list)
    marketing_copy: str = ""


class RecommendationRequest(BaseModel):
    user_id: str
    message: str = ""
    scene: str = "homepage"
    num_items: int = 10
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent_name: str
    success: bool = True
    latency_ms: float = 0.0
    error: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


class UserProfileResult(AgentResult):
    agent_name: str = "user_profile"
    profile: UserProfile | None = None


class ProductRecResult(AgentResult):
    agent_name: str = "product_rec"
    products: list[Product] = Field(default_factory=list)
    recall_strategy: str = ""


class MarketingCopyResult(AgentResult):
    agent_name: str = "marketing_copy"
    copies: list[dict[str, str]] = Field(default_factory=list)
    prompt_template_used: str = ""


class InventoryResult(AgentResult):
    agent_name: str = "inventory"
    available_products: list[str] = Field(default_factory=list)
    low_stock_alerts: list[dict[str, Any]] = Field(default_factory=list)
    purchase_limits: dict[str, int] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    request_id: str = ""
    user_id: str = ""
    products: list[Product] = Field(default_factory=list)
    marketing_copies: list[dict[str, str]] = Field(default_factory=list)
    experiment_group: str = "control"
    agent_results: dict[str, AgentResult] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
#  Intent Router
# ============================================================================


class GuideIntent(str, Enum):
    FAQ = "faq"
    PRODUCT_SEARCH = "product_search"
    INFO_SEARCH = "info_search"


class RoutedRequest(BaseModel):
    """顶层导购请求，mode="auto" 时由 GuideRouter 自动识别意图并分发。"""

    user_id: str
    query: str
    mode: str = "auto"  # "auto" | "faq" | "product_search" | "info_search"
    intent: GuideIntent | None = None  # auto 时由 router 填充
    product_ids: list[str] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
#  Info Search — 请求/响应
# ============================================================================


class InfoSearchRequest(BaseModel):
    """信息搜索请求。"""

    user_id: str
    query: str
    product_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=lambda: ["web", "reviews"])
    max_results_per_source: int = 5
    context: dict[str, Any] = Field(default_factory=dict)


# ── 卡片级输出 ──


class HighlightCard(BaseModel):
    """亮点卡片 — 精简概括，前端文字放大展示。"""

    emoji: str = ""
    title: str = ""  # ≤8字
    description: str = ""  # ≤25字


class BuyReasonCard(BaseModel):
    """值不值得买 — 按使用场景分析。"""

    scenario: str = ""  # "通勤/差旅场景"
    verdict: str = ""  # "很值得" / "谨慎" / "不推荐"
    reasoning: str = ""  # ≤40字


class PitfallCard(BaseModel):
    """避坑指南卡片。"""

    title: str = ""
    description: str = ""


class ReviewItem(BaseModel):
    """单条评价。"""

    review_id: str = ""
    user_name: str = ""  # 匿名则显示 "匿名用户"
    rating: int = 0
    content: str = ""
    created_at: str = ""


class ReviewSummary(BaseModel):
    """用户评价汇总。"""

    average_rating: float = 0.0
    total_count: int = 0
    summary_text: str = ""  # LLM 对评价的总结 (≤80字)
    top_reviews: list[ReviewItem] = Field(default_factory=list)  # 至多4条


class InfoSearchResponse(BaseModel):
    """信息搜索响应 — Canvas 结构化卡片。"""

    request_id: str = ""
    user_id: str = ""
    query: str = ""
    conclusion: str = ""  # 一句话总结
    highlights: list[HighlightCard] = Field(default_factory=list)  # 2-5条
    worth_buying: list[BuyReasonCard] = Field(default_factory=list)  # 按场景
    pitfalls: list[PitfallCard] = Field(default_factory=list)  # 1-3条
    review_summary: ReviewSummary | None = None
    sources_used: list[str] = Field(default_factory=list)  # ["web", "reviews"]
    agent_results: dict[str, AgentResult] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
#  搜索中间结果
# ============================================================================


class WebSearchItem(BaseModel):
    """Web 搜索单条结果。"""

    title: str = ""
    url: str = ""
    snippet: str = ""
    source: str = ""  # "tavily" / "brave"
    relevance_score: float = 0.0
    published_date: str | None = None


class WebSearchAgentResult(AgentResult):
    """Web 搜索 Agent 返回结果。"""

    agent_name: str = "web_search"
    items: list[WebSearchItem] = Field(default_factory=list)
    total_results: int = 0
    source_api: str = ""


class ReviewSearchAgentResult(AgentResult):
    """评价搜索 Agent 返回结果。"""

    agent_name: str = "review_search"
    per_product: dict[str, ReviewSummary] = Field(default_factory=dict)
    total_scanned: int = 0


# ============================================================================
#  追问建议
# ============================================================================


class FollowUpItem(BaseModel):
    """单个追问建议 — 可为带选项的交互式追问卡片。

    前端渲染为输入框上方的"猜你想问"卡片，支持两种交互模式：
    - send: 点击选项直接发送消息
    - fill: 点击选项填入输入框，用户可编辑后发送
    """

    text: str = ""  # 引导文案，如"你更想选哪个品牌的呢？"
    options: list[str] = Field(default_factory=list)  # 可点击的选项标签
    action: str = "send"  # "send"=直接发送 | "fill"=填入输入框
