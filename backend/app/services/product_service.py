"""
【商品 Service】— 商品 SPU + SKU + 属性值 业务逻辑

知识点速查：
  - 事务原子性: 创建商品 = 插入 Product + N 个 Sku + M 个 AttributeValue
    必须全部成功或全部回滚；如果不用事务: 部分成功会导致数据不一致
  - AsyncSession.flush() vs commit():
    flush() = 将内存变更刷到 DB 但不提交 → 其他事务看不到，本事务可见
    commit() = 提交事务 → 其他事务可见
    创建商品时，insert Product 后 flush() 获得 product.id 才能插入 SKU
  - selectinload: 一次 JOIN 预加载关联对象
  - 为什么不把 SKU 更新放在一个 UPDATE 语句中？
    商品编辑时 SKU 有增/删/改三种操作，必须逐一处理

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import contextlib
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    ProductCreate,
    ProductDetailResponse,
    ProductListQuery,
    ProductResponse,
    ProductUpdate,
    SkuResponse,
)


class ProductService:
    """商品服务 —— SPU + SKU + 属性值 一体化管理"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # =========================================================================
    #  创建商品 (事务原子操作: Product + SKUs + AttributeValues)
    # =========================================================================

    async def create(self, data: ProductCreate) -> ProductDetailResponse:
        """
        创建商品。

        步骤:
          1. 插入 PmsProduct → flush 获得 product.id
          2. 遍历 data.skus 逐一插入 PmsSku (关联 product.id)
          3. 遍历 data.attribute_values 逐一插入 PmsProductAttributeValue
          4. refresh 重新加载完整对象 (含 server_default 字段)
          5. (异步) 同步到 ES 搜索索引

        为什么不用 bulk_insert_mappings？
        - bulk 操作不触发 ORM 事件，不走 relationship 维护
        - 数据量小 (通常 < 20 个 SKU)，逐条插入性能足够
        """
        from app.models.product.attribute import PmsProductAttributeValue
        from app.models.product.product import PmsProduct
        from app.models.product.sku import PmsSku

        # 步骤1: 插入 SPU —— 排除 skus 和 attribute_values 字段
        product_data = data.model_dump(exclude={"skus", "attribute_values"})
        product = PmsProduct(**product_data)
        self.db.add(product)
        await self.db.flush()  # 获取得 product.id，后续 SKU 需要外键

        # 步骤2: 逐个插入 SKU
        for sku_data in data.skus:
            sku = PmsSku(
                product_id=product.id,
                **sku_data.model_dump(),
            )
            self.db.add(sku)
            # 更新商品库存汇总
            product.stock += sku.stock

        # 步骤3: 插入属性值
        for attr_id_str, value in data.attribute_values.items():
            attr_value = PmsProductAttributeValue(
                product_id=product.id,
                attribute_id=UUID(attr_id_str),
                value=value,
            )
            self.db.add(attr_value)

        await self.db.flush()
        await self.db.refresh(product)

        # 步骤5: 触发 ES 同步 (fire-and-forget，不阻塞返回)
        with contextlib.suppress(Exception):
            await _sync_product_to_es(product)

        return await self.get_detail(product.id)

    # =========================================================================
    #  编辑商品
    # =========================================================================

    async def update(self, product_id: UUID, data: ProductUpdate) -> ProductDetailResponse:
        """
        编辑商品基础信息。

        注意: 此方法只更新 Product 表字段，不处理 SKU 和属性值
        SKU 和属性值有独立的管理接口
        """
        from app.models.product.product import PmsProduct

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException
            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        stmt = update(PmsProduct).where(PmsProduct.id == product_id).values(**values).returning(PmsProduct)
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(product_id))
        await self.db.refresh(product)

        with contextlib.suppress(Exception):
            await _sync_product_to_es(product)

        return await self.get_detail(product.id)

    # =========================================================================
    #  删除商品 (软删除)
    # =========================================================================

    async def delete(self, product_id: UUID) -> None:
        """
        软删除商品 —— 不物理删除，设置 is_deleted=True。

        为什么不用物理删除？订单/收藏/浏览记录可能引用此商品，物理删除会导致外键断裂
        """
        from app.models.product.product import PmsProduct

        product = await self.db.get(PmsProduct, product_id)
        if not product:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(product_id))
        product.is_deleted = True
        product.publish_status = 0  # 同时下架

        from app.search.client import get_search_client
        with contextlib.suppress(Exception):
            await get_search_client().delete_product(str(product_id))

    # =========================================================================
    #  查询: 详情
    # =========================================================================

    async def get_detail(self, product_id: UUID) -> ProductDetailResponse:
        """
        查询商品详情 —— 含 SKU 列表和属性值。

        查询策略: get() 获取 Product → 单独查 SKU 列表 → 单独查属性值
        为什么不用 selectinload 一次 JOIN？
          Product JOIN Sku (1对N) JOIN AttributeValue (1对M)
          会生成笛卡尔积 N*M 行，数据量膨胀
          分三次查询更高效
        """
        from app.models.product.attribute import PmsProductAttributeValue
        from app.models.product.product import PmsProduct
        from app.models.product.sku import PmsSku

        product = await self.db.get(PmsProduct, product_id)
        if not product:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(product_id))

        # 查 SKU
        sku_result = await self.db.execute(
            select(PmsSku).where(PmsSku.product_id == product_id)
        )
        skus = sku_result.scalars().all()

        # 查属性值
        attr_result = await self.db.execute(
            select(PmsProductAttributeValue).where(
                PmsProductAttributeValue.product_id == product_id
            )
        )
        attrs = attr_result.scalars().all()

        return ProductDetailResponse(
            **ProductResponse.model_validate(product).model_dump(),
            skus=[SkuResponse.model_validate(s) for s in skus],
            attribute_values=[
                {"attribute_id": str(a.attribute_id), "value": a.value}
                for a in attrs
            ],
        )

    # =========================================================================
    #  查询: 分页列表 (管理后台)
    # =========================================================================

    async def list_paginated(
        self, query: ProductListQuery
    ) -> tuple[list[ProductResponse], int]:
        """
        管理后台商品列表 —— 多条件筛选 + 排序 + 分页。

        动态 WHERE 构建:
          每个筛选条件独立判断，只添加存在的条件到查询中
          比 if-else 嵌套更清晰，避免条件组合爆炸
        """
        from app.models.product.product import PmsProduct

        base = select(PmsProduct)
        count_q = select(func.count(PmsProduct.id))

        if query.keyword:
            base = base.where(
                PmsProduct.name.ilike(f"%{query.keyword}%") |
                PmsProduct.product_sn.ilike(f"%{query.keyword}%")
            )
            count_q = count_q.where(
                PmsProduct.name.ilike(f"%{query.keyword}%") |
                PmsProduct.product_sn.ilike(f"%{query.keyword}%")
            )
        if query.brand_id:
            base = base.where(PmsProduct.brand_id == query.brand_id)
            count_q = count_q.where(PmsProduct.brand_id == query.brand_id)
        if query.category_id:
            base = base.where(PmsProduct.category_id == query.category_id)
            count_q = count_q.where(PmsProduct.category_id == query.category_id)
        if query.publish_status is not None:
            base = base.where(PmsProduct.publish_status == query.publish_status)
            count_q = count_q.where(PmsProduct.publish_status == query.publish_status)
        if query.verify_status is not None:
            base = base.where(PmsProduct.verify_status == query.verify_status)
            count_q = count_q.where(PmsProduct.verify_status == query.verify_status)
        if query.product_sn:
            base = base.where(PmsProduct.product_sn == query.product_sn)
            count_q = count_q.where(PmsProduct.product_sn == query.product_sn)

        # 排序 —— 映射前端传的 sort_by 到实际的列
        sort_map = {
            "create_time": PmsProduct.created_at.desc(),
            "sale_count": PmsProduct.sale_count.desc(),
            "price_asc": PmsProduct.price.asc(),
            "price_desc": PmsProduct.price.desc(),
        }
        order_by = sort_map.get(query.sort_by or "", PmsProduct.updated_at.desc())

        result = await self.db.execute(count_q)
        total = result.scalar() or 0

        offset = (query.page - 1) * query.page_size
        result = await self.db.execute(
            base.order_by(order_by).offset(offset).limit(query.page_size)
        )
        products = result.scalars().all()

        return [ProductResponse.model_validate(p) for p in products], total

    # =========================================================================
    #  查询: 前台浏览 (仅上架+已审核)
    # =========================================================================

    async def list_portal(
        self,
        keyword: str | None = None,
        category_id: UUID | None = None,
        brand_id: UUID | None = None,
        sort_by: str = "default",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ProductResponse], int]:
        """
        前台商品浏览 —— 只显示上架且审核通过的商品。

        与后台列表的区别:
          1. 硬过滤 publish_status=1 AND verify_status=1
          2. 自动排除软删除商品 is_deleted=False
          3. 不需要 product_sn 筛选 (前台用户不需要)
        """
        from app.models.product.product import PmsProduct

        base = (
            select(PmsProduct)
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )
        count_q = (
            select(func.count(PmsProduct.id))
            .where(PmsProduct.publish_status == 1)
            .where(PmsProduct.verify_status == 1)
            .where(PmsProduct.is_deleted.is_(False))
        )

        if keyword:
            base = base.where(PmsProduct.name.ilike(f"%{keyword}%"))
            count_q = count_q.where(PmsProduct.name.ilike(f"%{keyword}%"))
        if category_id:
            base = base.where(PmsProduct.category_id == category_id)
            count_q = count_q.where(PmsProduct.category_id == category_id)
        if brand_id:
            base = base.where(PmsProduct.brand_id == brand_id)
            count_q = count_q.where(PmsProduct.brand_id == brand_id)

        sort_map = {
            "price_asc": PmsProduct.price.asc(),
            "price_desc": PmsProduct.price.desc(),
            "sales": PmsProduct.sale_count.desc(),
            "new": PmsProduct.created_at.desc(),
        }
        order_by = sort_map.get(sort_by, PmsProduct.sale_count.desc())

        result = await self.db.execute(count_q)
        total = result.scalar() or 0

        result = await self.db.execute(
            base.order_by(order_by).offset((page - 1) * page_size).limit(page_size)
        )
        products = result.scalars().all()
        return [ProductResponse.model_validate(p) for p in products], total

    # =========================================================================
    #  状态操作
    # =========================================================================

    async def toggle_status(self, product_id: UUID, field: str, status: int) -> ProductResponse:
        from app.models.product.product import PmsProduct

        stmt = (
            update(PmsProduct)
            .where(PmsProduct.id == product_id)
            .values(**{field: status})
            .returning(PmsProduct)
        )
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(product_id))

        with contextlib.suppress(Exception):
            await _sync_product_to_es(product)

        return ProductResponse.model_validate(product)


