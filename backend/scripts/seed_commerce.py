"""电商 seed 数据 — 供前端开发和 Swagger 调试使用。

运行: cd backend && uv run python scripts/seed_commerce.py
"""

import asyncio
import os
import uuid
from decimal import Decimal

os.environ["APP_ENV"] = "development"


async def seed():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy import text

    engine = create_async_engine(
        "postgresql+asyncpg://snaptrip:snaptrip123@localhost:5432/snaptrip_dev"
    )
    session = AsyncSession(engine, expire_on_commit=False)

    # ── Seed: 商品分类 ──
    cat_ids = {}
    cats = [
        ("电子数码", None, 0, "📱"),
        ("手机通讯", None, 0, "📞"),
        ("电脑办公", None, 0, "💻"),
        ("家用电器", None, 0, "🏠"),
        ("服装鞋帽", None, 0, "👗"),
        ("食品生鲜", None, 0, "🍎"),
    ]
    for name, parent_id, level, icon in cats:
        cid = uuid.uuid4()
        cat_ids[name] = cid
        await session.execute(text(
            "INSERT INTO pms_categories (id, name, parent_id, level, sort, icon, nav_status) "
            "VALUES (:id, :name, :pid, :level, 0, :icon, 1)"
        ), {"id": cid, "name": name, "pid": parent_id, "level": level, "icon": icon})
    print(f"  Categories: {len(cat_ids)}")

    # ── Seed: 品牌 ──
    brand_ids = {}
    brands = ["Apple", "Samsung", "Xiaomi", "Huawei", "Nike", "Adidas"]
    for i, name in enumerate(brands):
        bid = uuid.uuid4()
        brand_ids[name] = bid
        first = name[0].upper()
        await session.execute(text(
            "INSERT INTO pms_brands (id, name, first_letter, sort, factory_status) "
            "VALUES (:id, :name, :fl, :sort, 1)"
        ), {"id": bid, "name": name, "fl": first, "sort": i})
    print(f"  Brands: {len(brand_ids)}")

    # ── Seed: 商品 + SKU ──
    products = [
        ("iPhone 15 Pro Max", Decimal("9999.00"), "Apple", cat_ids["手机通讯"],
         [("IP15-256-BLK", '{"color":"黑色","storage":"256GB"}', Decimal("9999.00"), 500),
          ("IP15-512-NAT", '{"color":"原色","storage":"512GB"}', Decimal("10999.00"), 300)]),
        ("MacBook Pro 14", Decimal("14999.00"), "Apple", cat_ids["电脑办公"],
         [("MBP14-512", '{"color":"深空灰","storage":"512GB"}', Decimal("14999.00"), 200),
          ("MBP14-1TB", '{"color":"银色","storage":"1TB"}', Decimal("17999.00"), 100)]),
        ("Galaxy S24 Ultra", Decimal("8999.00"), "Samsung", cat_ids["手机通讯"],
         [("S24-256-BLK", '{"color":"黑色","storage":"256GB"}', Decimal("8999.00"), 400)]),
        ("Xiaomi 14 Pro", Decimal("4999.00"), "Xiaomi", cat_ids["手机通讯"],
         [("X14-256-WHT", '{"color":"白色","storage":"256GB"}', Decimal("4999.00"), 600),
          ("X14-512-BLK", '{"color":"黑色","storage":"512GB"}', Decimal("5499.00"), 300)]),
        ("Air Jordan 1", Decimal("1299.00"), "Nike", cat_ids["服装鞋帽"],
         [("AJ1-RED-42", '{"color":"红","size":"42"}', Decimal("1299.00"), 200)]),
        ("Ultraboost 23", Decimal("1099.00"), "Adidas", cat_ids["服装鞋帽"],
         [("UB23-BLK-41", '{"color":"黑","size":"41"}', Decimal("1099.00"), 150)]),
    ]

    product_ids = []
    for name, price, brand, cat_id, skus in products:
        pid = uuid.uuid4()
        product_ids.append(pid)
        total_stock = sum(s[3] for s in skus)
        await session.execute(text(
            "INSERT INTO pms_products (id, name, price, brand_id, category_id, stock, "
            "publish_status, verify_status, new_status, recommend_status, sub_title) "
            "VALUES (:id, :name, :price, :brand, :cat, :stock, 1, 1, 1, 1, :sub)"
        ), {"id": pid, "name": name, "price": str(price), "brand": brand_ids[brand],
            "cat": cat_id, "stock": total_stock, "sub": f"{name} - 热销爆款"})
        for sku_code, spec, sku_price, sku_stock in skus:
            await session.execute(text(
                "INSERT INTO pms_skus (id, product_id, sku_code, spec, price, stock, sale_count) "
                "VALUES (gen_random_uuid(), :pid, :code, :spec, :price, :stock, :sale)"
            ), {"pid": pid, "code": sku_code, "spec": spec, "price": str(sku_price),
                "stock": sku_stock, "sale": sku_stock // 5})
    print(f"  Products: {len(product_ids)}")

    # ── Seed: Banner ──
    await session.execute(text(
        "INSERT INTO cms_banners (id, title, pic, url, sort, status) VALUES "
        "(gen_random_uuid(), '618年中大促', 'https://picsum.photos/1200/400?random=1', '/products?tag=618', 0, 1),"
        "(gen_random_uuid(), '新品首发', 'https://picsum.photos/1200/400?random=2', '/products?tag=new', 1, 1),"
        "(gen_random_uuid(), '限时秒杀', 'https://picsum.photos/1200/400?random=3', '/flash', 2, 1)"
    ))
    print("  Banners: 3")

    # ── Seed: 专题 ──
    await session.execute(text(
        "INSERT INTO cms_subjects (id, title, summary, status, recommend_status) VALUES "
        "(gen_random_uuid(), '618省钱攻略', '超值好物推荐，不容错过', 1, 1),"
        "(gen_random_uuid(), '数码新品首发', '最新旗舰手机/电脑首发', 1, 1)"
    ))
    print("  Subjects: 2")

    # ── Seed: 帮助中心 ──
    await session.execute(text(
        "INSERT INTO cms_helps (id, title, content, category_name, status, sort) VALUES "
        "(gen_random_uuid(), '如何下单', '<p>选择商品→加入购物车→填写地址→支付</p>', '购物指南', 1, 0),"
        "(gen_random_uuid(), '退换货政策', '<p>7天无理由退换货</p>', '售后服务', 1, 1),"
        "(gen_random_uuid(), '配送说明', '<p>全国包邮，顺丰发货</p>', '配送说明', 1, 2)"
    ))
    print("  Helps: 3")

    # ── Seed: 优惠券 ──
    await session.execute(text(
        "INSERT INTO sms_coupons (id, name, type, use_type, amount, min_amount, count, per_limit, status) VALUES "
        "(gen_random_uuid(), '满200减30', 0, 0, 30, 200, 1000, 1, 1),"
        "(gen_random_uuid(), '满500减80', 0, 0, 80, 500, 500, 1, 1),"
        "(gen_random_uuid(), '新人专享-满99减20', 0, 0, 20, 99, 200, 1, 1),"
        "(gen_random_uuid(), '全场9折券', 0, 1, 0.9, 50, 100, 1, 1)"
    ))
    print("  Coupons: 4")

    await session.commit()
    await session.close()
    await engine.dispose()
    print("\n✅  Seed data created!")


asyncio.run(seed())
