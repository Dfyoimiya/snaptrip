"""
Integration tests: Admin endpoint authentication requirements.

Verifies that protected admin GET endpoints return 401 when no auth token
is provided. GET endpoints never need request bodies, so they reliably
exercise the auth Depends() path.

Author: SnapTrip QA Team
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Only GET endpoints are tested here — they never require a request body,
# so the auth Depends(get_current_user) is always exercised.
# POST/PUT/DELETE auth tests are covered in individual endpoint test files.
PROTECTED_GET_ENDPOINTS: list[str] = [
    # Dashboard & Stats
    "/api/v1/admin/dashboard",
    "/api/v1/admin/stats/overview",
    "/api/v1/admin/stats/sales?days=7",
    "/api/v1/admin/stats/products?limit=10",
    # Orders
    "/api/v1/admin/orders",
    # Members
    "/api/v1/admin/members",
    # Categories
    "/api/v1/admin/categories",
    "/api/v1/admin/categories/tree",
    # Brands
    "/api/v1/admin/brands/all",
    "/api/v1/admin/brands",
    # Products
    "/api/v1/admin/products",
    # Coupons
    "/api/v1/admin/coupons",
    # CMS
    "/api/v1/admin/cms/banners",
    "/api/v1/admin/cms/subjects",
    "/api/v1/admin/cms/helps",
    "/api/v1/admin/cms/subjects/categories",
    # Flash
    "/api/v1/admin/flash-promotions",
    "/api/v1/admin/flash-promotions/sessions",
    # Product Attributes
    "/api/v1/admin/product-attributes",
    "/api/v1/admin/product-attributes/categories",
    # Return reasons
    "/api/v1/admin/return-reasons",
    # Return applies
    "/api/v1/admin/return-applies",
    # Menu & RBAC
    "/api/v1/menu/treeList",
    "/api/v1/role/list",
    "/api/v1/role/listAll",
    "/api/v1/admin/list",
    # Resource
    "/api/v1/resourceCategory/listAll",
    "/api/v1/resource/listAll",
    "/api/v1/resource/list",
]


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()


class TestAdminAuthRequired:
    """Admin GET endpoints must return 401 without auth token."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PROTECTED_GET_ENDPOINTS)
    async def test_admin_get_endpoint_returns_401_without_auth(
        self, public_client: AsyncClient, path: str
    ):
        """GET {path} without auth returns 401."""
        resp = await public_client.get(path)
        assert resp.status_code == 401, (
            f"Expected 401 for GET {path}, got {resp.status_code}: {resp.text[:200]}"
        )
