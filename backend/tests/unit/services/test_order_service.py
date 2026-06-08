"""Unit tests for OrderService.

Tests cover create_from_cart, pay, cancel, delivery, confirm_receipt,
modify_price, get_detail, list_admin, list_user.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


async def _refresh_fake(obj: object) -> None:
    from uuid import uuid4

    obj.id = uuid4()  # type: ignore[attr-defined]


@pytest.fixture
def mock_db() -> AsyncSession:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock(side_effect=_refresh_fake)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    return db


def _make_order_mock(order_id=None, status=0) -> MagicMock:
    oid = order_id or uuid4()
    o = MagicMock()
    o.id = oid
    o.order_sn = "20260608120000123456"
    o.user_id = uuid4()
    o.member_username = "testuser"
    o.total_amount = Decimal("199.98")
    o.pay_amount = Decimal("199.98")
    o.freight_amount = Decimal("0.00")
    o.discount_amount = Decimal("0.00")
    o.pay_type = 1
    o.payment_time = None
    o.delivery_company = None
    o.delivery_sn = None
    o.delivery_time = None
    o.receiver_name = "Test User"
    o.receiver_phone = "13800138000"
    o.receiver_province = "Guangdong"
    o.receiver_city = "Shenzhen"
    o.receiver_region = None
    o.receiver_detail_address = "123 Test St"
    o.status = status
    o.note = None
    o.coupon_id = None
    o.created_at = None
    o.updated_at = None
    o.delete_status = 0
    o.confirm_status = 0
    o.pay_order_sn = None
    o.admin_note = None
    o.receiver_post_code = None
    o.auto_confirm_day = 15
    return o


def _make_cart_item_mock() -> MagicMock:
    item = MagicMock()
    item.id = uuid4()
    item.user_id = uuid4()
    item.product_id = uuid4()
    item.product_name = "Test Product"
    item.product_pic = "pic.jpg"
    item.sku_id = uuid4()
    item.sku_code = "SKU001"
    item.spec = "{}"
    item.price = Decimal("99.99")
    item.quantity = 2
    item.checked = 1
    return item


def _make_order_item_mock(order_id) -> MagicMock:
    item = MagicMock()
    item.id = uuid4()
    item.order_id = order_id
    item.order_sn = "20260608120000123456"
    item.product_id = uuid4()
    item.product_name = "Test Product"
    item.product_pic = "pic.jpg"
    item.sku_id = uuid4()
    item.sku_code = "SKU001"
    item.spec = "{}"
    item.price = Decimal("99.99")
    item.quantity = 2
    return item


# ---------------------------------------------------------------------------
#  create_from_cart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_from_cart_success(mock_db):
    """create_from_cart: happy path creates order from cart items."""
    from app.schemas.order import OrderCreateFromCart
    from app.services.order_service import OrderService

    order_id = uuid4()
    cart_item = _make_cart_item_mock()
    order_mock = _make_order_mock(order_id)
    order_item_mock = _make_order_item_mock(order_id)

    # cart items query
    cart_result = MagicMock()
    cart_result.scalars.return_value.all.return_value = [cart_item]
    # inventory update (optimistic lock)
    inv_result = MagicMock()
    inv_result.rowcount = 1
    # cart item delete
    delete_result = MagicMock()
    # order items query for get_detail
    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [order_item_mock]

    mock_db.execute.side_effect = [cart_result, inv_result, delete_result, items_result]
    mock_db.get.return_value = order_mock

    svc = OrderService(mock_db)
    data = OrderCreateFromCart(
        cart_item_ids=[cart_item.id],
        receiver_name="Test User",
        receiver_phone="13800138000",
        receiver_detail_address="123 Test St",
    )
    resp = await svc.create_from_cart(uuid4(), "testuser", data)

    assert resp.id == order_id
    assert len(resp.items) == 1


@pytest.mark.asyncio
async def test_create_from_cart_empty_cart_raises(mock_db):
    """create_from_cart: empty cart raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.order import OrderCreateFromCart
    from app.services.order_service import OrderService

    cart_result = MagicMock()
    cart_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = cart_result

    svc = OrderService(mock_db)
    data = OrderCreateFromCart(
        cart_item_ids=[uuid4()],
        receiver_name="Test",
        receiver_phone="13800000000",
        receiver_detail_address="Addr",
    )
    with pytest.raises(CommerceException) as exc:
        await svc.create_from_cart(uuid4(), "testuser", data)
    assert exc.value.code == "CART_EMPTY"


