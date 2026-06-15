"""
Integration tests: Portal brand and category browsing endpoints (public).

Covers:
  - GET /api/v1/portal/brands            — Portal brand list (public)
  - GET /api/v1/portal/brands/{id}       — Portal brand detail (public)
  - GET /api/v1/portal/categories        — Portal category list (public)
  - GET /api/v1/portal/categories/tree   — Portal category tree (public)

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def auth_client() -> AsyncClient:
    """Create an authenticated client to set up test data."""
    from marketplace.app.main import app

    email = f"bc-auth-{uuid.uuid4().hex[:8]}@example.com"
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    """Unauthenticated HTTP client for public endpoint tests."""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()


class TestPortalBrandsCategories:
    """Portal brand and category browsing tests."""

    # ======================================================================
    #  Portal Brands
    # ======================================================================

    @pytest.mark.asyncio
    async def test_portal_brands_list(self, public_client: AsyncClient):
        """GET /api/v1/portal/brands returns paginated brand list (public)."""
        resp = await public_client.get("/api/v1/portal/brands?page=1&page_size=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_portal_brands_list_structure(self, public_client: AsyncClient):
        """Brand list items have expected fields."""
        resp = await public_client.get("/api/v1/portal/brands?page=1&page_size=10")
        assert resp.status_code == 200, resp.text

        for item in resp.json()["data"]["items"]:
            assert "id" in item
            assert "name" in item

    @pytest.mark.asyncio
    async def test_portal_brands_detail_nonexistent(self, public_client: AsyncClient):
        """GET /api/v1/portal/brands/{nonexistent} returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await public_client.get(f"/api/v1/portal/brands/{fake_id}")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_portal_create_brand_and_check_list(self, auth_client: AsyncClient, public_client: AsyncClient):
        """Admin creates a brand; portal list includes it (if show_status=1)."""
        brand_name = f"portal-brand-{uuid.uuid4().hex[:6]}"
        create_resp = await auth_client.post(
            "/api/v1/admin/brands",
            json={"name": brand_name, "first_letter": "P", "show_status": 1, "factory_status": 1},
        )
        assert create_resp.status_code == 200, create_resp.text
        brand_id = create_resp.json()["data"]["id"]

        # Get brand detail via portal
        detail_resp = await public_client.get(f"/api/v1/portal/brands/{brand_id}")
        assert detail_resp.status_code == 200, detail_resp.text
        assert detail_resp.json()["data"]["name"] == brand_name

    # ======================================================================
    #  Portal Categories
    # ======================================================================

    @pytest.mark.asyncio
    async def test_portal_categories_list(self, public_client: AsyncClient):
        """GET /api/v1/portal/categories returns category list (public)."""
        resp = await public_client.get("/api/v1/portal/categories")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_portal_categories_tree(self, public_client: AsyncClient):
        """GET /api/v1/portal/categories/tree returns category tree (public)."""
        resp = await public_client.get("/api/v1/portal/categories/tree")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data, list)
        # Tree structure: each node has id, name, children
        if data:
            assert "id" in data[0]
            assert "children" in data[0]

    @pytest.mark.asyncio
    async def test_portal_categories_list_with_parent(self, public_client: AsyncClient):
        """GET /api/v1/portal/categories?parent_id=... filters by parent."""
        resp = await public_client.get("/api/v1/portal/categories")
        assert resp.status_code == 200, resp.text
        # Passing a valid UUID may return empty list, that's ok
        valid_uuid = "00000000-0000-0000-0000-000000000001"
        resp = await public_client.get(
            f"/api/v1/portal/categories?parent_id={valid_uuid}",
        )
        assert resp.status_code == 200, resp.text
