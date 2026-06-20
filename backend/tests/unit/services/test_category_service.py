"""Unit tests for CategoryService.

Tests cover CRUD, list_paginated, get_tree, toggle_status.
All DB interactions are mocked.

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest


def _make_category_mock(cat_id: UUID | None = None, parent_id: UUID | None = None) -> MagicMock:
    cid = cat_id or uuid4()
    c = MagicMock()
    c.id = cid
    c.name = "Test Category"
    c.parent_id = parent_id
    c.level = 0
    c.sort = 0
    c.type = None
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

    # mock_db.execute is called for max sort query (coalesce returns -1 for empty set)
    sort_result = MagicMock()
    sort_result.scalar.return_value = -1
    mock_db.execute.return_value = sort_result

    svc = CategoryService(mock_db)
    data = CategoryCreate(name="Electronics")
    resp = await svc.create(data)

    assert mock_db.add.called
    assert resp.name == "Electronics"
    assert resp.sort == 0  # auto-computed: coalesce(-1) + 1 = 0 (first item)


@pytest.mark.asyncio
async def test_create_subcategory(mock_db):
    """create: subcategory with parent_id auto-computes level from parent."""
    from app.schemas.product import CategoryCreate
    from app.services.category_service import CategoryService

    parent_id = uuid4()
    parent_mock = _make_category_mock(parent_id, parent_id=None)
    parent_mock.level = 0
    mock_db.get.return_value = parent_mock

    sort_result = MagicMock()
    sort_result.scalar.return_value = 3
    mock_db.execute.return_value = sort_result

    svc = CategoryService(mock_db)
    data = CategoryCreate(name="Phones", parent_id=parent_id)
    resp = await svc.create(data)

    assert mock_db.add.called
    assert resp.name == "Phones"
    assert resp.level == 1  # auto-computed from parent
    assert resp.sort == 4   # auto-computed: max_sibling(3) + 1


@pytest.mark.asyncio
async def test_create_subcategory_parent_not_found(mock_db):
    """create: missing parent raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import CategoryCreate
    from app.services.category_service import CategoryService

    mock_db.get.return_value = None
    svc = CategoryService(mock_db)
    data = CategoryCreate(name="Phones", parent_id=uuid4())

    with pytest.raises(CommerceException) as exc:
        await svc.create(data)
    assert exc.value.code == "PARENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_subcategory_level_exceeded(mock_db):
    """create: cannot create subcategory deeper than level 2."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import CategoryCreate
    from app.services.category_service import CategoryService

    # Level 2 parent → child would be level 3 → rejected
    parent_id = uuid4()
    parent_mock = _make_category_mock(parent_id, parent_id=None)
    parent_mock.level = 2
    mock_db.get.return_value = parent_mock

    svc = CategoryService(mock_db)
    data = CategoryCreate(name="TooDeep", parent_id=parent_id)

    with pytest.raises(CommerceException) as exc:
        await svc.create(data)
    assert exc.value.code == "CATEGORY_LEVEL_EXCEEDED"


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


@pytest.mark.asyncio
async def test_update_change_parent_success(mock_db):
    """update: moving to new parent recalculates level."""
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    cat_id = uuid4()
    new_parent_id = uuid4()
    parent_mock = _make_category_mock(new_parent_id, parent_id=None)
    parent_mock.level = 0

    # First call: get parent; second: update returning
    updated_mock = _make_category_mock(cat_id, parent_id=new_parent_id)
    updated_mock.level = 1
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = updated_mock
    # side_effect for mock_db.get and mock_db.execute
    mock_db.get.return_value = parent_mock
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    data = CategoryUpdate(parent_id=new_parent_id)
    resp = await svc.update(cat_id, data)

    assert resp.id == cat_id
    assert resp.level == 1
    assert resp.parent_id == new_parent_id


@pytest.mark.asyncio
async def test_update_self_parent_raises(mock_db):
    """update: setting self as parent raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    cat_id = uuid4()
    svc = CategoryService(mock_db)
    data = CategoryUpdate(parent_id=cat_id)

    with pytest.raises(CommerceException) as exc:
        await svc.update(cat_id, data)
    assert exc.value.code == "CATEGORY_SELF_PARENT"


