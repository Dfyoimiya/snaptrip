"""DiversityService — 搜索结果多样性重排。

提供两种算法:
  1. Category Spread (轻量, 推荐): 确保 Top-N 中类目分散
     已选同 category 商品 ≥ 2 个时, 下一个同 category 的打 0.7 折
     确保首页 ≥ 3 个不同类目

  2. MMR (Maximal Marginal Relevance, 需要 embedding):
     λ × relevance - (1-λ) × max_similarity
     平衡相关性与多样性

使用场景:
  - HybridSearchService 融合后 top-N 重排
  - HomeFeed 猜你喜欢多样性保障
  - Agent Pipeline 推荐结果后处理

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DiversityService:
    """搜索结果多样性重排服务。

    用法:
        svc = DiversityService()
        diverse = svc.apply_category_spread(products, top_n=10, min_categories=3)
    """

    # ── Category Spread (轻量算法) ─────────────────────────────────────────

    @staticmethod
    def apply_category_spread(
        products: list[dict],
        top_n: int = 10,
        min_categories: int = 3,
        max_per_category: int = 2,
        penalty: float = 0.70,
    ) -> list[dict]:
        """类目分散重排: 限制每个类目的最大出现次数。

        算法:
          for each product in sorted order:
            if count(category) >= max_per_category:
              score *= penalty  → 重新排序
            add to result

        Args:
            products: 排序后的商品列表 [{score, category_id, ...}]
            top_n: 返回数量
            min_categories: 最少不同类目数
            max_per_category: 每个类目最多出现次数
            penalty: 折扣系数 (0 < penalty < 1)

        Returns:
            多样性调整后的 Top-N 商品列表
        """
        if not products or len(products) <= top_n:
            return products

        # Step 1: 对每个商品标记类目计数并打折
        category_counts: dict[str, int] = {}
        penalized: list[dict] = []

        for p in products:
            cat_id = str(p.get("category_id", "")) or "__unknown__"
            count = category_counts.get(cat_id, 0)
            item = dict(p)

            if count >= max_per_category:
                item["score"] = round(item.get("score", 0) * penalty, 4)
                item["_diversity_penalized"] = True

            category_counts[cat_id] = count + 1
            penalized.append(item)

        # Step 2: 按调整后分数重新排序
        penalized.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Step 3: 选取 top_n, 确保最少 min_categories 个不同类目
        result: list[dict] = []
        seen_cats: set[str] = set()

        for p in penalized:
            if len(result) >= top_n:
                break
            cat_id = str(p.get("category_id", "")) or "__unknown__"
            result.append(p)
            seen_cats.add(cat_id)

        # Step 4: 如果类目数不足 min_categories, 从剩余中补充不同类目
        if len(seen_cats) < min_categories and len(result) < len(penalized):
            for p in penalized:
                if len(result) >= top_n:
                    break
                cat_id = str(p.get("category_id", "")) or "__unknown__"
                if cat_id not in seen_cats:
                    result.append(p)
                    seen_cats.add(cat_id)

        logger.debug(
            "diversity: category_spread input=%d output=%d categories=%d",
            len(products),
            len(result),
            len(seen_cats),
        )
        return result[:top_n]

    # ── MMR (需要 embedding) ───────────────────────────────────────────────

    @staticmethod
    def apply_mmr(
        products: list[dict],
        top_n: int = 10,
        lambda_: float = 0.70,
    ) -> list[dict]:
        """MMR (Maximal Marginal Relevance) 多样性重排。

        MMR = λ × relevance_score - (1-λ) × max_similarity

        需要商品包含 _embedding 字段 (list[float])。

        Args:
            products: 排序后的商品列表 [{score, _embedding, ...}]
            top_n: 返回数量
            lambda_: 相关性/多样性权衡 (0-1, 越大越重相关性)

        Returns:
            MMR 重排后的 Top-N 商品列表
        """
        if not products or len(products) <= 1:
            return products[:top_n]

        # Separate products with/without embeddings to avoid bias:
        # non-embedded products would get max_sim=0 (unfair advantage in MMR)
        embedded = [p for p in products if p.get("_embedding")]
        non_embedded = [p for p in products if not p.get("_embedding")]

        if len(embedded) < 2:
            # Not enough embedded products for meaningful MMR
            logger.debug("diversity: MMR skipped, only %d products with embeddings", len(embedded))
            # Sort by score, interleave non-embedded at natural positions
            result = sorted(products, key=lambda x: x.get("score", 0), reverse=True)
            return result[:top_n]

        remaining = list(embedded)
        selected: list[dict] = []

        # 第一个商品: 选相关性最高的 (from embedded)
        first = max(remaining, key=lambda x: x.get("score", 0))
        selected.append(first)
        remaining.remove(first)

        while len(selected) < top_n and remaining:
            best_item = None
            best_mmr = float("-inf")

            for p in remaining:
                relevance = p.get("score", 0)

                # 计算与已选商品的最大相似度
                max_sim = 0.0
                p_emb = p.get("_embedding")
                if p_emb:
                    for s in selected:
                        s_emb = s.get("_embedding")
                        if s_emb:
                            sim = _cosine_similarity(p_emb, s_emb)
                            max_sim = max(max_sim, sim)

                mmr = lambda_ * relevance - (1 - lambda_) * max_sim
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_item = p

            if best_item:
                selected.append(best_item)
                remaining.remove(best_item)
            else:
                break

        # 补充剩余 embedded (如果 MMR 未能填满 top_n)
        if len(selected) < top_n and remaining:
            selected.extend(remaining[: top_n - len(selected)])

        # 追加 non-embedded 商品 (按相关性排序, 放在 MMR 结果之后)
        if len(selected) < top_n and non_embedded:
            non_embedded.sort(key=lambda x: x.get("score", 0), reverse=True)
            selected.extend(non_embedded[: top_n - len(selected)])

        logger.debug(
            "diversity: MMR input=%d embedded=%d non_embedded=%d output=%d lambda=%.2f",
            len(products),
            len(embedded),
            len(non_embedded),
            len(selected),
            lambda_,
        )
        return selected[:top_n]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。

    假设输入向量已归一化 (单位向量), 则 cos_sim = dot(a, b)。
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    # 如果向量已归一化, dot 直接是余弦相似度
    # 否则需要除以模长
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
