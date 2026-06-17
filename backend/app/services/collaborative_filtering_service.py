"""协同过滤推荐服务 —— ALS 隐因子模型训练 + 推理。

基于 implicit 库的 ALS (Alternating Least Squares) 算法:
  - 离线: 从 ums_member_behaviors 构建 user-item 稀疏矩阵 → 训练 ALS
  - 产出: item vectors → pms_product_cf_vectors (pgvector), user vectors → Redis
  - 在线: 取用户向量 → pgvector ANN 搜索 → 返回相似商品

行为权重 (behavior_type → confidence):
  - view: 1.0 (低置信度)
  - search: 2.0
  - favorite: 2.0
  - add_cart: 3.0
  - purchase: 5.0 (最高置信度)

ALS 参数:
  - factors=64 (隐因子维度, 匹配 pms_product_cf_vectors.cf_vector)
  - regularization=0.1
  - iterations=15

用法:
    svc = CollaborativeFilteringService(db_factory, memory)
    await svc.train()                         # 离线训练
    recs = await svc.recommend(user_id, n=20)  # 在线推荐

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

logger = logging.getLogger(__name__)

# 行为 → 置信度权重
_BEHAVIOR_WEIGHTS: dict[str, float] = {
    "view": 1.0,
    "search": 2.0,
    "favorite": 2.0,
    "add_cart": 3.0,
    "purchase": 5.0,
}


class CollaborativeFilteringService:
    """ALS 协同过滤训练 + 推理服务。"""

    def __init__(self, db_factory, memory) -> None:
        self._db_factory = db_factory
        self._memory = memory

    # ── 训练 ────────────────────────────────────────────────────────

    async def train(self) -> dict[str, Any]:
        """全量训练 ALS 模型, 产出 item/user vectors 并持久化。

        Returns:
            {"model_version": str, "n_users": int, "n_items": int,
             "sparsity": float, "elapsed_s": float}
        """
        import time as _time

        t0 = _time.monotonic()

        # 1. 构建 user-item 稀疏矩阵
        user_ids, item_ids, matrix = await self._build_user_item_matrix()
        n_users = len(user_ids)
        n_items = len(item_ids)

        if n_users < 5 or n_items < 10:
            logger.warning("cf_train: insufficient data (users=%d, items=%d), skipping", n_users, n_items)
            return {"model_version": "", "n_users": n_users, "n_items": n_items, "sparsity": 0.0, "elapsed_s": 0.0, "skipped": True}

        sparsity = 1.0 - (matrix.nnz / (n_users * n_items))
        logger.info("cf_train: matrix (%d × %d), %d interactions, sparsity=%.4f", n_users, n_items, matrix.nnz, sparsity)

        # 2. 训练 ALS
        from implicit.als import AlternatingLeastSquares

        model = AlternatingLeastSquares(
            factors=64,
            regularization=0.1,
            iterations=15,
            random_state=42,
        )

        # implicit ALS.fit() expects users × items CSR matrix
        model.fit(matrix, show_progress=False)

        # 3. 提取向量
        item_factors = model.item_factors  # (n_items, 64)
        user_factors = model.user_factors  # (n_users, 64)

        logger.debug("cf_train: item_factors=%s, user_factors=%s, item_ids=%d",
                     item_factors.shape, user_factors.shape, len(item_ids))

        model_version = f"als-v{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

        # 4. 持久化 item vectors → PostgreSQL
        await self._save_item_vectors(item_ids, item_factors, model_version)

        # 5. 持久化 user vectors → Redis
        await self._save_user_vectors(user_ids, user_factors, model_version)

        elapsed = _time.monotonic() - t0
        logger.info("cf_train: done — model=%s, users=%d, items=%d, elapsed=%.1fs", model_version, n_users, n_items, elapsed)

        return {
            "model_version": model_version,
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": int(matrix.nnz),
            "sparsity": round(sparsity, 4),
            "elapsed_s": round(elapsed, 1),
        }

    async def _build_user_item_matrix(self) -> tuple[list[str], list[str], csr_matrix]:
        """从 ums_member_behaviors 构建 user-item 稀疏矩阵。"""
        from sqlalchemy import text

        async with self._db_factory() as db:
            # 查询有 user_id 且 item_id 非空的交互记录
            query = text("""
                SELECT user_id::text, item_id::text, behavior_type, COUNT(*) AS cnt
                FROM ums_member_behaviors
                WHERE user_id IS NOT NULL
                  AND item_id IS NOT NULL
                  AND behavior_type IN ('view', 'search', 'favorite', 'add_cart', 'purchase')
                GROUP BY user_id, item_id, behavior_type
            """)
            result = await db.execute(query)
            rows = result.fetchall()

        if not rows:
            return [], [], csr_matrix((0, 0))

        # 构建 ID 映射
        user_set: dict[str, int] = {}
        item_set: dict[str, int] = {}
        for row in rows:
            uid = row[0]
            iid = row[1]
            if uid not in user_set:
                user_set[uid] = len(user_set)
            if iid not in item_set:
                item_set[iid] = len(item_set)

        # 构建 COO 矩阵 (加权)
        row_indices = []
        col_indices = []
        values = []
        for row in rows:
            uid = row[0]
            iid = row[1]
            behavior = row[2]
            cnt = row[3]
            weight = _BEHAVIOR_WEIGHTS.get(behavior, 1.0) * cnt
            # implicit 使用 (items × users) 的置信度矩阵
            # 这里构建 (users × items) → 后续转置
            row_indices.append(user_set[uid])
            col_indices.append(item_set[iid])
            values.append(weight)

        user_list = [""] * len(user_set)
        item_list = [""] * len(item_set)
        for uid, idx in user_set.items():
            user_list[idx] = uid
        for iid, idx in item_set.items():
            item_list[idx] = iid

        coo = coo_matrix((values, (row_indices, col_indices)), shape=(len(user_set), len(item_set)))
        return user_list, item_list, coo.tocsr()

    async def _save_item_vectors(
        self, item_ids: list[str], item_factors: np.ndarray, model_version: str,
    ) -> None:
        """将 item 隐因子向量写入 pms_product_cf_vectors (pgvector)。

        item_factors shape = (n_items, 64), item_ids 是各 item 的原始 ID 列表。
        """
        from sqlalchemy import delete
        from sqlalchemy import text as sqla_text

        from app.models.product.cf_vector import PmsProductCFVector

        n_factors = item_factors.shape[0]
        n_ids = len(item_ids)
        if n_factors != n_ids:
            logger.warning("cf_train: item_factors shape[0]=%d != len(item_ids)=%d, truncating", n_factors, n_ids)

        async with self._db_factory() as db:
            await db.execute(delete(PmsProductCFVector))
            await db.commit()

            for i in range(min(n_factors, n_ids)):
                iid = item_ids[i]
                vec_list = item_factors[i].tolist()
                vec_str = "[" + ",".join(f"{v:.8f}" for v in vec_list) + "]"
                await db.execute(
                    sqla_text(
                        "INSERT INTO pms_product_cf_vectors (id, product_id, cf_vector, model_version) "
                        "VALUES (gen_random_uuid(), CAST(:pid AS uuid), CAST(:vec AS vector(64)), :ver)"
                    ),
                    {"pid": iid, "vec": vec_str, "ver": model_version},
                )
            await db.commit()

        logger.info("cf_train: saved %d item vectors (version=%s)", min(n_factors, n_ids), model_version)

    async def _save_user_vectors(
        self, user_ids: list[str], user_factors: np.ndarray, model_version: str,
    ) -> None:
        """将 user 隐因子向量写入 Redis (7天 TTL), JSON 字符串格式。"""
        import json

        pipe = await self._memory.client.pipeline()
        for i, uid in enumerate(user_ids):
            key = f"cf_user:{uid}"
            vec = user_factors[i].astype(np.float32).tolist()
            await pipe.set(key, json.dumps(vec), ex=604800)  # 7 天 TTL
        await pipe.execute()

        logger.info("cf_train: saved %d user vectors to Redis (version=%s)", len(user_ids), model_version)

    # ── 推理 ────────────────────────────────────────────────────────

    async def recommend(
        self, user_id: UUID | str, n: int = 20, exclude_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """基于用户协同过滤向量召回商品。

        Returns:
            [{"product_id": str, "score": float, "_source": "cf"}, ...]
        """
        uid = str(user_id)

        # 1. 获取用户向量
        user_vec = await self._get_user_vector(uid)
        if user_vec is None:
            return []

        # 2. pgvector ANN 搜索
        exclude_clause = ""
        params: dict[str, Any] = {"vec": user_vec, "n": n * 2}

        if exclude_ids:
            placeholders = ", ".join(f":excl_{i}" for i in range(len(exclude_ids)))
            exclude_clause = f"AND product_id::text NOT IN ({placeholders})"
            for i, pid in enumerate(exclude_ids):
                params[f"excl_{i}"] = str(pid)

        from sqlalchemy import text as sqla_text

        async with self._db_factory() as db:
            query = sqla_text(f"""
                SELECT v.product_id::text, 1 - (v.cf_vector <=> CAST(:vec AS vector(64))) AS similarity
                FROM pms_product_cf_vectors v
                JOIN pms_products p ON v.product_id = p.id
                WHERE p.publish_status = 1
                  AND p.verify_status = 1
                  AND p.is_deleted IS FALSE
                  {exclude_clause}
                ORDER BY v.cf_vector <=> CAST(:vec AS vector(64))
                LIMIT :n
            """)
            result = await db.execute(query, params)
            rows = result.fetchall()

        return [
            {"product_id": str(r[0]), "score": round(float(r[1]), 4), "_source": "cf"}
            for r in rows if r[0]
        ]

    async def _get_user_vector(self, uid: str) -> str | None:
        """从 Redis 获取用户 CF 向量, 返回 pgvector 兼容格式字符串。"""
        import json

        raw = await self._memory.client.get(f"cf_user:{uid}")
        if not raw:
            return await self._compute_fallback_user_vector(uid)

        # JSON 解码 → pgvector 字符串
        try:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            floats = json.loads(raw)
            return "[" + ",".join(f"{v:.8f}" for v in floats) + "]"
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.debug("cf_train: failed to parse user vector for %s: %s", uid, exc)
            return await self._compute_fallback_user_vector(uid)

    async def _compute_fallback_user_vector(self, uid: str) -> str | None:
        """用户不在训练集时的降级: 取最近浏览商品的 CF 向量平均值。"""
        from sqlalchemy import text as sqla_text

        async with self._db_factory() as db:
            query = sqla_text("""
                SELECT v.cf_vector::text
                FROM ums_member_behaviors b
                JOIN pms_product_cf_vectors v ON b.item_id = v.product_id
                WHERE b.user_id = CAST(:uid AS uuid)
                  AND b.behavior_type IN ('view', 'purchase', 'add_cart', 'favorite')
                ORDER BY b.created_at DESC
                LIMIT 10
            """)
            result = await db.execute(query, {"uid": uid})
            rows = result.fetchall()

        if not rows:
            return None

        # 解析 pgvector 字符串 → 取平均
        vecs = []
        for (vec_str,) in rows:
            if not vec_str:
                continue
            vals = [float(x.strip()) for x in vec_str.strip("[]").split(",") if x.strip()]
            vecs.append(vals)

        if not vecs:
            return None

        avg = np.mean(vecs, axis=0).tolist()
        return "[" + ",".join(f"{v:.8f}" for v in avg) + "]"

    async def get_status(self) -> dict[str, Any]:
        """获取模型状态 (版本/商品数/用户数)。"""
        from sqlalchemy import func, text as sqla_text

        async with self._db_factory() as db:
            result = await db.execute(sqla_text(
                "SELECT model_version, COUNT(*) FROM pms_product_cf_vectors GROUP BY model_version"
            ))
            row = result.fetchone()
            if not row:
                return {"ready": False, "model_version": None, "n_items": 0, "n_users": 0}

            # 统计 Redis 中用户向量数量
            # (粗略扫描, 生产环境应改用 SET 存储用户ID列表)
            n_users = 0
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._memory.client.scan(cursor, match="cf_user:*", count=100)
                    n_users += len(keys)
                    if cursor == 0:
                        break
            except Exception:
                n_users = -1

        return {
            "ready": True,
            "model_version": row[0],
            "n_items": int(row[1]),
            "n_users": n_users if n_users >= 0 else "unknown",
        }
