"""搜索建议编排服务 —— 聚合 autocomplete + trending + AI suggestions。

3 个数据源并发查询, 组装为多 section 响应:
  - autocomplete: Redis 前缀匹配 (AutocompleteService)
  - trending:     Redis query velocity (TrendingService)
  - ai:           Redis 缓存的 LLM 搜索建议 (离线生成)

在线延迟目标: < 30ms (无 LLM 调用, 纯 Redis)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "ai_suggest"
_CACHE_TTL = 86400 * 7  # 7 天


class SuggestionService:
    """搜索建议编排服务。"""

    def __init__(
        self,
        autocomplete_service=None,
        trending_service=None,
        memory=None,
        llm_adapter=None,
    ) -> None:
        self._autocomplete = autocomplete_service
        self._trending = trending_service
        self._memory = memory
        self._llm = llm_adapter

    async def suggest(
        self,
        prefix: str = "",
        user_id: str | None = None,
        session_id: str | None = None,
        limit: int = 8,
    ) -> dict:
        """获取搜索建议 (主入口)。

        Returns:
            {"sections": [...], "prefix": "...", "total_ms": float}
        """
        t0 = time.time()
        tasks = []

        # 1. 自动补全 (仅 prefix ≥ 1 时触发)
        if prefix and len(prefix) >= 1:
            tasks.append(self._get_autocomplete(prefix, limit))

        # 2. 热门搜索 (始终展示)
        tasks.append(self._get_trending(limit))

        # 3. AI 建议 (仅 prefix ≥ 2 时触发)
        if prefix and len(prefix) >= 2:
            tasks.append(self._get_ai_suggestions(prefix, min(limit, 5)))

        # 4. 搜索历史 (仅登录用户)
        uid = user_id or session_id
        if uid and prefix == "":
            tasks.append(self._get_history(str(uid), min(limit, 5)))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        sections = []
        for result in results:
            if isinstance(result, dict) and result.get("queries"):
                sections.append(result)
            elif isinstance(result, Exception):
                logger.debug("suggestion_service: section failed: %s", result)

        total_ms = (time.time() - t0) * 1000
        return {
            "sections": sections,
            "prefix": prefix,
            "total_ms": round(total_ms, 2),
        }

    async def _get_autocomplete(self, prefix: str, limit: int) -> dict:
        """自动补全建议。"""
        if not self._autocomplete:
            return {"section_type": "autocomplete", "title": "搜索建议", "queries": []}
        try:
            items = await self._autocomplete.suggest(prefix, limit=limit)
            return {
                "section_type": "autocomplete",
                "title": "搜索建议",
                "queries": [
                    {"query": item["query"], "type": "autocomplete", "frequency": item.get("frequency", 0)}
                    for item in items
                ],
            }
        except Exception as exc:
            logger.debug("suggestion: autocomplete failed: %s", exc)
            return {"section_type": "autocomplete", "title": "搜索建议", "queries": []}

    async def _get_trending(self, limit: int) -> dict:
        """热门搜索 query。"""
        if not self._trending:
            return {"section_type": "trending", "title": "热门搜索", "queries": []}
        try:
            queries = await self._trending.get_hot_queries_simple(window_minutes=30, limit=limit)
            if queries:
                return {
                    "section_type": "trending",
                    "title": "热门搜索",
                    "queries": [
                        {"query": q["query"], "type": "trending", "frequency": q.get("count", 0)} for q in queries
                    ],
                }
            # Redis 无数据, 使用静态兜底
            raise ValueError("no trending data")
        except Exception as exc:
            if "no trending data" not in str(exc):
                logger.debug("suggestion: trending failed: %s", exc)
        # 静态兜底
        return {
            "section_type": "trending",
            "title": "热门搜索",
            "queries": [
                {"query": kw, "type": "trending", "frequency": 0}
                for kw in ["手机", "笔记本电脑", "耳机", "运动鞋", "手表"]
            ],
        }

    async def _get_ai_suggestions(self, prefix: str, limit: int) -> dict:
        """AI 搜索建议 (从 Redis 缓存读取, 离线 LLM 生成)。"""
        if not self._memory:
            return {"section_type": "ai_suggestions", "title": "AI 推荐", "queries": []}
        try:
            key = self._cache_key(prefix)
            cached = await self._memory.cache_get(key)
            if cached:
                if isinstance(cached, str):
                    cached = json.loads(cached)
                if isinstance(cached, list):
                    return {
                        "section_type": "ai_suggestions",
                        "title": "AI 推荐",
                        "queries": [
                            {"query": q["query"], "type": "ai", "detail": q.get("detail", "")} for q in cached[:limit]
                        ],
                    }
            return {"section_type": "ai_suggestions", "title": "AI 推荐", "queries": []}
        except Exception as exc:
            logger.debug("suggestion: ai_suggestions failed: %s", exc)
            return {"section_type": "ai_suggestions", "title": "AI 推荐", "queries": []}

    async def _get_history(self, uid: str, limit: int) -> dict:
        """用户搜索历史。"""
        if not self._memory:
            return {"section_type": "history", "title": "搜索历史", "queries": []}
        try:
            history = await self._memory.get_search_history(uid, limit=limit)
            if not history:
                return {"section_type": "history", "title": "搜索历史", "queries": []}
            return {
                "section_type": "history",
                "title": "搜索历史",
                "queries": [{"query": q, "type": "history", "frequency": 0} for q in history],
            }
        except Exception as exc:
            logger.debug("suggestion: history failed: %s", exc)
            return {"section_type": "history", "title": "搜索历史", "queries": []}

    # ── 离线 AI 建议生成 ──

    async def generate_ai_suggestions(self, query: str, limit: int = 5) -> list[dict]:
        """LLM 生成对话式搜索建议 (离线调用)。

        例: "跑步鞋" → [
          {"query": "适合新手的缓震跑鞋推荐", "detail": "新手入门"},
          {"query": "轻便透气日常跑步鞋", "detail": "日常训练"},
        ]
        """
        if not self._llm:
            return []

        # 检查已有缓存
        key = self._cache_key(query)
        cached = await self._memory.cache_get(key)
        if cached:
            if isinstance(cached, str):
                cached = json.loads(cached)
            if isinstance(cached, list):
                return cached

        try:
            prompt = f"""为电商搜索词 "{query}" 生成 {limit} 条具体的搜索建议。每条建议附带一个简短的场景标签。

