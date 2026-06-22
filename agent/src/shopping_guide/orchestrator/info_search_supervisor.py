"""InfoSearchSupervisor — orchestrates WebSearchAgent + ReviewSearchAgent.

Pipeline:
  Phase 1 (parallel):  WebSearchAgent + ReviewSearchAgent
  Phase 2 (serial):    LLM structured synthesis → InfoSearchResponse
                        (conclusion + highlights + worth_buying + pitfalls + review_summary)

Author: SnapTrip Team
Date: 2026-06-23
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from shopping_guide.agents.review_search_agent import ReviewSearchAgent
from shopping_guide.agents.web_search_agent import WebSearchAgent
from shopping_guide.config.settings import get_shopping_guide_settings
from shopping_guide.models.schemas import (
    BuyReasonCard,
    HighlightCard,
    InfoSearchRequest,
    InfoSearchResponse,
    PitfallCard,
    ReviewItem,
    ReviewSearchAgentResult,
    ReviewSummary,
    WebSearchAgentResult,
    WebSearchItem,
)

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """你是一个专业的购物导购分析助手。基于提供的网络搜索结果和用户评价，生成一个结构化的商品分析报告。

## 输出格式 (严格 JSON)

{
  "conclusion": "一句话总结（含推荐判断），不超过50字",
  "highlights": [
    {"emoji": "🔊", "title": "亮点标题(≤8字)", "description": "一句话描述(≤25字)"}
  ],
  "worth_buying": [
    {"scenario": "使用场景", "verdict": "很值得/谨慎/不推荐", "reasoning": "不超过40字的理由"}
  ],
  "pitfalls": [
    {"title": "避坑点(≤8字)", "description": "描述(≤30字)"}
  ],
  "review_summary": {
    "summary_text": "基于用户评价的简短总结(≤80字)",
    "top_reviews": [
      {"review_id": "", "user_name": "", "rating": 5, "content": "评价内容原文截取", "created_at": ""}
    ]
  }
}

## 规则
1. highlights 输出 2-5 条，每条精简有力，适合卡片展示（文字放大）
2. worth_buying 按使用场景分析，每场景给出明确判断+理由
3. pitfalls 输出 1-3 条，基于事实，不要编造
4. review_summary.top_reviews 至多4条，保留原文关键信息，优先选不同评分的代表性评价
5. 如果某类信息不足，相应字段返回空数组
6. 基于提供的网络搜索和评价数据，不要编造信息

## 网络搜索结果
{web_results}

## 用户评价数据
{review_data}

