"""向量搜索服务 —— pgvector 余弦相似度查询。

用于:
  - Feature 1 Row 1: "猜你喜欢" vector recall (用户收藏商品 → 相似商品)
  - Feature 2: 混合搜索 (BM25 + vector fusion)

依赖:
  - pgvector 扩展 (已安装)
  - PmsProductEmbedding 表 (已创建, 1536-dim embeddings)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text

logger = logging.getLogger(__name__)


class VectorSearchService:
    """pgvector 余弦相似度搜索。

    用法:
        svc = VectorSearchService(db_factory=AsyncSessionLocal, memory=memory)
        similar = await svc.search_similar_by_product(product_id, limit=20)
    """

    def __init__(self, db_factory, memory) -> None:
        self._db_factory = db_factory
        self._memory = memory

    async def search_similar_by_product(
        self, product_id: UUID | str, limit: int = 20,
        category_id: str | None = None,
    ) -> list[dict]:
        """基于商品向量查找相似商品。

        SQL: SELECT e2.product_id, 1 - (e1.embedding <=> e2.embedding) AS similarity
             FROM pms_product_embeddings e1
             JOIN pms_product_embeddings e2 ON e1.product_id != e2.product_id
             JOIN pms_products p ON e2.product_id = p.id
             WHERE e1.product_id = :pid
               AND p.publish_status = 1 AND p.verify_status = 1 AND p.is_deleted = FALSE
             ORDER BY e1.embedding <=> e2.embedding
             LIMIT :limit
        """
        pid = str(product_id)
        async with self._db_factory() as db:
            query = text("""
                SELECT
                    e2.product_id,
                    1 - (e1.embedding <=> e2.embedding) AS similarity,
                    p.name,
                    p.price,
                    p.sale_count,
                    p.default_pic,
                    p.category_id,
                    p.stock
                FROM pms_product_embeddings e1
                JOIN pms_product_embeddings e2 ON e1.product_id != e2.product_id
                JOIN pms_products p ON e2.product_id = p.id
                WHERE e1.product_id = :pid
                  AND p.publish_status = 1
                  AND p.verify_status = 1
                  AND p.is_deleted = FALSE
            """)
            if category_id:
                query = text("""
                    SELECT
                        e2.product_id,
                        1 - (e1.embedding <=> e2.embedding) AS similarity,
                        p.name,
                        p.price,
                        p.sale_count,
                        p.default_pic,
                        p.category_id,
                        p.stock
                    FROM pms_product_embeddings e1
                    JOIN pms_product_embeddings e2 ON e1.product_id != e2.product_id
                    JOIN pms_products p ON e2.product_id = p.id
                    WHERE e1.product_id = :pid
                      AND p.publish_status = 1 AND p.verify_status = 1 AND p.is_deleted = FALSE
                      AND p.category_id = :cat_id
                    ORDER BY e1.embedding <=> e2.embedding
                    LIMIT :limit
                """)
                result = await db.execute(
                    query, {"pid": pid, "cat_id": category_id, "limit": limit},
                )
            else:
                result = await db.execute(
                    query, {"pid": pid, "limit": limit},
                )

            rows = result.fetchall()
            return [
                {
                    "product_id": str(r[0]),
                    "similarity": round(float(r[1]), 4),
                    "name": r[2] or "",
                    "price": float(r[3]) if r[3] else 0,
                    "sale_count": r[4] or 0,
                    "image_url": r[5] or "",
                    "category_id": str(r[6]) if r[6] else "",
                    "stock": r[7] or 0,
                    "score": round(float(r[1]), 4),
                    "_source": "vector",
                }
                for r in rows
            ]

    async def search_similar_by_favorites(
        self, user_id: UUID | str, limit: int = 20,
    ) -> list[dict]:
        """基于用户收藏商品的平均向量查找相似商品。

        如果用户有多个收藏, 取平均向量后查询;
        如果用户无收藏, 返回空列表。
        """
        uid = str(user_id)
        async with self._db_factory() as db:
            # 获取用户收藏的商品 ID
            fav_query = text("""
                SELECT f.product_id
                FROM ums_member_favorites f
                JOIN pms_product_embeddings e ON f.product_id = e.product_id
                WHERE f.user_id = :uid
                ORDER BY f.created_at DESC
                LIMIT 20
            """)
            result = await db.execute(fav_query, {"uid": uid})
            fav_ids = [str(r[0]) for r in result.fetchall()]

            if not fav_ids:
                return []

            # 平均向量查询
            avg_query = text("""
                SELECT
                    e2.product_id,
                    1 - (avg_e.avg_embedding <=> e2.embedding) AS similarity,
                    p.name, p.price, p.sale_count, p.default_pic, p.category_id, p.stock
                FROM (
                    SELECT AVG(e.embedding) AS avg_embedding
                    FROM pms_product_embeddings e
                    WHERE e.product_id = ANY(:fav_ids)
                ) avg_e
                CROSS JOIN pms_product_embeddings e2
                JOIN pms_products p ON e2.product_id = p.id
                WHERE e2.product_id != ALL(:fav_ids)
                  AND p.publish_status = 1 AND p.verify_status = 1 AND p.is_deleted = FALSE
                ORDER BY avg_e.avg_embedding <=> e2.embedding
                LIMIT :limit
            """)
            result = await db.execute(
                avg_query, {"fav_ids": fav_ids, "limit": limit},
            )
            rows = result.fetchall()
            return [
                {
                    "product_id": str(r[0]),
                    "similarity": round(float(r[1]), 4),
                    "name": r[2] or "",
                    "price": float(r[3]) if r[3] else 0,
                    "sale_count": r[4] or 0,
                    "image_url": r[5] or "",
                    "category_id": str(r[6]) if r[6] else "",
                    "stock": r[7] or 0,
                    "score": round(float(r[1]), 4),
                    "_source": "vector_fav",
                }
                for r in rows
            ]

    async def get_user_favorite_embedding(
        self, user_id: UUID | str,
    ) -> list[float] | None:
        """获取用户收藏商品的平均向量 (1536-dim), 缓存 1h。"""
        uid = str(user_id)
        cache_key = f"embedding:user_fav:{uid}"

        # 检查缓存
        cached = await self._memory.cache_get(cache_key)
        if cached:
            return cached

        async with self._db_factory() as db:
            query = text("""
                SELECT e.embedding
                FROM pms_product_embeddings e
                JOIN ums_member_favorites f ON e.product_id = f.product_id
                WHERE f.user_id = :uid
                ORDER BY f.created_at DESC
                LIMIT 10
            """)
            result = await db.execute(query, {"uid": uid})
            embeddings = [r[0] for r in result.fetchall() if r[0] is not None]

            if not embeddings:
                return None

            # 计算平均向量
            dim = len(embeddings[0])
            avg = [0.0] * dim
            for emb in embeddings:
                for i, v in enumerate(emb):
                    avg[i] += v
            avg = [v / len(embeddings) for v in avg]

            # 缓存 1h
            await self._memory.cache_set(cache_key, avg, ttl_s=3600)
            return avg

    async def search_by_text_embedding(
        self, embedding: list[float], limit: int = 20,
        category_id: str | None = None,
    ) -> list[dict]:
        """给定文本向量, 搜索最相似商品。

        用于 Feature 2: 将搜索 query embed 后做向量检索。
        """
        # 将 Python list 转为 pgvector 格式字符串
        emb_str = _format_vector(embedding)
        async with self._db_factory() as db:
            if category_id:
                query = text(f"""
                    SELECT
                        e.product_id,
                        1 - (e.embedding <=> '{emb_str}'::vector) AS similarity,
                        p.name, p.price, p.sale_count, p.default_pic, p.category_id, p.stock
                    FROM pms_product_embeddings e
                    JOIN pms_products p ON e.product_id = p.id
                    WHERE p.publish_status = 1 AND p.verify_status = 1 AND p.is_deleted = FALSE
                      AND p.category_id = :cat_id
                    ORDER BY e.embedding <=> '{emb_str}'::vector
                    LIMIT :limit
                """)
                result = await db.execute(
                    query, {"cat_id": category_id, "limit": limit},
                )
            else:
                query = text(f"""
                    SELECT
                        e.product_id,
                        1 - (e.embedding <=> '{emb_str}'::vector) AS similarity,
                        p.name, p.price, p.sale_count, p.default_pic, p.category_id, p.stock
                    FROM pms_product_embeddings e
                    JOIN pms_products p ON e.product_id = p.id
                    WHERE p.publish_status = 1 AND p.verify_status = 1 AND p.is_deleted = FALSE
                    ORDER BY e.embedding <=> '{emb_str}'::vector
                    LIMIT :limit
                """)
                result = await db.execute(query, {"limit": limit})

            rows = result.fetchall()
            return [
                {
                    "product_id": str(r[0]),
                    "similarity": round(float(r[1]), 4),
                    "name": r[2] or "",
                    "price": float(r[3]) if r[3] else 0,
                    "sale_count": r[4] or 0,
                    "image_url": r[5] or "",
                    "category_id": str(r[6]) if r[6] else "",
                    "stock": r[7] or 0,
                    "score": round(float(r[1]), 4),
                    "_source": "vector_text",
                }
                for r in rows
            ]


def _format_vector(embedding: list[float]) -> str:
    """将 Python float list 转为 pgvector 兼容的字符串 '[...]'。"""
    return "[" + ",".join(str(v) for v in embedding) + "]"
