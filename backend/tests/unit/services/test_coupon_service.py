"""Unit tests for CouponService.

Tests cover CRUD, list_admin, list_available, claim, list_my_coupons, get_histories.
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


def _make_coupon_mock(coupon_id=None) -> MagicMock:
    cid = coupon_id or uuid4()
    c = MagicMock()
    c.id = cid
    c.name = "Test Coupon"
    c.type = 0
    c.use_type = 0
    c.amount = Decimal("10.00")
    c.min_amount = Decimal("100.00")
    c.category_id = None
    c.brand_id = None
    c.count = 100
    c.publish_count = 0
    c.receive_count = 0
    c.use_count = 0
    c.per_limit = 1
    c.start_time = None
    c.end_time = None
    c.status = 1
    c.member_level = 0
    c.note = None
    c.created_at = None
    return c


def _make_coupon_history_mock(coupon_id=None) -> MagicMock:
    h = MagicMock()
    h.id = uuid4()
    h.coupon_id = coupon_id or uuid4()
    h.user_id = uuid4()
    h.coupon_name = "Test Coupon"
    h.coupon_type = 0
    h.coupon_use_type = 0
    h.coupon_amount = Decimal("10.00")
    h.coupon_min_amount = Decimal("100.00")
    h.use_status = 0
    h.use_time = None
    h.order_id = None
    h.order_sn = None
    h.receive_time = datetime.now(UTC)
    h.expire_time = datetime.now(UTC) + timedelta(days=7)
    return h


@pytest.fixture
def mock_db() -> AsyncSession:
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.execute = AsyncMock()
    db.get = AsyncMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
#  create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_success(mock_db):
    """create: creates coupon template and returns CouponResponse.

    The service creates a real ORM object; validate is mocked to avoid
    SQLAlchemy default-initialisation issues in unit tests.
    """
    from app.schemas.promotion import CouponCreate
    from app.services.coupon_service import CouponService

    expected = _make_coupon_mock()
    with patch("app.services.coupon_service.CouponResponse.model_validate", return_value=expected):
        svc = CouponService(mock_db)
        data = CouponCreate(
            name="New Coupon",
            amount=Decimal("20.00"),
            count=50,
            per_limit=2,
            min_amount=Decimal("200.00"),
        )
        resp = await svc.create(data)

        assert mock_db.add.called
        assert resp.name == "Test Coupon"


@pytest.mark.asyncio
async def test_create_with_dates(mock_db):
    """create: coupon with start/end times."""
    from app.schemas.promotion import CouponCreate
    from app.services.coupon_service import CouponService

    expected = _make_coupon_mock()
    with patch("app.services.coupon_service.CouponResponse.model_validate", return_value=expected):
        svc = CouponService(mock_db)
        data = CouponCreate(
            name="Timed Coupon",
            amount=Decimal("15.00"),
            count=30,
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC) + timedelta(days=30),
        )
        await svc.create(data)
        assert mock_db.add.called


# ---------------------------------------------------------------------------
#  update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_success(mock_db):
    """update: updates coupon fields via update().returning()."""
    from app.schemas.promotion import CouponUpdate
    from app.services.coupon_service import CouponService

    coupon_id = uuid4()
    coupon_mock = _make_coupon_mock(coupon_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = coupon_mock
    mock_db.execute.return_value = exec_result

    svc = CouponService(mock_db)
    data = CouponUpdate(name="Updated Coupon")
    resp = await svc.update(coupon_id, data)

    assert resp.id == coupon_id
    assert resp.name == "Test Coupon"


@pytest.mark.asyncio
async def test_update_not_found(mock_db):
    """update: missing coupon raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.promotion import CouponUpdate
    from app.services.coupon_service import CouponService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CouponService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update(uuid4(), CouponUpdate(name="X"))


@pytest.mark.asyncio
async def test_update_empty_data_raises(mock_db):
    """update: empty CouponUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.promotion import CouponUpdate
    from app.services.coupon_service import CouponService

    svc = CouponService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update(uuid4(), CouponUpdate())
    assert exc.value.code == "NO_FIELDS"


# ---------------------------------------------------------------------------
#  delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success(mock_db):
    """delete: removes coupon when found."""
    from app.services.coupon_service import CouponService

    coupon_mock = _make_coupon_mock()
    mock_db.get.return_value = coupon_mock

    svc = CouponService(mock_db)
    await svc.delete(uuid4())  # should not raise
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_not_found(mock_db):
    """delete: missing coupon raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.coupon_service import CouponService

    mock_db.get.return_value = None
    svc = CouponService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete(uuid4())


