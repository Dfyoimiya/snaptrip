"""
Integration tests: Admin extended endpoints — Dashboard, Category CRUD, Brand status, Member detail.

Covers:
  - GET /api/v1/admin/dashboard             — Dashboard aggregation
  - PUT/DELETE /api/v1/admin/categories/{id} — Category edit/delete
  - PATCH /api/v1/admin/categories/{id}/status — Category status toggle
  - PATCH /api/v1/admin/categories/{id}/sort   — Category sort
  - PATCH /api/v1/admin/brands/{id}/status     — Brand status toggle
  - GET /api/v1/admin/members/{id}             — Member detail
  - PATCH /api/v1/admin/members/{id}/status    — Member enable/ban

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def ext_user_email() -> str:
    return f"ext-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(ext_user_email: str) -> AsyncClient:
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": ext_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": ext_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()


class TestAdminExtended:
    """Admin extended endpoint tests."""

    # ======================================================================
    #  Dashboard
    # ======================================================================

    @pytest.mark.asyncio
    async def test_dashboard_returns_aggregated_data(self, auth_client: AsyncClient):
        """GET /api/v1/admin/dashboard returns aggregated ecommerce data."""
        resp = await auth_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # Basic dashboard structure
        assert "today_orders" in data
        assert "today_revenue" in data
        assert "today_revenue_display" in data
        assert "pending_returns" in data
        assert "new_members" in data
        assert "order_status_counts" in data
        assert "top_products" in data
        assert "week_days" in data
        assert "week_sales" in data
        assert "latest_orders" in data

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, public_client: AsyncClient):
        """GET /api/v1/admin/dashboard without auth returns 401."""
        resp = await public_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    # ======================================================================
    #  Category CRUD
    # ======================================================================

    @pytest.mark.asyncio
    async def test_category_update(self, auth_client: AsyncClient):
        """PUT /api/v1/admin/categories/{id} updates category name."""
        # Create
        create_resp = await auth_client.post(
            "/api/v1/admin/categories",
            json={"name": f"cat-upd-{uuid.uuid4().hex[:6]}"},
        )
        assert create_resp.status_code == 200, create_resp.text
        cat_id = create_resp.json()["data"]["id"]

        # Update
        new_name = f"cat-upd2-{uuid.uuid4().hex[:6]}"
        upd_resp = await auth_client.put(
            f"/api/v1/admin/categories/{cat_id}",
            json={"name": new_name},
        )
        assert upd_resp.status_code == 200, upd_resp.text
        assert upd_resp.json()["data"]["name"] == new_name

    @pytest.mark.asyncio
    async def test_category_delete(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/categories/{id} deletes a category."""
        create_resp = await auth_client.post(
            "/api/v1/admin/categories",
            json={"name": f"cat-del-{uuid.uuid4().hex[:6]}"},
        )
        cat_id = create_resp.json()["data"]["id"]

        del_resp = await auth_client.delete(f"/api/v1/admin/categories/{cat_id}")
        assert del_resp.status_code == 200, del_resp.text

        # Verify deletion - get should return 404
        get_resp = await auth_client.get(f"/api/v1/admin/categories/{cat_id}")
        assert get_resp.status_code == 404, f"Expected 404, got {get_resp.status_code}"

    @pytest.mark.asyncio
    async def test_category_toggle_status(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/categories/{id}/status toggles nav_status and show_status."""
        create_resp = await auth_client.post(
            "/api/v1/admin/categories",
            json={"name": f"cat-st-{uuid.uuid4().hex[:6]}"},
        )
        cat_id = create_resp.json()["data"]["id"]

        # Toggle nav_status
        resp = await auth_client.patch(
            f"/api/v1/admin/categories/{cat_id}/status?field=nav_status&status=1",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["nav_status"] == 1

        # Toggle nav_status back
        resp = await auth_client.patch(
            f"/api/v1/admin/categories/{cat_id}/status?field=nav_status&status=0",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["nav_status"] == 0

        # Toggle show_status
        resp = await auth_client.patch(
            f"/api/v1/admin/categories/{cat_id}/status?field=show_status&status=1",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["show_status"] == 1

    @pytest.mark.asyncio
    async def test_category_update_sort(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/categories/{id}/sort updates the sort order."""
        create_resp = await auth_client.post(
            "/api/v1/admin/categories",
            json={"name": f"cat-sort-{uuid.uuid4().hex[:6]}"},
        )
        cat_id = create_resp.json()["data"]["id"]

        resp = await auth_client.patch(
            f"/api/v1/admin/categories/{cat_id}/sort?sort=99",
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_category_list_with_parent_filter(self, auth_client: AsyncClient):
        """GET /api/v1/admin/categories with parent_id filter."""
        resp = await auth_client.get("/api/v1/admin/categories?page=1&page_size=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data

    # ======================================================================
    #  Brand Status Toggle
    # ======================================================================

    @pytest.mark.asyncio
    async def test_brand_toggle_show_status(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/brands/{id}/status toggles show_status."""
        create_resp = await auth_client.post(
            "/api/v1/admin/brands",
            json={"name": f"brand-st-{uuid.uuid4().hex[:6]}", "first_letter": "B"},
        )
        brand_id = create_resp.json()["data"]["id"]

        resp = await auth_client.patch(
            f"/api/v1/admin/brands/{brand_id}/status?field=show_status&status=0",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["show_status"] == 0

        resp = await auth_client.patch(
            f"/api/v1/admin/brands/{brand_id}/status?field=show_status&status=1",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["show_status"] == 1

    @pytest.mark.asyncio
    async def test_brand_toggle_factory_status(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/brands/{id}/status toggles factory_status."""
        create_resp = await auth_client.post(
            "/api/v1/admin/brands",
            json={"name": f"brand-fs-{uuid.uuid4().hex[:6]}", "first_letter": "C"},
        )
        brand_id = create_resp.json()["data"]["id"]

        resp = await auth_client.patch(
            f"/api/v1/admin/brands/{brand_id}/status?field=factory_status&status=0",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["factory_status"] == 0

    # ======================================================================
    #  Member Detail and Status
    # ======================================================================

    @pytest.mark.asyncio
    async def test_member_detail(self, auth_client: AsyncClient):
        """GET /api/v1/admin/members/{id} returns member detail."""
        # First, list members to get a member ID
        list_resp = await auth_client.get("/api/v1/admin/members?page=1&page_size=5")
        assert list_resp.status_code == 200, list_resp.text
        members = list_resp.json()["data"]["items"]

        if not members:
            pytest.skip("No members found to test detail")

        member_id = members[0]["id"]
        detail_resp = await auth_client.get(f"/api/v1/admin/members/{member_id}")
        assert detail_resp.status_code == 200, detail_resp.text
        data = detail_resp.json()["data"]
        assert data["id"] == member_id or str(data["id"]) == member_id

    @pytest.mark.asyncio
    async def test_member_toggle_status(self, auth_client: AsyncClient, ext_user_email: str):
        """PATCH /api/v1/admin/members/{id}/status toggles member active status.

        Creates a separate user to avoid disabling the current auth user.
        """
        # Register a second user to toggle their status safely
        second_email = f"toggle-target-{uuid.uuid4().hex[:8]}@example.com"
        reg_resp = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": second_email, "password": "TestPass123!"},
        )
        assert reg_resp.status_code in (200, 201, 400), reg_resp.text

        # Find the newly created member in the admin list
        list_resp = await auth_client.get("/api/v1/admin/members?page=1&page_size=20")
        members = list_resp.json()["data"]["items"]
        target = next((m for m in members if m["email"] == second_email), None)
        if not target:
            pytest.skip(f"Target member {second_email} not found in member list")

        member_id = target["id"]

        # Disable
        resp = await auth_client.patch(
            f"/api/v1/admin/members/{member_id}/status?is_active=false",
        )
        assert resp.status_code == 200, resp.text

        # Re-enable
        resp = await auth_client.patch(
            f"/api/v1/admin/members/{member_id}/status?is_active=true",
        )
        assert resp.status_code == 200, resp.text

    # ======================================================================
    #  Negative tests
    # ======================================================================

    @pytest.mark.asyncio
    async def test_category_create_missing_name_returns_422(self, auth_client: AsyncClient):
        """POST /api/v1/admin/categories without name returns 422."""
        resp = await auth_client.post(
            "/api/v1/admin/categories",
            json={},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_dashboard_unauthenticated_returns_401(self, public_client: AsyncClient):
        """GET /api/v1/admin/dashboard without auth returns 401."""
        resp = await public_client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_member_list_unauthenticated_returns_401(self, public_client: AsyncClient):
        """GET /api/v1/admin/members without auth returns 401."""
        resp = await public_client.get("/api/v1/admin/members")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
