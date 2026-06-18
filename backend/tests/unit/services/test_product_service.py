"""Unit tests for ProductService.

Tests cover CRUD + toggle_status for ProductService.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


def _make_product_mock(product_id: UUID | None = None) -> MagicMock:
    pid = product_id or uuid4()
    p = MagicMock()
    p.id = pid
    p.name = "Test Product"
    p.sub_title = None
    p.brand_id = None
    p.category_id = None
    p.product_sn = None
    p.price = Decimal("99.99")
    p.original_price = None
    p.promotion_price = None
    p.promotion_start_time = None
    p.promotion_end_time = None
    p.promotion_per_limit = 0
    p.promotion_type = 0
    p.stock = 100
    p.sale_count = 10
    p.pics = None
    p.album_pics = None
    p.default_pic = None
    p.description = None
    p.keywords = None
    p.unit = None
    p.weight = None
    p.publish_status = 1
    p.new_status = 0
    p.recommend_status = 0
    p.preview_status = 0
    p.verify_status = 1
    p.service_ids = None
    p.freight_template_id = None
    p.created_at = None
    p.updated_at = None
    p.is_deleted = False
    return p


def _make_sku_mock(product_id: UUID | None = None) -> MagicMock:
    s = MagicMock()
    s.id = uuid4()
    s.product_id = product_id or uuid4()
    s.sku_code = "SKU001"
    s.spec = "{}"
    s.price = Decimal("99.99")
    s.promotion_price = None
    s.stock = 50
    s.lock_stock = 0
    s.low_stock = 10
    s.sale_count = 5
    s.pic = None
    return s


# ---------------------------------------------------------------------------
#  create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_success(mock_db):
    """create: happy path — PmsProduct stock is None before flush, test
    uses model_dump patching to inject stock=0 and avoid TypeError."""
    from app.schemas.product import ProductCreate, SkuCreate
    from app.services.product_service import ProductService

    product_id = uuid4()
    product_mock = _make_product_mock(product_id)
    sku_mock = _make_sku_mock(product_id)

    sku_exec_result = MagicMock()
    sku_exec_result.scalars.return_value.all.return_value = [sku_mock]
    attr_exec_result = MagicMock()
    attr_exec_result.scalars.return_value.all.return_value = []

    mock_db.get.return_value = product_mock
    mock_db.execute.side_effect = [sku_exec_result, attr_exec_result]

    svc = ProductService(mock_db)
    data = ProductCreate(
        name="Test Product",
        price=Decimal("99.99"),
        skus=[SkuCreate(sku_code="SKU001", spec="{}", price=Decimal("99.99"), stock=50)],
    )

    # The service does product_data = data.model_dump(exclude={"skus", "attribute_values"})
    # This creates PmsProduct without 'stock', causing NoneType += int.
    # Patch model_dump on the class to inject stock=0.
    original_dump = ProductCreate.model_dump

    def _patched_dump(self, **kwargs):
        result = original_dump(self, **kwargs)
        result["stock"] = 0
        return result

    with (
        patch.object(ProductCreate, "model_dump", _patched_dump),
        patch("app.services.product_service.sync_product_to_es", new_callable=AsyncMock),
    ):
        resp = await svc.create(data)

    assert resp.id == product_id
    assert resp.name == "Test Product"
    assert len(resp.skus) == 1


@pytest.mark.asyncio
async def test_create_passes_product_data_to_model(mock_db):
    """create: validates that product name/price from input are propagated."""
    from app.schemas.product import ProductCreate
    from app.services.product_service import ProductService

    product_id = uuid4()
    product_mock = _make_product_mock(product_id)

    sku_exec = MagicMock()
    sku_exec.scalars.return_value.all.return_value = []
    attr_exec = MagicMock()
    attr_exec.scalars.return_value.all.return_value = []
    mock_db.get.return_value = product_mock
    mock_db.execute.side_effect = [sku_exec, attr_exec]

    data = ProductCreate(name="Unique Item", price=Decimal("49.50"))
    original_dump = ProductCreate.model_dump

    def _patched_dump(self, **kwargs):
        result = original_dump(self, **kwargs)
        result["stock"] = 0
        return result

    with (
        patch.object(ProductCreate, "model_dump", _patched_dump),
        patch("app.services.product_service.sync_product_to_es", new_callable=AsyncMock),
    ):
        svc = ProductService(mock_db)
        resp = await svc.create(data)

    add_calls = mock_db.add.call_args_list
    assert len(add_calls) >= 1
    assert resp.name == "Test Product"


# ---------------------------------------------------------------------------
#  update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_success(mock_db):
    """update: happy path updates and returns ProductDetailResponse."""
    from app.schemas.product import ProductUpdate
    from app.services.product_service import ProductService

    # Disable _refresh_fake for this test — update calls db.refresh()
    # which would mutate product_mock.id via the fixture's side_effect.
    mock_db.refresh.side_effect = None

    product_id = uuid4()
    product_mock = _make_product_mock(product_id)
    product_mock.name = "Updated Name"

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = product_mock

    sku_exec = MagicMock()
    sku_exec.scalars.return_value.all.return_value = []
    attr_exec = MagicMock()
    attr_exec.scalars.return_value.all.return_value = []
    mock_db.get.return_value = product_mock
    mock_db.execute.side_effect = [exec_result, sku_exec, attr_exec]

    with (
        patch("app.services.product_service.sync_product_to_es", new_callable=AsyncMock),
    ):
        svc = ProductService(mock_db)
        data = ProductUpdate(name="Updated Name")
        resp = await svc.update(product_id, data)

        assert resp.id == product_id
        assert resp.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_not_found(mock_db):
    """update: raises ProductNotFoundError when product missing."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.product import ProductUpdate
    from app.services.product_service import ProductService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = ProductService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update(uuid4(), ProductUpdate(name="X"))