@pytest.mark.asyncio
async def test_update_parent_not_found(mock_db):
    """update: moving to non-existent parent raises CommerceException."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    mock_db.get.return_value = None
    svc = CategoryService(mock_db)
    data = CategoryUpdate(parent_id=uuid4())

    with pytest.raises(CommerceException) as exc:
        await svc.update(uuid4(), data)
    assert exc.value.code == "PARENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_level_exceeded(mock_db):
    """update: moving to a level-2 parent raises CommerceException (would create level 3)."""
    from app.core.exceptions import CommerceException
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    parent_id = uuid4()
    parent_mock = _make_category_mock(parent_id, parent_id=None)
    parent_mock.level = 2
    mock_db.get.return_value = parent_mock

    svc = CategoryService(mock_db)
    data = CategoryUpdate(parent_id=parent_id)

    with pytest.raises(CommerceException) as exc:
        await svc.update(uuid4(), data)
    assert exc.value.code == "CATEGORY_LEVEL_EXCEEDED"


@pytest.mark.asyncio
async def test_update_set_parent_null_resets_level(mock_db):
    """update: removing parent (parent_id=None) resets level to 0."""
    from app.schemas.product import CategoryUpdate
    from app.services.category_service import CategoryService

    cat_id = uuid4()
    updated_mock = _make_category_mock(cat_id, parent_id=None)
    updated_mock.level = 0
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = updated_mock
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    data = CategoryUpdate(parent_id=None)
    resp = await svc.update(cat_id, data)

    assert resp.level == 0
    assert resp.parent_id is None


# ---------------------------------------------------------------------------
#  delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_success(mock_db):
    """delete: removes category when found."""
    from app.services.category_service import CategoryService

    cat_mock = _make_category_mock()
    mock_db.get.return_value = cat_mock

    # mock_db.execute is called twice: once for child count, once for product count
    child_count_result = MagicMock()
    child_count_result.scalar.return_value = 0
    product_count_result = MagicMock()
    product_count_result.scalar.return_value = 0
    mock_db.execute.side_effect = [child_count_result, product_count_result]

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


@pytest.mark.asyncio
async def test_list_paginated_empty(mock_db):
    """list_paginated: returns empty list with zero total."""
    from app.services.category_service import CategoryService

    count_result = MagicMock()
    count_result.scalar.return_value = 0
    list_result = MagicMock()
    list_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [count_result, list_result]

    svc = CategoryService(mock_db)
    items, total = await svc.list_paginated(page=1, page_size=20)

    assert total == 0
    assert len(items) == 0


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
    tree_result.scalars.return_value.all.return_value = [root_cat, child_cat]
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
    tree_result.scalars.return_value.all.return_value = []
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
    cat_mock.show_status = 0  # toggled from 1 to 0
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = cat_mock
    mock_db.execute.return_value = exec_result

    svc = CategoryService(mock_db)
    resp = await svc.toggle_status(cat_id, "show_status", 0)

    assert resp.id == cat_id
    assert resp.show_status == 0  # verify the toggle was applied


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


# ---------------------------------------------------------------------------
#  reorder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_success(mock_db):
    """reorder: batch updates sort values for multiple categories."""
    from app.services.category_service import CategoryService

    cat1_id = uuid4()
    cat2_id = uuid4()
    cat1 = _make_category_mock(cat1_id)
    cat1.sort = 0
    cat2 = _make_category_mock(cat2_id)
    cat2.sort = 1

    exec1 = MagicMock()
    exec1.scalar_one_or_none.return_value = cat1
    exec2 = MagicMock()
    exec2.scalar_one_or_none.return_value = cat2
    mock_db.execute.side_effect = [exec1, exec2]

    svc = CategoryService(mock_db)
    items = [
        {"id": str(cat1_id), "sort": 0},
        {"id": str(cat2_id), "sort": 1},
    ]
    results = await svc.reorder(items)

    assert len(results) == 2
    assert results[0].sort == 0
    assert results[1].sort == 1
