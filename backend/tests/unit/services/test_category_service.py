"""Unit tests for CategoryService.

Tests cover CRUD, list_paginated, get_tree, toggle_status.
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


def _make_category_mock(cat_id: UUID | None = None, parent_id: UUID | None = None) -> MagicMock:
    cid = cat_id or uuid4()
    c = MagicMock()
    c.id = cid
    c.name = "Test Category"
    c.parent_id = parent_id
    c.level = 0
    c.sort = 0
    c.nav_status = 1
    c.show_status = 1
    c.icon = None
    c.keywords = None
    c.description = None
    c.created_at = None
    c.updated_at = None
    c.children = []
    return c


# ---------------------------------------------------------------------------
#  create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_success(mock_db):
    """create: creates category and returns CategoryResponse."""
    from app.schemas.product import CategoryCreate
    from app.services.category_service import CategoryService

    svc = CategoryService(mock_db)
    data = CategoryCreate(name="Electronics", sort=10)
    resp = await svc.create(data)

    assert mock_db.add.called
    assert resp.name == "Electronics"


@pytest.mark.asyncio
async def test_create_subcategory(mock_db):
    """create: subcategory with parent_id is created."""
    from app.schemas.product import CategoryCreate
    from app.services.category_service import CategoryService

    parent_id = uuid4()
    svc = CategoryService(mock_db)
    data = CategoryCreate(name="Phones", parent_id=parent_id, level=1)
    resp = await svc.create(data)

    assert mock_db.add.called
    assert resp.name == "Phones"


# ---------------------------------------------------------------------------
#  update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_success(mock_db):
    """update: updates category via update().returning()."""
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    cat_id = uuid4()
    cat_mock = _make_category_mock(cat_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = cat_mock
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    data = CategoryUpdate(name="Updated Category")
    resp = await svc.update(cat_id, data)

    assert resp.id == cat_id
    assert resp.name == "Test Category"


@pytest.mark.asyncio
async def test_update_not_found(mock_db):
    """update: missing category raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.update(uuid4(), CategoryUpdate(name="X"))


@pytest.mark.asyncio
async def test_update_empty_data_raises(mock_db):
    """update: empty CategoryUpdate raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    svc = CategoryService(mock_db)
    with pytest.raises(CommerceException) as exc:
        await svc.update(uuid4(), CategoryUpdate())
    assert exc.value.code == "NO_FIELDS"


# ---------------------------------------------------------------------------
#  delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success(mock_db):
    """delete: removes category when found."""
    from app.services.category_service import CategoryService

    cat_mock = _make_category_mock()
    mock_db.get.return_value = cat_mock

    svc = CategoryService(mock_db)
    await svc.delete(uuid4())
    assert mock_db.delete.called


@pytest.mark.asyncio
async def test_delete_not_found(mock_db):
    """delete: missing category raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.category_service import CategoryService

    mock_db.get.return_value = None
    svc = CategoryService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.delete(uuid4())


# ---------------------------------------------------------------------------
#  get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_by_id_success(mock_db):
    """get_by_id: returns CategoryResponse when found."""
    from app.services.category_service import CategoryService

    cat_mock = _make_category_mock()
    mock_db.get.return_value = cat_mock

    svc = CategoryService(mock_db)
    resp = await svc.get_by_id(uuid4())
    assert resp.id == cat_mock.id


@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_db):
    """get_by_id: missing category raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.category_service import CategoryService

    mock_db.get.return_value = None
    svc = CategoryService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.get_by_id(uuid4())


# ---------------------------------------------------------------------------
#  list_paginated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_paginated_success(mock_db):
    """list_paginated: returns paginated categories with total."""
    from app.services.category_service import CategoryService

    cat_mock = _make_category_mock()
    count_result = MagicMock()
    count_result.scalar.return_value = 3
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = [cat_mock]

    mock_db.execute.side_effect = [count_result, list_result]

    svc = CategoryService(mock_db)
    items, total = await svc.list_paginated(page=1, page_size=20)

    assert total == 3
    assert len(items) == 1


# ---------------------------------------------------------------------------
#  get_tree
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tree_success(mock_db):
    """get_tree: returns category tree structure."""
    from app.services.category_service import CategoryService

    root_cat = _make_category_mock()
    child_cat = _make_category_mock(parent_id=root_cat.id)
    child_cat.level = 1
    root_cat.children = [child_cat]

    tree_result = MagicMock()
    tree_result.unique.return_value.scalars.return_value.all.return_value = [root_cat]
    mock_db.execute.return_value = tree_result

    svc = CategoryService(mock_db)
    tree = await svc.get_tree()

    assert len(tree) == 1
    assert len(tree[0].children) == 1
    assert tree[0].children[0].id == child_cat.id


@pytest.mark.asyncio
async def test_get_tree_empty(mock_db):
    """get_tree: returns empty list when no categories."""
    from app.services.category_service import CategoryService

    tree_result = MagicMock()
    tree_result.unique.return_value.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = tree_result

    svc = CategoryService(mock_db)
    tree = await svc.get_tree()

    assert len(tree) == 0


# ---------------------------------------------------------------------------
#  toggle_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_status_success(mock_db):
    """toggle_status: toggles show_status and returns CategoryResponse."""
    from app.services.category_service import CategoryService

    cat_id = uuid4()
    cat_mock = _make_category_mock(cat_id)
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = cat_mock
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    resp = await svc.toggle_status(cat_id, "show_status", 0)

    assert resp.id == cat_id


@pytest.mark.asyncio
async def test_toggle_status_not_found(mock_db):
    """toggle_status: missing category raises ProductNotFoundError."""
    from app.core.exceptions import ProductNotFoundError
    from app.services.category_service import CategoryService

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    with pytest.raises(ProductNotFoundError):
        await svc.toggle_status(uuid4(), "nav_status", 0)
