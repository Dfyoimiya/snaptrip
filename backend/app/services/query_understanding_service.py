"""QueryUnderstandingService — 查询理解统一层。

四步管道:
  1. 意图分类: 规则匹配 (80%+ 覆盖) + LLM 兜底
  2. 实体抽取: LLM 提取 category, brand, price_range, attributes
  3. 查询改写/扩展: 规则 + LLM + Redis 缓存 (委托 QueryExpansionService)
  4. 向量化: all-MiniLM-L6-v2 384 维 (用于语义召回)

输出: QueryUnderstandingResult
  - intent: transactional | navigational | informational
  - weights: 5-channel fusion weights
  - entities: {category, brand, price_min, price_max, attributes}
  - rewritten_query: 改写后的查询 (用于 ES 召回)
  - expanded_queries: 扩展查询列表 (用于多 query 召回)
  - embedding: 384 维查询向量 (用于 pgvector 召回)

使用场景:
  - HybridSearchService 混合搜索
  - RecallService 多路召回
  - Agent Pipeline ProductRecAgent

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Intent Classification ─────────────────────────────────────────────────────

_TRANSACTIONAL_KEYWORDS = [
    "买", "购", "价格", "便宜", "折扣", "优惠", "促销", "包邮",
    "下单", "现货", "秒杀", "特价", "清仓", "限时", "满减",
    "buy", "cheap", "discount", "sale", "deal", "price",
]
_NAVIGATIONAL_KEYWORDS = [
    "品牌", "官方", "旗舰店", "正品", "专卖",
    "brand", "official", "store",
]
_INFORMATIONAL_KEYWORDS = [
    "什么", "怎么", "如何", "哪个", "推荐", "排行", "对比",
    "测评", "怎么样", "好不好", "值得", "适合", "新手",
    "best", "vs", "compare", "review", "recommend", "top",
    "how", "what", "which", "guide",
]

INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    # BM25 权重已提升：ES + ik_max_word 中文分词后精确度显著提高
    # brand 权重: navigational 最高 (用户搜品牌), transactional 中 (品牌影响购买), informational 低
    "transactional": {"bm25": 0.35, "vector": 0.15, "cf": 0.10, "price": 0.18, "category": 0.12, "brand": 0.10},
    "navigational":  {"bm25": 0.60, "vector": 0.05, "cf": 0.05, "price": 0.05, "category": 0.10, "brand": 0.15},
    "informational": {"bm25": 0.25, "vector": 0.30, "cf": 0.10, "price": 0.05, "category": 0.15, "brand": 0.15},
}

# ── Entity Extraction ─────────────────────────────────────────────────────────

ENTITY_EXTRACTION_PROMPT = """你是一个电商查询实体抽取器。从用户搜索词中提取结构化信息。

用户搜索词: "{query}"

请输出 JSON:
{{
  "category": "商品类目 (如 笔记本电脑/运动鞋/护肤品, 无则为 null)",
  "brand": "品牌名 (如 华为/Nike/苹果, 无则为 null)",
  "price_min": 最低价格数值或 null,
  "price_max": 最高价格数值或 null,
  "attributes": ["属性1", "属性2"],
  "search_type": "精确搜索" | "模糊浏览" | "条件筛选"
}}