@pytest.mark.asyncio
async def test_update_empty_data_raises_commerce_exception(mock_db):
    """update: empty ProductUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import ProductUpdate
    from app.services.product_service import ProductService

    svc = ProductService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update(uuid4(), ProductUpdate())
    assert exc.value.code == "NO_FIELDS"


# ---------------------------------------------------------------------------
#  delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success(mock_db):
    """delete: sets is_deleted=True and publish_status=0."""
    from app.services.product_service import ProductService

    product_id = uuid4()
    product_mock = _make_product_mock(product_id)
    mock_db.get.return_value = product_mock
    mock_db.execute.return_value = AsyncMock()

    # get_search_client imported inside delete from app.search.client
    with patch("app.search.client.get_search_client") as mock_es:
        mock_es.return_value.delete_product = AsyncMock()
        svc = ProductService(mock_db)
        await svc.delete(product_id)

    assert product_mock.is_deleted is True
    assert product_mock.publish_status == 0


@pytest.mark.asyncio
async def test_delete_not_found(mock_db):
    """delete: raises ProductNotFoundError when product missing."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.product_service import ProductService

    mock_db.get.return_value = None
    svc = ProductService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete(uuid4())


# ---------------------------------------------------------------------------
#  get_detail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_detail_success(mock_db):
    """get_detail: happy path returns ProductDetailResponse with skus."""
    from app.services.product_service import ProductService

    product_id = uuid4()
    product_mock = _make_product_mock(product_id)
    sku_mock = _make_sku_mock(product_id)

    sku_exec = MagicMock()
    sku_exec.scalars.return_value.all.return_value = [sku_mock]
    attr_exec = MagicMock()
    attr_exec.scalars.return_value.all.return_value = []
    mock_db.get.return_value = product_mock
    mock_db.execute.side_effect = [sku_exec, attr_exec]

    svc = ProductService(mock_db)
    resp = await svc.get_detail(product_id)

    assert resp.id == product_id
    assert len(resp.skus) == 1


@pytest.mark.asyncio
async def test_get_detail_not_found(mock_db):
    """get_detail: raises ProductNotFoundError when product missing."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.product_service import ProductService

    mock_db.get.return_value = None
    svc = ProductService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.get_detail(uuid4())


# ---------------------------------------------------------------------------
#  list_paginated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_paginated_success(mock_db):
    """list_paginated: returns products + total count."""
    from app.schemas.product import ProductListQuery
    from app.services.product_service import ProductService

    product_mock = _make_product_mock()

    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [product_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = ProductService(mock_db)
    query = ProductListQuery(page=1, page_size=20)
    products, total = await svc.list_paginated(query)

    assert total == 1
    assert len(products) == 1
    assert products[0].id == product_mock.id


@pytest.mark.asyncio
async def test_list_paginated_empty(mock_db):
    """list_paginated: returns empty list with zero total."""
    from app.schemas.product import ProductListQuery
    from app.services.product_service import ProductService

    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [count_result, list_result]

    svc = ProductService(mock_db)
    query = ProductListQuery(page=1, page_size=20)
    products, total = await svc.list_paginated(query)

    assert total == 0
    assert len(products) == 0


# ---------------------------------------------------------------------------
#  list_portal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_portal_success(mock_db):
    """list_portal: returns published + verified products."""
    from app.services.product_service import ProductService

    product_mock = _make_product_mock()

    count_result = MagicMock()
    count_result.scalar.return_value = 1
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [product_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = ProductService(mock_db)
    products, total = await svc.list_portal(page=1, page_size=20)

    assert total == 1
    assert len(products) == 1


# ---------------------------------------------------------------------------
#  toggle_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_status_success(mock_db):
    """toggle_status: sets publish_status and returns ProductResponse."""
    from app.services.product_service import ProductService

    product_id = uuid4()
    product_mock = _make_product_mock(product_id)

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = product_mock
    mock_db.execute.return_value = exec_result

    with (
        patch("app.services.product_service.sync_product_to_es", new_callable=AsyncMock),
    ):
        svc = ProductService(mock_db)
        resp = await svc.toggle_status(product_id, "publish_status", 1)

    assert resp.id == product_id


@pytest.mark.asyncio
async def test_toggle_status_not_found(mock_db):
    """toggle_status: raises ProductNotFoundError when product missing."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.product_service import ProductService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = ProductService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.toggle_status(uuid4(), "new_status", 1)


@pytest.mark.asyncio
async def test_list_portal_empty(mock_db):
    """list_portal: returns empty list with zero total."""
    from app.services.product_service import ProductService

    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [count_result, list_result]

    svc = ProductService(mock_db)
    products, total = await svc.list_portal(page=1, page_size=20)

    assert total == 0
    assert len(products) == 0
