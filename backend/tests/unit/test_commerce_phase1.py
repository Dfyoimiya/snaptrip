"""Phase 1 单元测试 —— 验证 ORM 基类、RBAC 模型、业务异常、分页 Schema。

所有测试无需数据库, 纯内存执行。
运行: cd backend && uv run pytest tests/unit/test_commerce_phase1.py -v

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import pytest

# ============================================================================
#  1. Config 配置
# ============================================================================


class TestCommerceConfig:
    """验证 CommerceSettings 配置正确加载"""

    def test_default_values(self):
        from app.core.config import commerce_settings

        assert commerce_settings.OSS_ENDPOINT == "localhost:9000"
        assert commerce_settings.OSS_BUCKET == "snaptrip-commerce"
        assert commerce_settings.ES_INDEX_PRODUCTS == "commerce_products"
        assert commerce_settings.ORDER_AUTO_CANCEL_MINUTES == 30
        assert commerce_settings.COUPON_EXPIRE_DAYS == 7

    def test_es_hosts_list_parsing(self):
        from app.core.config import commerce_settings

        hosts = commerce_settings.es_hosts_list
        assert isinstance(hosts, list)
        assert len(hosts) >= 1

    def test_env_prefix_isolation(self):
        from app.core.config import CommerceSettings

        cs = CommerceSettings()
        assert cs.OSS_ENDPOINT == "localhost:9000"


# ============================================================================
#  2. 业务异常
# ============================================================================


class TestCommerceExceptions:
    """验证异常层级和属性"""

    def test_product_not_found(self):
        from app.core.exceptions import ProductNotFoundError

        exc = ProductNotFoundError("p-001")
        assert exc.code == "PRODUCT_NOT_FOUND"
        assert exc.status_code == 404
        assert "p-001" in exc.message

    def test_insufficient_stock_with_details(self):
        from app.core.exceptions import InsufficientStockError

        exc = InsufficientStockError(sku_id="sku-1", available=5, requested=10)
        assert exc.code == "INSUFFICIENT_STOCK"
        assert exc.status_code == 409
        assert exc.details["available"] == 5
        assert exc.details["requested"] == 10

    def test_order_status_error(self):
        from app.core.exceptions import OrderStatusError

        exc = OrderStatusError(order_id="o-1", current_status="cancelled", expected="paid")
        assert exc.code == "ORDER_STATUS_ERROR"
        assert exc.status_code == 409

    def test_coupon_already_claimed(self):
        from app.core.exceptions import CouponAlreadyClaimedError

        exc = CouponAlreadyClaimedError("c-001")
        assert exc.code == "COUPON_ALREADY_CLAIMED"
        assert exc.status_code == 409

    def test_coupon_expired(self):
        from app.core.exceptions import CouponExpiredError

        exc = CouponExpiredError("c-002")
        assert exc.code == "COUPON_EXPIRED"
        assert exc.status_code == 400

    def test_coupon_exhausted(self):
        from app.core.exceptions import CouponExhaustedError

        exc = CouponExhaustedError("c-003")
        assert exc.code == "COUPON_EXHAUSTED"
        assert exc.status_code == 409

    def test_product_off_shelf(self):
        from app.core.exceptions import ProductOffShelfError

        exc = ProductOffShelfError("p-002")
        assert exc.code == "PRODUCT_OFF_SHELF"
        assert exc.status_code == 400

    def test_order_not_found(self):
        from app.core.exceptions import OrderNotFoundError

        exc = OrderNotFoundError("o-002")
        assert exc.code == "ORDER_NOT_FOUND"
        assert exc.status_code == 404

    def test_commerce_exception_defaults(self):
        from app.core.exceptions import CommerceException

        exc = CommerceException(code="TEST", message="test error")
        assert exc.code == "TEST"
        assert exc.status_code == 500

    def test_cart_error(self):
        from app.core.exceptions import CartError

        exc = CartError(code="CART_ERROR", message="cart error message")
        assert exc.code == "CART_ERROR"
        assert exc.status_code == 400

    def test_all_exceptions_inherit_from_snaptrip(self):
        from snaptrip_shared.core.exceptions import SnapTripException

        from app.core.exceptions import (
            CartError,
            CommerceException,
            CouponAlreadyClaimedError,
            CouponError,
            CouponExhaustedError,
            CouponExpiredError,
            InsufficientStockError,
            OrderError,
            OrderNotFoundError,
            OrderPaymentError,
            OrderStatusError,
            ProductNotFoundError,
            ProductOffShelfError,
        )

        all_exceptions = [
            CommerceException,
            ProductNotFoundError,
            ProductOffShelfError,
            InsufficientStockError,
            OrderError,
            OrderNotFoundError,
            OrderStatusError,
            OrderPaymentError,
            CouponError,
            CouponExpiredError,
            CouponExhaustedError,
            CouponAlreadyClaimedError,
            CartError,
        ]
        for exc_cls in all_exceptions:
            assert issubclass(exc_cls, SnapTripException), f"{exc_cls.__name__} should inherit SnapTripException"


# ============================================================================
#  3. 分页工具
# ============================================================================


class TestPagination:
    """验证分页参数和结果计算"""

    def test_pagination_params_offset(self):
        from app.core.pagination import PaginationParams

        p = PaginationParams(page=1, page_size=20)
        assert p.offset == 0

        p = PaginationParams(page=3, page_size=10)
        assert p.offset == 20

    def test_pagination_params_bounds(self):
        from app.core.pagination import PaginationParams

        p = PaginationParams(page=1, page_size=1)
        assert p.offset == 0

        p = PaginationParams(page=1, page_size=100)
        assert p.offset == 0

    def test_paginated_result_create(self):
        from app.core.pagination import PaginatedResult, PaginationParams

        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        params = PaginationParams(page=1, page_size=2)
        result = PaginatedResult.create(items=items, total=10, params=params)
        assert result.items == items
        assert result.total == 10
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 5

    def test_paginated_result_total_pages_ceiling(self):
        from app.core.pagination import PaginatedResult, PaginationParams

        params = PaginationParams(page=1, page_size=3)
        result = PaginatedResult.create(items=[], total=10, params=params)
        assert result.total_pages == 4  # ceil(10/3) = 4

    def test_paginated_result_zero_total(self):
        from app.core.pagination import PaginatedResult, PaginationParams

        params = PaginationParams(page=1, page_size=20)
        result = PaginatedResult.create(items=[], total=0, params=params)
        assert result.total_pages == 0
        assert len(result.items) == 0

    def test_paginated_result_large_page_number(self):
        from app.core.pagination import PaginatedResult, PaginationParams

        params = PaginationParams(page=100, page_size=20)
        result = PaginatedResult.create(items=[], total=50, params=params)
        assert result.total_pages == 3
        assert result.page == 100


# ============================================================================
#  4. 通用 Schema
# ============================================================================


class TestCommonSchemas:
    """验证 Pydantic Schema 定义"""

    def test_paginated_response_of(self):
        from app.schemas.common import PaginatedResponse, PaginationParams

        params = PaginationParams(page=2, page_size=5)
        resp = PaginatedResponse.of(items=[1, 2, 3], total=23, params=params)
        assert resp.page == 2
        assert resp.page_size == 5
        assert resp.total == 23
        assert resp.total_pages == 5  # ceil(23/5) = 5
        assert len(resp.items) == 3

    def test_publish_status_enum(self):
        from app.schemas.common import PublishStatus

        assert PublishStatus.OFF_SHELF == 0
        assert PublishStatus.ON_SHELF == 1

    def test_verify_status_enum(self):
        from app.schemas.common import VerifyStatus

        assert VerifyStatus.PENDING == 0
        assert VerifyStatus.APPROVED == 1
        assert VerifyStatus.REJECTED == 2

    def test_batch_ids_request(self):
        from app.schemas.common import BatchIdsRequest

        req = BatchIdsRequest(ids=["a", "b", "c"])
        assert len(req.ids) == 3

    def test_batch_ids_request_min_length(self):
        from pydantic import ValidationError

        from app.schemas.common import BatchIdsRequest

        with pytest.raises(ValidationError):
            BatchIdsRequest(ids=[])


# ============================================================================
#  5. ORM 模型定义 (不连数据库)
# ============================================================================


class TestCommerceBase:
    """验证 CommerceBase 和 Mixin 的字段定义"""

    def test_commerce_base_has_id(self):
        from app.models.base import CommerceBase

        assert hasattr(CommerceBase, "id")
        assert hasattr(CommerceBase, "metadata")

    def test_commerce_base_is_independent_from_marketplace(self):
        from app.models.base import CommerceBase
        from marketplace.app.models.base import Base as MarketplaceBase

        assert CommerceBase is not MarketplaceBase
        assert CommerceBase.metadata is not MarketplaceBase.metadata

    def test_audit_mixin_fields(self):
        from app.models.base import AuditMixin

        assert hasattr(AuditMixin, "created_at")
        assert hasattr(AuditMixin, "updated_at")
        assert hasattr(AuditMixin, "created_by")
        assert hasattr(AuditMixin, "updated_by")

    def test_soft_delete_mixin_fields(self):
        from app.models.base import SoftDeleteMixin

        assert hasattr(SoftDeleteMixin, "is_deleted")
        assert hasattr(SoftDeleteMixin, "deleted_at")


class TestRBACModels:
    """验证 RBAC 模型定义 — 纯声明式检查"""

    def test_role_tablename(self):
        from app.models.rbac import Role

        assert Role.__tablename__ == "ums_roles"
        assert hasattr(Role, "name")
        assert hasattr(Role, "description")
        assert hasattr(Role, "status")
        assert hasattr(Role, "sort")

    def test_permission_tablename(self):
        from app.models.rbac import Permission

        assert Permission.__tablename__ == "ums_permissions"
        assert hasattr(Permission, "name")
        assert hasattr(Permission, "resource")
        assert hasattr(Permission, "method")

    def test_role_permission_tablename(self):
        from app.models.rbac import RolePermission

        assert RolePermission.__tablename__ == "ums_role_permissions"
        assert hasattr(RolePermission, "role_id")
        assert hasattr(RolePermission, "permission_id")

    def test_user_role_tablename(self):
        from app.models.rbac import UserRole

        assert UserRole.__tablename__ == "ums_user_roles"
        assert hasattr(UserRole, "user_id")
        assert hasattr(UserRole, "role_id")

    def test_role_permission_m2m_bidirectional(self):
        from app.models.rbac import Permission, Role

        rel_role = Role.__mapper__.relationships.get("permissions")
        rel_perm = Permission.__mapper__.relationships.get("roles")

        assert rel_role is not None, "Role should have permissions relationship"
        assert rel_perm is not None, "Permission should have roles relationship"
        assert rel_role.secondary is not None, "Role.permissions should use secondary table"
        assert rel_perm.secondary is not None, "Permission.roles should use secondary table"


# ============================================================================
#  6. OSS 客户端
# ============================================================================


class TestOSSClient:
    """验证 OSS 客户端工厂和 MinIO 实现"""

    def test_get_oss_client_returns_minio_client(self):
        from app.core.oss import MinioOSSClient, get_oss_client

        client = get_oss_client()
        assert isinstance(client, MinioOSSClient)

    def test_minio_client_default_config(self):
        from app.core.oss import MinioOSSClient

        client = MinioOSSClient()
        assert client._endpoint == "localhost:9000"
        assert client._bucket == "snaptrip-commerce"
        assert client._secure is False


# ============================================================================
#  7. ES 客户端 (不连接 ES)
# ============================================================================


class TestESSearchClient:
    """验证 ES 客户端结构和配置"""

    def test_client_instantiation(self):
        from app.search.client import ESSearchClient

        client = ESSearchClient()
        assert client._index_products == "commerce_products"
        assert client._timeout == 5

    def test_get_search_client_singleton(self):
        from app.search.client import ESSearchClient, get_search_client

        c1 = get_search_client()
        c2 = get_search_client()
        assert c1 is c2
        assert isinstance(c1, ESSearchClient)
