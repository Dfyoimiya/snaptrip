"""
Integration tests: Order authorization and ownership scoping.

Tests that portal order operations (GET detail, POST cancel, POST pay,
POST confirm-receipt) are scoped to the order owner. Non-owners should
receive 403 (Forbidden) or 404 (Not Found — order existence hidden).

The existing order service methods (get_detail, cancel, pay, confirm_receipt)
do NOT currently filter by user_id. These tests document the INTENDED
security boundary. Once ownership checks are implemented in the service layer,
these tests should pass.

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def user_b_client() -> AsyncClient:
    """Authenticated HTTP client for User B (different user from User A)."""
    from marketplace.app.main import app

    email = f"e2e-auth-b-{uuid.uuid4().hex[:8]}@example.com"
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"User B register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"User B login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


class TestOrderAuthorization:
    """Order ownership scoping: User A creates, User B should be denied."""

    @pytest_asyncio.fixture
    async def setup_order(self, auth_client: AsyncClient) -> dict:
        """
        Create a product and place an unpaid order as User A.
        Returns dict with order_id and cart_item_id.
        """
        # ---- 1. Prepare product ----
        cat_resp = await auth_client.post("/api/v1/admin/categories", json={"name": "授权测试分类"})
        cat_id = cat_resp.json()["data"]["id"]

        brand_resp = await auth_client.post("/api/v1/admin/brands", json={"name": "AuthTest"})
        brand_id = brand_resp.json()["data"]["id"]

        prod_resp = await auth_client.post(
            "/api/v1/admin/products",
            json={
                "name": "授权测试商品",
                "price": "99.00",
                "category_id": cat_id,
                "brand_id": brand_id,
                "publish_status": 1,
                "skus": [{"sku_code": "AT-001", "spec": "{}", "price": "99.00", "stock": 100}],
            },
        )
        product_id = prod_resp.json()["data"]["id"]
        sku_id = prod_resp.json()["data"]["skus"][0]["id"]

        await auth_client.patch(f"/api/v1/admin/products/{product_id}/verify?status=1")

        # ---- 2. Add to cart ----
        cart_resp = await auth_client.post(
            "/api/v1/portal/cart",
            json={"product_id": product_id, "sku_id": sku_id, "quantity": 1},
        )
        cart_item_id = cart_resp.json()["data"]["id"]

        # ---- 3. Place order (unpaid) ----
        order_resp = await auth_client.post(
            "/api/v1/portal/orders",
            json={
                "cart_item_ids": [cart_item_id],
                "receiver_name": "张三",
                "receiver_phone": "13800138000",
                "receiver_province": "北京",
                "receiver_city": "北京",
                "receiver_region": "朝阳区",
                "receiver_detail_address": "望京SOHO T1",
                "pay_type": 1,
            },
        )
        order_id = order_resp.json()["data"]["id"]

        return {"order_id": order_id, "cart_item_id": cart_item_id}

    @pytest_asyncio.fixture
    async def setup_paid_delivered_order(self, auth_client: AsyncClient, setup_order: dict) -> dict:
        """
        Extend setup_order: User A pays and admin delivers.
        Creates an order in "delivered" status ready for confirm-receipt tests.
        """
        order_id = setup_order["order_id"]

        # User A pays
        await auth_client.post(f"/api/v1/portal/orders/{order_id}/pay")

        # Admin delivers (using auth_client since it is the same authenticated user
        # who already has admin-like product access)
        await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/delivery",
            json={"delivery_company": "顺丰速运", "delivery_sn": "SF9876543210"},
        )
        return setup_order

    # ------------------------------------------------------------------
    #  Positive: owner operations succeed
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_owner_can_view_own_order(self, auth_client: AsyncClient, setup_order: dict):
        """User A can view their own order detail."""
        order_id = setup_order["order_id"]
        resp = await auth_client.get(f"/api/v1/portal/orders/{order_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["id"] == order_id

    @pytest.mark.asyncio
    async def test_owner_can_cancel_own_order(self, auth_client: AsyncClient, setup_order: dict):
        """User A can cancel their own unpaid order."""
        order_id = setup_order["order_id"]
        resp = await auth_client.post(f"/api/v1/portal/orders/{order_id}/cancel")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == 5  # CLOSED

    # ------------------------------------------------------------------
    #  Negative: non-owner operations should be rejected
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_non_owner_cannot_view_order_detail(self, user_b_client: AsyncClient, setup_order: dict):
        """User B cannot view User A's order detail."""
        order_id = setup_order["order_id"]
        resp = await user_b_client.get(f"/api/v1/portal/orders/{order_id}")
        # Expected: 403 (explicit forbidden) or 404 (order existence hidden)
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403/404, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_cancel_order(self, user_b_client: AsyncClient, setup_order: dict):
        """User B cannot cancel User A's order."""
        order_id = setup_order["order_id"]
        resp = await user_b_client.post(f"/api/v1/portal/orders/{order_id}/cancel")
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403/404, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_pay_order(self, user_b_client: AsyncClient, setup_order: dict):
        """User B cannot pay User A's order."""
        order_id = setup_order["order_id"]
        resp = await user_b_client.post(f"/api/v1/portal/orders/{order_id}/pay")
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403/404, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_confirm_receipt(self, user_b_client: AsyncClient, setup_paid_delivered_order: dict):
        """User B cannot confirm receipt of User A's delivered order."""
        order_id = setup_paid_delivered_order["order_id"]
        resp = await user_b_client.post(f"/api/v1/portal/orders/{order_id}/confirm-receipt")
        assert resp.status_code in (
            403,
            404,
        ), f"Expected 403/404, got {resp.status_code}: {resp.text}"
