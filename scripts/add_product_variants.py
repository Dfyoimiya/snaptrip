#!/usr/bin/env python3
"""
add_product_variants.py — Adds realistic variant SKUs to single-SKU products.

Connects directly to PostgreSQL via asyncpg and generates 4-6 SKUs per product
with spec dimensions determined by product category. Updates the existing single
SKU's spec to the first variant and inserts additional SKUs.

Usage:
    uv run --directory /Users/finley/01_Projects/Python_AI/snaptrip \
        python scripts/add_product_variants.py
"""

from __future__ import annotations

import asyncio
import json
import uuid
from decimal import Decimal
from hashlib import md5
from itertools import islice, product
from typing import Any

import asyncpg

# ── Database connection ────────────────────────────────────────────────────
DB_CONFIG: dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "snaptrip",
    "password": "snaptrip_dev_pass",
    "database": "snaptrip_dev",
}

# ── Category-to-spec-dimensions mapping ────────────────────────────────────
# Each entry: (dimension_names, {dim_name: [values]})
CATEGORY_SPECS: dict[str, tuple[list[str], dict[str, list[str]]]] = {
    "手机通讯": (
        ["颜色", "存储"],
        {
            "颜色": ["黑色", "白色", "蓝色"],
            "存储": ["128GB", "256GB", "512GB"],
        },
    ),
    "笔记本": (
        ["颜色", "配置"],
        {
            "颜色": ["银色", "深空灰"],
            "配置": ["8GB+256GB", "16GB+512GB", "32GB+1TB"],
        },
    ),
    "平板电脑": (
        ["颜色", "配置"],
        {
            "颜色": ["银色", "深空灰"],
            "配置": ["8GB+256GB", "16GB+512GB"],
        },
    ),
    "数码产品": (
        ["颜色", "配置"],
        {
            "颜色": ["黑色", "白色", "深灰"],
            "配置": ["标准版", "高配版", "旗舰版"],
        },
    ),
    "服饰鞋包": (
        ["颜色", "尺码"],
        {
            "颜色": ["黑色", "白色", "灰色"],
            "尺码": ["S", "M", "L", "XL", "XXL"],
        },
    ),
    "男鞋": (
        ["颜色", "尺码"],
        {
            "颜色": ["黑色", "白色", "灰色"],
            "尺码": ["38", "39", "40", "41", "42", "43"],
        },
    ),
    "T恤": (
        ["颜色", "尺码"],
        {
            "颜色": ["黑色", "白色", "藏青"],
            "尺码": ["S", "M", "L", "XL", "XXL"],
        },
    ),
    "户外运动": (
        ["颜色", "规格"],
        {
            "颜色": ["黑色", "军绿", "橙色"],
            "规格": ["标准", "加大", "轻量"],
        },
    ),
    "家用电器": (
        ["颜色", "规格"],
        {
            "颜色": ["白色", "银色", "黑色"],
            "规格": ["标准版", "节能版", "智能版"],
        },
    ),
    "电视": (
        ["尺寸", "配置"],
        {
            "尺寸": ["55英寸", "65英寸", "75英寸"],
            "配置": ["标准版", "高配版"],
        },
    ),
    "厨卫大电": (
        ["颜色", "规格"],
        {
            "颜色": ["白色", "银色"],
            "规格": ["标准版", "节能版", "智能版"],
        },
    ),
    "粮食调味": (
        ["规格"],
        {"规格": ["单包装", "组合装", "家庭装"]},
    ),
    "食品酒饮": (
        ["规格"],
        {"规格": ["单包装", "组合装", "礼品装"]},
    ),
    "粮油调味": (
        ["规格"],
        {"规格": ["单包装", "组合装", "家庭装"]},
    ),
    "个人美妆": (
        ["规格"],
        {"规格": ["标准装", "旅行装", "套装", "体验装"]},
    ),
    "家具建材": (
        ["颜色", "尺寸"],
        {
            "颜色": ["原木色", "白色", "胡桃色"],
            "尺寸": ["1.2m", "1.5m", "1.8m"],
        },
    ),
    "卧室家具": (
        ["颜色", "尺寸"],
        {
            "颜色": ["原木色", "白色", "胡桃色"],
            "尺寸": ["1.2m", "1.5m", "1.8m"],
        },
    ),
    "客厅家具": (
        ["颜色", "尺寸"],
        {
            "颜色": ["原木色", "白色", "胡桃色"],
            "尺寸": ["1.5m", "1.8m", "2.0m"],
        },
    ),
    "文具办公": (
        ["颜色"],
        {"颜色": ["黑色", "白色", "蓝色", "粉色"]},
    ),
    "健康保养": (
        ["规格"],
        {"规格": ["体验装", "标准装", "家庭装"]},
    ),
    "母婴亲子": (
        ["颜色", "尺码"],
        {
            "颜色": ["粉色", "蓝色", "米色"],
            "尺码": ["S", "M", "L"],
        },
    ),
    "汽车服务": (
        ["规格"],
        {"规格": ["通用型", "专用型", "升级版"]},
    ),
    "车载电器": (
        ["规格"],
        {"规格": ["通用型", "专用型"]},
    ),
    "维修保养": (
        ["规格"],
        {"规格": ["通用型", "专用型"]},
    ),
    "农资园艺": (
        ["规格"],
        {"规格": ["小包装", "大包装", "家庭装"]},
    ),
    "五金机电": (
        ["规格"],
        {"规格": ["家用版", "专业版", "工业版"]},
    ),
    "五金工具": (
        ["规格"],
        {"规格": ["家用版", "专业版", "工业版"]},
    ),
    "萌宠护理": (
        ["规格"],
        {"规格": ["小型犬", "中型犬", "大型犬"]},
    ),
}


