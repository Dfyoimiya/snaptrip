"""EmbeddingService — 商品语义向量生成服务。

为 pms_product_embeddings 表生成 384 维语义向量:
  - 模型: all-MiniLM-L6-v2 (与 HybridSearchService 查询侧一致)
  - 输入文本: product.name + sub_title + keywords
  - 输出: pgvector Vector(384), normalize_embeddings=True

支持三种模式:
  - generate_all: 全量生成 (首次初始化)
  - generate_incremental: 增量生成 (仅无 embedding 的商品)
  - generate_single: 单品生成 (商品创建/更新时触发)

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product.embedding import PmsProductEmbedding
from app.models.product.product import PmsProduct

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_EMBEDDING_DIM = 384
_BATCH_SIZE = 64  # 每批 encode 的商品数


class EmbeddingService:
    """商品语义向量生成服务 —— 调用本地 sentence-transformers 模型。

    用法:
        svc = EmbeddingService(db_factory=AsyncSessionLocal)
        result = await svc.generate_incremental()
    """

    def __init__(self, db_factory) -> None:
        self._db_factory = db_factory

    # ── Public API ──────────────────────────────────────────────────────────

    async def generate_all(self) -> dict:
        """全量生成: 为所有已上架商品生成 embedding。

        适用场景: 首次初始化、模型升级后重建。
        """
        async with self._db_factory() as db:
            products = await self._fetch_published_products(db)
            if not products:
                return {"embedded": 0, "skipped": 0, "total": 0}

            texts, product_ids = self._build_texts(products)
            embeddings = await self._encode(texts)
            count = await self._upsert_embeddings(db, product_ids, embeddings)

        logger.info("embedding_service: generate_all complete, embedded=%d", count)
        return {"embedded": count, "skipped": 0, "total": len(products)}

    async def generate_incremental(self) -> dict:
        """增量生成: 仅为尚无 embedding 的已上架商品生成。

        适用场景: 定时 Celery 任务 (每小时)。
        """
        async with self._db_factory() as db:
            products = await self._fetch_products_without_embedding(db)
            if not products:
                return {"embedded": 0, "skipped": 0, "total": 0}

            texts, product_ids = self._build_texts(products)
            embeddings = await self._encode(texts)
            count = await self._upsert_embeddings(db, product_ids, embeddings)

        logger.info("embedding_service: generate_incremental complete, embedded=%d", count)
        return {"embedded": count, "skipped": 0, "total": len(products)}

    async def generate_single(self, product_id: str) -> bool:
        """单品生成: 为单个商品生成/更新 embedding。

        适用场景: 商品创建/更新后的信号触发。
        """
        async with self._db_factory() as db:
            stmt = (
                select(PmsProduct)
                .where(PmsProduct.id == product_id)
                .where(PmsProduct.publish_status == 1)
                .where(PmsProduct.is_deleted.is_(False))
            )
            result = await db.execute(stmt)
            product = result.scalar_one_or_none()
            if not product:
                logger.debug("embedding_service: product %s not found or not published", product_id)
                return False

            text = _build_product_text(product)
            embeddings = await self._encode([text])
            if embeddings:
                await self._upsert_embeddings(db, [str(product.id)], embeddings)

        return True

    # ── Internal ────────────────────────────────────────────────────────────

    async def _fetch_published_products(self, db: AsyncSession) -> list[PmsProduct]:
        stmt = (
            select(PmsProduct)
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_products_without_embedding(self, db: AsyncSession) -> list[PmsProduct]:
        """查询已上架但无 embedding 的商品 (LEFT JOIN + IS NULL)。"""
        stmt = (
            select(PmsProduct)
            .outerjoin(PmsProductEmbedding, PmsProduct.id == PmsProductEmbedding.product_id)
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
            .where(PmsProductEmbedding.product_id.is_(None))
            .limit(500)  # 单次增量上限，避免首次运行时太久
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _build_texts(products: list[PmsProduct]) -> tuple[list[str], list[str]]:
        """构建 encode 输入文本 + 对应的 product_id 列表。"""
        texts: list[str] = []
        pids: list[str] = []
        for p in products:
            texts.append(_build_product_text(p))
            pids.append(str(p.id))
        return texts, pids

    async def _encode(self, texts: list[str]) -> list[list[float]]:
        """分批调用 sentence-transformers 生成 384 维向量。"""
        model = _get_embedding_model()
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            embeddings = await asyncio.to_thread(
                model.encode, batch, normalize_embeddings=True
            )
            all_embeddings.extend(embeddings.tolist())
        return all_embeddings

    @staticmethod
    async def _upsert_embeddings(
        db: AsyncSession,
        product_ids: list[str],
        embeddings: list[list[float]],
    ) -> int:
        """UPSERT embeddings into pms_product_embeddings via raw SQL.

        使用 ON CONFLICT DO UPDATE 确保幂等性。
        """
        if not product_ids or not embeddings:
            return 0

        import uuid as _uuid

        rows = []
        for pid, emb in zip(product_ids, embeddings, strict=False):
            vec_str = f"[{','.join(str(v) for v in emb)}]"
            rows.append(
                f"('{_uuid.uuid4()}', '{pid}', '{vec_str}'::vector({_EMBEDDING_DIM}), '{_MODEL_NAME}')"
            )

        sql = text(
            f"INSERT INTO pms_product_embeddings (id, product_id, embedding, model_name) "
            f"VALUES {','.join(rows)} "
            f"ON CONFLICT (product_id) DO UPDATE SET "
            f"embedding = EXCLUDED.embedding, "
            f"model_name = EXCLUDED.model_name, "
            f"updated_at = NOW()"
        )
        result = await db.execute(sql)
        await db.commit()
        return result.rowcount or len(product_ids)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_product_text(product: PmsProduct) -> str:
    """从商品字段拼接编码文本。"""
    parts = [product.name or ""]
    if product.sub_title:
        parts.append(product.sub_title)
    if product.keywords:
        parts.append(product.keywords)
    return " ".join(parts).strip()


# ── Lazy model singleton ────────────────────────────────────────────────────

_embedding_model: Any = None


def _get_embedding_model():
    """懒加载 sentence-transformers 模型 (线程安全, 单例)。

    与 HybridSearchService._get_local_embedding_model() 共用同一个模型实例。
    """
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(_MODEL_NAME, local_files_only=True)
        logger.info("embedding_service: model loaded (%s)", _MODEL_NAME)
    return _embedding_model
