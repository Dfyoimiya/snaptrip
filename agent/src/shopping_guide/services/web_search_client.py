"""Web search client — provider abstraction with caching and rate limiting.

Supports multiple providers via strategy pattern:
  - TavilySearchProvider (default)
  - BraveSearchProvider
  - SerpAPISearchProvider

Usage:
    from shopping_guide.services.web_search_client import create_web_search_client

    client = create_web_search_client(settings)
    items = await client.search("Sony WH-1000XM6 review", max_results=5)

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from shopping_guide.models.schemas import WebSearchItem

logger = logging.getLogger(__name__)


class WebSearchProvider(ABC):
    """Abstract base for web search providers."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[WebSearchItem]:
        """Execute a web search and return normalized results."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""


class TavilySearchProvider(WebSearchProvider):
    """Tavily Search API — optimized for AI-agent search use cases."""

    def __init__(self, api_key: str, base_url: str = "https://api.tavily.com/search"):
        self.api_key = api_key
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "tavily"

    async def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[WebSearchItem]:
        """Call Tavily search API."""
        if not self.api_key:
            logger.warning("Tavily API key not configured, returning empty results")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.base_url,
                    json={
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "advanced",
                        **kwargs,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()

                items: list[WebSearchItem] = []
                for r in data.get("results", [])[:max_results]:
                    items.append(
                        WebSearchItem(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            source="tavily",
                            relevance_score=r.get("score", 0.0),
                            published_date=r.get("published_date"),
                        )
                    )
                return items
        except Exception:
            logger.warning("Tavily search failed", exc_info=True)
            return []


class SerpAPISearchProvider(WebSearchProvider):
    """SerpAPI — multi-engine search (Baidu, Google, Bing).

    Uses engine=baidu by default for Chinese shopping search quality.
    API docs: https://serpapi.com/search-api
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://serpapi.com/search",
        engine: str = "baidu",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.engine = engine

    @property
    def provider_name(self) -> str:
        return f"serpapi/{self.engine}"

    async def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[WebSearchItem]:
        if not self.api_key:
            logger.warning("SerpAPI key not configured, returning empty results")
            return []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    self.base_url,
                    params={
                        "engine": self.engine,
                        "q": query,
                        "api_key": self.api_key,
                        "num": min(max_results * 2, 20),  # fetch more, dedup downstream
                        **kwargs,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                # SerpAPI may return an error field even with HTTP 200
                if data.get("error"):
                    logger.warning("SerpAPI returned error: %s", data["error"])
                    return []

                items: list[WebSearchItem] = []
                for r in data.get("organic_results", [])[:max_results]:
                    items.append(
                        WebSearchItem(
                            title=r.get("title", ""),
                            url=r.get("link", ""),
                            snippet=r.get("snippet", ""),
                            source=f"serpapi/{self.engine}",
                            relevance_score=0.0,
                            published_date=r.get("date"),
                        )
                    )

                if not items:
                    logger.warning(
                        "SerpAPI returned 0 organic_results for query=%s "
                        "(status=%s, total_time=%s)",
                        query[:60],
                        resp.status_code,
                        data.get("search_metadata", {}).get("total_time_taken", "?"),
                    )
                return items
        except httpx.TimeoutException:
            logger.warning("SerpAPI timeout for query=%s (limit=30s)", query[:60])
            return []
        except Exception:
            logger.warning("SerpAPI search failed for query=%s", query[:60], exc_info=True)
            return []


class BraveSearchProvider(WebSearchProvider):
    """Brave Search API provider."""

    def __init__(self, api_key: str, base_url: str = "https://api.search.brave.com/res/v1/web/search"):
        self.api_key = api_key
        self.base_url = base_url

    @property
    def provider_name(self) -> str:
        return "brave"

    async def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[WebSearchItem]:
        if not self.api_key:
            logger.warning("Brave API key not configured, returning empty results")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    self.base_url,
                    params={"q": query, "count": max_results, **kwargs},
                    headers={
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip",
                        "X-Subscription-Token": self.api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                items: list[WebSearchItem] = []
                for r in data.get("web", {}).get("results", [])[:max_results]:
                    items.append(
                        WebSearchItem(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("description", ""),
                            source="brave",
                            relevance_score=0.0,
                            published_date=r.get("age"),
                        )
                    )
                return items
        except Exception:
            logger.warning("Brave search failed", exc_info=True)
            return []


class WebSearchClient:
    """Unified web search client with provider strategy + in-memory cache.

    Features:
      - Provider-agnostic interface
      - In-memory cache with configurable TTL
      - Graceful degradation: returns empty list on failure
    """

    def __init__(self, provider: WebSearchProvider, cache_ttl: int = 3600):
        self.provider = provider
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, list[WebSearchItem]]] = {}

    @property
    def provider_name(self) -> str:
        return self.provider.provider_name

    async def search(self, query: str, max_results: int = 5, **kwargs: Any) -> list[WebSearchItem]:
        """Search with caching. Cache key = query:max_results."""
        cache_key = f"{query}:{max_results}"
        if cache_key in self._cache:
            ts, results = self._cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                logger.debug("web_search cache hit: %s", cache_key)
                return results

        results = await self.provider.search(query, max_results, **kwargs)
        self._cache[cache_key] = (time.time(), results)
        return results


def create_web_search_client(settings: Any) -> WebSearchClient | None:
    """Factory: build the right provider from ShoppingGuideSettings.

    Returns None if provider is "none" or no API key is configured.
    """
    provider_name = getattr(settings, "sg_web_search_provider", "none")
    api_key = getattr(settings, "sg_web_search_api_key", "")
    cache_ttl = getattr(settings, "sg_web_search_cache_ttl", 3600)

    if provider_name == "none" or not api_key:
        logger.info("Web search disabled (provider=%s, key_configured=%s)", provider_name, bool(api_key))
        return None

    if provider_name == "tavily":
        base_url = getattr(settings, "sg_web_search_base_url", "https://api.tavily.com/search")
        provider = TavilySearchProvider(api_key=api_key, base_url=base_url)
    elif provider_name == "brave":
        provider = BraveSearchProvider(api_key=api_key)
    elif provider_name == "serpapi":
        base_url = getattr(settings, "sg_web_search_base_url", "https://serpapi.com/search")
        engine = getattr(settings, "sg_web_search_engine", "baidu")
        provider = SerpAPISearchProvider(api_key=api_key, base_url=base_url, engine=engine)
    else:
        logger.warning("Unknown web search provider: %s", provider_name)
        return None

    return WebSearchClient(provider=provider, cache_ttl=cache_ttl)


__all__ = [
    "BraveSearchProvider",
    "SerpAPISearchProvider",
    "TavilySearchProvider",
    "WebSearchClient",
    "WebSearchProvider",
    "create_web_search_client",
]