def _short_category(category_name: str) -> str:
    """Return a short English key for a category name."""
    mapping = {
        "手机通讯": "PHONE",
        "笔记本": "LAPTOP",
        "平板电脑": "PAD",
        "数码产品": "DIGI",
        "服饰鞋包": "FASHION",
        "男鞋": "SHOE",
        "T恤": "TSHIRT",
        "户外运动": "SPORT",
        "家用电器": "APPLIANCE",
        "电视": "TV",
        "厨卫大电": "KITCHEN",
        "食品酒饮": "FOOD",
        "粮油调味": "OIL",
        "个人美妆": "BEAUTY",
        "家具建材": "FURNITURE",
        "文具办公": "OFFICE",
        "健康保养": "HEALTH",
        "母婴亲子": "BABY",
        "汽车服务": "AUTO",
        "农资园艺": "FARM",
        "五金机电": "TOOL",
        "萌宠护理": "PET",
        "硬盘": "SSD",
    }
    return mapping.get(category_name, "GEN")


def short_hash(s: str) -> str:
    """Return a 6-character hex hash prefix."""
    return md5(s.encode()).hexdigest()[:6].upper()


def generate_spec_json(dim_names: list[str], values: list[str]) -> str:
    """Generate the spec JSON string in the canonical array-of-objects format."""
    items = [{"key": dim_names[i], "value": values[i]} for i in range(len(dim_names))]
    return json.dumps(items, ensure_ascii=False)


def generate_sku_code(product_sn: str, product_name: str, category_name: str, dim_abbr: str) -> str:
    """Generate a compact but readable SKU code, guaranteed <= 64 chars."""
    # Build prefix from product_sn, or generate from name
    if product_sn and product_sn.strip():
        prefix = product_sn.strip()
    else:
        # Generate prefix: category short + name hash
        cat_short = _short_category(category_name)
        name_hash = short_hash(product_name)
        prefix = f"{cat_short}-{name_hash}"

    code = f"{prefix}-{dim_abbr}"

    # Truncate if too long (shouldn't happen but be safe)
    if len(code) > 64:
        # Keep prefix to 50 chars so we have room for variant
        prefix = prefix[:50]
        code = f"{prefix}-{dim_abbr}"[:64]

    return code


