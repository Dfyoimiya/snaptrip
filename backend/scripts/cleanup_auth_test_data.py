"""隐藏误写入开发数据库的订单授权测试数据。

运行:
    cd backend
    uv run python scripts/cleanup_auth_test_data.py
"""

from __future__ import annotations

import asyncio
import os

from sqlalchemy import update

os.environ["APP_ENV"] = "development"


async def cleanup_auth_test_data() -> None:
    from app.models.product.brand import PmsBrand
    from app.models.product.category import PmsCategory
    from app.models.product.product import PmsProduct
    from snaptrip_shared.core.logging import get_logger
    from snaptrip_shared.db.session import AsyncSessionLocal

    logger = get_logger(__name__)

    async with AsyncSessionLocal() as session:
        brand_result = await session.execute(
            update(PmsBrand)
            .where(PmsBrand.name.ilike("authtest"))
            .values(show_status=0)
            .returning(PmsBrand.id)
        )
        brand_ids = list(brand_result.scalars())

        hidden_products = 0
        if brand_ids:
            product_result = await session.execute(
                update(PmsProduct)
                .where(PmsProduct.brand_id.in_(brand_ids))
                .values(publish_status=0, recommend_status=0, is_deleted=True)
                .returning(PmsProduct.id)
            )
            hidden_products = len(list(product_result.scalars()))

        category_result = await session.execute(
            update(PmsCategory)
            .where(PmsCategory.name == "授权测试分类")
            .values(show_status=0, nav_status=0)
            .returning(PmsCategory.id)
        )
        hidden_categories = len(list(category_result.scalars()))

        await session.commit()
        logger.info(
            "auth_test_data_hidden",
            brands=len(brand_ids),
            products=hidden_products,
            categories=hidden_categories,
        )


if __name__ == "__main__":
    asyncio.run(cleanup_auth_test_data())
