"""Unit tests for MemberService.

Tests cover address CRUD, favorites, and member admin queries.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

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


def _make_address_mock(addr_id: UUID | None = None) -> MagicMock:
    aid = addr_id or uuid4()
    a = MagicMock()
    a.id = aid
    a.name = "Test User"
    a.phone = "13800138000"
    a.province = "Guangdong"
    a.city = "Shenzhen"
    a.region = "Nanshan"
    a.detail_address = "123 Test St"
    a.post_code = "518000"
    a.default_status = 1
    a.created_at = None
    return a


def _make_favorite_mock() -> MagicMock:
    f = MagicMock()
    f.id = uuid4()
    f.product_id = uuid4()
    f.product_name = "Test Product"
    f.product_pic = "pic.jpg"
    f.product_price = "99.99"
    f.created_at = None
    return f


# ---------------------------------------------------------------------------
#  create_address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_address_success(mock_db):
    """create_address: creates address and returns AddressResponse."""
    from app.schemas.member import AddressCreate
    from app.services.member_service import MemberService

    addr_mock = _make_address_mock()
    mock_db.get.return_value = addr_mock

    svc = MemberService(mock_db)
    data = AddressCreate(
        name="Test User",
        phone="13800138000",
        detail_address="123 Test St",
        default_status=0,
    )
    resp = await svc.create_address(uuid4(), data)

    assert mock_db.add.called
    assert resp.name == "Test User"


@pytest.mark.asyncio
async def test_create_address_default_clears_others(mock_db):
    """create_address: setting default=1 clears other defaults first."""
    from app.schemas.member import AddressCreate
    from app.services.member_service import MemberService

    addr_mock = _make_address_mock()
    mock_db.get.return_value = addr_mock

    svc = MemberService(mock_db)
    data = AddressCreate(
        name="Default Address",
        phone="13800138000",
        detail_address="456 Main St",
        default_status=1,
    )
    resp = await svc.create_address(uuid4(), data)

    # should execute the update to clear old defaults + add + flush
    assert mock_db.add.called
    assert mock_db.execute.called


# ---------------------------------------------------------------------------
#  update_address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_address_success(mock_db):
    """update_address: updates address via returning().update()."""
    from app.schemas.member import AddressUpdate
    from app.services.member_service import MemberService

    addr_id = uuid4()
    addr_mock = _make_address_mock(addr_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = addr_mock
    mock_db.execute.return_value = exec_result

    svc = MemberService(mock_db)
    data = AddressUpdate(name="Updated Name")
    resp = await svc.update_address(uuid4(), addr_id, data)

    assert resp.id == addr_id


@pytest.mark.asyncio
async def test_update_address_not_found(mock_db):
    """update_address: missing address raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.member import AddressUpdate
    from app.services.member_service import MemberService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = MemberService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_address(uuid4(), uuid4(), AddressUpdate(name="X"))


@pytest.mark.asyncio
async def test_update_address_empty_data_raises(mock_db):
    """update_address: empty AddressUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.member import AddressUpdate
    from app.services.member_service import MemberService

    svc = MemberService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update_address(uuid4(), uuid4(), AddressUpdate())
    assert exc.value.code == "NO_FIELDS"


# ---------------------------------------------------------------------------
#  delete_address
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_address_success(mock_db):
    """delete_address: removes address when rowcount>0."""
    from app.services.member_service import MemberService

    exec_result = MagicMock()
    exec_result.rowcount = 1
    mock_db.execute.return_value = exec_result

    svc = MemberService(mock_db)
    await svc.delete_address(uuid4(), uuid4())  # should not raise


@pytest.mark.asyncio
async def test_delete_address_not_found(mock_db):
    """delete_address: rowcount==0 raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.member_service import MemberService

    exec_result = MagicMock()
    exec_result.rowcount = 0
    mock_db.execute.return_value = exec_result

    svc = MemberService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_address(uuid4(), uuid4())


# ---------------------------------------------------------------------------
#  list_addresses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_addresses_success(mock_db):
    """list_addresses: returns all addresses for user."""
    from app.services.member_service import MemberService

    addr_mock = _make_address_mock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [addr_mock]
    mock_db.execute.return_value = list_result

    svc = MemberService(mock_db)
    items = await svc.list_addresses(uuid4())

    assert len(items) == 1
    assert items[0].name == "Test User"


# ---------------------------------------------------------------------------
#  add_favorite / remove_favorite / list_favorites
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_favorite_success(mock_db):
    """add_favorite: creates favorite if not existing.

    The service creates a real UmsMemberFavorite; validate is patched
    to avoid SQLAlchemy default-initialisation issues.
    """
    from app.services.member_service import MemberService
    from unittest.mock import patch

    product_mock = MagicMock()
    product_mock.is_deleted = False
    product_mock.name = "Test Product"
    product_mock.default_pic = "pic.jpg"
    product_mock.price = "99.99"

    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = None

    fav_mock = _make_favorite_mock()
    mock_db.get.return_value = product_mock
    mock_db.execute.return_value = existing_result

    with patch("app.services.member_service.FavoriteResponse.model_validate", return_value=fav_mock):
        svc = MemberService(mock_db)
        resp = await svc.add_favorite(uuid4(), uuid4())

    assert mock_db.add.called
    assert resp is not None


@pytest.mark.asyncio
async def test_add_favorite_product_not_found(mock_db):
    """add_favorite: deleted product raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.member_service import MemberService

    product_mock = MagicMock()
    product_mock.is_deleted = True
    mock_db.get.return_value = product_mock

    svc = MemberService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.add_favorite(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_add_favorite_idempotent(mock_db):
    """add_favorite: existing favorite returns without creating duplicate."""
    from app.services.member_service import MemberService

    product_mock = MagicMock()
    product_mock.is_deleted = False
    product_mock.name = "Test Product"
    product_mock.default_pic = "pic.jpg"

    fav_mock = _make_favorite_mock()
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = fav_mock

    mock_db.get.return_value = product_mock
    mock_db.execute.return_value = existing_result

    svc = MemberService(mock_db)
    resp = await svc.add_favorite(uuid4(), uuid4())

    assert resp.id == fav_mock.id
    assert mock_db.add.call_count == 0


@pytest.mark.asyncio
async def test_remove_favorite_no_error(mock_db):
    """remove_favorite: executes delete without error even if not found."""
    from app.services.member_service import MemberService

    svc = MemberService(mock_db)
    await svc.remove_favorite(uuid4(), uuid4())  # should not raise


@pytest.mark.asyncio
async def test_list_favorites_success(mock_db):
    """list_favorites: returns paginated favorites."""
    from app.services.member_service import MemberService

    fav_mock = _make_favorite_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 2
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [fav_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = MemberService(mock_db)
    items, total = await svc.list_favorites(uuid4(), page=1, page_size=20)

    assert total == 2
    assert len(items) == 1