def generate_dim_abbr(values: list[str]) -> str:
    """Generate a short abbreviation string for variant values.

    Example: ['黑色', '128GB'] -> 'BLK-128G'
    """
    abbr_mapping = {
        # Colors
        "黑色": "BLK", "白色": "WHT", "蓝色": "BLU", "银色": "SLV",
        "金色": "GLD", "红色": "RED", "绿色": "GRN", "橙色": "ORG",
        "灰色": "GRY", "深空灰": "DGRY", "深灰": "DGRY", "紫色": "PUR",
        "军绿": "MGRN", "藏青": "NAVY", "粉色": "PNK", "米色": "BEG",
        "原木色": "WOOD", "胡桃色": "WAL",
        "午夜色": "MDNT", "星光色": "STRL", "晴空蓝": "SKBL", "鸢尾紫": "IRIS",
        "冰霜银": "FRSV", "曜金黑": "BLK", "墨羽": "INK", "银迹": "SLVT",
        "亮黑色": "BLK",
        # Sizes
        "38": "38", "39": "39", "40": "40", "41": "41", "42": "42", "43": "43",
        "S": "S", "M": "M", "L": "L", "XL": "XL", "XXL": "XXL",
        "1.2m": "1.2M", "1.5m": "1.5M", "1.8m": "1.8M", "2.0m": "2.0M",
        # Storage
        "128GB": "128G", "256GB": "256G", "512GB": "512G", "1TB": "1T",
        "16G": "16G", "32G": "32G", "64G": "64G",
        # Configs
        "8GB+256GB": "8G256G", "16GB+512GB": "16G512G", "32GB+1TB": "32G1T",
        "标准版": "STD", "高配版": "PRO", "旗舰版": "ULTRA",
        "节能版": "ECO", "智能版": "SMART",
        # Spec types
        "标准": "STD", "加大": "L", "轻量": "LITE",
        "标准装": "STD", "旅行装": "TRAVEL", "套装": "SET", "体验装": "TRIAL",
        "单包装": "1PK", "组合装": "COMBO", "家庭装": "FAMILY",
        "礼品装": "GIFT",
        "家用版": "HOME", "专业版": "PRO", "工业版": "IND",
        "通用型": "UNI", "专用型": "SPC", "升级版": "UPG",
        "小包装": "SMLPK", "大包装": "LGPK",
        "小型犬": "SMALL", "中型犬": "MED", "大型犬": "LARGE",
        "轻量版": "LITE", "标准版(重复)": "STD",
        "50英寸": "50IN", "55英寸": "55IN", "65英寸": "65IN",
        "70英寸": "70IN", "75英寸": "75IN",
    }

    parts = []
    for v in values:
        abbr = abbr_mapping.get(v, v[:6].upper().replace(" ", ""))
        parts.append(abbr)
    return "-".join(parts)


MAX_VARIANTS = 6  # Maximum total SKUs per product


