"""Integration — Plan API 全链路 (Phase 3a: 异步 Celery 派发)

Phase 3a 变更：
  - POST /create 和 /confirm 改为 Celery 异步派发，返回 202
  - 新增 GET /status 查询 plan_run 审计记录
  - Celery task 调用被 mock（无真实 broker），深层测试 skip
"""

from unittest.mock import MagicMock, patch

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
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _managed_client():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            if not hasattr(app.state, "runtime_events"):
                from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
                from agent.events.store import RuntimeEventStore

                app.state.runtime_events = RuntimeEventStore(repository=SQLRuntimeEventRepository())
            if not hasattr(app.state, "_agent_service") or app.state._agent_service is None:
                from agent.graph import build_plan_graph
                from agent.services.agent import AgentService

                app.state._agent_service = AgentService(build_plan_graph())
            yield c

    async with _managed_client() as c:
        yield c


# ===== Phase 3a: 异步 API 表面测试 =====


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


@pytest.mark.asyncio
async def test_get_plan_status_returns_run(client):
    """GET /status → 查询 plan_runs 审计记录。"""
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
async def test_confirm_plan_not_found(client):
    """POST /confirm 对不存在的 plan_id → 404。"""
    resp = await client.post(
        "/api/v1/plan/nonexistent-id/confirm",
        json={"decision": "confirmed"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_plan_status_not_found(client):
    """GET /status 对不存在的 plan_id → 404。"""
    resp = await client.get("/api/v1/plan/nonexistent-id/status")
    assert resp.status_code == 404
