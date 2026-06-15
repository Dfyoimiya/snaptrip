"""
Integration tests: Admin order modification endpoints.

Covers:
  - POST /api/v1/admin/orders/{id}/modify-address   — Modify order address
  - POST /api/v1/admin/orders/{id}/modify-price      — Modify order price
  - POST /api/v1/admin/orders/{id}/remark             — Add admin remark
  - DELETE /api/v1/admin/orders/{id}                  — Delete order (soft delete)

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


async def _create_test_product(client: AsyncClient) -> dict:
    """Create a complete product (category + brand + SKU), return product dict."""
    cat_resp = await client.post(
        "/api/v1/admin/categories",
        json={"name": f"om-cat-{uuid.uuid4().hex[:6]}"},
    )
    assert cat_resp.status_code == 200, cat_resp.text
    cat_id = cat_resp.json()["data"]["id"]

    brand_resp = await client.post(
        "/api/v1/admin/brands",
        json={"name": f"om-brand-{uuid.uuid4().hex[:6]}"},
    )
    assert brand_resp.status_code == 200, brand_resp.text
    brand_id = brand_resp.json()["data"]["id"]

    sku_code = f"OM-{uuid.uuid4().hex[:6]}"
    prod_resp = await client.post(
        "/api/v1/admin/products",
        json={
            "name": f"om-prod-{uuid.uuid4().hex[:6]}",
            "price": "199.00",
            "category_id": cat_id,
            "brand_id": brand_id,
            "publish_status": 1,
            "skus": [{"sku_code": sku_code, "spec": "{}", "price": "199.00", "stock": 100}],
        },
    )
    assert prod_resp.status_code in (200, 201), prod_resp.text
    return prod_resp.json()["data"]


async def _create_order(client: AsyncClient) -> dict:
    """Create a paid order for modification testing."""
    product = await _create_test_product(client)
    product_id = product["id"]
    sku_id = product["skus"][0]["id"]

    await client.patch(f"/api/v1/admin/products/{product_id}/verify?status=1")

    cart_resp = await client.post(
        "/api/v1/portal/cart",
        json={"product_id": product_id, "sku_id": sku_id, "quantity": 1},
    )
    assert cart_resp.status_code in (200, 201), cart_resp.text
    cart_item_id = cart_resp.json()["data"]["id"]

    order_resp = await client.post(
        "/api/v1/portal/orders",
        json={
            "cart_item_ids": [cart_item_id],
            "receiver_name": "测试用户",
            "receiver_phone": "13800000000",
            "receiver_province": "北京",
            "receiver_city": "北京",
            "receiver_region": "朝阳区",
            "receiver_detail_address": "测试地址",
            "pay_type": 1,
        },
    )
    assert order_resp.status_code in (200, 201), order_resp.text
    return order_resp.json()["data"]


@pytest_asyncio.fixture
async def om_user_email() -> str:
    return f"om-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(om_user_email: str) -> AsyncClient:
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": om_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": om_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


class TestAdminOrderModify:
    """Admin order modification endpoint tests."""

    @pytest.mark.asyncio
    async def test_modify_order_address(self, auth_client: AsyncClient):
        """POST /api/v1/admin/orders/{id}/modify-address updates receiver info."""
        order = await _create_order(auth_client)
        order_id = order["id"]

        resp = await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/modify-address",
            params={
                "receiver_name": "NewName",
                "receiver_phone": "13900001111",
                "receiver_detail_address": "新地址",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["receiver_name"] == "NewName"
        assert data["receiver_phone"] == "13900001111"

    @pytest.mark.asyncio
    async def test_modify_order_price(self, auth_client: AsyncClient):
        """POST /api/v1/admin/orders/{id}/modify-price updates order price."""
        order = await _create_order(auth_client)
        order_id = order["id"]

        resp = await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/modify-price",
            json={"price": "150.00"},
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_order_remark(self, auth_client: AsyncClient):
        """POST /api/v1/admin/orders/{id}/remark adds an admin note."""
        order = await _create_order(auth_client)
        order_id = order["id"]

        resp = await auth_client.post(
            f"/api/v1/admin/orders/{order_id}/remark?note=test+admin+remark",
        )
        assert resp.status_code == 200, resp.text

    @pytest.mark.asyncio
    async def test_delete_order(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/orders/{id} soft-deletes an order."""
        order = await _create_order(auth_client)
        order_id = order["id"]

        resp = await auth_client.delete(f"/api/v1/admin/orders/{order_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["message"] == "删除成功"

    @pytest.mark.asyncio
    async def test_order_modify_address_invalid_id_returns_error(self, auth_client: AsyncClient):
        """POST /api/v1/admin/orders/{nonexistent}/modify-address returns error."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await auth_client.post(
            f"/api/v1/admin/orders/{fake_id}/modify-address",
            params={"receiver_name": "Nobody"},
        )
        assert resp.status_code in (404, 400), f"Expected error, got {resp.status_code}: {resp.text}"