def pick_variant_combinations(dim_names: list[str], dim_values: dict[str, list[str]]) -> list[list[str]]:
    """Pick up to MAX_VARIANTS variant combinations from the spec dimensions.

    Uses cartesian product but limits to MAX_VARIANTS total, prioritizing
    diversity across all dimensions.
    """
    all_values = [dim_values[name] for name in dim_names]
    all_combos = list(product(*all_values))

    if len(all_combos) <= MAX_VARIANTS:
        return [list(c) for c in all_combos]

    # Too many combos — pick a diverse subset
    # Strategy: rotate through first dimensions to ensure diversity
    result: list[list[str]] = []
    # Take first N values from each dimension, cycling to cover breadth
    indices = [0] * len(dim_names)
    seen: set[tuple[int, ...]] = set()

    while len(result) < MAX_VARIANTS:
        combo_idx = tuple(indices)
        if combo_idx not in seen and all(
            indices[i] < len(all_values[i]) for i in range(len(dim_names))
        ):
            combo = [all_values[i][indices[i]] for i in range(len(dim_names))]
            result.append(combo)
            seen.add(combo_idx)

        # Advance the rightmost dimension that hasn't maxed out
        for i in reversed(range(len(dim_names))):
            indices[i] += 1
            if indices[i] < len(all_values[i]):
                break
            indices[i] = 0

        # If we've looped back to all zeros, we've exhausted
        if tuple(indices) == (0,) * len(dim_names) and len(seen) > 0:
            break

    return result


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        # ── Step 1: Fetch all products with their category and existing SKU count ──
        rows = await conn.fetch("""
            SELECT
                p.id AS product_id,
                p.name AS product_name,
                p.product_sn,
                p.price,
                p.promotion_price,
                p.category_id,
                c.name AS category_name,
                (SELECT COUNT(*) FROM pms_skus s WHERE s.product_id = p.id) AS sku_count
            FROM pms_products p
            JOIN pms_categories c ON c.id = p.category_id
            WHERE p.is_deleted = false
            ORDER BY c.name, p.name
        """)

        print(f"Total products in database: {len(rows)}")

        # ── Step 2: Categorize ──
        single_sku: list[asyncpg.Record] = []
        multi_sku: list[asyncpg.Record] = []
        no_spec: list[asyncpg.Record] = []

        for row in rows:
            if row["sku_count"] > 1:
                multi_sku.append(row)
            else:
                single_sku.append(row)

        print(f"  Already multi-SKU (skip): {len(multi_sku)} products")
        print(f"  Single-SKU (to process):  {len(single_sku)} products")

        # ── Step 3: Fetch existing SKU for each single-SKU product ──
        product_sku_map: dict[uuid.UUID, asyncpg.Record] = {}

        for row in single_sku:
            sku_row = await conn.fetchrow(
                "SELECT * FROM pms_skus WHERE product_id = $1 LIMIT 1",
                row["product_id"],
            )
            if sku_row is not None:
                product_sku_map[row["product_id"]] = sku_row

        print(f"  Products with existing SKU: {len(product_sku_map)}")

        # ── Step 4: Process each product ──
        stats = {
            "processed": 0,
            "skipped_no_category_spec": 0,
            "skipped_already_variant": 0,
            "total_new_skus": 0,
            "total_updated_skus": 0,
            "errors": 0,
        }

        for row in single_sku:
            product_id = row["product_id"]
            product_name = row["product_name"]
            product_sn = row["product_sn"]
            base_price = row["price"]
            promotion_price = row["promotion_price"]
            category_name = row["category_name"]

            # Get existing SKU
            existing_sku = product_sku_map.get(product_id)
            if existing_sku is None:
                stats["errors"] += 1
                print(f"  ERROR: No SKU found for product {product_id} — {product_name}")
                continue

            existing_spec = existing_sku["spec"]

            # Skip if spec already looks like a variant array (multi-key format)
            try:
                parsed = json.loads(existing_spec) if existing_spec else {}
                if isinstance(parsed, list) and len(parsed) > 1:
                    stats["skipped_already_variant"] += 1
                    continue
            except (json.JSONDecodeError, TypeError):
                pass

            # Look up spec dimensions for this category
            spec_entry = CATEGORY_SPECS.get(category_name)
            if spec_entry is None:
                stats["skipped_no_category_spec"] += 1
                continue

            dim_names, dim_values = spec_entry

            # ── Generate variant combinations ──
            combinations = pick_variant_combinations(dim_names, dim_values)
            if len(combinations) < 2:
                # Need at least 2 variants to make it worthwhile
                stats["skipped_no_category_spec"] += 1
                continue

            # ── Existing SKU becomes the first variant ──
            first_combo = combinations[0]
            new_spec_json = generate_spec_json(dim_names, first_combo)
            dim_abbr = generate_dim_abbr(first_combo)
            new_sku_code = generate_sku_code(product_sn, product_name, category_name, dim_abbr)

            # Update existing SKU (table has no timestamp columns)
            await conn.execute(
                """
                UPDATE pms_skus
                SET spec = $1, sku_code = $2
                WHERE id = $3
                """,
                new_spec_json,
                new_sku_code,
                existing_sku["id"],
            )
            stats["total_updated_skus"] += 1

            # ── Insert additional SKUs ──
            import random

            rng = random.Random(product_id.int % (2**31))

            for combo in combinations[1:]:
                spec_json = generate_spec_json(dim_names, combo)
                abbr = generate_dim_abbr(combo)
                sku_code = generate_sku_code(product_sn, product_name, category_name, abbr)

                # Varied pricing: base_price +/- 5-15%
                price_multiplier = rng.uniform(0.85, 1.15)
                variant_price = round(Decimal(str(base_price)) * Decimal(str(round(price_multiplier, 2))), 2)

                # Varied promotion price if parent has one
                variant_promo = None
                if promotion_price:
                    promo_mult = rng.uniform(0.88, 1.12)
                    variant_promo = round(
                        Decimal(str(promotion_price)) * Decimal(str(round(promo_mult, 2))), 2
                    )

                stock = rng.randint(50, 200)
                low_stock = rng.randint(10, 20)
                lock_stock = 0
                sale_count = rng.randint(0, 500)

                sku_id = uuid.uuid4()

                await conn.execute(
                    """
                    INSERT INTO pms_skus
                        (id, product_id, sku_code, spec, price, promotion_price,
                         stock, low_stock, lock_stock, pic, sale_count)
                    VALUES
                        ($1, $2, $3, $4, $5, $6,
                         $7, $8, $9, $10, $11)
                    """,
                    sku_id,
                    product_id,
                    sku_code,
                    spec_json,
                    variant_price,
                    variant_promo,
                    stock,
                    low_stock,
                    lock_stock,
                    existing_sku["pic"],
                    sale_count,
                )
                stats["total_new_skus"] += 1

            stats["processed"] += 1

            if stats["processed"] % 25 == 0:
                print(f"  Progress: {stats['processed']} products processed...")

        # ── Step 5: Print summary ──
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Products already multi-SKU (skipped): {len(multi_sku):>5}")
        print(f"  Products processed successfully:      {stats['processed']:>5}")
        print(f"  Existing SKUs updated (spec):         {stats['total_updated_skus']:>5}")
        print(f"  New SKUs inserted:                    {stats['total_new_skus']:>5}")
        print(f"  Skipped — no category spec mapping:   {stats['skipped_no_category_spec']:>5}")
        print(f"  Skipped — already had variant spec:   {stats['skipped_already_variant']:>5}")
        print(f"  Errors:                               {stats['errors']:>5}")
        print("=" * 60)

        # ── Verify final state ──
        verify = await conn.fetchrow("""
            SELECT
                COUNT(*) AS total_products,
                COUNT(*) FILTER (WHERE sku_count = 1) AS single_sku,
                COUNT(*) FILTER (WHERE sku_count BETWEEN 2 AND 6) AS variant_range,
                COUNT(*) FILTER (WHERE sku_count > 6) AS large_variant
            FROM (
                SELECT p.id, COUNT(s.id) AS sku_count
                FROM pms_products p
                LEFT JOIN pms_skus s ON s.product_id = p.id
                WHERE p.is_deleted = false
                GROUP BY p.id
            ) sub
        """)
        print(f"\n  Final totals: {verify['total_products']} products")
        print(f"    Single-SKU remaining: {verify['single_sku']}")
        print(f"    With 2-6 variants:    {verify['variant_range']}")
        print(f"    With 7+ variants:     {verify['large_variant']}")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
