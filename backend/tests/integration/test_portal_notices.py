"""
Integration tests: Portal notice/help endpoints (public).

Covers:
  - GET /api/v1/portal/notices          — Portal notice list (public)
  - GET /api/v1/portal/notices/{id}     — Portal notice detail (public)

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def auth_client() -> AsyncClient:
    """Authenticated client for creating test data."""
    from marketplace.app.main import app

    email = f"nt-auth-{uuid.uuid4().hex[:8]}@example.com"
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


class TestPortalNotices:
    """Portal notice/help endpoint tests."""

    @pytest.mark.asyncio
    async def test_portal_notices_list(self, public_client: AsyncClient):
        """GET /api/v1/portal/notices returns paginated help list (public)."""
        resp = await public_client.get("/api/v1/portal/notices?page=1&page_size=10")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_portal_notices_list_structure(self, public_client: AsyncClient):
        """Notice list items have expected fields."""
        resp = await public_client.get("/api/v1/portal/notices?page=1&page_size=10")
        assert resp.status_code == 200, resp.text

        for item in resp.json()["data"]["items"]:
            assert "id" in item
            assert "title" in item

    @pytest.mark.asyncio
    async def test_portal_notice_detail_nonexistent(self, public_client: AsyncClient):
        """GET /api/v1/portal/notices/{nonexistent} returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await public_client.get(f"/api/v1/portal/notices/{fake_id}")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_admin_creates_help_and_portal_views(self, auth_client: AsyncClient, public_client: AsyncClient):
        """Admin creates a help article; portal list/detail returns it."""
        help_title = f"test-help-{uuid.uuid4().hex[:6]}"
        create_resp = await auth_client.post(
            "/api/v1/admin/cms/helps",
            json={
                "title": help_title,
                "content": "本文用于集成测试",
                "category_name": "test",
                "status": 1,
                "sort": 1,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        help_id = create_resp.json()["data"]["id"]

        # Portal list
        list_resp = await public_client.get("/api/v1/portal/notices")
        assert list_resp.status_code == 200, list_resp.text
        items = list_resp.json()["data"]["items"]
        helpt_ids = [h["id"] for h in items]
        assert help_id in helpt_ids, f"Help {help_id} not found in portal list"

        # Portal detail
        detail_resp = await public_client.get(f"/api/v1/portal/notices/{help_id}")
        assert detail_resp.status_code == 200, detail_resp.text
        assert detail_resp.json()["data"]["title"] == help_title
