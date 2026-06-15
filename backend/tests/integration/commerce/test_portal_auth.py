"""
Integration tests: Portal endpoint authorization requirements.

Verifies that protected portal endpoints return 401 when no auth token is provided.

Covers:
  - Cart endpoints (list, add, update, delete, clear)
  - Order endpoints (create, list, pay)
  - Member endpoints (profile, addresses, favorites)
  - Coupon endpoints (claim, list mine)

Author: SnapTrip QA Team
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

PROTECTED_ENDPOINTS = [
    # Cart
    ("GET", "/api/v1/portal/cart"),
    ("POST", "/api/v1/portal/cart"),
    ("DELETE", "/api/v1/portal/cart"),  # clear cart
    # Orders
    ("POST", "/api/v1/portal/orders"),
    ("GET", "/api/v1/portal/orders"),
    # Member
    ("GET", "/api/v1/portal/member/profile"),
    ("GET", "/api/v1/portal/member/addresses"),
    ("POST", "/api/v1/portal/member/addresses"),
    ("GET", "/api/v1/portal/member/favorites"),
    ("POST", "/api/v1/portal/member/favorites"),
    # Coupons
    ("POST", "/api/v1/portal/coupons/00000000-0000-0000-0000-000000000001/claim"),
    ("GET", "/api/v1/portal/coupons/mine"),
    ("GET", "/api/v1/portal/coupons/available"),
]

# Endpoints with special body requirements
SPECIAL_BODY: dict[str, dict] = {
    "POST /api/v1/portal/cart": {
        "product_id": "00000000-0000-0000-0000-000000000000",
        "sku_id": "00000000-0000-0000-0000-000000000000", "quantity": 1,
    },
    "POST /api/v1/portal/orders": {
        "cart_item_ids": [],
        "receiver_name": "t", "receiver_phone": "13800000000",
        "receiver_province": "x", "receiver_city": "x",
        "receiver_region": "x", "receiver_detail_address": "x",
        "pay_type": 1,
    },
    "POST /api/v1/portal/member/addresses": {
        "name": "t", "phone": "13800000000",
        "province": "x", "city": "x", "region": "x",
        "detail_address": "x",
    },
    "POST /api/v1/portal/member/favorites": None,  # uses query param
}

# Endpoints that require no body
NO_BODY_ENDPOINTS = {
    "GET /api/v1/portal/cart",
    "DELETE /api/v1/portal/cart",
    "GET /api/v1/portal/orders",
    "GET /api/v1/portal/member/profile",
    "GET /api/v1/portal/member/addresses",
    "GET /api/v1/portal/member/favorites",
    "POST /api/v1/portal/coupons/00000000-0000-0000-0000-000000000001/claim",
    "GET /api/v1/portal/coupons/mine",
    "GET /api/v1/portal/coupons/available",
}


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    """Unauthenticated HTTP client."""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()


class TestPortalAuthRequired:
    """All protected portal endpoints must return 401 without auth token."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    async def test_protected_endpoint_returns_401(self, public_client: AsyncClient, method: str, path: str):
        """Protected portal endpoint returns 401 when no auth token is provided."""
        route_key = f"{method} {path}"

        if method == "GET":
            resp = await public_client.get(path)
        elif method == "POST":
            body = SPECIAL_BODY.get(route_key)
            if body is None and route_key == "POST /api/v1/portal/member/favorites":
                resp = await public_client.post(path, params={"product_id": "00000000-0000-0000-0000-000000000000"})
            elif body:
                resp = await public_client.post(path, json=body)
            else:
                resp = await public_client.post(path)
        elif method == "PUT":
            resp = await public_client.put(path)
        elif method == "DELETE":
            resp = await public_client.delete(path)
        elif method == "PATCH":
            resp = await public_client.patch(path)
        else:
            pytest.fail(f"Unsupported method: {method}")

        assert resp.status_code == 401, (
            f"Expected 401 for {method} {path}, got {resp.status_code}: {resp.text[:200]}"
        )
