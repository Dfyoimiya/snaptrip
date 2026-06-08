"""Unit tests for CmsService.

Tests cover Banner, Subject, and Help CRUD operations.
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


def _make_banner_mock(banner_id: UUID | None = None) -> MagicMock:
    bid = banner_id or uuid4()
    b = MagicMock()
    b.id = bid
    b.title = "Test Banner"
    b.pic = "banner.jpg"
    b.url = "http://example.com"
    b.sort = 0
    b.status = 1
    b.start_time = None
    b.end_time = None
    b.created_at = None
    return b


def _make_subject_mock(subject_id: UUID | None = None) -> MagicMock:
    sid = subject_id or uuid4()
    s = MagicMock()
    s.id = sid
    s.title = "Test Subject"
    s.summary = "Summary"
    s.pic = "pic.jpg"
    s.content = "<p>Content</p>"
    s.category_name = "News"
    s.status = 1
    s.recommend_status = 0
    s.created_at = None
    return s


def _make_help_mock(help_id: UUID | None = None) -> MagicMock:
    hid = help_id or uuid4()
    h = MagicMock()
    h.id = hid
    h.title = "Test Help"
    h.content = "Help content"
    h.category_name = "Shopping Guide"
    h.status = 1
    h.sort = 0
    h.created_at = None
    return h


# ===========================================================================
#  Banner tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_banner_success(mock_db):
    """create_banner: creates banner and returns BannerResponse."""
    from app.schemas.cms import BannerCreate
    from app.services.cms_service import CmsService

    svc = CmsService(mock_db)
    data = BannerCreate(title="New Banner", pic="banner.jpg")
    resp = await svc.create_banner(data)

    assert mock_db.add.called
    assert resp.title == "New Banner"


@pytest.mark.asyncio
async def test_update_banner_success(mock_db):
    """update_banner: updates banner via returning()."""
    from app.schemas.cms import BannerUpdate
    from app.services.cms_service import CmsService

    banner_id = uuid4()
    banner_mock = _make_banner_mock(banner_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = banner_mock
    mock_db.execute.return_value = exec_result

    svc = CmsService(mock_db)
    data = BannerUpdate(title="Updated Banner")
    resp = await svc.update_banner(banner_id, data)

    assert resp.id == banner_id


@pytest.mark.asyncio
async def test_update_banner_not_found(mock_db):
    """update_banner: missing banner raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.cms import BannerUpdate
    from app.services.cms_service import CmsService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CmsService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_banner(uuid4(), BannerUpdate(title="X"))


@pytest.mark.asyncio
async def test_update_banner_empty_data_raises(mock_db):
    """update_banner: empty BannerUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.cms import BannerUpdate
    from app.services.cms_service import CmsService

    svc = CmsService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update_banner(uuid4(), BannerUpdate())
    assert exc.value.code == "NO_FIELDS"


@pytest.mark.asyncio
async def test_delete_banner_success(mock_db):
    """delete_banner: removes banner when found."""
    from app.services.cms_service import CmsService

    banner_mock = _make_banner_mock()
    mock_db.get.return_value = banner_mock

    svc = CmsService(mock_db)
    await svc.delete_banner(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_banner_not_found(mock_db):
    """delete_banner: missing banner raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.cms_service import CmsService

    mock_db.get.return_value = None
    svc = CmsService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_banner(uuid4())


@pytest.mark.asyncio
async def test_list_banners_success(mock_db):
    """list_banners: returns all banners."""
    from app.services.cms_service import CmsService

    banner_mock = _make_banner_mock()
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [banner_mock]
    mock_db.execute.return_value = list_result

    svc = CmsService(mock_db)
    items = await svc.list_banners()

    assert len(items) == 1


# ===========================================================================
#  Subject tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_subject_success(mock_db):
    """create_subject: creates subject and returns SubjectResponse."""
    from app.schemas.cms import SubjectCreate
    from app.services.cms_service import CmsService

    svc = CmsService(mock_db)
    data = SubjectCreate(title="New Subject")
    resp = await svc.create_subject(data)

    assert mock_db.add.called
    assert resp.title == "New Subject"


@pytest.mark.asyncio
async def test_update_subject_success(mock_db):
    """update_subject: updates subject via returning()."""
    from app.schemas.cms import SubjectUpdate
    from app.services.cms_service import CmsService

    subject_id = uuid4()
    subject_mock = _make_subject_mock(subject_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = subject_mock
    mock_db.execute.return_value = exec_result

    svc = CmsService(mock_db)
    resp = await svc.update_subject(subject_id, SubjectUpdate(title="Updated"))
    assert resp.id == subject_id


@pytest.mark.asyncio
async def test_update_subject_not_found(mock_db):
    """update_subject: missing subject raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.cms import SubjectUpdate
    from app.services.cms_service import CmsService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CmsService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_subject(uuid4(), SubjectUpdate(title="X"))


@pytest.mark.asyncio
async def test_delete_subject_success(mock_db):
    """delete_subject: removes subject when found."""
    from app.services.cms_service import CmsService

    subject_mock = _make_subject_mock()
    mock_db.get.return_value = subject_mock

    svc = CmsService(mock_db)
    await svc.delete_subject(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_subject_not_found(mock_db):
    """delete_subject: missing subject raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.cms_service import CmsService

    mock_db.get.return_value = None
    svc = CmsService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_subject(uuid4())


# ===========================================================================
#  Help tests
# ===========================================================================


@pytest.mark.asyncio
async def test_create_help_success(mock_db):
    """create_help: creates help entry and returns HelpResponse."""
    from app.schemas.cms import HelpCreate
    from app.services.cms_service import CmsService

    svc = CmsService(mock_db)
    data = HelpCreate(title="How to return items")
    resp = await svc.create_help(data)

    assert mock_db.add.called
    assert resp.title == "How to return items"


@pytest.mark.asyncio
async def test_update_help_success(mock_db):
    """update_help: updates help via returning()."""
    from app.schemas.cms import HelpUpdate
    from app.services.cms_service import CmsService

    help_id = uuid4()
    help_mock = _make_help_mock(help_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = help_mock
    mock_db.execute.return_value = exec_result

    svc = CmsService(mock_db)
    resp = await svc.update_help(help_id, HelpUpdate(title="Updated Help"))
    assert resp.id == help_id


@pytest.mark.asyncio
async def test_update_help_not_found(mock_db):
    """update_help: missing help raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.cms import HelpUpdate
    from app.services.cms_service import CmsService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CmsService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update_help(uuid4(), HelpUpdate(title="X"))


@pytest.mark.asyncio
async def test_delete_help_success(mock_db):
    """delete_help: removes help entry when found."""
    from app.services.cms_service import CmsService

    help_mock = _make_help_mock()
    mock_db.get.return_value = help_mock

    svc = CmsService(mock_db)
    await svc.delete_help(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_help_not_found(mock_db):
    """delete_help: missing help raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.cms_service import CmsService

    mock_db.get.return_value = None
    svc = CmsService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete_help(uuid4())