@pytest.mark.asyncio
async def test_create_from_cart_insufficient_stock(mock_db):
    """create_from_cart: inventory update rowcount==0 raises InsufficientStockError."""
    from app.core.exceptions import InsufficientStockError
    from app.schemas.order import OrderCreateFromCart
    from app.services.order_service import OrderService

    cart_item = _make_cart_item_mock()
    cart_result = MagicMock()
    cart_result.scalars.return_value.all.return_value = [cart_item]
    inv_result = MagicMock()
    inv_result.rowcount = 0  # optimistic lock failure

    mock_db.execute.side_effect = [cart_result, inv_result]

    svc = OrderService(mock_db)
    data = OrderCreateFromCart(
        cart_item_ids=[cart_item.id],
        receiver_name="Test",
        receiver_phone="13800000000",
        receiver_detail_address="Addr",
    )
    with pytest.raises(InsufficientStockError):
        await svc.create_from_cart(uuid4(), "testuser", data)


# ---------------------------------------------------------------------------
#  pay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pay_success(mock_db):
    """pay: transitions PENDING_PAYMENT -> PAID."""
    from app.services.order_service import OrderService
    from app.schemas.order import OrderStatus

    order_id = uuid4()
    order_mock = _make_order_mock(order_id, status=OrderStatus.PENDING_PAYMENT)
    order_item = _make_order_item_mock(order_id)

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [order_item]
    mock_db.get.return_value = order_mock
    mock_db.execute.return_value = items_result

    svc = OrderService(mock_db)
    resp = await svc.pay(order_id, "PAY_SN_001")

    assert order_mock.status == OrderStatus.PAID
    assert order_mock.pay_order_sn == "PAY_SN_001"
    assert resp.id == order_id


@pytest.mark.asyncio
async def test_pay_order_not_found(mock_db):
    """pay: raises OrderNotFoundError when order missing."""
    from app.core.exceptions import OrderNotFoundError
    from app.services.order_service import OrderService

    mock_db.get.return_value = None
    svc = OrderService(mock_db)
    with pytest.raises(OrderNotFoundError):
        await svc.pay(uuid4())


# ---------------------------------------------------------------------------
#  cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_from_pending(mock_db):
    """cancel: pending payment -> closed, restores locked stock."""
    from app.services.order_service import OrderService
    from app.schemas.order import OrderStatus

    order_id = uuid4()
    order_mock = _make_order_mock(order_id, status=OrderStatus.PENDING_PAYMENT)
    order_item = _make_order_item_mock(order_id)

    # cancel queries items for stock restore
    items_q_result = MagicMock()
    items_q_result.scalars.return_value.all.return_value = [order_item]
    # stock restore execute
    restore_result = MagicMock()
    # get_detail items query
    detail_items = MagicMock()
    detail_items.scalars.return_value.all.return_value = [order_item]

    mock_db.get.return_value = order_mock
    mock_db.execute.side_effect = [items_q_result, restore_result, detail_items]

    svc = OrderService(mock_db)
    resp = await svc.cancel(order_id)

    assert order_mock.status == OrderStatus.CLOSED
    assert resp.id == order_id


@pytest.mark.asyncio
async def test_cancel_not_found(mock_db):
    """cancel: raises OrderNotFoundError when order missing."""
    from app.core.exceptions import OrderNotFoundError
    from app.services.order_service import OrderService

    mock_db.get.return_value = None
    svc = OrderService(mock_db)
    with pytest.raises(OrderNotFoundError):
        await svc.cancel(uuid4())


