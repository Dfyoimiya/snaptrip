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

from uuid import UUID

from snaptrip_shared.core.logging import get_logger
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

logger = get_logger(__name__)


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
        # NOTE: ES 失败不回滚 DB 操作 —— 搜索索引允许最终一致性
        # FUTURE: 改用 Celery 异步重试 (指数退避) 替代 fire-and-forget
        try:
            await sync_product_to_es(self.db, product)
        except Exception as exc:
            logger.warning(
                "es_sync_create_failed",
                product_id=str(product.id),
                product_name=product.name,
                error_type=type(exc).__name__,
                error=str(exc),
                exc_info=True,
            )

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

        # FUTURE: 改用 Celery 异步重试 (指数退避) 替代 fire-and-forget
        try:
            await sync_product_to_es(self.db, product)
        except Exception as exc:
            logger.warning(
                "es_sync_update_failed",
                product_id=str(product_id),
                product_name=product.name,
                error_type=type(exc).__name__,
                error=str(exc),
                exc_info=True,
            )

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

        # FUTURE: 改用 Celery 异步重试 (指数退避) 替代 fire-and-forget
        try:
            await get_search_client().delete_product(str(product_id))
        except Exception as exc:
            logger.warning(
                "es_delete_failed",
                product_id=str(product_id),
                product_name=product.name,
                error_type=type(exc).__name__,
                error=str(exc),
                exc_info=True,
            )

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
        if not product or product.is_deleted:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))

        # 查 SKU
        sku_result = await self.db.execute(select(PmsSku).where(PmsSku.product_id == product_id))
        skus = sku_result.scalars().all()

        # 查属性值
        attr_result = await self.db.execute(
            select(PmsProductAttributeValue).where(PmsProductAttributeValue.product_id == product_id)
        )
        attrs = attr_result.scalars().all()

        return ProductDetailResponse(
            **ProductResponse.model_validate(product).model_dump(),
            skus=[SkuResponse.model_validate(s) for s in skus],
            attribute_values=[{"attribute_id": str(a.attribute_id), "value": a.value} for a in attrs],
        )

    # =========================================================================
    #  查询: 分页列表 (管理后台)
    # =========================================================================

    async def list_paginated(self, query: ProductListQuery) -> tuple[list[ProductResponse], int]:
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
                PmsProduct.name.ilike(f"%{query.keyword}%") | PmsProduct.product_sn.ilike(f"%{query.keyword}%")
            )
            count_q = count_q.where(
                PmsProduct.name.ilike(f"%{query.keyword}%") | PmsProduct.product_sn.ilike(f"%{query.keyword}%")
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
            base.order_by(order_by).offset(offset).limit(query.page_size)  # type: ignore[arg-type]
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
            base.order_by(order_by).offset((page - 1) * page_size).limit(page_size)  # type: ignore[arg-type]
        )
        products = result.scalars().all()
        return [ProductResponse.model_validate(p) for p in products], total

    # =========================================================================
    #  状态操作
    # =========================================================================

    async def toggle_status(self, product_id: UUID, field: str, status: int) -> ProductResponse:
        from app.models.product.product import PmsProduct

        stmt = update(PmsProduct).where(PmsProduct.id == product_id).values(**{field: status}).returning(PmsProduct)
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))

        # FUTURE: 改用 Celery 异步重试 (指数退避) 替代 fire-and-forget
        try:
            await sync_product_to_es(self.db, product)
        except Exception as exc:
            logger.warning(
                "es_sync_toggle_status_failed",
                product_id=str(product_id),
                field=field,
                new_status=status,
                error_type=type(exc).__name__,
                error=str(exc),
                exc_info=True,
            )

        return ProductResponse.model_validate(product)

    # =========================================================================
    #  仪表盘统计
    # =========================================================================

    async def top_by_sales(self, limit: int = 5) -> list[dict]:
        """商品销售排行 TOP N"""
        from app.models.product.product import PmsProduct

        result = await self.db.execute(
            select(PmsProduct.name, PmsProduct.sale_count, PmsProduct.price)
            .where(PmsProduct.is_deleted == False)  # noqa: E712
            .order_by(PmsProduct.sale_count.desc())
            .limit(limit)
        )
        return [
            {
                "name": row[0],
                "sales": row[1] or 0,
                "amount": int((row[1] or 0) * float(row[2] or 0)),
            }
            for row in result.all()
        ]

    # =========================================================================
    #  SKU 管理
    # =========================================================================

    async def add_sku(self, product_id: UUID, data) -> SkuResponse:
        """
        向已有商品添加一个新 SKU。

        操作流程:
          1. 验证商品存在且未删除
          2. 创建 PmsSku 并 flush 获取 ID
          3. 原子重算商品总库存 (子查询 SUM)
          4. 触发 ES 同步
        """
        from app.models.product.product import PmsProduct
        from app.models.product.sku import PmsSku

        product = await self.db.get(PmsProduct, product_id)
        if not product or product.is_deleted:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))

        sku = PmsSku(product_id=product_id, **data.model_dump())
        self.db.add(sku)
        await self.db.flush()
        await self.db.refresh(sku)

        await self._recalculate_and_sync(product_id)
        return SkuResponse.model_validate(sku)

    async def update_sku(self, product_id: UUID, sku_id: UUID, data) -> SkuResponse:
        """
        更新已有 SKU 的指定字段。

        只更新传入的字段 (exclude_unset)。若库存发生变化则原子重算商品总库存。
        变更后触发 ES 同步。
        """
        from app.models.product.sku import PmsSku

        sku = await self.db.get(PmsSku, sku_id)
        if not sku or sku.product_id != product_id:
            from app.core.exceptions import CommerceException

            raise CommerceException(
                code="SKU_NOT_FOUND",
                message=f"SKU '{sku_id}' not found for product '{product_id}'",
                status_code=404,
            )

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        for key, val in values.items():
            setattr(sku, key, val)
        await self.db.flush()
        await self.db.refresh(sku)

        await self._recalculate_and_sync(product_id)
        return SkuResponse.model_validate(sku)

    async def delete_sku(self, product_id: UUID, sku_id: UUID) -> None:
        """
        删除一个 SKU。

        规则:
          1. 验证 SKU 存在且属于该商品
          2. 不允许删除商品的最后一个 SKU (至少保留一个)
          3. 原子重算商品总库存
          4. 触发 ES 同步
        """
        from sqlalchemy import func
        from sqlalchemy import select as sql_select

        from app.models.product.sku import PmsSku

        sku = await self.db.get(PmsSku, sku_id)
        if not sku or sku.product_id != product_id:
            from app.core.exceptions import CommerceException

            raise CommerceException(
                code="SKU_NOT_FOUND",
                message=f"SKU '{sku_id}' not found for product '{product_id}'",
                status_code=404,
            )

        # 检查是否为最后一个 SKU
        count_result = await self.db.execute(sql_select(func.count(PmsSku.id)).where(PmsSku.product_id == product_id))
        remaining = count_result.scalar() or 0
        if remaining <= 1:
            from app.core.exceptions import CommerceException

            raise CommerceException(
                code="LAST_SKU",
                message="不允许删除商品的最后一个 SKU，至少保留一个",
                status_code=400,
            )

        await self.db.delete(sku)
        await self.db.flush()
        await self._recalculate_and_sync(product_id)

    # =========================================================================
    #  属性值管理
    # =========================================================================

    async def update_attributes(self, product_id: UUID, attribute_values: dict[str, str]) -> list[dict]:
        """
        更新商品的属性值 —— 先删后插 (replace 语义)。

        操作:
          1. 验证商品存在
          2. DELETE 该商品所有已有属性值
          3. INSERT 新属性值
          4. 触发 ES 同步
        """
        from sqlalchemy import delete as sql_delete

        from app.models.product.attribute import PmsProductAttributeValue
        from app.models.product.product import PmsProduct

        product = await self.db.get(PmsProduct, product_id)
        if not product or product.is_deleted:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(product_id))

        # 先删后插 —— 全量替换
        await self.db.execute(
            sql_delete(PmsProductAttributeValue).where(PmsProductAttributeValue.product_id == product_id)
        )

        inserted: list[dict] = []
        for attr_id_str, value in attribute_values.items():
            attr_value = PmsProductAttributeValue(
                product_id=product_id,
                attribute_id=UUID(attr_id_str),
                value=value,
            )
            self.db.add(attr_value)
            inserted.append({"attribute_id": attr_id_str, "value": value})

        await self.db.flush()

        # FUTURE: 改用 Celery 异步重试 (指数退避) 替代 fire-and-forget
        try:
            await sync_product_to_es(self.db, product)
        except Exception as exc:
            logger.warning(
                "es_sync_attr_update_failed",
                product_id=str(product_id),
                error_type=type(exc).__name__,
                error=str(exc),
                exc_info=True,
            )

        return inserted

    # =========================================================================
    #  内部辅助
    # =========================================================================

    async def _recalculate_and_sync(self, product_id: UUID) -> None:
        """
        原子重算商品总库存 (子查询 SUM) 并触发 ES 同步。

        使用子查询在 UPDATE 语句中完成 SUM，避免 SELECT-then-UPDATE 竞态。
        PostgreSQL 行级锁保证并发安全。
        """
        from sqlalchemy import func
        from sqlalchemy import select as sql_select
        from sqlalchemy import update as sql_update

        from app.models.product.product import PmsProduct
        from app.models.product.sku import PmsSku

        # 原子重算库存
        stock_subq = (
            sql_select(func.coalesce(func.sum(PmsSku.stock), 0))
            .where(PmsSku.product_id == product_id)
            .scalar_subquery()
        )
        await self.db.execute(sql_update(PmsProduct).where(PmsProduct.id == product_id).values(stock=stock_subq))
        await self.db.flush()

        # 获取最新 product 对象用于 ES 同步
        product = await self.db.get(PmsProduct, product_id)
        if not product:
            return

        # FUTURE: 改用 Celery 异步重试 (指数退避) 替代 fire-and-forget
        try:
            await sync_product_to_es(self.db, product)
        except Exception as exc:
            logger.warning(
                "es_sync_sku_change_failed",
                product_id=str(product_id),
                error_type=type(exc).__name__,
                error=str(exc),
                exc_info=True,
            )


