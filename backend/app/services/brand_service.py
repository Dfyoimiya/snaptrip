"""
【品牌 Service】— 业务逻辑层

知识点速查：
  - get() vs execute(select()): db.get(Model, pk) 是快捷方法，按主键查询
    db.execute(select()).where(...) 可以添加任意 WHERE 条件
  - 为什么 update() 用 stmt + execute 而非修改对象属性？
    修改属性: 需要先 get 再赋值，两次 IO
    update() RETURNING: 一次 SQL 完成查找+更新+返回，更高效、原子
  - Haversine 公式: 基于球面三角学计算两点间大圆距离，误差 < 0.5%
    适用于短距离门店筛选场景，无需调用外部 API

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    BrandCreate,
    BrandDetailResponse,
    BrandListResponse,
    BrandResponse,
    BrandUpdate,
    ProductBriefResponse,
)

# Earth's mean radius in kilometers (WGS-84)
_EARTH_RADIUS_KM = 6371.0


def _haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points using the Haversine formula.

    Args:
        lat1, lng1: Latitude/longitude of point 1 (degrees).
        lat2, lng2: Latitude/longitude of point 2 (degrees).

    Returns:
        Distance in kilometers, rounded to 2 decimal places.
    """
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(_EARTH_RADIUS_KM * c, 2)


