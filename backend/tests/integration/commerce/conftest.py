"""
共享 fixtures —— 测试用户与 HTTP 客户端。

电商全链路集成测试的公共依赖:
  - test_user_email: 每次运行生成唯一测试邮箱
  - auth_client: 注册/登录后带 Bearer token 的客户端
  - public_client: 未认证游客客户端
"""

from __future__ import annotations

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def test_user_email() -> str:
    return f"e2e-test-{uuid.uuid4().hex[:8]}@example.com"


@pytest_asyncio.fixture
async def auth_client(test_user_email: str) -> AsyncClient:
    """
    创建已认证的 HTTP 客户端。

    步骤:
      1. 注册新用户
      2. 登录获取 access_token
      3. 返回带 Authorization Header 的客户端
    """
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")

    # 注册
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "password": "TestPass123!",
        },
    )
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.text}"

    # 如果已注册，直接登录
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_email,
            "password": "TestPass123!",
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def public_client() -> AsyncClient:
    """未认证客户端 —— 游客可访问前台接口"""
    from marketplace.app.main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    await client.aclose()