# ============================================================================
#  ES 同步工具函数 (module-level, used by Service + API + Celery tasks)
# ============================================================================


async def sync_product_to_es(db: AsyncSession, product) -> None:
    """
    将单个商品同步到 Elasticsearch。

    从 Product 构造 ES 文档，从 DB 查询品牌名称和分类名称。
    搜索索引的字段比 DB 表少，只包含搜索/筛选需要的字段。
    """
    from app.models.product.brand import PmsBrand
    from app.models.product.category import PmsCategory
    from app.search.client import get_search_client

    # 查询品牌名称
    brand_name = ""
    if product.brand_id:
        brand = await db.get(PmsBrand, product.brand_id)
        if brand:
            brand_name = brand.name

    # 查询分类名称
    category_name = ""
    if product.category_id:
        category = await db.get(PmsCategory, product.category_id)
        if category:
            category_name = category.name

    doc = {
        "id": str(product.id),
        "name": product.name,
        "sub_title": product.sub_title or "",
        "keywords": product.keywords or "",
        "category_id": str(product.category_id) if product.category_id else "",
        "category_name": category_name,
        "brand_id": str(product.brand_id) if product.brand_id else "",
        "brand_name": brand_name,
        "price": float(product.price),
        "promotion_price": float(product.promotion_price) if product.promotion_price else None,
        "sale_count": product.sale_count or 0,
        "stock": product.stock or 0,
        "pics": product.pics or "",
        "publish_status": product.publish_status,
        "verify_status": product.verify_status,
        "publish_time": product.created_at.isoformat() if product.created_at else None,
    }

    await get_search_client().index_product(str(product.id), doc)
