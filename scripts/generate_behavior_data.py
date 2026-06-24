"""
批量生成用户行为数据 — 为 CF 模型训练提供基础数据

为所有用户生成 view / search / favorite / add_cart / purchase 行为，
每人有 2-3 个偏好品类，行为在品类内偏斜分布。

用法: uv run scripts/generate_behavior_data.py
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

import asyncpg

# ── 数据库连接 ──
DSN = "postgresql://snaptrip:snaptrip_dev_pass@127.0.0.1:5432/snaptrip_dev"

# 行为类型权重（约 100 次浏览 = 1 次购买）
BEHAVIOR_WEIGHTS = {
    "view": 60,
    "search": 15,
    "favorite": 10,
    "add_cart": 8,
    "purchase": 2,
}
BEHAVIORS = list(BEHAVIOR_WEIGHTS.keys())
BEHAVIOR_WEIGHT_LIST = list(BEHAVIOR_WEIGHTS.values())

# 数据时间范围
DAYS_BACK = 14
MIN_EVENTS_PER_USER = 30
MAX_EVENTS_PER_USER = 120


async def main():
    conn = await asyncpg.connect(DSN)

    # 获取所有用户
    user_rows = await conn.fetch("SELECT id FROM users ORDER BY created_at")
    user_ids = [r["id"] for r in user_rows]
    print(f"用户数: {len(user_ids)}")

    # 获取有商品的一级品类 + 商品
    cat_rows = await conn.fetch("""
        SELECT c.id AS category_id, c.name AS category_name,
               array_agg(p.id) AS product_ids
        FROM pms_categories c
        JOIN pms_products p ON p.category_id = c.id AND p.is_deleted IS FALSE
        GROUP BY c.id, c.name
        HAVING COUNT(p.id) >= 3
        ORDER BY COUNT(p.id) DESC
    """)
    categories = [(r["category_id"], r["product_ids"]) for r in cat_rows]
    print(f"可用品类数: {len(categories)} (≥3商品)")

    if len(categories) < 2:
        print("品类不足，退出")
        await conn.close()
        return

    # 为每个用户随机分配 2-3 个偏好品类
    total = 0
    now = datetime.now(UTC)
    batch: list[tuple] = []

    for i, uid in enumerate(user_ids):
        n_prefs = random.randint(2, min(3, len(categories)))
        pref_cats = random.sample(categories, n_prefs)

        n_events = random.randint(MIN_EVENTS_PER_USER, MAX_EVENTS_PER_USER)
        for _ in range(n_events):
            # 80% 概率选偏好品类, 20% 随机探索
            if random.random() < 0.8 and pref_cats:
                _, product_ids = random.choice(pref_cats)
            else:
                _, product_ids = random.choice(categories)

            if not product_ids:
                continue

            behavior_type = random.choices(BEHAVIORS, weights=BEHAVIOR_WEIGHT_LIST, k=1)[0]
            item_id = random.choice(product_ids)
            ts = now - timedelta(
                days=random.randint(0, DAYS_BACK),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # 搜索行为 item_id 为 NULL
            if behavior_type == "search":
                item_id_val = None
            else:
                item_id_val = item_id

            batch.append((
                uuid.uuid4(),
                uid,
                behavior_type,
                item_id_val,
                "product",
                ts,
                ts,
            ))

        if len(batch) >= 500:
            await conn.executemany("""
                INSERT INTO ums_member_behaviors (id, user_id, behavior_type, item_id, item_type, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, batch)
            total += len(batch)
            batch.clear()

        if (i + 1) % 5 == 0:
            print(f"  已处理 {i+1}/{len(user_ids)} 用户...")

    # 剩余
    if batch:
        await conn.executemany("""
            INSERT INTO ums_member_behaviors (id, user_id, behavior_type, item_id, item_type, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, batch)
        total += len(batch)

    await conn.close()
    print(f"\n完成! 插入 {total} 条行为记录, {len(user_ids)} 个用户")


if __name__ == "__main__":
    asyncio.run(main())
