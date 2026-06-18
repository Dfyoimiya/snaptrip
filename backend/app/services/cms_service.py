"""
【CMS 内容 + 统计 Service】

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.cms import (
    BannerCreate,
    BannerResponse,
    BannerUpdate,
    DashboardOverview,
    HelpCreate,
    HelpResponse,
    HelpUpdate,
    HomePageAggregation,
    ProductRankItem,
    SalesStatItem,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)
from app.schemas.notice import NoticeCreate, NoticeResponse, NoticeUpdate


class CmsService:
    """内容管理 —— Banner/Subject/Help CRUD"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Banner ──

    async def create_banner(self, data: BannerCreate) -> BannerResponse:
        from app.models.cms.content import CmsBanner

        b = CmsBanner(**data.model_dump())
        self.db.add(b)
        await self.db.flush()
        await self.db.refresh(b)
        return BannerResponse.model_validate(b)

    async def update_banner(self, banner_id: UUID, data: BannerUpdate) -> BannerResponse:
        from app.models.cms.content import CmsBanner

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = update(CmsBanner).where(CmsBanner.id == banner_id).values(**values).returning(CmsBanner)
        result = await self.db.execute(stmt)
        b = result.scalar_one_or_none()
        if not b:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(banner_id))
        return BannerResponse.model_validate(b)

    async def delete_banner(self, banner_id: UUID) -> None:
        from app.models.cms.content import CmsBanner

        b = await self.db.get(CmsBanner, banner_id)
        if not b:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(banner_id))
        await self.db.delete(b)

    async def list_banners(self, status: int | None = None, position: str | None = None) -> list[BannerResponse]:
        from app.models.cms.content import CmsBanner

        base = select(CmsBanner)
        if status is not None:
            base = base.where(CmsBanner.status == status)
        if position:
            base = base.where(CmsBanner.position == position)
        result = await self.db.execute(base.order_by(CmsBanner.sort.asc()))
        return [BannerResponse.model_validate(b) for b in result.scalars().all()]

    async def toggle_banner(self, banner_id: UUID, field: str, value: int) -> BannerResponse:
        if field not in ("status", "sort"):
            raise ValueError(f"不允许更新字段: {field}")
        from app.models.cms.content import CmsBanner

        stmt = update(CmsBanner).where(CmsBanner.id == banner_id).values(**{field: value}).returning(CmsBanner)
        result = await self.db.execute(stmt)
        b = result.scalar_one_or_none()
        if not b:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(banner_id))
        return BannerResponse.model_validate(b)

    # ── Subject ──

    async def create_subject(self, data: SubjectCreate) -> SubjectResponse:
        from app.models.cms.content import CmsSubject

        s = CmsSubject(**data.model_dump())
        self.db.add(s)
        await self.db.flush()
        await self.db.refresh(s)
        return SubjectResponse.model_validate(s)

    async def update_subject(self, subject_id: UUID, data: SubjectUpdate) -> SubjectResponse:
        from app.models.cms.content import CmsSubject

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = update(CmsSubject).where(CmsSubject.id == subject_id).values(**values).returning(CmsSubject)
        result = await self.db.execute(stmt)
        s = result.scalar_one_or_none()
        if not s:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(subject_id))
        return SubjectResponse.model_validate(s)

    async def delete_subject(self, subject_id: UUID) -> None:
        from app.models.cms.content import CmsSubject

        s = await self.db.get(CmsSubject, subject_id)
        if not s:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(subject_id))
        await self.db.delete(s)

    async def list_subjects(
        self, status: int | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[SubjectResponse], int]:
        from app.models.cms.content import CmsSubject

        base = select(CmsSubject)
        cnt = select(func.count(CmsSubject.id))
        if status is not None:
            base = base.where(CmsSubject.status == status)
            cnt = cnt.where(CmsSubject.status == status)
        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(CmsSubject.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [SubjectResponse.model_validate(s) for s in result.scalars().all()], total

    async def list_subject_categories(self) -> list[dict]:
        """返回所有专题的分类名（去重+排序），格式 [{id, name}]"""
        from app.models.cms.content import CmsSubject

        result = await self.db.execute(
            select(CmsSubject.category_name).where(CmsSubject.category_name.isnot(None)).distinct()
        )
        names = sorted([r for r in result.scalars().all() if r])
        return [{"id": i + 1, "name": name} for i, name in enumerate(names)]

    # ── Help ──

    async def create_help(self, data: HelpCreate) -> HelpResponse:
        from app.models.cms.content import CmsHelp

        h = CmsHelp(**data.model_dump())
        self.db.add(h)
        await self.db.flush()
        await self.db.refresh(h)
        return HelpResponse.model_validate(h)

    async def update_help(self, help_id: UUID, data: HelpUpdate) -> HelpResponse:
        from app.models.cms.content import CmsHelp

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = update(CmsHelp).where(CmsHelp.id == help_id).values(**values).returning(CmsHelp)
        result = await self.db.execute(stmt)
        h = result.scalar_one_or_none()
        if not h:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(help_id))
        return HelpResponse.model_validate(h)

    async def delete_help(self, help_id: UUID) -> None:
        from app.models.cms.content import CmsHelp

        h = await self.db.get(CmsHelp, help_id)
        if not h:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(help_id))
        await self.db.delete(h)

    async def list_helps(
        self, category_name: str | None = None, status: int | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[HelpResponse], int]:
        from app.models.cms.content import CmsHelp

        base = select(CmsHelp)
        cnt = select(func.count(CmsHelp.id))
        if category_name:
            base = base.where(CmsHelp.category_name == category_name)
            cnt = cnt.where(CmsHelp.category_name == category_name)
        if status is not None:
            base = base.where(CmsHelp.status == status)
            cnt = cnt.where(CmsHelp.status == status)
        result = await self.db.execute(cnt)
        total = result.scalar() or 0
        result = await self.db.execute(
            base.order_by(CmsHelp.sort.asc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [HelpResponse.model_validate(h) for h in result.scalars().all()], total


class StatsService:
    """统计服务 —— 仪表盘概览 + 销售趋势 + 商品排行"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard_overview(self) -> DashboardOverview:
        """
        仪表盘概览 —— 聚合今日订单/销售额 + 商品总数。

        统计来源:
          - 订单: oms_orders (status >= 1 即已支付)
          - 商品: pms_products
        """
        from app.models.product.product import PmsProduct

        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 今日订单数 + 销售额 (status >= 1 已支付)
        from app.models.order.order import OmsOrder

        order_result = await self.db.execute(
            select(
                func.count(OmsOrder.id),
                func.coalesce(func.sum(OmsOrder.pay_amount), 0),
            ).where(
                OmsOrder.status >= 1,
                OmsOrder.created_at >= today_start,
                OmsOrder.delete_status == 0,
            )
        )
        today_orders, today_sales = order_result.one()

        # 商品总数
        product_result = await self.db.execute(select(func.count(PmsProduct.id)))
        total_products = product_result.scalar() or 0

        # 上架商品数
        on_shelf_result = await self.db.execute(
            select(func.count(PmsProduct.id)).where(PmsProduct.publish_status == 1, PmsProduct.is_deleted.is_(False))
        )
        on_shelf = on_shelf_result.scalar() or 0

        return DashboardOverview(
            today_order_count=int(today_orders or 0),
            today_sales_amount=float(today_sales or 0),
            today_new_member_count=0,  # 需要 ums_members 表，Phase 6 补充
            total_product_count=int(total_products),
            on_shelf_product_count=int(on_shelf),
        )

    async def get_sales_stats(self, days: int = 7) -> list[SalesStatItem]:
        """
        按日统计销售额 —— 默认近 7 天。

        用 PostgreSQL DATE_TRUNC 函数按天聚合:
          SELECT DATE(created_at), COUNT(*), SUM(pay_amount)
          FROM oms_orders
          WHERE created_at >= NOW() - INTERVAL '7 days' AND status >= 1
          GROUP BY DATE(created_at) ORDER BY 1
        """
        from app.models.order.order import OmsOrder

        start_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)

        result = await self.db.execute(
            select(
                func.date(OmsOrder.created_at).label("date"),
                func.count(OmsOrder.id).label("cnt"),
                func.coalesce(func.sum(OmsOrder.pay_amount), 0).label("amt"),
            )
            .where(
                OmsOrder.status >= 1,
                OmsOrder.created_at >= start_date,
                OmsOrder.delete_status == 0,
            )
            .group_by(func.date(OmsOrder.created_at))
            .order_by(func.date(OmsOrder.created_at).asc())
        )
        rows = result.all()
        return [SalesStatItem(date=str(r.date), order_count=int(r.cnt), amount=float(r.amt)) for r in rows]

    async def get_product_rank(self, limit: int = 10) -> list[ProductRankItem]:
        """
        商品销量排行 —— 按 sale_count 降序取 Top N。

        为什么不用 oms_order_items 聚合？
          商品表的 sale_count 是冗余汇总字段，查询 O(1) 直接读取
          如果要精确统计，可以用 oms_order_items GROUP BY product_id，
          但需要全表扫描，这里用冗余字段做一个快速排行
        """
        from app.models.product.product import PmsProduct

        result = await self.db.execute(
            select(PmsProduct)
            .where(PmsProduct.is_deleted.is_(False))
            .order_by(PmsProduct.sale_count.desc())
            .limit(limit)
        )
        products = result.scalars().all()
        return [
            ProductRankItem(
                product_id=str(p.id),
                product_name=p.name,
                sale_count=p.sale_count or 0,
                amount=float(p.price * (p.sale_count or 0)),
            )
            for p in products
        ]

    async def get_homepage(self) -> HomePageAggregation:
        """首页聚合 —— Banner(按位置分组) + 新品 + 推荐商品 + 推荐专题"""
        from app.models.cms.content import CmsBanner, CmsSubject

        # Banner —— 按 position 分组查询
        top_result = await self.db.execute(
            select(CmsBanner)
            .where(CmsBanner.status == 1, CmsBanner.position == "HOME_TOP")
            .order_by(CmsBanner.sort.asc())
            .limit(5)
        )
        home_top_banners = [BannerResponse.model_validate(b) for b in top_result.scalars().all()]

        middle_result = await self.db.execute(
            select(CmsBanner)
            .where(CmsBanner.status == 1, CmsBanner.position == "HOME_MIDDLE")
            .order_by(CmsBanner.sort.asc())
            .limit(5)
        )
        home_middle_banners = [BannerResponse.model_validate(b) for b in middle_result.scalars().all()]

        # 新品推荐 (最近上架的 8 个商品)
        from app.models.product.product import PmsProduct

        new_result = await self.db.execute(
            select(PmsProduct)
            .where(PmsProduct.publish_status == 1, PmsProduct.verify_status == 1, PmsProduct.is_deleted.is_(False))
            .order_by(PmsProduct.created_at.desc())
            .limit(8)
        )
        new_products = [
            {
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "default_pic": p.default_pic or "",
                "sale_count": p.sale_count or 0,
            }
            for p in new_result.scalars().all()
        ]

        # 推荐商品
        rec_result = await self.db.execute(
            select(PmsProduct)
            .where(
                PmsProduct.publish_status == 1,
                PmsProduct.verify_status == 1,
                PmsProduct.recommend_status == 1,
                PmsProduct.is_deleted.is_(False),
            )
            .order_by(PmsProduct.sale_count.desc())
            .limit(8)
        )
        recommend_products = [
            {
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "default_pic": p.default_pic or "",
                "sale_count": p.sale_count or 0,
            }
            for p in rec_result.scalars().all()
        ]

        # 推荐专题
        subject_result = await self.db.execute(
            select(CmsSubject)
            .where(CmsSubject.status == 1, CmsSubject.recommend_status == 1)
            .order_by(CmsSubject.created_at.desc())
            .limit(4)
        )
        subjects = [SubjectResponse.model_validate(s) for s in subject_result.scalars().all()]

        return HomePageAggregation(
            home_top_banners=home_top_banners,
            home_middle_banners=home_middle_banners,
            new_products=new_products,
            recommend_products=recommend_products,
            subjects=subjects,
        )


class NoticeService:
    """公告管理 —— CmsNotice CRUD"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_notice(self, data: NoticeCreate) -> NoticeResponse:
        from app.models.cms.notice import CmsNotice

        n = CmsNotice(**data.model_dump())
        self.db.add(n)
        await self.db.flush()
        await self.db.refresh(n)
        return NoticeResponse.model_validate(n)

    async def update_notice(self, notice_id: UUID, data: NoticeUpdate) -> NoticeResponse:
        from app.models.cms.notice import CmsNotice

        values = data.model_dump(exclude_unset=True)
        if not values:
            from app.core.exceptions import CommerceException

            raise CommerceException(code="NO_FIELDS", message="没有提供需要更新的字段", status_code=400)
        stmt = (
            update(CmsNotice)
            .where(CmsNotice.id == notice_id, CmsNotice.is_deleted.is_(False))
            .values(**values)
            .returning(CmsNotice)
        )
        result = await self.db.execute(stmt)
        n = result.scalar_one_or_none()
        if not n:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(notice_id))
        return NoticeResponse.model_validate(n)

    async def delete_notice(self, notice_id: UUID) -> None:
        from app.models.cms.notice import CmsNotice

        n = await self.db.get(CmsNotice, notice_id)
        if not n:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(notice_id))
        # 软删除
        n.is_deleted = True
        n.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def get_notice(self, notice_id: UUID) -> NoticeResponse:
        from app.models.cms.notice import CmsNotice

        n = await self.db.get(CmsNotice, notice_id)
        if not n or n.is_deleted:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(notice_id))
        return NoticeResponse.model_validate(n)

    async def list_notices(
        self, target_type: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[NoticeResponse], int]:
        from app.models.cms.notice import CmsNotice

        base = select(CmsNotice).where(CmsNotice.is_deleted.is_(False))
        cnt = select(func.count(CmsNotice.id)).where(CmsNotice.is_deleted.is_(False))
        if target_type:
            base = base.where(CmsNotice.target_type == target_type)
            cnt = cnt.where(CmsNotice.target_type == target_type)
        cnt_result = await self.db.execute(cnt)
        total = cnt_result.scalar() or 0
        result = await self.db.execute(
            base.order_by(CmsNotice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [NoticeResponse.model_validate(n) for n in result.scalars().all()], total

    async def list_portal_notices(self, page: int = 1, page_size: int = 20) -> tuple[list[NoticeResponse], int]:
        """前台公告：只返回已发布且目标类型为 ALL 或 CUSTOMER 的公告，按发布时间倒序。"""
        from app.models.cms.notice import CmsNotice

        base = select(CmsNotice).where(
            CmsNotice.is_deleted.is_(False),
            CmsNotice.status == 1,
            CmsNotice.target_type.in_(["ALL", "CUSTOMER"]),
        )
        cnt = select(func.count(CmsNotice.id)).where(
            CmsNotice.is_deleted.is_(False),
            CmsNotice.status == 1,
            CmsNotice.target_type.in_(["ALL", "CUSTOMER"]),
        )
        cnt_result = await self.db.execute(cnt)
        total = cnt_result.scalar() or 0
        result = await self.db.execute(
            base.order_by(CmsNotice.publish_time.desc().nullslast(), CmsNotice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [NoticeResponse.model_validate(n) for n in result.scalars().all()], total

    async def toggle_notice_status(self, notice_id: UUID, status: int) -> NoticeResponse:
        from datetime import UTC

        from app.models.cms.notice import CmsNotice

        values: dict = {"status": status}
        if status == 1:
            values["publish_time"] = datetime.now(UTC)
        stmt = (
            update(CmsNotice)
            .where(CmsNotice.id == notice_id, CmsNotice.is_deleted.is_(False))
            .values(**values)
            .returning(CmsNotice)
        )
        result = await self.db.execute(stmt)
        n = result.scalar_one_or_none()
        if not n:
            from app.core.exceptions import ProductNotFoundError

            raise ProductNotFoundError(str(notice_id))
        return NoticeResponse.model_validate(n)