格式: JSON 数组 [{{"query": "具体搜索短语", "detail": "场景标签"}}]

要求:
- 建议要具体、多样化, 包含不同角度 (品牌、价格、功能、场景)
- detail 标签简短 (2-4字), 如 "新手入门"、"高性能"、"性价比"、"送礼"
- 仅输出 JSON 数组, 不要其他内容"""
            messages = [
                {"role": "system", "content": "你是电商搜索建议专家。只输出 JSON 数组。"},
                {"role": "user", "content": prompt},
            ]
            response = await self._llm.chat(messages=messages, temperature=0.5, max_tokens=300)
            content = response.content if hasattr(response, "content") else str(response)
            suggestions = self._parse_ai_suggestions(content, limit)
            if suggestions:
                await self._memory.cache_set(key, json.dumps(suggestions, ensure_ascii=False), ttl_s=_CACHE_TTL)
            return suggestions
        except Exception as exc:
            logger.debug("suggestion: generate_ai_suggestions failed for '%s': %s", query, exc)
            return []

    @staticmethod
    def _cache_key(query: str) -> str:
        h = hashlib.md5(query.strip().lower().encode()).hexdigest()[:16]
        return f"{_CACHE_PREFIX}:{h}"

    @staticmethod
    def _parse_ai_suggestions(raw: str, limit: int) -> list[dict]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return [
                    {"query": s.get("query", ""), "detail": s.get("detail", "")}
                    for s in parsed[:limit]
                    if isinstance(s, dict) and s.get("query")
                ]
        except json.JSONDecodeError:
            pass
        return []
