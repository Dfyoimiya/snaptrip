"""
Phase 3 单元测试 —— 验证订单域模型、Schema、订单状态机。

运行: cd backend && uv run pytest tests/unit/test_commerce_phase3.py -v

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

# ============================================================================
#  1. 模型定义验证
# ============================================================================


class TestOrderModels:
    def test_cart_item_tablename(self):
        from app.models.order.cart import OmsCartItem

        assert OmsCartItem.__tablename__ == "oms_cart_items"
        assert hasattr(OmsCartItem, "user_id")
        assert hasattr(OmsCartItem, "sku_id")
        assert hasattr(OmsCartItem, "checked")

    def test_order_tablename(self):
        from app.models.order.order import OmsOrder

        assert OmsOrder.__tablename__ == "oms_orders"
        assert hasattr(OmsOrder, "order_sn")
        assert hasattr(OmsOrder, "status")
        assert hasattr(OmsOrder, "items")

    def test_order_item_tablename(self):
        from app.models.order.order import OmsOrderItem

        assert OmsOrderItem.__tablename__ == "oms_order_items"
        assert hasattr(OmsOrderItem, "order_id")

    def test_operate_log_tablename(self):
        from app.models.order.order import OmsOrderOperateLog

        assert OmsOrderOperateLog.__tablename__ == "oms_order_operate_logs"

    def test_order_subclasses_commerce_base(self):
        from app.models.base import CommerceBase
        from app.models.order.order import OmsOrder

        assert issubclass(OmsOrder, CommerceBase)


# ============================================================================
#  2. Schema 验证
# ============================================================================


class TestCartSchemas:
    def test_cart_item_create(self):
        from app.schemas.order import CartItemCreate

        c = CartItemCreate(product_id=uuid.uuid4(), sku_id=uuid.uuid4(), quantity=2)
        assert c.quantity == 2

    def test_cart_item_create_defaults(self):
        from app.schemas.order import CartItemCreate

        c = CartItemCreate(product_id=uuid.uuid4(), sku_id=uuid.uuid4())
        assert c.quantity == 1

    def test_cart_item_create_quantity_min(self):
        from app.schemas.order import CartItemCreate

        with pytest.raises(ValidationError):
            CartItemCreate(product_id=uuid.uuid4(), sku_id=uuid.uuid4(), quantity=0)

    def test_cart_item_update_partial(self):
        from app.schemas.order import CartItemUpdate

        u = CartItemUpdate(checked=0)
        assert u.model_dump(exclude_unset=True) == {"checked": 0}


class TestOrderSchemas:
    def test_order_create_from_cart(self):
        from app.schemas.order import OrderCreateFromCart

        o = OrderCreateFromCart(
            cart_item_ids=[uuid.uuid4()],
            receiver_name="张三",
            receiver_phone="13800138000",
            receiver_detail_address="北京市朝阳区xxx",
        )
        assert o.receiver_name == "张三"

    def test_order_create_empty_cart(self):
        from app.schemas.order import OrderCreateFromCart

        with pytest.raises(ValidationError):
            OrderCreateFromCart(
                cart_item_ids=[],
                receiver_name="张三",
                receiver_phone="13800138000",
                receiver_detail_address="北京市朝阳区xxx",
            )

    def test_order_delivery_request(self):
        from app.schemas.order import OrderDeliveryRequest

        d = OrderDeliveryRequest(delivery_company="顺丰", delivery_sn="SF123456")
        assert d.delivery_company == "顺丰"

    def test_order_list_query_defaults(self):
        from app.schemas.order import OrderListQuery

        q = OrderListQuery()
        assert q.page == 1
        assert q.page_size == 20


# ============================================================================
#  3. 订单状态机验证
# ============================================================================


class TestOrderStateMachine:
    def test_valid_transitions(self):
        from app.schemas.order import STATUS_TRANSITIONS, OrderStatus

        # 待付款 → 已付款
        assert OrderStatus.PAID in STATUS_TRANSITIONS[OrderStatus.PENDING_PAYMENT]
        # 待付款 → 已关闭
        assert OrderStatus.CLOSED in STATUS_TRANSITIONS[OrderStatus.PENDING_PAYMENT]
        # 已付款 → 已发货
        assert OrderStatus.DELIVERED in STATUS_TRANSITIONS[OrderStatus.PAID]
        # 已发货 → 已收货
        assert OrderStatus.RECEIVED in STATUS_TRANSITIONS[OrderStatus.DELIVERED]

    def test_invalid_transition_detected(self):
        from app.core.exceptions import OrderStatusError
        from app.services.order_service import _validate_transition

        # 已关闭 → 已付款: 不允许
        with pytest.raises(OrderStatusError):
            _validate_transition(5, 1)  # CLOSED → PAID

    def test_generate_order_sn(self):
        from app.services.order_service import _generate_order_sn

        sn1 = _generate_order_sn()
        sn2 = _generate_order_sn()
        assert sn1 != sn2  # 两次生成的编号不同
        assert len(sn1) == 20  # 14位时间戳 + 6位随机数
        assert sn1.isdigit()


# ============================================================================
#  4. 路由验证
# ============================================================================


class TestPhase3Routes:
    def test_admin_router_has_order(self):
        from app.api.admin import admin_router

        routes = [r.path for r in admin_router.routes]
        assert "/admin/orders" in routes

    def test_portal_router_has_cart(self):
        from app.api.portal import portal_router

        routes = [r.path for r in portal_router.routes]
        assert "/portal/cart" in routes

    def test_portal_router_has_order(self):
        from app.api.portal import portal_router

        routes = [r.path for r in portal_router.routes]
        assert "/portal/orders" in routes


# ============================================================================
#  5. 迁移文件验证
# ============================================================================


class TestPhase3Migration:
    def test_migration_exists(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "phase3_migration",
            "alembic/versions/c3d4e5f6a7b8_create_commerce_order_tables.py",
        )
        assert spec is not None

    def test_migration_correct_chain(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "phase3_migration",
            "alembic/versions/c3d4e5f6a7b8_create_commerce_order_tables.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        assert mod.revision == "c3d4e5f6a7b8"
        assert mod.down_revision == "b2c3d4e5f6a7"
