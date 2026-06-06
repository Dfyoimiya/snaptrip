"""
【品牌 Service】— 业务逻辑层

知识点速查：
  - get() vs execute(select()): db.get(Model, pk) 是快捷方法，按主键查询
    db.execute(select(Model).where(...)) 可以添加任意 WHERE 条件
  - 为什么 update() 用 stmt + execute 而非修改对象属性？
    修改属性: 需要先 get 再赋值，两次 IO
    update() RETURNING: 一次 SQL 完成查找+更新+返回，更高效、原子

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import BrandCreate, BrandResponse, BrandUpdate


class BrandService:
    """品牌服务 —— 提供品牌 CRUD + 列表查询"""

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

    # ── 删除 ──

    async def delete(self, brand_id: UUID) -> None:
        from app.models.product.brand import PmsBrand

        brand = await self.db.get(PmsBrand, brand_id)
        if not brand:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(brand_id))
        await self.db.delete(brand)

    # ── 详情 ──

    async def get_by_id(self, brand_id: UUID) -> BrandResponse:
        from app.models.product.brand import PmsBrand

        brand = await self.db.get(PmsBrand, brand_id)
        if not brand:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(brand_id))
        return BrandResponse.model_validate(brand)

    # ── 分页列表 ──

    async def list_paginated(
        self,
        keyword: str | None = None,
        first_letter: str | None = None,
        factory_status: int | None = None,
        show_status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BrandResponse], int]:
        """
        分页获取品牌 —— 支持名称搜索 + 首字母筛选 + 状态筛选。

        筛选条件组合: 只在用户传入时添加 WHERE，未传入的跳过。
        如果用 if-else 嵌套: 会导致 2^n 种组合，n=4 → 16 个分支
        用动态构建 query: 线性复杂度，每个条件独立判断
        """
        from app.models.product.brand import PmsBrand

        query = select(PmsBrand)
        count_q = select(func.count(PmsBrand.id))

        if keyword:
            # ilike: 不区分大小写的 LIKE，适合中文搜索
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
            query
            .order_by(PmsBrand.sort.asc(), PmsBrand.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = result.scalars().all()
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
            .where(PmsBrand.show_status == 1)
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
