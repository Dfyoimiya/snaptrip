"""Unit tests for CartService.

Tests cover add, list_items, update_item, delete_item, clear_cart.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


def _make_cart_item_mock() -> MagicMock:
    item = MagicMock()
    item.id = uuid4()
    item.product_id = uuid4()
    item.product_name = "Test Product"
    item.product_pic = "pic.jpg"
    item.sku_id = uuid4()
    item.sku_code = "SKU001"
    item.spec = "{}"
    item.price = Decimal("99.99")
    item.quantity = 1
    item.checked = 1
    return item


def _make_product_mock() -> MagicMock:
    p = MagicMock()
    p.is_deleted = False
    p.publish_status = 1
    p.name = "Test Product"
    p.default_pic = "pic.jpg"
    return p


def _make_sku_mock(sku_id=None) -> MagicMock:
    s = MagicMock()
    s.id = sku_id or uuid4()
    s.product_id = uuid4()
    s.stock = 100
    s.lock_stock = 0
    s.sku_code = "SKU001"
    s.spec = "{}"
    s.price = Decimal("99.99")
    s.promotion_price = None
    return s


# ---------------------------------------------------------------------------
#  add
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_new_item_success(mock_db):
    """add: creates new cart item when no existing entry."""
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    product_id = uuid4()
    sku_id = uuid4()
    product_mock = _make_product_mock()
    sku_mock = _make_sku_mock(sku_id)
    sku_mock.product_id = product_id

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    mock_db.get.side_effect = [product_mock, sku_mock]
    mock_db.execute.return_value = existing_result

    svc = CartService(mock_db)
    data = CartItemCreate(product_id=product_id, sku_id=sku_id, quantity=1)
    resp = await svc.add(uuid4(), data)

    assert mock_db.add.called
    assert resp.quantity == 1


@pytest.mark.asyncio
async def test_add_existing_item_increments_quantity(mock_db):
    """add: existing SKU -> quantity is incremented."""
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    product_id = uuid4()
    sku_id = uuid4()
    product_mock = _make_product_mock()
    sku_mock = _make_sku_mock(sku_id)
    sku_mock.product_id = product_id
    existing_cart = _make_cart_item_mock()
    existing_cart.quantity = 3

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = existing_cart

    mock_db.get.side_effect = [product_mock, sku_mock]
    mock_db.execute.return_value = existing_result

    svc = CartService(mock_db)
    data = CartItemCreate(product_id=product_id, sku_id=sku_id, quantity=2)
    await svc.add(uuid4(), data)

    assert existing_cart.quantity == 5  # 3 + 2
    assert existing_cart.checked == 1


@pytest.mark.asyncio
async def test_add_product_off_shelf(mock_db):
    """add: product not published raises ProductOffShelfError."""
    from app.core.exceptions import ProductOffShelfError
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    product_mock = MagicMock()
    product_mock.is_deleted = True
    mock_db.get.return_value = product_mock

    svc = CartService(mock_db)
    with pytest.raises(ProductOffShelfError):
        await svc.add(uuid4(), CartItemCreate(product_id=uuid4(), sku_id=uuid4()))


@pytest.mark.asyncio
async def test_add_product_not_found_raises(mock_db):
    """add: product not found raises ProductOffShelfError."""
    from app.core.exceptions import ProductOffShelfError
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    mock_db.get.return_value = None

    svc = CartService(mock_db)
    with pytest.raises(ProductOffShelfError):
        await svc.add(uuid4(), CartItemCreate(product_id=uuid4(), sku_id=uuid4()))


@pytest.mark.asyncio
async def test_add_sku_not_found_raises(mock_db):
    """add: SKU not found raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    product_mock = _make_product_mock()
    mock_db.get.side_effect = [product_mock, None]

    svc = CartService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.add(uuid4(), CartItemCreate(product_id=uuid4(), sku_id=uuid4()))


