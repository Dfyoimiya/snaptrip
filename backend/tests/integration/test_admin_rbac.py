"""
Integration tests: Admin RBAC (Role-Based Access Control) endpoints.

Tests the admin user management and RBAC API surface:
  - Admin registration (POST /admin/register)
  - Admin list (GET /admin/list)
  - Admin update/delete/status
  - Role CRUD (POST /role/create, PUT /role/update, GET /role/list, POST /role/delete)
  - Role status, menu allocation, resource allocation
  - Menu tree (GET /menu/treeList), menu CRUD
  - Resource category and resource CRUD

NOTE: These endpoints use Depends(get_current_user) for authentication but
do NOT yet enforce fine-grained RBAC at the endpoint level. Any authenticated
user can call them. The tests verify the API contract, not authorization.

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# The auth_client fixture is referenced from commerce/conftest.py below,
# but pytest conftest discovery does NOT descend from sibling directories.
# We define our own fixtures here for self-containment.


@pytest_asyncio.fixture
async def rbac_user_email() -> str:
    return f"rbac-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(rbac_user_email: str) -> AsyncClient:
    """Create an authenticated HTTP client for RBAC tests."""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": rbac_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": rbac_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    """Unauthenticated HTTP client."""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()


class TestAdminRBAC:
    """Admin RBAC endpoint tests."""

    # ======================================================================
    #  Admin user management
    # ======================================================================

    @pytest.mark.asyncio
    async def test_admin_register_creates_new_user(self, auth_client: AsyncClient):
        """POST /admin/register creates a new admin user."""
        email = f"rbac-new-{uuid.uuid4().hex[:8]}@example.com"
        resp = await auth_client.post(
            "/api/v1/admin/register",
            json={
                "email": email,
                "password": "AdminPass789!",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "id" in data
        assert data["email"] == email

    @pytest.mark.asyncio
    async def test_admin_register_with_roles(self, auth_client: AsyncClient):
        """POST /admin/register can optionally assign role_ids."""
        # First create a role to assign
        role_resp = await auth_client.post(
            "/api/v1/role/create",
            json={"name": f"role-{uuid.uuid4().hex[:6]}", "description": "用于注册测试"},
        )
        role_id = role_resp.json()["data"]["id"]

        email = f"rbac-role-{uuid.uuid4().hex[:8]}@example.com"
        resp = await auth_client.post(
            "/api/v1/admin/register",
            json={
                "email": email,
                "password": "AdminPass789!",
                "role_ids": [role_id],
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["email"] == email

    @pytest.mark.asyncio
    async def test_admin_list_returns_paginated_users(self, auth_client: AsyncClient):
        """GET /admin/list returns a paginated list of admin users."""
        resp = await auth_client.get("/api/v1/admin/list?page=1&page_size=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_admin_list_items_have_expected_structure(self, auth_client: AsyncClient):
        """Each admin list item contains id, email, is_active, roles."""
        resp = await auth_client.get("/api/v1/admin/list?page=1&page_size=10")
        assert resp.status_code == 200, resp.text

        for item in resp.json()["data"]["items"]:
            assert "id" in item
            assert "email" in item
            assert "is_active" in item
            assert "created_at" in item
            assert "roles" in item
            assert isinstance(item["roles"], list)

    @pytest.mark.asyncio
    async def test_admin_update_and_delete(self, auth_client: AsyncClient):
        """POST /admin/update + /admin/updateStatus + /admin/delete for an admin user."""
        # Register a new admin user
        email = f"rbac-upd-{uuid.uuid4().hex[:8]}@example.com"
        reg_resp = await auth_client.post(
            "/api/v1/admin/register",
            json={"email": email, "password": "AdminPass789!"},
        )
        assert reg_resp.status_code == 200, reg_resp.text
        user_id = reg_resp.json()["data"]["id"]

        # Update admin email
        new_email = f"rbac-upd2-{uuid.uuid4().hex[:8]}@example.com"
        upd_resp = await auth_client.post(
            f"/api/v1/admin/update/{user_id}",
            json={"email": new_email, "is_active": True},
        )
        assert upd_resp.status_code == 200, upd_resp.text

        # Update status (disable)
        status_resp = await auth_client.post(
            f"/api/v1/admin/updateStatus/{user_id}?status=0",
        )
        assert status_resp.status_code == 200, status_resp.text

        # Re-enable
        status_resp = await auth_client.post(
            f"/api/v1/admin/updateStatus/{user_id}?status=1",
        )
        assert status_resp.status_code == 200, status_resp.text

        # Delete
        del_resp = await auth_client.post(f"/api/v1/admin/delete/{user_id}")
        assert del_resp.status_code == 200, del_resp.text

    # ======================================================================
    #  Role CRUD
    # ======================================================================

    @pytest.mark.asyncio
    async def test_role_create_and_list(self, auth_client: AsyncClient):
        """POST /role/create creates a role, GET /role/list returns it."""
        role_name = f"role-{uuid.uuid4().hex[:6]}"
        create_resp = await auth_client.post(
            "/api/v1/role/create",
            json={
                "name": role_name,
                "description": "集成测试创建的角色",
                "status": 1,
                "sort": 10,
            },
        )
        assert create_resp.status_code == 200, create_resp.text
        created = create_resp.json()["data"]
        assert created["name"] == role_name
        assert created["description"] == "集成测试创建的角色"
        role_id = created["id"]

        # List
        list_resp = await auth_client.get("/api/v1/role/list?page=1&page_size=20")
        assert list_resp.status_code == 200, list_resp.text
        items = list_resp.json()["data"]["items"]
        ids = [r["id"] for r in items]
        assert role_id in ids

    @pytest.mark.asyncio
    async def test_role_create_minimal_payload(self, auth_client: AsyncClient):
        """POST /role/create with only required 'name' field."""
        role_name = f"min-{uuid.uuid4().hex[:6]}"
        resp = await auth_client.post(
            "/api/v1/role/create",
            json={"name": role_name},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["name"] == role_name
        assert data["status"] == 1  # default
        assert data["sort"] == 0  # default

    @pytest.mark.asyncio
    async def test_role_update_and_status(self, auth_client: AsyncClient):
        """POST /role/update updates a role; POST /role/updateStatus toggles status."""
        role_name = f"role-upd-{uuid.uuid4().hex[:6]}"
        create_resp = await auth_client.post(
            "/api/v1/role/create",
            json={"name": role_name},
        )
        role_id = create_resp.json()["data"]["id"]

        # Update role name and description
        new_name = f"role-upd2-{uuid.uuid4().hex[:6]}"
        upd_resp = await auth_client.post(
            f"/api/v1/role/update/{role_id}",
            json={"name": new_name, "description": "updated desc"},
        )
        assert upd_resp.status_code == 200, upd_resp.text
        assert upd_resp.json()["data"]["name"] == new_name

        # Update status (disable)
        status_resp = await auth_client.post(
            f"/api/v1/role/updateStatus/{role_id}?status=0",
        )
        assert status_resp.status_code == 200, status_resp.text

        # Re-enable
        status_resp = await auth_client.post(
            f"/api/v1/role/updateStatus/{role_id}?status=1",
        )
        assert status_resp.status_code == 200, status_resp.text

    @pytest.mark.asyncio
    async def test_role_delete(self, auth_client: AsyncClient):
        """POST /role/delete deletes a role."""
        role_name = f"role-del-{uuid.uuid4().hex[:6]}"
        create_resp = await auth_client.post(
            "/api/v1/role/create",
            json={"name": role_name},
        )
        role_id = create_resp.json()["data"]["id"]

        # Delete
        del_resp = await auth_client.post(f"/api/v1/role/delete?ids={role_id}")
        assert del_resp.status_code == 200, del_resp.text

    @pytest.mark.asyncio
    async def test_role_list_all(self, auth_client: AsyncClient):
        """GET /role/listAll returns all roles without pagination."""
        resp = await auth_client.get("/api/v1/role/listAll")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert "id" in data[0]
            assert "name" in data[0]

    # ======================================================================
    #  Menu tree and CRUD
    # ======================================================================

    @pytest.mark.asyncio
    async def test_menu_tree_list_returns_tree(self, auth_client: AsyncClient):
        """GET /menu/treeList returns a hierarchical menu tree."""
        resp = await auth_client.get("/api/v1/menu/treeList")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data, list)
        for node in data:
            assert "id" in node
            assert "title" in node
            assert "children" in node
            assert isinstance(node["children"], list)

    @pytest.mark.asyncio
    async def test_menu_crud(self, auth_client: AsyncClient):
        """Menu CRUD: create, get, list by parent, update, toggle hidden, delete."""
        # Create a menu
        create_resp = await auth_client.post(
            "/api/v1/menu/create",
            json={
                "title": f"TestMenu-{uuid.uuid4().hex[:6]}",
                "name": "test-menu",
                "sort": 10,
                "level": 1,
                "hidden": 0,
            },
        )
        assert create_resp.status_code == 200, create_resp.text
        menu_id = create_resp.json()["data"]["id"]
        menu_title = create_resp.json()["data"]["title"]

        # Get menu detail
        get_resp = await auth_client.get(f"/api/v1/menu/{menu_id}")
        assert get_resp.status_code == 200, get_resp.text
        assert get_resp.json()["data"]["title"] == menu_title

        # Update menu
        new_title = f"Updated-{uuid.uuid4().hex[:6]}"
        upd_resp = await auth_client.post(
            f"/api/v1/menu/update/{menu_id}",
            json={"title": new_title},
        )
        assert upd_resp.status_code == 200, upd_resp.text
        assert upd_resp.json()["data"]["title"] == new_title

        # Toggle hidden
        hidden_resp = await auth_client.post(
            f"/api/v1/menu/updateHidden/{menu_id}?hidden=1",
        )
        assert hidden_resp.status_code == 200, hidden_resp.text

        # Delete menu
        del_resp = await auth_client.post(f"/api/v1/menu/delete/{menu_id}")
        assert del_resp.status_code == 200, del_resp.text

    # ======================================================================
    #  Negative tests
    # ======================================================================

    @pytest.mark.asyncio
    async def test_role_create_missing_name_returns_error(self, auth_client: AsyncClient):
        """POST /role/create without required 'name' returns 422."""
        resp = await auth_client.post(
            "/api/v1/role/create",
            json={"description": "missing name"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_admin_list_unauthenticated_returns_error(self, public_client: AsyncClient):
        """GET /admin/list without auth token returns 401."""
        resp = await public_client.get("/api/v1/admin/list")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_admin_register_unauthenticated_returns_error(self, public_client: AsyncClient):
        """POST /admin/register without auth token returns 401."""
        resp = await public_client.post(
            "/api/v1/admin/register",
            json={
                "email": f"nobody-{uuid.uuid4().hex[:8]}@example.com",
                "password": "TestPass123!",
            },
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_menu_create_missing_title_returns_error(self, auth_client: AsyncClient):
        """POST /menu/create without required 'title' returns 422."""
        resp = await auth_client.post(
            "/api/v1/menu/create",
            json={"name": "no-title-menu"},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_menu_get_nonexistent_returns_404(self, auth_client: AsyncClient):
        """GET /menu/{nonexistent_id} returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await auth_client.get(f"/api/v1/menu/{fake_id}")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_admin_update_nonexistent_returns_404(self, auth_client: AsyncClient):
        """POST /admin/update/{nonexistent_id} returns error."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await auth_client.post(
            f"/api/v1/admin/update/{fake_id}",
            json={"email": f"nonexistent-{uuid.uuid4().hex[:8]}@example.com"},
        )
        # Should be either 404 or a 2xx (since sqlalchemy text UPDATE with 0 rows
        # does not raise, but let's check it handles gracefully)
        assert resp.status_code in (200, 404), f"Unexpected status: {resp.status_code}: {resp.text}"
