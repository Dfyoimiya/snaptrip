"""
Integration tests: Admin return reasons CRUD endpoints.

Covers:
  - POST   /api/v1/admin/return-reasons        — Create return reason
  - GET    /api/v1/admin/return-reasons         — List return reasons (paginated)
  - GET    /api/v1/admin/return-reasons/{id}    — Get return reason detail
  - PUT    /api/v1/admin/return-reasons/{id}    — Update return reason
  - DELETE /api/v1/admin/return-reasons         — Batch delete return reasons
  - PATCH  /api/v1/admin/return-reasons/status  — Batch update status

Author: SnapTrip QA Team
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def rr_user_email() -> str:
    return f"rr-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(rr_user_email: str) -> AsyncClient:
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": rr_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": rr_user_email, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


class TestAdminReturnReasons:
    """Return reasons CRUD endpoint tests."""

    @pytest.mark.asyncio
    async def test_create_return_reason(self, auth_client: AsyncClient):
        """POST /api/v1/admin/return-reasons creates a return reason."""
        reason_name = f"退货原因-{uuid.uuid4().hex[:6]}"
        resp = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": reason_name, "sort": 1, "status": 1},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["name"] == reason_name
        assert "id" in data
        return data["id"]

    @pytest.mark.asyncio
    async def test_list_return_reasons(self, auth_client: AsyncClient):
        """GET /api/v1/admin/return-reasons returns a paginated list."""
        # Create two reasons first
        await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-list1-{uuid.uuid4().hex[:6]}", "sort": 1, "status": 1},
        )
        await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-list2-{uuid.uuid4().hex[:6]}", "sort": 2, "status": 1},
        )

        resp = await auth_client.get("/api/v1/admin/return-reasons?page=1&page_size=20")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 2

    @pytest.mark.asyncio
    async def test_get_return_reason_detail(self, auth_client: AsyncClient):
        """GET /api/v1/admin/return-reasons/{id} returns reason detail."""
        reason_name = f"reason-detail-{uuid.uuid4().hex[:6]}"
        create_resp = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": reason_name, "sort": 3, "status": 1},
        )
        reason_id = create_resp.json()["data"]["id"]

        resp = await auth_client.get(f"/api/v1/admin/return-reasons/{reason_id}")
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["name"] == reason_name

    @pytest.mark.asyncio
    async def test_update_return_reason(self, auth_client: AsyncClient):
        """PUT /api/v1/admin/return-reasons/{id} updates a return reason."""
        create_resp = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-upd-{uuid.uuid4().hex[:6]}", "sort": 5, "status": 1},
        )
        reason_id = create_resp.json()["data"]["id"]

        new_name = f"reason-upd2-{uuid.uuid4().hex[:6]}"
        upd_resp = await auth_client.put(
            f"/api/v1/admin/return-reasons/{reason_id}",
            json={"name": new_name, "status": 0},
        )
        assert upd_resp.status_code == 200, upd_resp.text
        assert upd_resp.json()["data"]["name"] == new_name
        assert upd_resp.json()["data"]["status"] == 0

    @pytest.mark.asyncio
    async def test_batch_delete_return_reasons(self, auth_client: AsyncClient):
        """DELETE /api/v1/admin/return-reasons batch deletes reasons."""
        create1 = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-bdel1-{uuid.uuid4().hex[:6]}", "sort": 10, "status": 1},
        )
        create2 = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-bdel2-{uuid.uuid4().hex[:6]}", "sort": 11, "status": 1},
        )
        id1 = create1.json()["data"]["id"]
        id2 = create2.json()["data"]["id"]

        resp = await auth_client.delete(
            f"/api/v1/admin/return-reasons?ids={id1}&ids={id2}",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["message"] == "删除成功"

    @pytest.mark.asyncio
    async def test_batch_update_return_reason_status(self, auth_client: AsyncClient):
        """PATCH /api/v1/admin/return-reasons/status batch updates reason status."""
        create1 = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-bst1-{uuid.uuid4().hex[:6]}", "sort": 20, "status": 1},
        )
        create2 = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={"name": f"reason-bst2-{uuid.uuid4().hex[:6]}", "sort": 21, "status": 1},
        )
        id1 = create1.json()["data"]["id"]
        id2 = create2.json()["data"]["id"]

        resp = await auth_client.patch(
            f"/api/v1/admin/return-reasons/status?ids={id1}&ids={id2}&status=0",
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["message"] == "更新成功"

    @pytest.mark.asyncio
    async def test_return_reason_missing_name_returns_422(self, auth_client: AsyncClient):
        """POST /api/v1/admin/return-reasons without name returns 422."""
        resp = await auth_client.post(
            "/api/v1/admin/return-reasons",
            json={},
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_return_reason_nonexistent_detail_returns_404(self, auth_client: AsyncClient):
        """GET /api/v1/admin/return-reasons/{nonexistent} returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await auth_client.get(f"/api/v1/admin/return-reasons/{fake_id}")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