@pytest.mark.asyncio
async def test_add_sku_mismatch_product_id_raises(mock_db):
    """add: SKU belongs to different product raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    sku_mock = _make_sku_mock()
    sku_mock.product_id = uuid4()  # different from data.product_id
    product_mock = _make_product_mock()
    mock_db.get.side_effect = [product_mock, sku_mock]

    svc = CartService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.add(uuid4(), CartItemCreate(product_id=uuid4(), sku_id=sku_mock.id))


@pytest.mark.asyncio
async def test_add_insufficient_stock(mock_db):
    """add: stock exhausted raises InsufficientStockError."""
    from app.core.exceptions import InsufficientStockError
    from app.schemas.order import CartItemCreate
    from app.services.cart_service import CartService

    product_id = uuid4()
    sku_id = uuid4()
    product_mock = _make_product_mock()
    sku_mock = _make_sku_mock(sku_id)
    sku_mock.product_id = product_id
    sku_mock.stock = 5
    sku_mock.lock_stock = 3  # available = 2

    mock_db.get.side_effect = [product_mock, sku_mock]

    svc = CartService(mock_db)
    with pytest.raises(InsufficientStockError):
        await svc.add(uuid4(), CartItemCreate(product_id=product_id, sku_id=sku_id, quantity=10))


# ---------------------------------------------------------------------------
#  list_items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_items_success(mock_db):
    """list_items: returns all cart items for user."""
    from app.services.cart_service import CartService

    cart_items = [_make_cart_item_mock(), _make_cart_item_mock()]
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = cart_items
    mock_db.execute.return_value = list_result

    svc = CartService(mock_db)
    resp = await svc.list_items(uuid4())

    assert len(resp) == 2


@pytest.mark.asyncio
async def test_list_items_empty(mock_db):
    """list_items: returns empty list for user with no cart items."""
    from app.services.cart_service import CartService

    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = list_result

    svc = CartService(mock_db)
    resp = await svc.list_items(uuid4())

    assert len(resp) == 0


# ---------------------------------------------------------------------------
#  update_item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_item_success(mock_db):
    """update_item: updates quantity via update().returning()."""
    from app.schemas.order import CartItemUpdate
    from app.services.cart_service import CartService

    cart_item = _make_cart_item_mock()
    cart_item.quantity = 5  # updated value
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = cart_item
    mock_db.execute.return_value = exec_result

    svc = CartService(mock_db)
    data = CartItemUpdate(quantity=5)
    resp = await svc.update_item(uuid4(), cart_item.id, data)

    assert resp.id == cart_item.id
    assert resp.quantity == 5


@pytest.mark.asyncio
async def test_update_item_not_found(mock_db):
    """update_item: missing item raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.order import CartItemUpdate
    from app.services.cart_service import CartService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CartService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_item(uuid4(), uuid4(), CartItemUpdate(quantity=3))


@pytest.mark.asyncio
async def test_update_item_empty_data_raises(mock_db):
    """update_item: empty CartItemUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.order import CartItemUpdate
    from app.services.cart_service import CartService

    svc = CartService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update_item(uuid4(), uuid4(), CartItemUpdate())
    assert exc.value.code == "NO_FIELDS"


# ---------------------------------------------------------------------------
#  delete_item
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_item_success(mock_db):
    """delete_item: removes item when found."""
    from app.services.cart_service import CartService

    exec_result = MagicMock()
    exec_result.rowcount = 1
    mock_db.execute.return_value = exec_result

    svc = CartService(mock_db)
    await svc.delete_item(uuid4(), uuid4())  # should not raise


@pytest.mark.asyncio
async def test_delete_item_not_found(mock_db):
    """delete_item: raises ProductNotFoundError when rowcount==0."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.cart_service import CartService

    exec_result = MagicMock()
    exec_result.rowcount = 0
    mock_db.execute.return_value = exec_result

    svc = CartService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_item(uuid4(), uuid4())


# ---------------------------------------------------------------------------
#  clear_cart
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clear_cart_success(mock_db):
    """clear_cart: removes all cart items for user without error."""
    from app.services.cart_service import CartService

    exec_result = MagicMock()
    mock_db.execute.return_value = exec_result

    svc = CartService(mock_db)
    await svc.clear_cart(uuid4())  # should not raise

    assert mock_db.execute.called


@pytest.mark.asyncio
async def test_clear_cart_on_empty_cart_does_not_raise(mock_db):
    """clear_cart: does not raise even when cart is already empty."""
    from app.services.cart_service import CartService

    exec_result = MagicMock()
    mock_db.execute.return_value = exec_result

    svc = CartService(mock_db)
    await svc.clear_cart(uuid4())  # should not raise
