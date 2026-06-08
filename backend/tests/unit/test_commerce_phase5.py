"""
Phase 5 单元测试 —— 验证 CMS 模型/Schema/统计聚合

运行: cd backend && uv run pytest tests/unit/test_commerce_phase5.py -v
"""

from __future__ import annotations


class TestCmsModels:
    def test_banner_tablename(self):
        from app.models.cms.content import CmsBanner

        assert CmsBanner.__tablename__ == "cms_banners"

    def test_subject_tablename(self):
        from app.models.cms.content import CmsSubject

        assert CmsSubject.__tablename__ == "cms_subjects"

    def test_help_tablename(self):
        from app.models.cms.content import CmsHelp

        assert CmsHelp.__tablename__ == "cms_helps"


class TestCmsSchemas:
    def test_banner_create(self):
        from app.schemas.cms import BannerCreate

        b = BannerCreate(title="618大促", pic="https://img.example.com/banner.jpg")
        assert b.title == "618大促"
        assert b.sort == 0
        assert b.status == 1

    def test_banner_update_partial(self):
        from app.schemas.cms import BannerUpdate

        u = BannerUpdate(sort=100)
        assert u.model_dump(exclude_unset=True) == {"sort": 100}

    def test_subject_create(self):
        from app.schemas.cms import SubjectCreate

        s = SubjectCreate(title="新品首发", category_name="新品")
        assert s.recommend_status == 0

    def test_help_create(self):
        from app.schemas.cms import HelpCreate

        h = HelpCreate(title="如何退货", category_name="售后")
        assert h.status == 1
        assert h.sort == 0

    def test_dashboard_overview_defaults(self):
        from app.schemas.cms import DashboardOverview

        d = DashboardOverview()
        assert d.today_order_count == 0
        assert d.today_sales_amount == 0.0

    def test_sales_stat_item(self):
        from app.schemas.cms import SalesStatItem

        s = SalesStatItem(date="2026-05-26", amount=12345.67, order_count=56)
        assert s.amount == 12345.67

    def test_product_rank_item(self):
        from app.schemas.cms import ProductRankItem

        p = ProductRankItem(product_id="uuid-1", product_name="Test", sale_count=100, amount=9999.0)
        assert p.sale_count == 100

    def test_homepage_aggregation_defaults(self):
        from app.schemas.cms import HomePageAggregation

        h = HomePageAggregation()
        assert h.banners == []
        assert h.new_products == []


class TestMigration:
    def test_exists(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "p5",
            "alembic/versions/e5f6a7b8c9d0_create_commerce_cms_tables.py",
        )
        assert spec is not None

    def test_chain(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "p5",
            "alembic/versions/e5f6a7b8c9d0_create_commerce_cms_tables.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.revision == "e5f6a7b8c9d0"
        assert mod.down_revision == "d4e5f6a7b8c9"


class TestRoutes:
    def test_admin_cms(self):
        from app.api.admin import admin_router

        paths = [r.path for r in admin_router.routes]
        assert any("/admin/cms/banners" in p for p in paths)
        assert any("/admin/cms/subjects" in p for p in paths)
        assert any("/admin/cms/helps" in p for p in paths)

    def test_admin_stats(self):
        from app.api.admin import admin_router

        paths = [r.path for r in admin_router.routes]
        assert any("/admin/stats/overview" in p for p in paths)

    def test_portal_home(self):
        from app.api.portal import portal_router

        paths = [r.path for r in portal_router.routes]
        assert any("/portal/home" in p for p in paths)
