"""WebSearchAgent — external web search via provider strategy.

Responsibilities:
  - Accept a natural-language query
  - Optionally expand query via LLM for better search results
  - Call WebSearchClient (Tavily/Brave/etc.) with retry + rate limiting
  - Normalize results into WebSearchItem list
  - Fallback gracefully (empty results) when API is unavailable

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations

import logging
from typing import Any

from shopping_guide.agents.base_agent import BaseAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import WebSearchAgentResult, WebSearchItem

logger = logging.getLogger(__name__)

QUERY_EXPANSION_PROMPT = """将用户的购物咨询问题扩展为更适合搜索引擎的关键词组合。

用户问题: __QUERY__
搜索场景: __CONTEXT__

规则:
1. 提取核心商品名 + 评测/对比/避坑/性价比等搜索意图
2. 输出1-2个搜索词，用 | 分隔
3. 优先中文搜索词

只输出搜索词，不要其他内容。"""


class WebSearchAgent(BaseAgent):
    """External web search agent.

    Searches the web for product reviews, comparisons, pricing, and general
    information. Results are normalized into WebSearchItem for downstream
    synthesis.

    Constructor injection:
      - llm_adapter: For optional query expansion
      - http_client: Async HTTP client (fallback if no WebSearchClient)
      - web_search_client: Dedicated WebSearchClient (preferred)
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        http_client: Any = None,
        web_search_client: Any = None,
    ):
        settings = get_shopping_guide_settings()
        super().__init__(
            name="web_search",
            timeout=settings.sg_agent_timeout_web_search,
            max_retries=settings.sg_agent_max_retries_web_search,
        )
        self.llm = llm_adapter
        self.http = http_client
        self.search_client = web_search_client
        self.model_alias = getattr(settings, "sg_llm_model", "qwen3.6-flash")

    async def _execute(self, **kwargs: Any) -> WebSearchAgentResult:
        query: str = kwargs.get("query", "")
        max_results: int = kwargs.get("max_results", 5)
        search_context: str = kwargs.get("search_context", "")

        if not query:
            return WebSearchAgentResult(
                success=False,
                error="No query provided",
                confidence=0.0,
            )

        # 1. Query expansion (optional)
        expanded_queries = await self._expand_query(query, search_context)

        # 2. Execute searches in parallel (was sequential — major latency bottleneck)
        all_items: list[WebSearchItem] = []
        source_api = "none"

        if self.search_client:
            source_api = self.search_client.provider_name
            import asyncio
            tasks = [
                self.search_client.search(eq, max_results=max_results)
                for eq in expanded_queries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("web_search: expanded query failed: %s", result)
                else:
                    all_items.extend(result)
        else:
            # No web search client configured — graceful degradation
            logger.info("web_search: no search client configured, returning empty")

        # Deduplicate by URL
        seen_urls: set[str] = set()
        deduped: list[WebSearchItem] = []
        for item in all_items:
            if item.url and item.url not in seen_urls:
                seen_urls.add(item.url)
                deduped.append(item)
        deduped = deduped[:max_results]

        logger.info(
            "web_search: completed query=%s results=%d source=%s",
            query,
            len(deduped),
            source_api,
        )

        return WebSearchAgentResult(
            success=True,
            items=deduped,
            total_results=len(deduped),
            source_api=source_api,
            data={
                "query": query,
                "expanded_queries": expanded_queries,
            },
            confidence=0.7 if deduped else 0.1,
        )

    async def _expand_query(self, query: str, context: str) -> list[str]:
        """Expand query for better search results. Returns list of search queries."""
        if not self.llm:
            return [query]

        try:
            prompt = (
                QUERY_EXPANSION_PROMPT
                .replace("__QUERY__", query)
                .replace("__CONTEXT__", context or "综合评测")
            )
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": "你是搜索优化专家。"},
                    {"role": "user", "content": prompt},
                ],
                model_alias=self.model_alias,
                temperature=0.3,
                max_tokens=128,
                enable_thinking=False,
            )
            raw = (response.content or "").strip()
            queries = [q.strip() for q in raw.split("|") if q.strip()]
            if queries:
                logger.debug("web_search: expanded query: %s → %s", query, queries)
                return queries
        except Exception:
            logger.debug("web_search: query expansion failed, using original query", exc_info=True)

        return [query]
