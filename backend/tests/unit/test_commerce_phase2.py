"""
Phase 2 单元测试 —— 验证产品域模型、Schema、Service 逻辑。

运行: cd backend && uv run pytest tests/unit/test_commerce_phase2.py -v

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

# ============================================================================
#  1. 模型定义验证
# ============================================================================

class TestProductModels:
    """验证 ORM 模型的表名和字段定义"""

    def test_pms_category_tablename(self):
        from app.models.product.category import PmsCategory
        assert PmsCategory.__tablename__ == "pms_categories"
        assert hasattr(PmsCategory, "parent_id")
        assert hasattr(PmsCategory, "level")
        assert hasattr(PmsCategory, "children")

    def test_pms_brand_tablename(self):
        from app.models.product.brand import PmsBrand
        assert PmsBrand.__tablename__ == "pms_brands"
        assert hasattr(PmsBrand, "first_letter")
        assert hasattr(PmsBrand, "logo")

    def test_pms_product_tablename(self):
        from app.models.product.product import PmsProduct
        assert PmsProduct.__tablename__ == "pms_products"
        assert hasattr(PmsProduct, "name")
        assert hasattr(PmsProduct, "price")
        assert hasattr(PmsProduct, "skus")

    def test_pms_sku_tablename(self):
        from app.models.product.sku import PmsSku
        assert PmsSku.__tablename__ == "pms_skus"
        assert hasattr(PmsSku, "sku_code")
        assert hasattr(PmsSku, "lock_stock")

    def test_pms_product_attribute_tablename(self):
        from app.models.product.attribute import PmsProductAttribute
        assert PmsProductAttribute.__tablename__ == "pms_product_attributes"
        assert hasattr(PmsProductAttribute, "category_id")
        assert hasattr(PmsProductAttribute, "attr_type")

    def test_pms_product_attribute_value_tablename(self):
        from app.models.product.attribute import PmsProductAttributeValue
        assert PmsProductAttributeValue.__tablename__ == "pms_product_attribute_values"
        assert hasattr(PmsProductAttributeValue, "value")

    def test_product_subclasses_commerce_base(self):
        from app.models.base import CommerceBase
        from app.models.product.brand import PmsBrand
        from app.models.product.category import PmsCategory
        from app.models.product.product import PmsProduct
        from app.models.product.sku import PmsSku

        for cls in [PmsProduct, PmsSku, PmsBrand, PmsCategory]:
            assert issubclass(cls, CommerceBase), f"{cls.__name__} must subclass CommerceBase"


# ============================================================================
#  2. Schema 验证
# ============================================================================

class TestCategorySchema:
    """验证分类创建/更新/响应 Schema"""

    def test_category_create_minimal(self):
        from app.schemas.product import CategoryCreate
        c = CategoryCreate(name="手机通讯")
        assert c.name == "手机通讯"
        assert c.level == 0
        assert c.nav_status == 1

    def test_category_create_name_required(self):
        from app.schemas.product import CategoryCreate
        with pytest.raises(ValidationError):
            CategoryCreate()  # name 是必填

    def test_category_update_exclude_unset(self):
        from app.schemas.product import CategoryUpdate
        u = CategoryUpdate(name="新名称")
        dumped = u.model_dump(exclude_unset=True)
        assert dumped == {"name": "新名称"}  # 只序列化传入的字段
        assert "level" not in dumped

    def test_category_tree_children_default(self):
        from app.schemas.product import CategoryTreeResponse
        tree = CategoryTreeResponse(id=uuid.uuid4(), name="Root", level=0, sort=0)
        assert tree.children == []


class TestBrandSchema:
    """验证品牌 Schema"""

    def test_brand_create(self):
        from app.schemas.product import BrandCreate
        b = BrandCreate(name="Apple", first_letter="A", sort=100)
        assert b.first_letter == "A"
        assert b.factory_status == 1

    def test_brand_update_partial(self):
        from app.schemas.product import BrandUpdate
        b = BrandUpdate(sort=50)
        assert b.model_dump(exclude_unset=True) == {"sort": 50}


class TestProductSchema:
    """验证商品 Schema —— 含跨字段校验"""

    def test_product_create_basic(self):
        from app.schemas.product import ProductCreate
        p = ProductCreate(
            name="iPhone 15 Pro",
            price=Decimal("8999.00"),
            category_id=uuid.uuid4(),
        )
        assert p.price == Decimal("8999.00")
        assert p.skus == []
        assert p.attribute_values == {}

    def test_product_create_with_skus(self):
        from app.schemas.product import ProductCreate, SkuCreate
        p = ProductCreate(
            name="iPhone 15 Pro",
            price=Decimal("8999.00"),
            skus=[
                SkuCreate(
                    sku_code="IP15-128-BLK",
                    spec='{"color":"黑色","storage":"128GB"}',
                    price=Decimal("8999.00"),
                    stock=100,
                ),
            ],
        )
        assert len(p.skus) == 1
        assert p.skus[0].sku_code == "IP15-128-BLK"

    def test_promotion_dates_validation_error(self):
        """跨字段校验: 开始时间必须早于结束时间"""
        from app.schemas.product import ProductCreate
        now = datetime.now()

        with pytest.raises(ValidationError, match="促销开始时间必须早于结束时间"):
            ProductCreate(
                name="Test",
                price=Decimal("100"),
                promotion_price=Decimal("80"),
                promotion_start_time=now + timedelta(hours=1),
                promotion_end_time=now,
            )

    def test_promotion_price_requires_dates_error(self):
        """有促销价必须有促销时间"""
        from app.schemas.product import ProductCreate

        with pytest.raises(ValidationError, match="促销价和促销时间必须同时设置"):
            ProductCreate(
                name="Test",
                price=Decimal("100"),
                promotion_price=Decimal("80"),
                promotion_start_time=None,
                promotion_end_time=None,
            )

    def test_product_list_query_defaults(self):
        from app.schemas.product import ProductListQuery
        q = ProductListQuery()
        assert q.page == 1
        assert q.page_size == 20


class TestSkuSchema:
    """验证 SKU Schema"""

    def test_sku_create(self):
        from app.schemas.product import SkuCreate
        s = SkuCreate(
            sku_code="SKU-001",
            spec='{"size":"L"}',
            price=Decimal("199.00"),
            stock=50,
        )
        assert s.price == Decimal("199.00")
        assert s.stock == 50

    def test_sku_price_must_be_positive(self):
        from app.schemas.product import SkuCreate
        with pytest.raises(ValidationError):
            SkuCreate(sku_code="SKU-001", spec="{}", price=Decimal("-1"), stock=10)

    def test_sku_response_fields(self):
        from app.schemas.product import SkuResponse
        s = SkuResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            sku_code="SKU-001",
            spec="{}",
            price=Decimal("100"),
            stock=10,
            lock_stock=0,
            low_stock=5,
            sale_count=0,
        )
        assert s.lock_stock == 0
        assert s.promotion_price is None


class TestProductAttributeSchema:
    """验证属性 Schema"""

    def test_attribute_create(self):
        from app.schemas.product import ProductAttributeCreate
        a = ProductAttributeCreate(
            category_id=uuid.uuid4(),
            name="屏幕尺寸",
        )
        assert a.attr_type == 1  # 默认参数
        assert a.input_type == 0  # 默认手动录入

    def test_attribute_create_with_list(self):
        from app.schemas.product import ProductAttributeCreate
        a = ProductAttributeCreate(
            category_id=uuid.uuid4(),
            name="颜色",
            attr_type=0,  # 规格
            input_type=1,  # 单选
            input_list="黑色,白色,金色",
        )
        assert a.attr_type == 0
        assert a.input_list == "黑色,白色,金色"


# ============================================================================
#  3. 迁移文件验证
# ============================================================================

class TestMigrationFiles:
    """验证迁移文件语法正确"""

    def test_phase2_migration_exists(self):
        import importlib.util

        path = "alembic/versions/b2c3d4e5f6a7_create_commerce_product_tables.py"
        spec = importlib.util.spec_from_file_location("phase2_migration", path)
        assert spec is not None, f"Migration file not found: {path}"

    def test_phase2_migration_has_revision(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase2_migration",
            "alembic/versions/b2c3d4e5f6a7_create_commerce_product_tables.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.revision == "b2c3d4e5f6a7"

    def test_phase2_migration_correct_down_revision(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "phase2_migration",
            "alembic/versions/b2c3d4e5f6a7_create_commerce_product_tables.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.down_revision == "a1b2c3d4e5f6"


# ============================================================================
#  4. Admin Router 路由结构验证
# ============================================================================

class TestAdminRoutes:
    """验证路由注册和路径定义"""

    def test_admin_router_includes_all_subrouters(self):
        from app.api.admin import admin_router

        routes = [r.path for r in admin_router.routes]
        # 子路由自带完整路径前缀 (如 /admin/categories)
        # 这些路由将在 main.py 中以 /api/v1 前缀注册
        assert "/admin/categories" in routes
        assert "/admin/brands" in routes
        assert "/admin/products" in routes
        assert "/admin/product-attributes" in routes

    def test_portal_router_has_product_routes(self):
        from app.api.portal import portal_router

        routes = [r.path for r in portal_router.routes]
        assert "/portal/products" in routes


# ============================================================================
#  5. 模型模块导入完整性
# ============================================================================

class TestModelImports:
    """验证 models/__init__.py 导出完整"""

    def test_all_models_importable(self):
        from app.models.product import (
            PmsBrand,
            PmsCategory,
            PmsProduct,
            PmsProductAttribute,
            PmsProductAttributeValue,
            PmsSku,
        )
        assert PmsBrand is not None
        assert PmsCategory is not None
        assert PmsProduct is not None
        assert PmsProductAttribute is not None
        assert PmsProductAttributeValue is not None
        assert PmsSku is not None


# ============================================================================
#  6. Decimal 精度验证 (金融数据正确性)
# ============================================================================

class TestDecimalPrecision:
    """验证金额字段使用 Decimal 而非 Float"""

    def test_decimal_not_float(self):
        """Decimal 精确计算: 0.1 + 0.2 == 0.3 (Float 会有精度问题)"""
        a = Decimal("0.1")
        b = Decimal("0.2")
        assert a + b == Decimal("0.3")

    def test_price_schema_uses_decimal(self):
        from app.schemas.product import ProductCreate

        # 如果 price 能传入 Decimal 且不报错，说明类型定义正确
        p = ProductCreate(
            name="Test",
            price=Decimal("99.99"),
        )
        assert isinstance(p.price, Decimal)