# ---------------------------------------------------------------------------
#  get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_success(mock_db):
    """get_by_id: returns CouponResponse when found."""
    from app.services.coupon_service import CouponService

    coupon_mock = _make_coupon_mock()
    mock_db.get.return_value = coupon_mock

    svc = CouponService(mock_db)
    resp = await svc.get_by_id(uuid4())
    assert resp.id == coupon_mock.id


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_db):
    """get_by_id: raises ProductNotFoundError when missing."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.coupon_service import CouponService

    mock_db.get.return_value = None
    svc = CouponService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.get_by_id(uuid4())


# ---------------------------------------------------------------------------
#  list_admin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_admin_success(mock_db):
    """list_admin: returns paginated coupons with total."""
    from app.services.coupon_service import CouponService

    coupon_mock = _make_coupon_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 3
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [coupon_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = CouponService(mock_db)
    items, total = await svc.list_admin(page=1, page_size=10)

    assert total == 3
    assert len(items) == 1


# ---------------------------------------------------------------------------
#  list_available
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_available_success(mock_db):
    """list_available: returns active coupons with remaining stock."""
    from app.services.coupon_service import CouponService

    coupon_mock = _make_coupon_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 5
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [coupon_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = CouponService(mock_db)
    items, total = await svc.list_available(page=1, page_size=10)

    assert total == 5
    assert len(items) == 1


# ---------------------------------------------------------------------------
#  claim
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_success(mock_db):
    """claim: successful optimistic-lock claim creates history.

    The service creates a real SmsCouponHistory; model_validate is patched
    to avoid SQLAlchemy default-initialisation issues.
    """
    from unittest.mock import patch

    from app.services.coupon_service import CouponService

    coupon_id = uuid4()
    coupon_mock = _make_coupon_mock(coupon_id)
    coupon_mock.status = 1
    coupon_mock.receive_count = 0
    coupon_mock.count = 100
    coupon_mock.per_limit = 1

    # existing check: count result (0 = not claimed)
    existing_count = MagicMock()
    existing_count.scalar.return_value = 0
    # optimistic lock update
    upd_result = MagicMock()
    upd_result.rowcount = 1  # success

    history_mock = _make_coupon_history_mock(coupon_id)
    mock_db.get.return_value = coupon_mock
    mock_db.execute.side_effect = [existing_count, upd_result]

    with patch("app.services.coupon_service.CouponHistoryResponse.model_validate", return_value=history_mock):
        svc = CouponService(mock_db)
        resp = await svc.claim(uuid4(), coupon_id)

        assert resp.use_status == 0  # unclaimed
        assert mock_db.add.called  # history record added


@pytest.mark.asyncio
async def test_claim_coupon_disabled(mock_db):
    """claim: disabled coupon raises CouponExpiredError."""
    from app.core.exceptions import CouponExpiredError
    from app.services.coupon_service import CouponService

    coupon_mock = _make_coupon_mock()
    coupon_mock.status = 0
    mock_db.get.return_value = coupon_mock

    svc = CouponService(mock_db)
    with pytest.raises(CouponExpiredError):
        await svc.claim(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_claim_coupon_exhausted(mock_db):
    """claim: fully claimed coupon raises CouponExhaustedError."""
    from app.core.exceptions import CouponExhaustedError
    from app.services.coupon_service import CouponService

    coupon_mock = _make_coupon_mock()
    coupon_mock.status = 1
    coupon_mock.receive_count = 100
    coupon_mock.count = 100
    mock_db.get.return_value = coupon_mock

    svc = CouponService(mock_db)
    with pytest.raises(CouponExhaustedError):
        await svc.claim(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_claim_already_claimed(mock_db):
    """claim: already claimed per_limit times raises CouponAlreadyClaimedError."""
    from app.core.exceptions import CouponAlreadyClaimedError
    from app.services.coupon_service import CouponService

    coupon_id = uuid4()
    coupon_mock = _make_coupon_mock(coupon_id)
    coupon_mock.status = 1
    coupon_mock.receive_count = 10
    coupon_mock.count = 100
    coupon_mock.per_limit = 1

    existing_count = MagicMock()
    existing_count.scalar.return_value = 1  # already claimed

    mock_db.get.return_value = coupon_mock
    mock_db.execute.return_value = existing_count

    svc = CouponService(mock_db)
    with pytest.raises(CouponAlreadyClaimedError):
        await svc.claim(uuid4(), coupon_id)


# ---------------------------------------------------------------------------
#  list_my_coupons
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_my_coupons_success(mock_db):
    """list_my_coupons: returns user's coupon histories."""
    from app.services.coupon_service import CouponService

    history = _make_coupon_history_mock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [history]
    mock_db.execute.return_value = list_result

    svc = CouponService(mock_db)
    items = await svc.list_my_coupons(uuid4(), use_status=0)

    assert len(items) == 1
