"""电商 seed 数据 — 供前端开发和 Swagger 调试使用。

运行: cd backend && uv run python scripts/seed_commerce.py
"""

import asyncio
import os
import uuid
from decimal import Decimal

os.environ["APP_ENV"] = "development"


async def seed(session=None):
    from snaptrip_shared.core.config import settings
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    own_session = False
    if session is None:
        engine = create_async_engine(settings.effective_database_url)
        session = AsyncSession(engine, expire_on_commit=False)
        own_session = True
    else:
        engine = None

    # ====================================================================
    # 商品分类 — 两级结构
    # ====================================================================
    cat_ids = {}
    top_cats = [
        ("手机通讯", None, 0, "📱"),
        ("电脑办公", None, 0, "💻"),
        ("家用电器", None, 0, "🏠"),
        ("服装鞋帽", None, 0, "👗"),
        ("运动户外", None, 0, "⚽"),
        ("食品生鲜", None, 0, "🍎"),
        ("美妆个护", None, 0, "💄"),
        ("图书文娱", None, 0, "📚"),
    ]
    for name, parent_id, level, icon in top_cats:
        cid = uuid.uuid4()
        cat_ids[name] = cid
        await session.execute(
            text(
                "INSERT INTO pms_categories (id, name, parent_id, level, sort, icon, nav_status, show_status) "
                "VALUES (:id, :name, :pid, :level, 0, :icon, 1, 1)"
            ),
            {"id": cid, "name": name, "pid": parent_id, "level": level, "icon": icon},
        )

    sub_cats = [
        ("智能手机", cat_ids["手机通讯"], 1, "📱"),
        ("手机配件", cat_ids["手机通讯"], 1, "🔌"),
        ("笔记本电脑", cat_ids["电脑办公"], 1, "💻"),
        ("平板电脑", cat_ids["电脑办公"], 1, "📋"),
        ("厨房电器", cat_ids["家用电器"], 1, "🍳"),
        ("生活电器", cat_ids["家用电器"], 1, "🌀"),
        ("男装", cat_ids["服装鞋帽"], 1, "👔"),
        ("女装", cat_ids["服装鞋帽"], 1, "👗"),
        ("运动鞋", cat_ids["运动户外"], 1, "👟"),
        ("健身器材", cat_ids["运动户外"], 1, "🏋️"),
        ("休闲零食", cat_ids["食品生鲜"], 1, "🍪"),
        ("生鲜水果", cat_ids["食品生鲜"], 1, "🍓"),
        ("护肤", cat_ids["美妆个护"], 1, "🧴"),
        ("彩妆", cat_ids["美妆个护"], 1, "💄"),
    ]
    for name, parent_id, level, icon in sub_cats:
        cid = uuid.uuid4()
        cat_ids[name] = cid
        await session.execute(
            text(
                "INSERT INTO pms_categories (id, name, parent_id, level, sort, icon, nav_status, show_status) "
                "VALUES (:id, :name, :pid, :level, 0, :icon, 1, 1)"
            ),
            {"id": cid, "name": name, "pid": parent_id, "level": level, "icon": icon},
        )
    print(f"  Categories: {len(cat_ids)} (8 top + 14 sub)")

    # ====================================================================
    # 品牌
    # ====================================================================
    brand_ids = {}
    brands_data = [
        ("Apple", "A", "https://picsum.photos/200/200?random=10"),
        ("Samsung", "S", "https://picsum.photos/200/200?random=11"),
        ("Xiaomi", "X", "https://picsum.photos/200/200?random=12"),
        ("Huawei", "H", "https://picsum.photos/200/200?random=13"),
        ("Nike", "N", "https://picsum.photos/200/200?random=14"),
        ("Adidas", "A", "https://picsum.photos/200/200?random=15"),
        ("戴森", "D", "https://picsum.photos/200/200?random=16"),
        ("SK-II", "S", "https://picsum.photos/200/200?random=17"),
        ("索尼", "S", "https://picsum.photos/200/200?random=18"),
        ("美的", "M", "https://picsum.photos/200/200?random=19"),
        ("海尔", "H", "https://picsum.photos/200/200?random=20"),
        ("良品铺子", "L", "https://picsum.photos/200/200?random=21"),
    ]
    for i, (name, letter, logo) in enumerate(brands_data):
        bid = uuid.uuid4()
        brand_ids[name] = bid
        await session.execute(
            text(
                "INSERT INTO pms_brands (id, name, first_letter, sort, factory_status, show_status, logo) "
                "VALUES (:id, :name, :fl, :sort, 1, 1, :logo)"
            ),
            {"id": bid, "name": name, "fl": letter, "sort": i, "logo": logo},
        )
    print(f"  Brands: {len(brand_ids)}")

    # ====================================================================
    # 商品 + SKU
    # ====================================================================
    def p(name, price, brand, cat, skus, sub=None, original=None, is_new=1, is_rec=1, desc=None):
        return (name, price, brand, cat, skus, sub, original, is_new, is_rec, desc)

    products = [
        p(
            "iPhone 15 Pro Max",
            Decimal("9999.00"),
            "Apple",
            cat_ids["智能手机"],
            [
                ("IP15-256-BLK", '{"color":"黑色钛金属","storage":"256GB"}', Decimal("9999.00"), 500),
                ("IP15-512-NAT", '{"color":"原色钛金属","storage":"512GB"}', Decimal("10999.00"), 300),
                ("IP15-1TB-WHT", '{"color":"白色钛金属","storage":"1TB"}', Decimal("12999.00"), 100),
            ],
            sub="A17 Pro 芯片 | 钛金属设计 | 4800 万像素",
            original=Decimal("10999.00"),
            desc="<p>iPhone 15 Pro Max 采用航天级钛金属设计，搭载 A17 Pro 芯片，配备 4800 万像素主摄系统，支持 5 倍光学变焦。超视网膜 XDR 显示屏，ProMotion 自适应刷新率技术。</p>",
        ),
        p(
            "MacBook Pro 14 (M3 Pro)",
            Decimal("14999.00"),
            "Apple",
            cat_ids["笔记本电脑"],
            [
                (
                    "MBP14-18G-512",
                    '{"color":"深空黑","芯片":"M3 Pro","内存":"18GB","存储":"512GB"}',
                    Decimal("14999.00"),
                    200,
                ),
                (
                    "MBP14-36G-1TB",
                    '{"color":"银色","芯片":"M3 Pro","内存":"36GB","存储":"1TB"}',
                    Decimal("19999.00"),
                    80,
                ),
            ],
            sub="M3 Pro 芯片 | 18GB 内存 | Liquid Retina XDR",
            original=Decimal("16999.00"),
            desc="<p>MacBook Pro 搭载 M3 Pro 芯片，配备绚丽的 Liquid Retina XDR 显示屏，电池续航最长 17 小时。</p>",
        ),
        p(
            "Galaxy S24 Ultra",
            Decimal("8999.00"),
            "Samsung",
            cat_ids["智能手机"],
            [
                ("S24-256-BLK", '{"color":"钛灰","storage":"256GB"}', Decimal("8999.00"), 400),
                ("S24-512-VLT", '{"color":"钛紫","storage":"512GB"}', Decimal("9999.00"), 200),
            ],
            sub="Galaxy AI | 钛金属框架 | 2亿像素",
            original=Decimal("9999.00"),
            desc="<p>Samsung Galaxy S24 Ultra 搭载 Galaxy AI 智能助手，2 亿像素专业摄像头，内置 S Pen。</p>",
        ),
        p(
            "Xiaomi 14 Pro",
            Decimal("4999.00"),
            "Xiaomi",
            cat_ids["智能手机"],
            [
                ("X14-256-WHT", '{"color":"白色","storage":"256GB"}', Decimal("4999.00"), 600),
                ("X14-512-BLK", '{"color":"黑色","storage":"512GB"}', Decimal("5499.00"), 300),
            ],
            sub="徕卡光学 Summilux 镜头 | 骁龙 8 Gen3",
            original=Decimal("5299.00"),
            desc="<p>Xiaomi 14 Pro 与徕卡联合研发，搭载 Summilux 光学镜头，骁龙 8 Gen 3 旗舰处理器。</p>",
        ),
        p(
            "Mate 60 Pro",
            Decimal("6999.00"),
            "Huawei",
            cat_ids["智能手机"],
            [
                ("M60-256-BLK", '{"color":"雅丹黑","storage":"256GB"}', Decimal("6999.00"), 300),
                ("M60-512-CYN", '{"color":"白沙银","storage":"512GB"}', Decimal("7999.00"), 150),
            ],
            sub="卫星通话 | 昆仑玻璃 | 超光变主摄",
            original=Decimal("7999.00"),
            desc="<p>HUAWEI Mate 60 Pro 支持卫星通话，搭载超光变 XMAGE 影像系统，昆仑玻璃面板。</p>",
        ),
        p(
            "Air Jordan 1 Retro High",
            Decimal("1299.00"),
            "Nike",
            cat_ids["运动鞋"],
            [
                ("AJ1-RED-42", '{"color":"经典红黑","size":"42"}', Decimal("1299.00"), 200),
                ("AJ1-BLU-41", '{"color":"北卡蓝","size":"41"}', Decimal("1299.00"), 150),
            ],
            sub="经典复刻 | 牛皮革鞋面 | Air Sole 气垫",
            original=Decimal("1499.00"),
            desc="<p>Air Jordan 1 Retro High OG 经典复刻，优质牛皮革鞋面，Air Sole 气垫缓震。</p>",
        ),
        p(
            "Ultraboost 23",
            Decimal("1099.00"),
            "Adidas",
            cat_ids["运动鞋"],
            [
                ("UB23-BLK-41", '{"color":"核心黑","size":"41"}', Decimal("1099.00"), 180),
                ("UB23-WHT-42", '{"color":"云白","size":"42"}', Decimal("1099.00"), 220),
            ],
            sub="BOOST 中底 | Primeknit+ 袜套式鞋面 | 环保材质",
            original=Decimal("1299.00"),
            desc="<p>adidas Ultraboost 23 采用全新 LEP 系统，BOOST 中底回弹十足，Primeknit+ 袜套式鞋面。</p>",
        ),
        p(
            "戴森 HD15 吹风机",
            Decimal("3290.00"),
            "戴森",
            cat_ids["生活电器"],
            [
                ("HD15-NKL", '{"颜色":"镍灰色"}', Decimal("3290.00"), 300),
                ("HD15-BLUE", '{"颜色":"普鲁士蓝"}', Decimal("3490.00"), 200),
            ],
            sub="智能温控 | 负离子护发 | 5分钟快干",
            original=Decimal("3490.00"),
            desc="<p>Dyson Supersonic HD15 新一代吹风机，智能温控系统防止过热损伤，负离子技术减少静电毛躁。</p>",
        ),
        p(
            "SK-II 神仙水 230ml",
            Decimal("2150.00"),
            "SK-II",
            cat_ids["护肤"],
            [
                ("SKII-230", '{"规格":"230ml"}', Decimal("2150.00"), 400),
                ("SKII-330", '{"规格":"330ml"}', Decimal("2890.00"), 150),
            ],
            sub="PITERA 酵母精华 | 紧致修护 | 补水保湿",
            original=Decimal("2390.00"),
            desc="<p>SK-II 护肤精华露（神仙水），富含超过 90% 的天然活酵母精萃 PITERA，有效改善肌肤五大维度。</p>",
        ),
        p(
            "Sony WH-1000XM5 头戴式降噪耳机",
            Decimal("2999.00"),
            "索尼",
            cat_ids["手机配件"],
            [
                ("XM5-BLK", '{"颜色":"黑色"}', Decimal("2999.00"), 250),
                ("XM5-SLV", '{"颜色":"银色"}', Decimal("2999.00"), 200),
            ],
            sub="AI 降噪 | 30h续航 | Hi-Res 无线",
            original=Decimal("3299.00"),
            desc="<p>Sony WH-1000XM5 拥有行业领先的降噪能力，30小时续航，支持 Hi-Res Audio 无线传输。</p>",
        ),
        p(
            "Nike Dri-FIT 运动T恤",
            Decimal("299.00"),
            "Nike",
            cat_ids["男装"],
            [
                ("NK-T-M-L", '{"颜色":"黑色","尺码":"L"}', Decimal("299.00"), 500),
                ("NK-T-W-XL", '{"颜色":"白色","尺码":"XL"}', Decimal("299.00"), 400),
            ],
            sub="Dri-FIT 科技 | 透气速干 | 轻盈舒适",
            original=Decimal("349.00"),
            is_rec=0,
            desc="<p>Nike Dri-FIT 运动T恤采用速干面料，保持干爽舒适。</p>",
        ),
        p(
            "良品铺子 坚果大礼包 1.5kg",
            Decimal("168.00"),
            "良品铺子",
            cat_ids["休闲零食"],
            [("LP-GIFT-1", '{"规格":"1.5kg 混合装"}', Decimal("168.00"), 1000)],
            sub="每日坚果 | 10袋独立包装 | 送礼佳品",
            original=Decimal("198.00"),
            is_new=1,
            is_rec=1,
            desc="<p>良品铺子坚果大礼包，精选优质坚果，独立包装锁鲜，送礼自用两相宜。</p>",
        ),
        p(
            "美的 空气炸锅 4.7L",
            Decimal("399.00"),
            "美的",
            cat_ids["厨房电器"],
            [
                ("MD-AF-47L", '{"颜色":"白色","容量":"4.7L"}', Decimal("399.00"), 600),
                ("MD-AF-55L-BLK", '{"颜色":"黑色","容量":"5.5L"}', Decimal("499.00"), 300),
            ],
            sub="无油炸 | 智能菜单 | 360°热风循环",
            original=Decimal("499.00"),
            desc="<p>Midea 空气炸锅，360°热风循环加热，无油健康烹饪，8大智能菜单一键操作。</p>",
        ),
        p(
            "海尔 三门冰箱 218L",
            Decimal("2499.00"),
            "海尔",
            cat_ids["生活电器"],
            [("HR-218-WHT", '{"颜色":"白色","容量":"218L"}', Decimal("2499.00"), 100)],
            sub="风冷无霜 | 智能控温 | 一级能效",
            original=Decimal("2799.00"),
            is_rec=0,
            desc="<p>Haier 三门冰箱，风冷无霜，DEO 净味养鲜，一级能效省电。</p>",
        ),
        p(
            'iPad Pro M4 12.9"',
            Decimal("8999.00"),
            "Apple",
            cat_ids["平板电脑"],
            [
                ("IPAD-M4-256", '{"颜色":"深空黑","存储":"256GB"}', Decimal("8999.00"), 200),
                ("IPAD-M4-1TB", '{"颜色":"银色","存储":"1TB"}', Decimal("12999.00"), 80),
            ],
            sub="M4 芯片 | Ultra Retina XDR | Apple Pencil Pro",
            original=Decimal("9699.00"),
            desc="<p>iPad Pro M4 搭载全新 Ultra Retina XDR 显示屏，M4 芯片性能飞跃。</p>",
        ),
    ]

    product_ids = []
    for name, price, brand, cat, skus, sub, original, is_new, is_rec, desc in products:
        pid = uuid.uuid4()
        product_ids.append(pid)
        total_stock = sum(s[3] for s in skus)
        await session.execute(
            text(
                "INSERT INTO pms_products (id, name, price, original_price, brand_id, category_id, stock, "
                "publish_status, verify_status, new_status, recommend_status, sub_title, description, "
                "default_pic) "
                "VALUES (:id, :name, :price, :orig, :brand, :cat, :stock, 1, 1, :new, :rec, :sub, :desc, :pic)"
            ),
            {
                "id": pid,
                "name": name,
                "price": str(price),
                "orig": str(original) if original else None,
                "brand": brand_ids[brand],
                "cat": cat,
                "stock": total_stock,
                "new": is_new,
                "rec": is_rec,
                "sub": sub,
                "desc": desc,
                "pic": f"https://picsum.photos/400/400?random={len(product_ids)}",
            },
        )
        for sku_code, spec, sku_price, sku_stock in skus:
            await session.execute(
                text(
                    "INSERT INTO pms_skus (id, product_id, sku_code, spec, price, stock, sale_count) "
                    "VALUES (gen_random_uuid(), :pid, :code, :spec, :price, :stock, :sale)"
                ),
                {
                    "pid": pid,
                    "code": sku_code,
                    "spec": spec,
                    "price": str(sku_price),
                    "stock": sku_stock,
                    "sale": sku_stock // 5,
                },
            )
    print(f"  Products: {len(product_ids)} (with SKUs)")

    # ====================================================================
    # Banner 轮播图
    # ====================================================================
    await session.execute(
        text(
            "INSERT INTO cms_banners (id, title, pic, url, sort, status) VALUES "
            "(gen_random_uuid(), '618年中大促 全场低至5折', 'https://picsum.photos/1200/400?random=30', '/search', 0, 1),"
            "(gen_random_uuid(), '新品首发 — 旗舰手机抢先购', 'https://picsum.photos/1200/400?random=31', '/new', 1, 1),"
            "(gen_random_uuid(), '运动户外 品牌特卖', 'https://picsum.photos/1200/400?random=32', '/brand', 2, 1),"
            "(gen_random_uuid(), '数码焕新季 限时秒杀', 'https://picsum.photos/1200/400?random=33', '/hot', 3, 1)"
        )
    )
    print("  Banners: 4")

    # ====================================================================
    # 专题
    # ====================================================================
    await session.execute(
        text(
            "INSERT INTO cms_subjects (id, title, summary, status, recommend_status, pic) VALUES "
            "(gen_random_uuid(), '618省钱攻略', '超值好物推荐，大促必买清单', 1, 1, 'https://picsum.photos/400/300?random=40'),"
            "(gen_random_uuid(), '数码新品首发', '最新旗舰手机/电脑/平板首发', 1, 1, 'https://picsum.photos/400/300?random=41'),"
            "(gen_random_uuid(), '运动健身季', '运动装备低至3折起', 1, 1, 'https://picsum.photos/400/300?random=42'),"
            "(gen_random_uuid(), '护肤美妆课堂', '科学护肤，找到你的专属方案', 1, 0, 'https://picsum.photos/400/300?random=43')"
        )
    )
    print("  Subjects: 4")

    # ====================================================================
    # 帮助中心
    # ====================================================================
    await session.execute(
        text(
            "INSERT INTO cms_helps (id, title, content, category_name, status, sort) VALUES "
            "(gen_random_uuid(), '如何下单', '<p>1.选择心仪的商品 → 2.加入购物车 → 3.填写收货地址 → 4.选择支付方式 → 5.完成支付</p>', '购物指南', 1, 0),"
            "(gen_random_uuid(), '退换货政策', '<p>支持7天无理由退换货，15天内质量问题免费换新。请保持商品完好，不影响二次销售。</p>', '售后服务', 1, 1),"
            "(gen_random_uuid(), '配送说明', '<p>全国包邮（偏远地区除外）。默认顺丰快递发货，下单后24小时内发货。</p>', '配送说明', 1, 2),"
            "(gen_random_uuid(), '支付方式', '<p>支持微信支付、支付宝、银行卡在线支付。</p>', '支付帮助', 1, 3),"
            "(gen_random_uuid(), '优惠券使用规则', '<p>优惠券不可叠加使用，每笔订单限用一张。请在有效期内使用，逾期作废。</p>', '优惠券', 1, 4)"
        )
    )
    print("  Helps: 5")

    # ====================================================================
    # 优惠券
    # ====================================================================
    await session.execute(
        text(
            "INSERT INTO sms_coupons (id, name, type, use_type, amount, min_amount, count, publish_count, "
            "per_limit, start_time, end_time, status) VALUES "
            "(gen_random_uuid(), '满200减30', 0, 0, 30, 200, 1000, 1000, 1, NOW(), NOW() + INTERVAL '30 days', 1),"
            "(gen_random_uuid(), '满500减80', 0, 0, 80, 500, 500, 500, 1, NOW(), NOW() + INTERVAL '30 days', 1),"
            "(gen_random_uuid(), '新人专享-满99减20', 0, 0, 20, 99, 200, 200, 1, NOW(), NOW() + INTERVAL '90 days', 1),"
            "(gen_random_uuid(), '满1000减150', 0, 0, 150, 1000, 300, 300, 1, NOW(), NOW() + INTERVAL '30 days', 1),"
            "(gen_random_uuid(), '满2000减300', 0, 0, 300, 2000, 100, 100, 1, NOW(), NOW() + INTERVAL '60 days', 1)"
        )
    )
    print("  Coupons: 5")

    if own_session:
        await session.commit()
        await session.close()
        await engine.dispose()
    print("\n✅ Seed data created! Run make dev to start.")


if __name__ == "__main__":
    asyncio.run(seed())
