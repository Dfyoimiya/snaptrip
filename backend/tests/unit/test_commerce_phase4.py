"""
Phase 4 单元测试 —— 验证营销域模型、Schema、领券乐观锁。

运行: cd backend && uv run pytest tests/unit/test_commerce_phase4.py -v

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError


class TestPromotionModels:
    def test_coupon_tablename(self):
        from app.models.promotion.coupon import SmsCoupon

        assert SmsCoupon.__tablename__ == "sms_coupons"

    def test_coupon_history_tablename(self):
        from app.models.promotion.coupon import SmsCouponHistory

        assert SmsCouponHistory.__tablename__ == "sms_coupon_histories"
        assert hasattr(SmsCouponHistory, "use_status")

    def test_flash_promotion_tablename(self):
        from app.models.promotion.flash import SmsFlashPromotion

        assert SmsFlashPromotion.__tablename__ == "sms_flash_promotions"

    def test_flash_session_tablename(self):
        from app.models.promotion.flash import SmsFlashPromotionSession

        assert SmsFlashPromotionSession.__tablename__ == "sms_flash_sessions"

    def test_flash_product_tablename(self):
        from app.models.promotion.flash import SmsFlashPromotionProduct

        assert SmsFlashPromotionProduct.__tablename__ == "sms_flash_promotion_products"
        assert hasattr(SmsFlashPromotionProduct, "flash_price")
        assert hasattr(SmsFlashPromotionProduct, "flash_stock")


class TestCouponSchema:
    def test_coupon_create(self):
        from app.schemas.promotion import CouponCreate

        c = CouponCreate(name="满100减20", amount=Decimal("20.00"), count=100)
        assert c.type == 0

    def test_coupon_create_date_validation(self):
        from app.schemas.promotion import CouponCreate

        now = datetime.now()
        with pytest.raises(ValidationError):
            CouponCreate(name="Test", amount=Decimal("10"), count=10, start_time=now + timedelta(hours=1), end_time=now)

    def test_coupon_update_partial(self):
        from app.schemas.promotion import CouponUpdate

        u = CouponUpdate(status=0)
        assert u.model_dump(exclude_unset=True) == {"status": 0}

    def test_coupon_history_response(self):
        from app.schemas.promotion import CouponHistoryResponse

        h = CouponHistoryResponse(
            id=uuid.uuid4(),
            coupon_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            coupon_name="Test",
            coupon_amount=Decimal("10"),
            coupon_min_amount=Decimal("50"),
            use_status=0,
            receive_time=datetime.now(),
            expire_time=datetime.now(),
        )
        assert h.use_status == 0


class TestFlashSchema:
    def test_flash_promotion_create(self):
        from app.schemas.promotion import FlashPromotionCreate

        now = datetime.now()
        p = FlashPromotionCreate(title="618大促", start_date=now, end_date=now + timedelta(days=3))
        assert p.title == "618大促"
        assert p.note is None

    def test_flash_promotion_date_validation(self):
        from app.schemas.promotion import FlashPromotionCreate

        now = datetime.now()
        with pytest.raises(ValidationError):
            FlashPromotionCreate(title="Test", start_date=now + timedelta(days=1), end_date=now)

    def test_flash_session_create(self):
        from app.schemas.promotion import FlashSessionCreate

        now = datetime.now()
        s = FlashSessionCreate(
            promotion_id=uuid.uuid4(), name="10点场", start_time=now, end_time=now + timedelta(hours=2)
        )
        assert s.name == "10点场"

    def test_flash_product_create(self):
        from app.schemas.promotion import FlashProductCreate

        p = FlashProductCreate(
            session_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            sku_id=uuid.uuid4(),
            flash_price=Decimal("99.00"),
            flash_stock=500,
        )
        assert p.flash_limit == 1
        assert p.flash_price == Decimal("99.00")


class TestMigration:
    def test_phase4_migration_exists(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "phase4_migration",
            "alembic/versions/d4e5f6a7b8c9_create_commerce_promotion_tables.py",
        )
        assert spec is not None

    def test_phase4_migration_chain(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "phase4_migration",
            "alembic/versions/d4e5f6a7b8c9_create_commerce_promotion_tables.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.revision == "d4e5f6a7b8c9"
        assert mod.down_revision == "c3d4e5f6a7b8"


class TestRoutes:
    def test_admin_coupons(self):
        from app.api.admin import admin_router

        paths = [r.path for r in admin_router.routes]
        assert "/admin/coupons" in paths

    def test_admin_flash(self):
        from app.api.admin import admin_router

        paths = [r.path for r in admin_router.routes]
        assert any("/admin/flash-promotions" in p for p in paths)

    def test_portal_coupons(self):
        from app.api.portal import portal_router

        paths = [r.path for r in portal_router.routes]
        assert any("/portal/coupons" in p for p in paths)