只输出 JSON, 不要其他内容。"""


@dataclass
class QueryEntities:
    """从查询中抽取的结构化实体。"""
    category: str | None = None
    brand: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    attributes: list[str] = field(default_factory=list)
    search_type: str = "模糊浏览"


@dataclass
class QueryUnderstandingResult:
    """查询理解的完整输出。"""
    intent: str = "navigational"
    weights: dict[str, float] = field(default_factory=dict)
    entities: QueryEntities = field(default_factory=QueryEntities)
    original_query: str = ""
    rewritten_query: str = ""
    expanded_queries: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    confidence: float = 0.5

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "weights": self.weights,
            "entities": {
                "category": self.entities.category,
                "brand": self.entities.brand,
                "price_min": self.entities.price_min,
                "price_max": self.entities.price_max,
                "attributes": self.entities.attributes,
                "search_type": self.entities.search_type,
            },
            "rewritten_query": self.rewritten_query,
            "expanded_queries": self.expanded_queries,
        }


class QueryUnderstandingService:
    """查询理解统一服务。

    用法:
        svc = QueryUnderstandingService(llm_adapter=adapter, memory=memory)
        result = await svc.understand("学生平价笔记本电脑")
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        memory: Any = None,
        model_alias: str = "",
        enable_thinking: bool = False,
        # ── Per-step model selection ──
        model_intent: str = "qwen3.6-flash",
        model_entity: str = "qwen3.6-flash",
        model_rewrite: str = "qwen3.6-plus",
    ) -> None:
        self._llm = llm_adapter
        self._memory = memory
        self._model_alias = model_alias  # fallback for backward compat
        self._enable_thinking = enable_thinking
        self._model_intent = model_intent or model_alias
        self._model_entity = model_entity or model_alias
        self._model_rewrite = model_rewrite or model_alias

    async def understand(
        self,
        query: str,
        *,
        with_embedding: bool = True,
        with_expansion: bool = False,
    ) -> QueryUnderstandingResult:
        """执行完整查询理解管道。

        Args:
            query: 原始查询字符串
            with_embedding: 是否生成查询向量 (用于语义召回)
            with_expansion: 是否执行查询扩展 (用于多 query 召回)
        """
        q = query.strip()
        result = QueryUnderstandingResult(original_query=q)

        if not q:
            result.intent = "navigational"
            result.weights = INTENT_WEIGHTS["navigational"]
            result.confidence = 1.0
            return result

        # Step 1: Intent classification
        intent = _classify_intent_rules(q)
        if intent:
            result.intent = intent
            result.weights = dict(INTENT_WEIGHTS[intent])
            result.confidence = 0.85
        elif self._llm:
            try:
                intent = await self._llm_classify(q)
                result.intent = intent
                result.weights = dict(INTENT_WEIGHTS.get(intent, INTENT_WEIGHTS["navigational"]))
                result.confidence = 0.70
            except Exception as exc:
                logger.debug("query_understanding: LLM intent failed: %s", exc)
                result.weights = dict(INTENT_WEIGHTS["navigational"])
        else:
            result.weights = dict(INTENT_WEIGHTS["navigational"])

        # Step 2: Entity extraction (LLM only)
        if self._llm:
            try:
                result.entities = await self._extract_entities(q)
            except Exception as exc:
                logger.debug("query_understanding: entity extraction failed: %s", exc)

        # Step 3: Query rewrite (LLM preferred, rule fallback)
        result.rewritten_query = await self._rewrite_query_llm(q, result.entities, result.intent)

        # Step 4: Query expansion (Redis cache + LLM)
        if with_expansion and self._memory:
            try:
                from app.services.query_expansion_service import QueryExpansionService

                expand_svc = QueryExpansionService(self._memory, self._llm)
                result.expanded_queries = await expand_svc.get_expanded_queries(q, limit=5)
            except Exception as exc:
                logger.debug("query_understanding: expansion failed: %s", exc)

        # Step 5: Vectorization
        if with_embedding:
            try:
                result.embedding = await self._vectorize(q)
            except Exception as exc:
                logger.debug("query_understanding: vectorization failed: %s", exc)

        return result

    # ── Intent Classification ─────────────────────────────────────────────

    async def _llm_classify(self, query: str) -> str:
        prompt = (
            f'用户搜索词: "{query}"\n'
            "意图类型: transactional(明确购买意图) / "
            "navigational(搜索特定品类/品牌) / "
            "informational(信息搜集/对比/求推荐)\n"
            "只回复一个单词。"
        )
        messages = [
            {"role": "system", "content": "只回复一个单词: transactional, navigational, 或 informational"},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.chat(
            messages=messages,
            model_alias=self._model_intent,
            temperature=0.1,
            max_tokens=16,
            enable_thinking=False,
        )
        content = (
            (response.content if hasattr(response, "content") else str(response))
            .strip()
            .lower()
        )
        if content in ("transactional", "navigational", "informational"):
            return content
        return "navigational"

    # ── Entity Extraction ─────────────────────────────────────────────────

    async def _extract_entities(self, query: str) -> QueryEntities:
        prompt = ENTITY_EXTRACTION_PROMPT.format(query=query)
        messages = [
            {"role": "system", "content": "只输出 JSON，不要其他内容。"},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.chat(
            messages=messages,
            model_alias=self._model_entity,
            temperature=0.2,
            max_tokens=256,
            enable_thinking=False,
        )
        raw = (response.content if hasattr(response, "content") else str(response)).strip()
        return _parse_entities(raw)

    # ── Query Rewrite ─────────────────────────────────────────────────────

    async def _rewrite_query_llm(
        self, query: str, entities: QueryEntities, intent: str
    ) -> str:
        """LLM-based query rewrite, with rule-based fallback.

        Generates an optimized search query by:
        - Expanding abbreviations and synonyms
        - Adding relevant category/brand context
        - Adapting language to the search intent
        """
        # Try LLM rewrite when available (放宽条件: 任何非短查询都尝试改写)
        if self._llm and len(query) >= 2:
            try:
                rewritten = await self._llm_rewrite(query, entities, intent)
                if rewritten and rewritten != query:
                    return rewritten
            except Exception as exc:
                logger.debug("query_understanding: LLM rewrite failed: %s", exc)

        # Fallback: rule-based rewrite
        return _rewrite_query_rules(query, entities)

    async def _llm_rewrite(
        self, query: str, entities: QueryEntities, intent: str
    ) -> str:
        """Call LLM to rewrite query for better search recall."""
        entity_ctx = []
        if entities.category:
            entity_ctx.append(f"类目: {entities.category}")
        if entities.brand:
            entity_ctx.append(f"品牌: {entities.brand}")
        if entities.attributes:
            entity_ctx.append(f"属性: {', '.join(entities.attributes[:3])}")
        entity_str = "; ".join(entity_ctx) if entity_ctx else "无"

        channel_hint = {
            "transactional": "侧重价格、促销、购买相关词汇",
            "navigational": "侧重品牌、型号、品类精确词汇",
            "informational": "侧重功能、场景、对比属性词汇",
        }.get(intent, "")

        prompt = f"""你是电商搜索查询改写专家。将用户搜索词改写为更适合搜索引擎召回的关键词组合。

原始查询: "{query}"
抽取的实体: {entity_str}
搜索意图: {intent}
改写策略: {channel_hint}

规则:
1. 保留原查询的核心语义
2. 补充缺失的关键属性词
3. 扩展同义词和相关词
4. 去掉语气词和标点
5. 仅输出改写后的查询文本，不要解释

改写后的查询:"""

        messages = [
            {"role": "system", "content": "你是电商搜索查询改写专家。只输出改写后的查询文本。"},
            {"role": "user", "content": prompt},
        ]
        response = await self._llm.chat(
            messages=messages,
            model_alias=self._model_rewrite,
            temperature=0.3,
            max_tokens=128,
            enable_thinking=False,
        )
        rewritten = (
            (response.content if hasattr(response, "content") else str(response))
            .strip()
            .strip('"')
        )
        if rewritten and len(rewritten) >= 2:
            return rewritten
        return query

    # ── Vectorization ─────────────────────────────────────────────────────

    @staticmethod
    async def _vectorize(query: str) -> list[float] | None:
        """生成 384 维查询向量 (复用 HybridSearchService 的模型)。"""
        try:
            from app.services.hybrid_search_service import _get_local_embedding_model

            model = _get_local_embedding_model()
            embedding = await asyncio.to_thread(
                model.encode, query, normalize_embeddings=True
            )
            return embedding.tolist()
        except Exception as exc:
            logger.debug("query_understanding: local embedding failed: %s", exc)
            return None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _rewrite_query_rules(query: str, entities: QueryEntities) -> str:
    """基于实体进行规则改写: 补充缺失的关键词维度。

    同时做基本的查询清洁: 去除标点/多余空格, 保留核心搜索词。
    当 LLM 不可用时作为降级方案。
    """
    import re

    # 1. 基础清洁: 去除标点符号（保留中英文关键词）
    cleaned = re.sub(r'[，,。！!？?、；;：:（）()【】\[\]《》""''\s]+', ' ', query).strip()

    # 2. 实体补充
    parts = [cleaned] if cleaned else [query]
    if entities.brand and entities.brand.lower() not in query.lower():
        parts.append(entities.brand)
    if entities.category and entities.category not in query:
        parts.append(entities.category)
    if entities.attributes:
        for attr in entities.attributes[:2]:
            if attr not in query:
                parts.append(attr)

    return " ".join(parts) if len(parts) > 1 else cleaned if cleaned else query


def _classify_intent_rules(query: str) -> str | None:
    """规则匹配意图分类, 返回 None 表示无法确定。

    按最高匹配数选择意图, 平局时 informational > transactional > navigational。
    """
    q = query.lower()
    i_score = sum(1 for kw in _INFORMATIONAL_KEYWORDS if kw in q)
    t_score = sum(1 for kw in _TRANSACTIONAL_KEYWORDS if kw in q)
    n_score = sum(1 for kw in _NAVIGATIONAL_KEYWORDS if kw in q)

    if i_score == t_score == n_score == 0:
        return None

    best = max(
        (i_score, "informational"),
        (t_score, "transactional"),
        (n_score, "navigational"),
    )
    return best[1] if best[0] > 0 else None


def _parse_entities(raw: str) -> QueryEntities:
    """Parse LLM JSON response into QueryEntities."""
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else cleaned
        data = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        return QueryEntities()

    return QueryEntities(
        category=data.get("category"),
        brand=data.get("brand"),
        price_min=_to_float_or_none(data.get("price_min")),
        price_max=_to_float_or_none(data.get("price_max")),
        attributes=list(data.get("attributes", []) or [])[:5],
        search_type=data.get("search_type", "模糊浏览"),
    )


def _to_float_or_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