class BrandService:
    """品牌服务 —— 提供品牌 CRUD + 列表查询 + 距离排序"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 创建 ──

    async def create(self, data: BrandCreate) -> BrandResponse:
        from app.models.product.brand import PmsBrand

        brand = PmsBrand(**data.model_dump())
        self.db.add(brand)
        await self.db.flush()
        await self.db.refresh(brand)
        return BrandResponse.model_validate(brand)

    # ── 更新 ──

    async def update(self, brand_id: UUID, data: BrandUpdate) -> BrandResponse:
        from app.models.product.brand import PmsBrand

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        stmt = update(PmsBrand).where(PmsBrand.id == brand_id).values(**values).returning(PmsBrand)
        result = await self.db.execute(stmt)
        brand = result.scalar_one_or_none()
        if not brand:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(brand_id))
        return BrandResponse.model_validate(brand)

    # ── 软删除 ──

    async def delete(self, brand_id: UUID) -> None:
        """软删除品牌 —— 设置 is_deleted=True 而非物理删除。"""
        from app.models.product.brand import PmsBrand

        brand = await self.db.get(PmsBrand, brand_id)
        if not brand:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(brand_id))
        brand.is_deleted = True
        brand.deleted_at = datetime.now(UTC)
        await self.db.flush()

    # ── 详情 ──

    async def get_by_id(self, brand_id: UUID) -> BrandResponse:
        from app.models.product.brand import PmsBrand

        brand = await self.db.get(PmsBrand, brand_id)
        if not brand:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(brand_id))
        return BrandResponse.model_validate(brand)

    async def get_detail(
        self,
        brand_id: UUID,
        product_page: int = 1,
        product_page_size: int = 10,
    ) -> BrandDetailResponse:
        """获取品牌详情，含商品数量与分页商品列表。

        仅返回上架且未删除的商品。
        """
        from app.models.product.brand import PmsBrand
        from app.models.product.product import PmsProduct

        brand = await self.db.get(PmsBrand, brand_id)
        if not brand:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(brand_id))

        # 商品总数
        count_q = select(func.count(PmsProduct.id)).where(
            PmsProduct.brand_id == brand_id,
            PmsProduct.publish_status == 1,
            PmsProduct.is_deleted == False,  # noqa: E712
        )
        count_result = await self.db.execute(count_q)
        product_count = count_result.scalar() or 0

        # 分页商品列表
        products_q = (
            select(
                PmsProduct.id,
                PmsProduct.name,
                PmsProduct.default_pic,
                PmsProduct.price,
                PmsProduct.sale_count,
            )
            .where(
                PmsProduct.brand_id == brand_id,
                PmsProduct.publish_status == 1,
                PmsProduct.is_deleted == False,  # noqa: E712
            )
            .order_by(PmsProduct.sale_count.desc())
            .offset((product_page - 1) * product_page_size)
            .limit(product_page_size)
        )
        product_result = await self.db.execute(products_q)
        product_rows = product_result.all()

        products = [
            ProductBriefResponse(
                id=row.id,
                name=row.name,
                default_pic=row.default_pic,
                price=row.price,
                sale_count=row.sale_count,
            )
            for row in product_rows
        ]

        brand_resp = BrandResponse.model_validate(brand)
        return BrandDetailResponse(
            **brand_resp.model_dump(),
            product_count=product_count,
            products=products,
        )

    # ── 分页列表 ──

    async def list_paginated(
        self,
        keyword: str | None = None,
        first_letter: str | None = None,
        factory_status: int | None = None,
        show_status: int | None = None,
        lat: float | None = None,
        lng: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BrandResponse | BrandListResponse], int]:
        """
        分页获取品牌 —— 支持名称搜索 + 首字母筛选 + 状态筛选 + 距离排序。

        Args:
            lat: 用户纬度，用于距离计算。不传则不计算距离。
            lng: 用户经度，用于距离计算。不传则不计算距离。
        """
        from app.models.product.brand import PmsBrand

        query = select(PmsBrand)
        count_q = select(func.count(PmsBrand.id))

        # 软删除过滤 —— 始终排除已删除的品牌
        query = query.where(PmsBrand.is_deleted == False)  # noqa: E712
        count_q = count_q.where(PmsBrand.is_deleted == False)  # noqa: E712

        if keyword:
            query = query.where(PmsBrand.name.ilike(f"%{keyword}%"))
            count_q = count_q.where(PmsBrand.name.ilike(f"%{keyword}%"))
        if first_letter:
            query = query.where(PmsBrand.first_letter == first_letter.upper())
            count_q = count_q.where(PmsBrand.first_letter == first_letter.upper())
        if factory_status is not None:
            query = query.where(PmsBrand.factory_status == factory_status)
            count_q = count_q.where(PmsBrand.factory_status == factory_status)
        if show_status is not None:
            query = query.where(PmsBrand.show_status == show_status)
            count_q = count_q.where(PmsBrand.show_status == show_status)

        result = await self.db.execute(count_q)
        total = result.scalar() or 0

        result = await self.db.execute(
            query.order_by(PmsBrand.sort.asc(), PmsBrand.name.asc()).offset((page - 1) * page_size).limit(page_size)
        )
        items: list[PmsBrand] = list(result.scalars().all())  # type: ignore[arg-type]

        # 如果有 lat/lng，计算距离并包装为 BrandListResponse
        if lat is not None and lng is not None:
            outputs: list[BrandResponse | BrandListResponse] = []
            for b in items:
                base = BrandResponse.model_validate(b)
                dist: float | None = None
                if b.latitude is not None and b.longitude is not None:
                    dist = _haversine_distance_km(lat, lng, b.latitude, b.longitude)
                outputs.append(
                    BrandListResponse(
                        **base.model_dump(),
                        distance_km=dist,
                    )
                )
            # Sort by distance ascending (None values at the end)
            outputs.sort(
                key=lambda x: (
                    x.distance_km is None,  # type: ignore[union-attr]
                    x.distance_km or 999999,  # type: ignore[union-attr]
                )
            )
            return outputs, total

        return [BrandResponse.model_validate(b) for b in items], total

    # ── 全部品牌 (下拉选择器) ──

    async def list_all(self) -> list[BrandResponse]:
        """
        获取所有启用的品牌 —— 用于商品编辑页选择品牌。

        无分页，全部返回: 品牌数量通常 < 500，前端下拉框不需要分页
        """
        from app.models.product.brand import PmsBrand

        result = await self.db.execute(
            select(PmsBrand)
            .where(PmsBrand.show_status == 1, PmsBrand.is_deleted == False)  # noqa: E712
            .order_by(PmsBrand.sort.asc(), PmsBrand.name.asc())
        )
        brands = result.scalars().all()
        return [BrandResponse.model_validate(b) for b in brands]

    # ── 状态切换 ──

    async def toggle_status(self, brand_id: UUID, field: str, status: int) -> BrandResponse:
        from app.models.product.brand import PmsBrand

        stmt = update(PmsBrand).where(PmsBrand.id == brand_id).values(**{field: status}).returning(PmsBrand)
        result = await self.db.execute(stmt)
        brand = result.scalar_one_or_none()
        if not brand:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(brand_id))
        return BrandResponse.model_validate(brand)
