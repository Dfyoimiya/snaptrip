"""幂等导入开发商城商品目录。

运行:
    cd backend
    uv run python scripts/seed_catalog_products.py
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

os.environ["APP_ENV"] = "development"


async def seed_catalog() -> None:
    from app.data.product_catalog_seed import CATALOG_PRODUCTS
    from app.models.product.brand import PmsBrand
    from app.models.product.category import PmsCategory
    from app.models.product.product import PmsProduct
    from app.models.product.sku import PmsSku
    from snaptrip_shared.core.logging import get_logger
    from snaptrip_shared.db.session import AsyncSessionLocal

    logger = get_logger(__name__)

    async with AsyncSessionLocal() as session:
        category_names = {item.category for item in CATALOG_PRODUCTS}
        brand_names = {item.brand for item in CATALOG_PRODUCTS}

        category_result = await session.execute(
            select(PmsCategory)
            .where(PmsCategory.level == 0, PmsCategory.name.in_(category_names))
            .order_by(PmsCategory.created_at.desc())
        )
        categories: dict[str, PmsCategory] = {}
        for category in category_result.scalars():
            categories.setdefault(category.name, category)

        missing_categories = category_names - categories.keys()
        if missing_categories:
            raise RuntimeError(
                f"缺少一级分类: {', '.join(sorted(missing_categories))}，请先运行基础 commerce seed"
            )

        brand_result = await session.execute(
            select(PmsBrand).where(PmsBrand.name.in_(brand_names))
        )
        brands = {brand.name: brand for brand in brand_result.scalars()}
        for index, brand_name in enumerate(sorted(brand_names - brands.keys())):
            brand = PmsBrand(
                name=brand_name,
                first_letter=brand_name[:1].upper(),
                sort=100 + index,
                factory_status=1,
                show_status=1,
            )
            session.add(brand)
            await session.flush()
            brands[brand_name] = brand

        product_result = await session.execute(
            select(PmsProduct).where(
                PmsProduct.product_sn.in_([item.product_sn for item in CATALOG_PRODUCTS])
            )
        )
        existing_products = {
            product.product_sn: product
            for product in product_result.scalars()
            if product.product_sn
        }

        created = 0
        updated = 0
        for item in CATALOG_PRODUCTS:
            category = categories[item.category]
            brand = brands[item.brand]
            product = existing_products.get(item.product_sn)

            if product is None:
                product = PmsProduct(product_sn=item.product_sn, name=item.name, price=item.price)
                session.add(product)
                created += 1
            else:
                updated += 1

            product.name = item.name
            product.sub_title = item.sub_title
            product.brand_id = brand.id
            product.category_id = category.id
            product.price = item.price
            product.original_price = item.original_price
            product.default_pic = item.image_url
            product.pics = item.image_url
            product.album_pics = item.image_url
            product.description = f"<p>{item.sub_title}</p>"
            product.keywords = item.keywords
            product.unit = item.unit
            product.stock = item.stock
            product.sale_count = item.sale_count
            product.publish_status = 1
            product.verify_status = 1
            product.new_status = 1
            product.recommend_status = 1
            product.is_deleted = False
            product.deleted_at = None
            await session.flush()

            sku_result = await session.execute(
                select(PmsSku).where(
                    PmsSku.product_id == product.id,
                    PmsSku.sku_code == f"{item.product_sn}-DEFAULT",
                )
            )
            sku = sku_result.scalar_one_or_none()
            if sku is None:
                sku = PmsSku(
                    product_id=product.id,
                    sku_code=f"{item.product_sn}-DEFAULT",
                    spec='{"规格":"默认"}',
                    price=item.price,
                    stock=item.stock,
                )
                session.add(sku)
            sku.price = item.price
            sku.stock = item.stock
            sku.sale_count = item.sale_count
            sku.pic = item.image_url

        await session.commit()
        logger.info(
            "catalog_products_seeded",
            created=created,
            updated=updated,
            total=len(CATALOG_PRODUCTS),
            categories=len(category_names),
        )


if __name__ == "__main__":
    asyncio.run(seed_catalog())
