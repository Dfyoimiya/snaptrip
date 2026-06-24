"""Shopping guide agent configuration.

Settings are sourced from environment variables prefixed with SG_ (Shopping Guide).
Agent timeouts are tuned for the 3-phase parallel pipeline.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

# 项目根目录 = agent/src/shopping_guide/config/settings.py → 上 5 层
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


class ShoppingGuideSettings(BaseSettings):
    """Configuration for the shopping guide multi-agent system."""

    # ── LLM ──
    # 默认模型 (UserProfileAgent + MarketingCopyAgent 共用)
    sg_llm_model: str = "qwen3.6-flash"
    # 重排模型 (ProductRecAgent LLM rerank — 核心转化环节，用大模型)
    sg_llm_model_rerank: str = "qwen3.6-plus"
    sg_llm_temperature_profile: float = 0.3
    sg_llm_temperature_rerank: float = 0.3
    sg_llm_temperature_copy: float = 0.9
    sg_llm_max_tokens_profile: int = 1024
    sg_llm_max_tokens_rerank: int = 512
    sg_llm_max_tokens_copy: int = 2048

    # ── Agent timeouts (seconds) ──
    sg_agent_timeout_user_profile: float = 5.0
    sg_agent_timeout_product_rec: float = 8.0
    sg_agent_timeout_marketing_copy: float = 10.0
    sg_agent_timeout_inventory: float = 5.0

    # ── A/B Testing ──
    sg_ab_test_enabled: bool = True
    sg_ab_test_bucket_count: int = 100

    # ── Recommendation ──
    sg_default_num_items: int = 10
    sg_max_candidates: int = 30

    # ── Inventory ──
    sg_safety_stock_threshold: int = 50
    sg_low_stock_threshold: int = 100

    # ── Web Search ──
    sg_web_search_provider: str = "tavily"  # "tavily" | "brave" | "serpapi" | "none"
    sg_web_search_api_key: str = ""
    sg_web_search_base_url: str = "https://api.tavily.com/search"
    sg_web_search_engine: str = "baidu"  # serpapi engine: baidu | google | bing
    sg_web_search_max_results: int = 5
    sg_web_search_cache_ttl: int = 3600  # seconds

    # ── Search Agent Timeouts ──
    sg_agent_timeout_web_search: float = 15.0
    sg_agent_max_retries_web_search: int = 2
    sg_agent_timeout_review_search: float = 10.0
    sg_agent_max_retries_review_search: int = 2

    # ── Review Search ──
    sg_review_search_max_per_product: int = 20

    # ── Info Synthesis LLM ──
    sg_llm_model_info_synthesize: str = "qwen3.6-plus"
    sg_llm_temperature_info_synthesize: float = 0.5
    sg_llm_max_tokens_info_synthesize: int = 2048

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_prefix": "", "extra": "ignore"}


@lru_cache()
def get_shopping_guide_settings() -> ShoppingGuideSettings:
    return ShoppingGuideSettings()
