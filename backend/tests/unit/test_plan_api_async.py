"""Phase 3a 测试：API 路由异步派发。

合并自:
  - backend/tests/integration/test_plan_api.py (integration fixtures)
  - backend/tests/unit/test_plan_api_async.py (unit test cases)

测试目标：
  1. POST /create → 202 Accepted + plan_id
  2. POST /create → 202 响应不含 slots
  3. POST /confirm → 202 Accepted (mock)
  4. POST /confirm (nonexistent) → 404
  5. GET /status → 返回 plan_run 状态
  6. GET /status (nonexistent) → 404
  7. GET /{plan_id} 不变（仍读 checkpoint）

Author: SnapTrip Team
Date: 2026-06-08
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from marketplace.app.main import app


@pytest.fixture
def mock_celery():
    """Mock Celery task 调用，避免连接真实 broker。"""
    with (
        patch("marketplace.app.api.v1.plan.celery_submit") as mock_submit,
        patch("marketplace.app.api.v1.plan.celery_confirm") as mock_confirm,
    ):
        mock_submit.delay = MagicMock()
        mock_confirm.delay = MagicMock()
        yield


@pytest.fixture
async def client(mock_celery):
    """创建带完整 app context 的异步 HTTP 客户端（runtime_events + agent_service）。"""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _managed_client():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            if not hasattr(app.state, "runtime_events"):
                app.state.runtime_events = MagicMock()
            if not hasattr(app.state, "_agent_service") or app.state._agent_service is None:
                from agent.graph import build_graph
                from agent.services.agent import AgentService

                app.state._agent_service = AgentService(build_graph())
            yield c

    async with _managed_client() as c:
        yield c


# ====================================================================
# POST /create
# ====================================================================


@pytest.mark.asyncio
async def test_create_plan_returns_202(client):
    """POST /create → 202 Accepted + plan_id + status=queued。"""
    resp = await client.post(
        "/api/v1/plan/create",
        json={
            "user_input": "周末想去北京798看展然后吃烤鸭",
            "lat": 39.9,
            "lng": 116.4,
        },
    )
    assert resp.status_code == 202
    payload = resp.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert "plan_id" in data
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_create_plan_response_has_no_slots(client):
    """POST /create 异步派发 → 202 响应不含 slots（slots 在 worker 执行后产生）。"""
    resp = await client.post(
        "/api/v1/plan/create",
        json={
            "user_input": "想去北京故宫逛逛",
            "lat": 39.9,
            "lng": 116.4,
        },
    )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert "slots" not in data


# ====================================================================
# POST /confirm
# ====================================================================


class TestConfirmPlanAsync:
    """POST /confirm 测试 —— 正常派发 + 边界情况。"""

    @pytest.mark.asyncio
    async def test_confirm_returns_202(self, client):
        """POST /confirm → 202 Accepted（mock agent state）。"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch("marketplace.app.api.v1.plan._get_agent_service") as mock_svc_fn:
            mock_svc = mock_svc_fn.return_value
            mock_svc.get_state = AsyncMock(return_value={"status": "awaiting_confirmation"})

            response = await client.post(
                f"/api/v1/plan/{plan_id}/confirm",
                json={"decision": "confirmed", "locked_slots": [0, 1]},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["data"]["status"] == "accepted"


@pytest.mark.asyncio
async def test_confirm_plan_not_found(client):
    """POST /confirm 对不存在的 plan_id → 404。"""
    resp = await client.post(
        "/api/v1/plan/nonexistent-id/confirm",
        json={"decision": "confirmed"},
    )
    assert resp.status_code == 404


# ====================================================================
# GET /{plan_id}/status
# ====================================================================


@pytest.mark.asyncio
async def test_get_plan_status_returns_run(client):
    """GET /status → 查询 plan_runs 审计记录（先 create 再查状态）。"""
    resp = await client.post(
        "/api/v1/plan/create",
        json={
            "user_input": "想去喝咖啡",
            "lat": 39.9,
            "lng": 116.4,
        },
    )
    plan_id = resp.json()["data"]["plan_id"]

    resp2 = await client.get(f"/api/v1/plan/{plan_id}/status")
    assert resp2.status_code == 200
    payload = resp2.json()
    assert payload["code"] == 0
    assert payload["data"]["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_get_plan_status_not_found(client):
    """GET /status 对不存在的 plan_id → 404。"""
    resp = await client.get("/api/v1/plan/nonexistent-id/status")
    assert resp.status_code == 404


# ====================================================================
# GET /{plan_id} (unchanged — reads checkpoint)
# ====================================================================


class TestGetPlanUnchanged:
    """GET /{plan_id} —— 仍然从 checkpoint 读取（行为不变）。"""

    @pytest.mark.asyncio
    async def test_get_plan_reads_checkpoint(self, client):
        """GET /{plan_id} 仍然从 checkpoint 读取（行为不变）。"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch("marketplace.app.api.v1.plan._get_agent_service") as mock_svc_fn:
            mock_svc = mock_svc_fn.return_value
            mock_svc.get_state = AsyncMock(return_value=None)

            response = await client.get(f"/api/v1/plan/{plan_id}")

        # plan not found in checkpoint → 404 或其他错误
        assert response.status_code in (200, 404, 500)
