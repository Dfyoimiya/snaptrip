"""Unit tests for BrandService.

Tests cover CRUD, list_paginated, list_all, toggle_status.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


async def _refresh_fake(obj: object) -> None:
    """Simulate flush/refresh generating the primary key."""
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


def _make_brand_mock(brand_id: UUID | None = None) -> MagicMock:
    bid = brand_id or uuid4()
    b = MagicMock()
    b.id = bid
    b.name = "Test Brand"
    b.first_letter = "T"
    b.sort = 0
    b.factory_status = 1
    b.show_status = 1
    b.logo = None
    b.big_pic = None
    b.brand_story = None
    b.created_at = None
    b.updated_at = None
    return b


# ---------------------------------------------------------------------------
#  create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_success(mock_db):
    """create: creates brand and returns BrandResponse."""
    from app.schemas.product import BrandCreate
    from app.services.brand_service import BrandService

    brand_mock = _make_brand_mock()
    mock_db.get.return_value = brand_mock

    svc = BrandService(mock_db)
    data = BrandCreate(name="New Brand", sort=10)
    resp = await svc.create(data)

    assert mock_db.add.called
    assert resp.name == "New Brand"


@pytest.mark.asyncio
async def test_create_with_all_fields(mock_db):
    """create: brand with full fields is created."""
    from app.schemas.product import BrandCreate
    from app.services.brand_service import BrandService

    svc = BrandService(mock_db)
    data = BrandCreate(
        name="Full Brand",
        first_letter="F",
        sort=5,
        factory_status=1,
        show_status=1,
        logo="logo.png",
        big_pic="big.png",
        brand_story="A great story.",
    )
    resp = await svc.create(data)
    assert mock_db.add.called
    assert resp.name == "Full Brand"


# ---------------------------------------------------------------------------
#  update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_success(mock_db):
    """update: updates brand via update().returning()."""
    from app.schemas.product import BrandUpdate
    from app.services.brand_service import BrandService

    brand_id = uuid4()
    brand_mock = _make_brand_mock(brand_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = brand_mock
    mock_db.execute.return_value = exec_result

    svc = BrandService(mock_db)
    data = BrandUpdate(name="Updated Brand")
    resp = await svc.update(brand_id, data)

    assert resp.id == brand_id
    assert resp.name == "Test Brand"


@pytest.mark.asyncio
async def test_update_not_found(mock_db):
    """update: missing brand raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.product import BrandUpdate
    from app.services.brand_service import BrandService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = BrandService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update(uuid4(), BrandUpdate(name="X"))


@pytest.mark.asyncio
async def test_update_empty_data_raises(mock_db):
    """update: empty BrandUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import BrandUpdate
    from app.services.brand_service import BrandService

    svc = BrandService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update(uuid4(), BrandUpdate())
    assert exc.value.code == "NO_FIELDS"


# ---------------------------------------------------------------------------
#  delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success(mock_db):
    """delete: removes brand when found."""
    from app.services.brand_service import BrandService

    brand_mock = _make_brand_mock()
    mock_db.get.return_value = brand_mock

    svc = BrandService(mock_db)
    await svc.delete(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_not_found(mock_db):
    """delete: missing brand raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.brand_service import BrandService

    mock_db.get.return_value = None
    svc = BrandService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete(uuid4())


# ---------------------------------------------------------------------------
#  get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_success(mock_db):
    """get_by_id: returns BrandResponse when found."""
    from app.services.brand_service import BrandService

    brand_mock = _make_brand_mock()
    mock_db.get.return_value = brand_mock

    svc = BrandService(mock_db)
    resp = await svc.get_by_id(uuid4())
    assert resp.id == brand_mock.id


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_db):
    """get_by_id: missing brand raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.brand_service import BrandService

    mock_db.get.return_value = None
    svc = BrandService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.get_by_id(uuid4())


# ---------------------------------------------------------------------------
#  list_paginated / list_all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_paginated_success(mock_db):
    """list_paginated: returns paginated brands with total."""
    from app.services.brand_service import BrandService

    brand_mock = _make_brand_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 5
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [brand_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = BrandService(mock_db)
    items, total = await svc.list_paginated(page=1, page_size=20)

    assert total == 5
    assert len(items) == 1


@pytest.mark.asyncio
async def test_list_all_success(mock_db):
    """list_all: returns all active brands."""
    from app.services.brand_service import BrandService

    brand_mock = _make_brand_mock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [brand_mock]
    mock_db.execute.return_value = list_result

    svc = BrandService(mock_db)
    items = await svc.list_all()

    assert len(items) == 1


# ---------------------------------------------------------------------------
#  toggle_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_status_success(mock_db):
    """toggle_status: toggles factory_status and returns BrandResponse."""
    from app.services.brand_service import BrandService

    brand_id = uuid4()
    brand_mock = _make_brand_mock(brand_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = brand_mock
    mock_db.execute.return_value = exec_result

    svc = BrandService(mock_db)
    resp = await svc.toggle_status(brand_id, "factory_status", 0)

    assert resp.id == brand_id
    assert resp.factory_status == 1


@pytest.mark.asyncio
async def test_toggle_status_not_found(mock_db):
    """toggle_status: missing brand raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.brand_service import BrandService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = BrandService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.toggle_status(uuid4(), "factory_status", 1)
