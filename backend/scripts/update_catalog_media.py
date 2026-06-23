"""将现有商品和品牌记录切换到本地媒体资源。

运行:
    cd backend
    uv run python scripts/update_catalog_media.py
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import select

os.environ["APP_ENV"] = "development"


async def update_catalog_media() -> None:
    from snaptrip_shared.core.logging import get_logger
    from snaptrip_shared.db.session import AsyncSessionLocal

    from app.data.catalog_media import get_brand_logo_path, get_product_image_path
    from app.models.product.brand import PmsBrand
    from app.models.product.product import PmsProduct
    from app.models.product.sku import PmsSku

    logger = get_logger(__name__)

    async with AsyncSessionLocal() as session:
        products = list((await session.execute(select(PmsProduct))).scalars())
        brands = list((await session.execute(select(PmsBrand))).scalars())

        updated_products = 0
        updated_skus = 0
        skipped_products: list[str] = []
        for product in products:
            try:
                image_path = get_product_image_path(product.name)
            except KeyError:
                skipped_products.append(product.name)
                continue

            product.default_pic = image_path
            product.pics = image_path
            product.album_pics = image_path
            updated_products += 1

            skus = list(
                (
                    await session.execute(
                        select(PmsSku).where(PmsSku.product_id == product.id)
                    )
                ).scalars()
            )
            for sku in skus:
                sku.pic = image_path
                updated_skus += 1

        updated_brands = 0
        skipped_brands: list[str] = []
        for brand in brands:
            try:
                brand.logo = get_brand_logo_path(brand.name)
            except KeyError:
                skipped_brands.append(brand.name)
                continue
            updated_brands += 1

        await session.commit()
        logger.info(
            "catalog_media_updated",
            products=updated_products,
            skus=updated_skus,
            brands=updated_brands,
            skipped_products=sorted(set(skipped_products)),
            skipped_brands=sorted(set(skipped_brands)),
        )


if __name__ == "__main__":
    asyncio.run(update_catalog_media())