# ---------------------------------------------------------------------------
#  delivery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delivery_success(mock_db):
    """delivery: transitions PAID -> DELIVERED."""
    from app.schemas.order import OrderDeliveryRequest, OrderStatus
    from app.services.order_service import OrderService

    order_id = uuid4()
    order_mock = _make_order_mock(order_id, status=OrderStatus.PAID)
    order_item = _make_order_item_mock(order_id)

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [order_item]
    mock_db.get.return_value = order_mock
    mock_db.execute.return_value = items_result

    svc = OrderService(mock_db)
    data = OrderDeliveryRequest(delivery_company="SF", delivery_sn="SF123456")
    resp = await svc.delivery(order_id, data, "admin")

    assert order_mock.status == OrderStatus.DELIVERED
    assert resp.id == order_id


# ---------------------------------------------------------------------------
#  confirm_receipt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirm_receipt_success(mock_db):
    """confirm_receipt: transitions DELIVERED -> RECEIVED."""
    from app.schemas.order import OrderStatus
    from app.services.order_service import OrderService

    order_id = uuid4()
    order_mock = _make_order_mock(order_id, status=OrderStatus.DELIVERED)
    order_item = _make_order_item_mock(order_id)

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [order_item]
    mock_db.get.return_value = order_mock
    mock_db.execute.return_value = items_result

    svc = OrderService(mock_db)
    resp = await svc.confirm_receipt(order_id)

    assert order_mock.status == OrderStatus.RECEIVED
    assert resp.id == order_id


# ---------------------------------------------------------------------------
#  modify_price
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_modify_price_success(mock_db):
    """modify_price: updates freight/discount and recalculates pay_amount."""
    from app.schemas.order import OrderPriceModifyRequest
    from app.services.order_service import OrderService

    order_id = uuid4()
    order_mock = _make_order_mock(order_id)
    order_mock.total_amount = Decimal("199.98")
    order_item = _make_order_item_mock(order_id)

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [order_item]
    mock_db.get.return_value = order_mock
    mock_db.execute.return_value = items_result

    svc = OrderService(mock_db)
    data = OrderPriceModifyRequest(freight_amount=Decimal("10.00"))
    resp = await svc.modify_price(order_id, data)

    assert order_mock.freight_amount == Decimal("10.00")
    assert resp.id == order_id


# ---------------------------------------------------------------------------
#  get_detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_detail_success(mock_db):
    """get_detail: returns OrderDetailResponse with items."""
    from app.services.order_service import OrderService

    order_id = uuid4()
    order_mock = _make_order_mock(order_id)
    order_item = _make_order_item_mock(order_id)

    items_result = MagicMock()
    items_result.scalars.return_value.all.return_value = [order_item]
    mock_db.get.return_value = order_mock
    mock_db.execute.return_value = items_result

    svc = OrderService(mock_db)
    resp = await svc.get_detail(order_id)

    assert resp.id == order_id
    assert len(resp.items) == 1


@pytest.mark.asyncio
async def test_get_detail_not_found(mock_db):
    """get_detail: raises OrderNotFoundError when order missing."""
    from app.core.exceptions import OrderNotFoundError
    from app.services.order_service import OrderService

    mock_db.get.return_value = None
    svc = OrderService(mock_db)
    with pytest.raises(OrderNotFoundError):
        await svc.get_detail(uuid4())


# ---------------------------------------------------------------------------
#  list_admin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_admin_success(mock_db):
    """list_admin: returns filtered order list with total."""
    from app.schemas.order import OrderListQuery
    from app.services.order_service import OrderService

    order_mock = _make_order_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 5
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [order_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = OrderService(mock_db)
    query = OrderListQuery(page=1, page_size=20)
    orders, total = await svc.list_admin(query)

    assert total == 5
    assert len(orders) == 1
