"""认证系统集成测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio(loop_scope="session")
async def test_register_and_login_flow(client: AsyncClient):
    suffix = uuid.uuid4().hex[:8]
    email = f"test-{suffix}@snaptrip.cn"
    password = "test123456"

    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    access_token = body["data"]["access_token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == email

    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 409

    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    new_refresh = resp.json()["data"]["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert resp.status_code == 200
    refresh_body = resp.json()
    assert "access_token" in refresh_body["data"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert resp.status_code == 401

    resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_body["data"]["refresh_token"]})
    assert resp.status_code == 200


@pytest.mark.asyncio(loop_scope="session")
async def test_login_invalid_credentials(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"email": "no-user@test.com", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio(loop_scope="session")
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/register", json={"email": "x@test.com", "password": "12"})
    assert resp.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