# ============================================================================
#  ES 同步工具函数
# ============================================================================

async def _sync_product_to_es(product) -> None:
    """
    将单个商品同步到 Elasticsearch。

    从 Product 构造 ES 文档、从 DB 查询 SKU 最低价用于搜索排序。
    搜索索引的字段比 DB 表少，只包含搜索/筛选需要的字段。
    """
    from app.search.client import get_search_client

    # 查该商品的 SKU 最低价 —— ES 搜索排序需要
    # 这里不依赖 Service 避免循环引用，直接用原生查询
    doc = {
        "id": str(product.id),
        "name": product.name,
        "sub_title": product.sub_title or "",
        "keywords": product.keywords or "",
        "category_id": str(product.category_id) if product.category_id else "",
        "category_name": "",  # 后续可 JOIN category 填充
        "brand_id": str(product.brand_id) if product.brand_id else "",
        "brand_name": "",  # 后续可 JOIN brand 填充
        "price": float(product.price),
        "promotion_price": float(product.promotion_price) if product.promotion_price else None,
        "sale_count": product.sale_count or 0,
        "stock": product.stock or 0,
        "pics": product.pics or "",
        "publish_status": product.publish_status,
        "verify_status": product.verify_status,
    }

    await get_search_client().index_product(str(product.id), doc)
