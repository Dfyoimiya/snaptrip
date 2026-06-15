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
        # FastAPI 依赖注入机制: get_db → yield session → 路由 → CategoryService(session)
        # 每个请求一个独立的 AsyncSession，请求结束自动 commit/rollback
        self.db = db

    # ── 创建 ──

    async def create(self, data: CategoryCreate) -> CategoryResponse:
        """
        创建分类。

        关键点:
        - model_dump() 把 Pydantic 对象转成 dict，直接解包到 ORM 构造函数
          不这样做: 需要手动逐个字段赋值，代码冗长且容易遗漏
        """
        from app.models.product.category import PmsCategory

        category = PmsCategory(**data.model_dump())
        self.db.add(category)
        await self.db.flush()  # flush 不提交事务，仅让 DB 生成 id，后续可以在同一事务中使用
        # refresh 从 DB 重新加载对象，确保 created_at 等 server_default 字段被填充
        await self.db.refresh(category)
        return CategoryResponse.model_validate(category)

    # ── 更新 ──

    async def update(self, category_id: UUID, data: CategoryUpdate) -> CategoryResponse:
        """
        编辑分类。

        关键点:
        - model_dump(exclude_unset=True): 只序列化用户实际传了的字段
          如果用 model_dump(): 所有字段都序列化，未传的字段会设成 None，覆盖已有值
          这是 Pydantic v2 的核心特性之一
        """
        from app.models.product.category import PmsCategory

        values = data.model_dump(exclude_unset=True)  # 只取用户实际传入的字段
        if not values:
            from app.core.exceptions import CommerceException
            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)

        stmt = (
            update(PmsCategory)
            .where(PmsCategory.id == category_id)
            .values(**values)
            .returning(PmsCategory)  # RETURNING 子句，一次性获取更新后的行
        )
        result = await self.db.execute(stmt)
        category = result.scalar_one_or_none()
        if not category:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(category_id))

        return CategoryResponse.model_validate(category)

    # ── 删除 ──

    async def delete(self, category_id: UUID) -> None:
        """
        删除分类。

        关键点:
        - 子分类处理: ON DELETE SET NULL (见模型定义)，子分类的 parent_id 自动变 NULL
          如果不设这个: 删除父分类时会报外键约束错误
        """
        from app.models.product.category import PmsCategory

        category = await self.db.get(PmsCategory, category_id)
        if not category:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(category_id))
        await self.db.delete(category)

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
        self, parent_id: UUID | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[CategoryResponse], int]:
        """
        分页获取分类列表 —— 按 parent_id 筛选 + 分页。

        返回值: (当前页列表, 总数)
        """
        from app.models.product.category import PmsCategory

        # 构建基础查询
        base_query = select(PmsCategory)
        count_query = select(func.count(PmsCategory.id))

        if parent_id is not None:
            base_query = base_query.where(PmsCategory.parent_id == parent_id)
            count_query = count_query.where(PmsCategory.parent_id == parent_id)

        # 获取总数
        result = await self.db.execute(count_query)
        total = result.scalar() or 0

        # 获取当前页数据 —— order_by sort 确保自定义排序生效
        result = await self.db.execute(
            base_query
            .order_by(PmsCategory.sort.asc(), PmsCategory.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        categories = result.scalars().all()
        return [CategoryResponse.model_validate(c) for c in categories], total

    # ── 查询: 树形结构 ──

    async def get_tree(self) -> list[CategoryTreeResponse]:
        """
        获取分类树 —— 一次查询全部分类，Python 端构建树。

        为什么不直接在 SQL 中递归构建？
        - 分类数据量少 (通常 < 1000)，全量加载到内存是最快的
        - SQL 递归 CTE 的写法在不同 DB 中差异大，可移植性差
        - Python 端构建更灵活 (排序、过滤子节点等)
        """
        from app.models.product.category import PmsCategory

        result = await self.db.execute(
            select(PmsCategory).order_by(PmsCategory.sort.asc(), PmsCategory.created_at.desc())
        )
        all_categories = result.scalars().all()

        # Build parent_id → children map
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
        """
        切换分类状态 —— 通用方法，支持 nav_status / show_status。

        field 参数是列名，通过 update() 动态设置。
        如果不用通用方法: 每种状态切换都要写一个独立函数，代码重复
        """
        from app.models.product.category import PmsCategory

        stmt = (
            update(PmsCategory)
            .where(PmsCategory.id == category_id)
            .values(**{field: status})
            .returning(PmsCategory)
        )
        result = await self.db.execute(stmt)
        category = result.scalar_one_or_none()
        if not category:
            from app.core.exceptions import ProductNotFoundError
            raise ProductNotFoundError(str(category_id))
        return CategoryResponse.model_validate(category)
