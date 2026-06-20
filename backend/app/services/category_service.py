"""
【分类 Service】— 业务逻辑层

知识点速查：
  - async session: 所有 DB 操作必须 await，因为使用了 asyncpg 异步驱动
    如果忘记 await: SQLAlchemy 会报 coroutine was never awaited 错误
  - selectinload: 预加载关系数据，一次 SQL 加载所有关联对象
    如果用默认 lazy="select": 访问每个 .parent 会发一次 SQL (N+1 问题)
  - 蛇形命名转驼峰: 数据库中字段是 snake_case，Pydantic schema 也是 snake_case，
    FastAPI 自动序列化时保持 snake_case，前端按惯例用 camelCase

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    CategoryCreate,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdate,
)


class CategoryService:
    """分类服务 —— 提供分类 CRUD + 树形结构查询"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 创建 ──

    async def create(self, data: CategoryCreate) -> CategoryResponse:
        from app.models.product.category import PmsCategory

        # Auto-compute level from parent chain; ignore caller-supplied level.
        level = 0
        if data.parent_id:
            parent = await self.db.get(PmsCategory, data.parent_id)
            if not parent:
                from app.core.exceptions import CommerceException

                raise CommerceException(
                    code="PARENT_NOT_FOUND",
                    message=f"父分类不存在: {data.parent_id}",
                    status_code=400,
                )
            level = parent.level + 1
            if level > 2:
                from app.core.exceptions import CommerceException

                raise CommerceException(
                    code="CATEGORY_LEVEL_EXCEEDED",
                    message=f"分类层级不能超过2级 (父分类为{parent.level}级，子分类将为{level}级)",
                    status_code=400,
                )

        # Auto-compute sort = max sibling sort + 1, so new category always at the end.
        max_sort_result = await self.db.execute(
            select(func.coalesce(func.max(PmsCategory.sort), -1)).where(
                PmsCategory.parent_id == data.parent_id
            )
        )
        next_sort = (max_sort_result.scalar() or -1) + 1

        category_data = data.model_dump()
        category_data["level"] = level
        category_data["sort"] = next_sort
        category = PmsCategory(**category_data)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return CategoryResponse.model_validate(category)

    # ── 更新 ──

    async def update(self, category_id: UUID, data: CategoryUpdate) -> CategoryResponse:
        from app.models.product.category import PmsCategory

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        # If parent_id is being changed, validate new parent and recompute level
        if "parent_id" in values:
            new_parent_id = values["parent_id"]
            if new_parent_id is not None:
                if new_parent_id == category_id:
                    from app.core.exceptions import CommerceException

                    raise CommerceException(
                        code="CATEGORY_SELF_PARENT",
                        message="分类不能将自己设为父分类",
                        status_code=400,
                    )
                parent = await self.db.get(PmsCategory, new_parent_id)
                if not parent:
                    from app.core.exceptions import CommerceException

                    raise CommerceException(
                        code="PARENT_NOT_FOUND",
                        message=f"父分类不存在: {new_parent_id}",
                        status_code=400,
                    )
                new_level = parent.level + 1
                if new_level > 2:
                    from app.core.exceptions import CommerceException

                    raise CommerceException(
                        code="CATEGORY_LEVEL_EXCEEDED",
                        message=f"分类层级不能超过2级 (父分类为{parent.level}级，子分类将为{new_level}级)",
                        status_code=400,
                    )
                values["level"] = new_level
            else:
                values["level"] = 0

        stmt = update(PmsCategory).where(PmsCategory.id == category_id).values(**values).returning(PmsCategory)
        result = await self.db.execute(stmt)
        category = result.scalar_one_or_none()
        if not category:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(category_id))

        return CategoryResponse.model_validate(category)

    # ── 删除 ──

    async def delete(self, category_id: UUID, force: bool = False) -> None:
        """删除分类 —— 带安全校验。

        安全规则:
        1. 如果存在子分类且 force=False，抛出错误
        2. 如果存在关联商品且 force=False，抛出错误
        3. force=True 时：子分类的 parent_id 设为被删除分类的 parent_id，
           关联商品的 category_id 设为 NULL

        Args:
            category_id: 要删除的分类 ID。
            force: 是否强制删除（处理子分类和关联商品）。

        Raises:
            CommerceException: 当存在子分类或关联商品且 force=False 时。
        """
        from app.models.product.category import PmsCategory
        from app.models.product.product import PmsProduct

        category = await self.db.get(PmsCategory, category_id)
        if not category:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(category_id))

        # 检查子分类数量
        child_count_result = await self.db.execute(
            select(func.count(PmsCategory.id)).where(PmsCategory.parent_id == category_id)
        )
        child_count = child_count_result.scalar() or 0

        # 检查关联商品数量
        product_count_result = await self.db.execute(
            select(func.count(PmsProduct.id)).where(PmsProduct.category_id == category_id)
        )
        product_count = product_count_result.scalar() or 0

        blockers: list[str] = []
        if child_count > 0:
            blockers.append(f"该分类下有 {child_count} 个子分类")
        if product_count > 0:
            blockers.append(f"该分类下有 {product_count} 个关联商品")

        if blockers and not force:
            from app.core.exceptions import CommerceException

            raise CommerceException(
                code="CATEGORY_DELETE_BLOCKED",
                message="无法删除分类: " + "；".join(blockers) + "。可使用 force=true 强制删除",
                status_code=409,
            )

        if force:
            new_parent_id = category.parent_id
            if child_count > 0:
                # 将子分类重新挂载到被删除分类的父分类
                await self.db.execute(
                    update(PmsCategory).where(PmsCategory.parent_id == category_id).values(parent_id=new_parent_id)
                )
            if product_count > 0:
                # 将关联商品的 category_id 设为 NULL
                await self.db.execute(
                    update(PmsProduct).where(PmsProduct.category_id == category_id).values(category_id=None)
                )

        await self.db.delete(category)
        await self.db.flush()

    # ── 查询: 详情 ──

    async def get_by_id(self, category_id: UUID) -> CategoryResponse:
        from app.models.product.category import PmsCategory

        category = await self.db.get(PmsCategory, category_id)
        if not category:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(category_id))
        return CategoryResponse.model_validate(category)

    # ── 查询: 分页列表 ──

    async def list_paginated(
        self,
        parent_id: UUID | None = None,
        show_status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CategoryResponse], int]:
        """
        分页获取分类列表 —— 按 parent_id 筛选 + show_status 过滤 + 分页。

        Args:
            parent_id: 父分类 ID，不传则不过滤层级。
            show_status: 显示状态过滤，portal 端传 1 仅显示可见分类。
            page: 页码。
            page_size: 每页数量。

        Returns:
            (当前页列表, 总数)
        """
        from app.models.product.category import PmsCategory

        base_query = select(PmsCategory)
        count_query = select(func.count(PmsCategory.id))

        if parent_id is not None:
            base_query = base_query.where(PmsCategory.parent_id == parent_id)
            count_query = count_query.where(PmsCategory.parent_id == parent_id)

        if show_status is not None:
            base_query = base_query.where(PmsCategory.show_status == show_status)
            count_query = count_query.where(PmsCategory.show_status == show_status)

        result = await self.db.execute(count_query)
        total = result.scalar() or 0

        result = await self.db.execute(
            base_query.order_by(PmsCategory.sort.asc(), PmsCategory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        categories = result.scalars().all()
        return [CategoryResponse.model_validate(c) for c in categories], total

    # ── 查询: 树形结构 ──

    async def get_tree(self, show_status: int | None = None) -> list[CategoryTreeResponse]:
        """
        获取分类树 —— 一次查询全部分类，Python 端构建树。

        Args:
            show_status: 显示状态过滤，portal 端传 1 仅显示可见分类。
        """
        from app.models.product.category import PmsCategory

        stmt = select(PmsCategory).order_by(PmsCategory.sort.asc(), PmsCategory.created_at.desc())
        if show_status is not None:
            stmt = stmt.where(PmsCategory.show_status == show_status)

        result = await self.db.execute(stmt)
        all_categories = result.scalars().all()

        # Build parent_id -> children map
        children_map: dict[UUID | None, list[PmsCategory]] = {}
        for cat in all_categories:
            pid = cat.parent_id
            if pid not in children_map:
                children_map[pid] = []
            children_map[pid].append(cat)

        def _build_node(cat: PmsCategory) -> CategoryTreeResponse:
            """递归构建树节点"""
            return CategoryTreeResponse(
                id=cat.id,
                name=cat.name,
                parent_id=cat.parent_id,
                type=cat.type,
                level=cat.level,
                sort=cat.sort,
                nav_status=cat.nav_status,
                show_status=cat.show_status,
                icon=cat.icon,
                children=[_build_node(child) for child in children_map.get(cat.id, [])],
            )

        return [_build_node(root) for root in children_map.get(None, [])]

    # ── 状态切换 ──

    async def toggle_status(self, category_id: UUID, field: str, status: int) -> CategoryResponse:
        from app.models.product.category import PmsCategory

        stmt = update(PmsCategory).where(PmsCategory.id == category_id).values(**{field: status}).returning(PmsCategory)
        result = await self.db.execute(stmt)
        category = result.scalar_one_or_none()
        if not category:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(category_id))
        return CategoryResponse.model_validate(category)

    # ── 批量排序 ──

    async def reorder(self, items: list[dict]) -> list[CategoryResponse]:
        """批量更新分类排序值。

        拖拽排序后前端传入 [{id, sort}, ...] 列表，一次性更新所有变更项。
        """
        from app.models.product.category import PmsCategory

        results: list[CategoryResponse] = []
        for item in items:
            cat_id = UUID(item["id"])
            new_sort = item["sort"]
            stmt = (
                update(PmsCategory)
                .where(PmsCategory.id == cat_id)
                .values(sort=new_sort)
                .returning(PmsCategory)
            )
            result = await self.db.execute(stmt)
            category = result.scalar_one_or_none()
            if category:
                results.append(CategoryResponse.model_validate(category))
        await self.db.flush()
        return results