请只输出 JSON，不要其他内容。"""


class InfoSearchSupervisor:
    """Coordinates WebSearchAgent + ReviewSearchAgent → structured synthesis.

    Usage:
        supervisor = InfoSearchSupervisor(
            llm_adapter=adapter,
            http_client=client,
            web_search_client=ws_client,
        )
        response = await supervisor.search(request)
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        http_client: Any = None,
        web_search_client: Any = None,
    ):
        self.llm = llm_adapter
        settings = get_shopping_guide_settings()

        self.web_search_agent = WebSearchAgent(
            llm_adapter=llm_adapter,
            http_client=http_client,
            web_search_client=web_search_client,
        )
        self.review_search_agent = ReviewSearchAgent(
            http_client=http_client,
            llm_adapter=llm_adapter,
        )

        self.synthesize_model = settings.sg_llm_model_info_synthesize
        self.synthesize_temperature = settings.sg_llm_temperature_info_synthesize
        self.synthesize_max_tokens = settings.sg_llm_max_tokens_info_synthesize

    async def search(self, request: InfoSearchRequest) -> InfoSearchResponse:
        """Execute the 2-phase info search pipeline."""
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        logger.info(
            "info_search.start request_id=%s query=%s sources=%s",
            request_id,
            request.query,
            request.sources,
        )

        sources = request.sources if request.sources else ["web", "reviews"]

        # ═══════════════════════════════════════════════════════════════════
        # Phase 1: parallel — web search + review search
        # ═══════════════════════════════════════════════════════════════════
        tasks: list[Any] = []
        task_labels: list[str] = []

        if "web" in sources:
            tasks.append(
                self.web_search_agent.run(
                    query=request.query,
                    max_results=request.max_results_per_source,
                    search_context="产品评测 对比 优缺点",
                )
            )
            task_labels.append("web")

        if "reviews" in sources:
            tasks.append(
                self.review_search_agent.run(
                    product_ids=request.product_ids,
                    query=request.query,
                    max_reviews=request.max_results_per_source,
                )
            )
            task_labels.append("reviews")

        if not tasks:
            return InfoSearchResponse(
                request_id=request_id,
                user_id=request.user_id,
                query=request.query,
                sources_used=[],
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        web_result: WebSearchAgentResult | None = None
        review_result: ReviewSearchAgentResult | None = None

        for label, result in zip(task_labels, results):
            if isinstance(result, Exception):
                logger.warning("info_search: %s agent failed: %s", label, result)
            elif label == "web":
                web_result = result
            elif label == "reviews":
                review_result = result

        web_items: list[WebSearchItem] = getattr(web_result, "items", []) if web_result else []
        review_data: dict[str, ReviewSummary] = (
            getattr(review_result, "per_product", {}) if review_result else {}
        )

        logger.info(
            "info_search.phase1 request_id=%s web=%d review_products=%d",
            request_id,
            len(web_items),
            len(review_data),
        )

        # ═══════════════════════════════════════════════════════════════════
        # Phase 2: LLM synthesis — structured card output
        # ═══════════════════════════════════════════════════════════════════
        if self.llm:
            synthesis = await self._synthesize(request.query, web_items, review_data)
        else:
            synthesis = self._empty_synthesis()

        total_latency = (time.perf_counter() - start) * 1000

        # Merge review data from DB into synthesis if the LLM didn't populate it
        if synthesis["review_summary"] is None and review_data:
            first_summary = next(iter(review_data.values()))
            synthesis["review_summary"] = ReviewSummary(
                average_rating=first_summary.average_rating,
                total_count=first_summary.total_count,
                summary_text=first_summary.summary_text or "",
                top_reviews=first_summary.top_reviews,
            )

        response = InfoSearchResponse(
            request_id=request_id,
            user_id=request.user_id,
            query=request.query,
            conclusion=synthesis.get("conclusion", ""),
            highlights=synthesis.get("highlights", []),
            worth_buying=synthesis.get("worth_buying", []),
            pitfalls=synthesis.get("pitfalls", []),
            review_summary=synthesis.get("review_summary"),
            sources_used=list(task_labels),
            agent_results={
                "web_search": web_result,
                "review_search": review_result,
            },
            total_latency_ms=total_latency,
        )

        logger.info(
            "info_search.complete request_id=%s latency_ms=%.1f highlights=%d",
            request_id,
            total_latency,
            len(response.highlights),
        )

        return response

    # ── Synthesis ──────────────────────────────────────────────────────────

    async def _synthesize(
        self,
        query: str,
        web_items: list[WebSearchItem],
        review_data: dict[str, ReviewSummary],
    ) -> dict[str, Any]:
        """LLM synthesis: web + review data → structured card output."""
        if not self.llm:
            return self._empty_synthesis()

        # Format web results
        web_parts: list[str] = []
        for item in web_items[:8]:
            web_parts.append(f"- [{item.title}]({item.url})\n  {item.snippet[:200]}")
        web_text = "\n".join(web_parts) if web_parts else "（无网络搜索结果）"

        # Format review data
        review_parts: list[str] = []
        for pid, summary in review_data.items():
            review_parts.append(f"商品 {pid[:8]}...:")
            review_parts.append(f"  评分: {summary.average_rating}/5 ({summary.total_count}条评价)")
            for r in summary.top_reviews[:4]:
                review_parts.append(f"  [{r.rating}星] {r.content[:120]}")
        review_text = "\n".join(review_parts) if review_parts else "（暂无用户评价）"

        try:
            prompt = (
                SYNTHESIS_PROMPT
                .replace("{web_results}", web_text[:3000])
                .replace("{review_data}", review_text[:2000])
            )

            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": f"你正在帮助用户分析: {query}"},
                    {"role": "user", "content": prompt},
                ],
                model_alias=self.synthesize_model,
                temperature=self.synthesize_temperature,
                max_tokens=self.synthesize_max_tokens,
                enable_thinking=False,
            )
            raw = (response.content or "").strip()

            # Strip markdown fences
            if raw.startswith("```"):
                lines = raw.split("\n")
                if len(lines) > 2 and lines[-1].strip() == "```":
                    raw = "\n".join(lines[1:-1])
                elif lines[0].startswith("```"):
                    raw = "\n".join(lines[1:])

            parsed = json.loads(raw)
            return self._normalize_synthesis(parsed, review_data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.exception("info_search: synthesis LLM failed")
            return self._fallback_synthesis(web_items, review_data)

    def _normalize_synthesis(
        self, raw: dict[str, Any], review_data: dict[str, ReviewSummary]
    ) -> dict[str, Any]:
        """Normalize LLM output into the expected schema shape."""
        highlights = [
            HighlightCard(
                emoji=h.get("emoji", ""),
                title=h.get("title", ""),
                description=h.get("description", ""),
            )
            for h in raw.get("highlights", [])
        ]
        worth_buying = [
            BuyReasonCard(
                scenario=w.get("scenario", ""),
                verdict=w.get("verdict", ""),
                reasoning=w.get("reasoning", ""),
            )
            for w in raw.get("worth_buying", [])
        ]
        pitfalls = [
            PitfallCard(
                title=p.get("title", ""),
                description=p.get("description", ""),
            )
            for p in raw.get("pitfalls", [])
        ]

        # Prefer LLM's review_summary, fall back to raw DB data
        review_summary = None
        rs_raw = raw.get("review_summary")
        if rs_raw and isinstance(rs_raw, dict):
            review_summary = ReviewSummary(
                average_rating=float(rs_raw.get("average_rating", 0)),
                total_count=int(rs_raw.get("total_count", 0)),
                summary_text=str(rs_raw.get("summary_text", "")),
                top_reviews=[
                    ReviewItem(
                        review_id=str(r.get("review_id", "")),
                        user_name=str(r.get("user_name", "")),
                        rating=int(r.get("rating", 0)),
                        content=str(r.get("content", "")),
                        created_at=str(r.get("created_at", "")),
                    )
                    for r in rs_raw.get("top_reviews", [])[:4]
                ],
            )
        elif review_data:
            first = next(iter(review_data.values()))
            if first.total_count > 0:
                review_summary = first

        return {
            "conclusion": raw.get("conclusion", ""),
            "highlights": highlights,
            "worth_buying": worth_buying,
            "pitfalls": pitfalls,
            "review_summary": review_summary,
        }

    @staticmethod
    def _fallback_synthesis(
        web_items: list[WebSearchItem],
        review_data: dict[str, ReviewSummary],
    ) -> dict[str, Any]:
        """Fallback synthesis when LLM is unavailable."""
        highlights: list[HighlightCard] = []
        for item in web_items[:5]:
            highlights.append(
                HighlightCard(
                    title=item.title[:20],
                    description=item.snippet[:80],
                )
            )

        review_summary = None
        if review_data:
            first = next(iter(review_data.values()))
            if first.total_count > 0:
                review_summary = first

        return {
            "conclusion": "",
            "highlights": highlights,
            "worth_buying": [],
            "pitfalls": [],
            "review_summary": review_summary,
        }

    @staticmethod
    def _empty_synthesis() -> dict[str, Any]:
        return {
            "conclusion": "",
            "highlights": [],
            "worth_buying": [],
            "pitfalls": [],
            "review_summary": None,
        }
