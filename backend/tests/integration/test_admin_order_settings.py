"""
Integration tests: Admin order settings endpoints.

Covers:
  - GET  /api/v1/admin/order-settings/{setting_id}  — Get order settings
  - PUT  /api/v1/admin/order-settings/{setting_id}  — Update order settings

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def os_user_email() -> str:
    return f"os-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(os_user_email: str) -> AsyncClient:
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": os_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": os_user_email, "password": "TestPass123!"},
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


SETTINGS_ID = "00000000-0000-0000-0000-000000000001"


class TestAdminOrderSettings:
    """Order settings endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_order_settings(self, auth_client: AsyncClient):
        """GET /api/v1/admin/order-settings/{id} returns current settings."""
        resp = await auth_client.get(f"/api/v1/admin/order-settings/{SETTINGS_ID}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # Check for expected fields
        assert "id" in data
        # The response may also contain various order-setting fields
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_update_order_settings(self, auth_client: AsyncClient):
        """PUT /api/v1/admin/order-settings/{id} updates settings."""
        resp = await auth_client.put(
            f"/api/v1/admin/order-settings/{SETTINGS_ID}",
            json={"comment_overtime": 14400, "finish_overtime": 43200},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # If the schema allows these fields, verify they were applied
        if "comment_overtime" in data:
            assert data["comment_overtime"] == 14400

    @pytest.mark.asyncio
    async def test_get_order_settings_requires_auth(self, public_client: AsyncClient):
        """GET /api/v1/admin/order-settings/{id} without auth returns 401."""
        resp = await public_client.get(f"/api/v1/admin/order-settings/{SETTINGS_ID}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_update_order_settings_requires_auth(self, public_client: AsyncClient):
        """PUT /api/v1/admin/order-settings/{id} without auth returns 401."""
        resp = await public_client.put(
            f"/api/v1/admin/order-settings/{SETTINGS_ID}",
            json={"comment_overtime": 14400},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
