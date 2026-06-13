"""Unit tests for FlashService.

Tests cover promotion/session/product CRUD operations.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


def _make_flash_promotion_mock(promo_id=None) -> MagicMock:
    pid = promo_id or uuid4()
    p = MagicMock()
    p.id = pid
    p.title = "Flash Sale"
    p.start_date = datetime.now(UTC)
    p.end_date = datetime.now(UTC) + timedelta(days=1)
    p.status = 0
    p.note = None
    p.created_at = None
    return p


def _make_flash_session_mock(session_id=None, promo_id=None) -> MagicMock:
    sid = session_id or uuid4()
    s = MagicMock()
    s.id = sid
    s.promotion_id = promo_id or uuid4()
    s.name = "10:00 Session"
    s.start_time = datetime.now(UTC)
    s.end_time = datetime.now(UTC) + timedelta(hours=2)
    s.status = 0
    return s


def _make_flash_product_mock(fp_id=None) -> MagicMock:
    fid = fp_id or uuid4()
    p = MagicMock()
    p.id = fid
    p.session_id = uuid4()
    p.product_id = uuid4()
    p.sku_id = uuid4()
    p.flash_price = Decimal("49.99")
    p.flash_stock = 100
    p.flash_limit = 2
    p.sort = 0
    return p


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


@patch("app.services.flash_service.FlashPromotionResponse.model_validate")
@pytest.mark.asyncio
async def test_create_promotion_success(mock_validate, mock_db):
    """create_promotion: creates flash promotion and returns response."""
    from app.schemas.promotion import FlashPromotionCreate
    from app.services.flash_service import FlashService

    expected = _make_flash_promotion_mock()
    mock_validate.return_value = expected

    svc = FlashService(mock_db)
    data = FlashPromotionCreate(
        title="618 Sale",
        start_date=datetime.now(UTC),
        end_date=datetime.now(UTC) + timedelta(days=3),
    )
    resp = await svc.create_promotion(data)

    assert mock_db.add.called
    assert resp.title == "Flash Sale"


@patch("app.services.flash_service.FlashSessionResponse.model_validate")
@pytest.mark.asyncio
async def test_create_session_success(mock_validate, mock_db):
    """create_session: creates flash session."""
    from app.schemas.promotion import FlashSessionCreate
    from app.services.flash_service import FlashService

    expected = _make_flash_session_mock()
    mock_validate.return_value = expected

    svc = FlashService(mock_db)
    data = FlashSessionCreate(
        promotion_id=uuid4(),
        name="10:00 Flash",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(hours=1),
    )
    resp = await svc.create_session(data)

    assert mock_db.add.called
    assert resp.name == "10:00 Session"


@patch("app.services.flash_service.FlashProductResponse.model_validate")
@pytest.mark.asyncio
async def test_add_product_success(mock_validate, mock_db):
    """add_product: creates flash product association."""
    from app.schemas.promotion import FlashProductCreate
    from app.services.flash_service import FlashService

    expected = _make_flash_product_mock()
    mock_validate.return_value = expected

    svc = FlashService(mock_db)
    data = FlashProductCreate(
        session_id=uuid4(),
        product_id=uuid4(),
        sku_id=uuid4(),
        flash_price=Decimal("19.99"),
        flash_stock=50,
    )
    resp = await svc.add_product(data)

    assert mock_db.add.called
    assert resp.flash_price == Decimal("49.99")


# ---------------------------------------------------------------------------
#  update_promotion / delete_promotion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_promotion_success(mock_db):
    """update_promotion: updates flash promotion via returning()."""
    from app.schemas.promotion import FlashPromotionUpdate
    from app.services.flash_service import FlashService

    promo_id = uuid4()
    promo_mock = _make_flash_promotion_mock(promo_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = promo_mock
    mock_db.execute.return_value = exec_result

    svc = FlashService(mock_db)
    data = FlashPromotionUpdate(title="Updated Sale")
    resp = await svc.update_promotion(promo_id, data)

    assert resp.id == promo_id


@pytest.mark.asyncio
async def test_update_promotion_not_found(mock_db):
    """update_promotion: missing promotion raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.promotion import FlashPromotionUpdate
    from app.services.flash_service import FlashService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = FlashService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_promotion(uuid4(), FlashPromotionUpdate(title="X"))


@pytest.mark.asyncio
async def test_update_promotion_empty_data_raises(mock_db):
    """update_promotion: empty data raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.promotion import FlashPromotionUpdate
    from app.services.flash_service import FlashService

    svc = FlashService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update_promotion(uuid4(), FlashPromotionUpdate())
    assert exc.value.code == "NO_FIELDS"


@pytest.mark.asyncio
async def test_delete_promotion_success(mock_db):
    """delete_promotion: removes promotion when found."""
    from app.services.flash_service import FlashService

    promo_mock = _make_flash_promotion_mock()
    mock_db.get.return_value = promo_mock

    svc = FlashService(mock_db)
    await svc.delete_promotion(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_promotion_not_found(mock_db):
    """delete_promotion: missing promotion raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.flash_service import FlashService

    mock_db.get.return_value = None
    svc = FlashService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_promotion(uuid4())


# ---------------------------------------------------------------------------
#  update_session / delete_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_session_success(mock_db):
    """update_session: updates session via returning()."""
    from app.schemas.promotion import FlashSessionUpdate
    from app.services.flash_service import FlashService

    session_id = uuid4()
    session_mock = _make_flash_session_mock(session_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = session_mock
    mock_db.execute.return_value = exec_result

    svc = FlashService(mock_db)
    resp = await svc.update_session(session_id, FlashSessionUpdate(name="New Name"))
    assert resp.id == session_id


@pytest.mark.asyncio
async def test_update_session_not_found(mock_db):
    """update_session: missing session raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.promotion import FlashSessionUpdate
    from app.services.flash_service import FlashService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = FlashService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_session(uuid4(), FlashSessionUpdate(name="X"))


@pytest.mark.asyncio
async def test_delete_session_success(mock_db):
    """delete_session: removes session when found."""
    from app.services.flash_service import FlashService

    session_mock = _make_flash_session_mock()
    mock_db.get.return_value = session_mock

    svc = FlashService(mock_db)
    await svc.delete_session(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_session_not_found(mock_db):
    """delete_session: missing session raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.flash_service import FlashService

    mock_db.get.return_value = None
    svc = FlashService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_session(uuid4())


# ---------------------------------------------------------------------------
#  delete_product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_product_success(mock_db):
    """delete_product: removes flash product when found."""
    from app.services.flash_service import FlashService

    fp_mock = _make_flash_product_mock()
    mock_db.get.return_value = fp_mock

    svc = FlashService(mock_db)
    await svc.delete_product(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_product_not_found(mock_db):
    """delete_product: missing flash product raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.flash_service import FlashService

    mock_db.get.return_value = None
    svc = FlashService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_product(uuid4())


# ---------------------------------------------------------------------------
#  list_promotions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_promotions_success(mock_db):
    """list_promotions: returns paginated promotions."""
    from app.services.flash_service import FlashService

    promo_mock = _make_flash_promotion_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 2
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [promo_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = FlashService(mock_db)
    items, total = await svc.list_promotions(page=1, page_size=10)

    assert total == 2
    assert len(items) == 1
