"""查询扩展服务 —— LLM 离线查询扩展 + Redis 缓存。

为 head queries (高频搜索词) 生成扩展查询, 存储在 Redis 中。
在线查询时 sub-ms 获取, 不影响搜索延迟。

流程:
  - 离线: 定时任务 → top N 高频查询 → LLM 扩展 → Redis query_expand:{md5[:16]}
  - 在线: 搜索时查询 Redis → 合并扩展词 → 提升召回率

用法:
    svc = QueryExpansionService(memory)
    expanded = await svc.get_expanded_queries("跑步鞋")
    # → ["轻便透气跑步鞋", "减震跑鞋", "新手跑步鞋推荐"]

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import hashlib
import json
import logging

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "query_expand"
_CACHE_TTL = 86400 * 7  # 7 天


class QueryExpansionService:
    """LLM 查询扩展服务 (离线生成 + Redis 缓存)。"""

    def __init__(self, memory, llm_adapter=None) -> None:
        self._memory = memory
        self._llm = llm_adapter

    async def get_expanded_queries(self, query: str, limit: int = 5) -> list[str]:
        """获取扩展查询 (在线, sub-ms)。"""
        if not query or len(query) < 2:
            return []

        key = self._cache_key(query)
        try:
            cached = await self._memory.cache_get(key)
            if cached:
                if isinstance(cached, str):
                    cached = json.loads(cached)
                return cached[:limit] if isinstance(cached, list) else []
        except Exception:
            pass

        return []

    async def expand_and_cache(self, query: str, limit: int = 5) -> list[str]:
        """LLM 扩展查询并缓存 (离线调用)。

        预算:
          - 输入: ~20 tokens
          - 输出: ~50 tokens
          - 总: ~70 tokens/query
        """
        if not self._llm:
            return []

        existing = await self.get_expanded_queries(query, limit)
        if existing:
            return existing

        try:
            prompt = f"""将电商搜索词扩展为 {limit} 个具体的搜索短语。扩展词应包含同义词、长尾变体、属性限定词。

原始搜索词: "{query}"

只输出 JSON 字符串数组, 不要其他内容。"""
            messages = [
                {"role": "system", "content": "你是电商搜索查询扩展专家。只输出 JSON 数组。"},
                {"role": "user", "content": prompt},
            ]
            response = await self._llm.chat(messages=messages, temperature=0.3, max_tokens=200)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON 数组
            expanded = self._parse_expansion(content, limit)
            if expanded:
                key = self._cache_key(query)
                await self._memory.cache_set(key, json.dumps(expanded, ensure_ascii=False), ttl_s=_CACHE_TTL)
                return expanded
        except Exception as exc:
            logger.debug("query_expansion: LLM expansion failed for '%s': %s", query, exc)

        return []

    async def build_index_batch(
        self,
        queries: list[str],
        top_n: int = 200,
    ) -> int:
        """批量构建查询扩展索引 (离线任务)。

        为 top N 查询生成 LLM 扩展, 存入 Redis。
        返回成功数。
        """
        if not self._llm:
            return 0

        success = 0
        for query in queries[:top_n]:
            try:
                existing = await self.get_expanded_queries(query)
                if existing:
                    success += 1
                    continue
                expanded = await self.expand_and_cache(query)
                if expanded:
                    success += 1
            except Exception as exc:
                logger.debug("query_expansion: batch build failed for '%s': %s", query, exc)

        logger.info("query_expansion: batch build complete, success=%d/%d", success, min(len(queries), top_n))
        return success

    @staticmethod
    def _cache_key(query: str) -> str:
        h = hashlib.md5(query.strip().lower().encode()).hexdigest()[:16]
        return f"{_CACHE_PREFIX}:{h}"

    @staticmethod
    def _parse_expansion(raw: str, limit: int) -> list[str]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
        try:
            parsed = json.loads(text.strip())
            if isinstance(parsed, list):
                return [str(s) for s in parsed[:limit] if s and isinstance(s, str)]
        except json.JSONDecodeError:
            pass
        return []
