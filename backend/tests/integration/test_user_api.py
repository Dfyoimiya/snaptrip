"""用户中心集成测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from marketplace.app.main import app


@pytest.fixture(scope="session")
async def client_and_user():
    suffix = uuid.uuid4().hex[:8]
    email = f"user-{suffix}@snaptrip.cn"
    password = "test123456"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert resp.status_code == 200
        token = resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        yield c, headers


@pytest.mark.asyncio
async def test_get_profile(client_and_user):
    c, headers = client_and_user
    resp = await c.get("/api/v1/user/profile", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "nickname" in data


@pytest.mark.asyncio
async def test_update_profile(client_and_user):
    c, headers = client_and_user
    resp = await c.put(
        "/api/v1/user/profile",
        headers=headers,
        json={"nickname": "新昵称", "travel_style": "relaxed", "preferences": {"food": "spicy"}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["nickname"] == "新昵称"


@pytest.mark.asyncio
async def test_list_plans_empty(client_and_user):
    c, headers = client_and_user
    resp = await c.get("/api/v1/user/plans", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_profile_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/user/profile")
        assert resp.status_code == 401
