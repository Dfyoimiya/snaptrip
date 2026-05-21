"""Integration — Plan API 全链路 (Phase 3a: 异步 Celery 派发)

Phase 3a 变更：
  - POST /create 和 /confirm 改为 Celery 异步派发，返回 202
  - 新增 GET /status 查询 plan_run 审计记录
  - 需要真实 Celery Worker 才能执行 graph（标记为 celery 测试）
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _managed_client():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            if not hasattr(app.state, "runtime_events"):
                from app.adapters.persistence.runtime_event_repository import SQLRuntimeEventRepository
                from app.agent_runtime import RuntimeEventStore
                app.state.runtime_events = RuntimeEventStore(repository=SQLRuntimeEventRepository())
            if not hasattr(app.state, "_agent_service") or app.state._agent_service is None:
                from app.agent_runtime import build_plan_graph
                from app.services.agent_service import AgentService
                app.state._agent_service = AgentService(build_plan_graph())
            yield c

    async with _managed_client() as c:
        yield c


# ===== Phase 3a: 异步 API 表面测试 =====


@pytest.mark.asyncio
async def test_create_plan_returns_202(client):
    """POST /create → 202 Accepted + plan_id + status=queued。"""
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "周末想去北京798看展然后吃烤鸭",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 202
    payload = resp.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert "plan_id" in data
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_create_plan_response_has_no_slots(client):
    """POST /create 异步派发 → 202 响应不含 slots（slots 在 worker 执行后产生）。"""
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京故宫逛逛",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert "slots" not in data


@pytest.mark.asyncio
async def test_get_plan_status_returns_run(client):
    """GET /status → 查询 plan_runs 审计记录。"""
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去喝咖啡",
        "lat": 39.9, "lng": 116.4,
    })
    plan_id = resp.json()["data"]["plan_id"]

    resp2 = await client.get(f"/api/v1/plan/{plan_id}/status")
    assert resp2.status_code == 200
    payload = resp2.json()
    assert payload["code"] == 0
    assert payload["data"]["plan_id"] == plan_id


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: /confirm 需要 Celery Worker 先执行 graph 写入 checkpoint")
async def test_confirm_plan_returns_202(client):
    ...


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


# ===== 需要 Celery Worker 的深层测试（跳过） =====


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: /create 返回 202，slots 需要 Celery Worker 执行 graph 后才能在 checkpoint 中看到")
async def test_create_plan_has_slots(client):
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: checkpoint 由 Celery Worker 创建，GET /{plan_id} 需要 Worker 先执行")
async def test_get_plan_by_id(client):
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: SSE 事件由 Celery Worker 通过 Redis Pub/Sub 推送")
async def test_sse_stream_contains_events(client):
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: confirm dispatch 后状态由 Celery Worker 更新")
async def test_confirm_plan_interrupt_resume(client):
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: 局部修改需要 Celery Worker 执行 re-plan")
async def test_confirm_plan_partial_change(client):
    ...


@pytest.mark.asyncio
@pytest.mark.skip(reason="Phase 3a: 拒绝计划需要 Celery Worker 重新规划")
async def test_confirm_plan_rejected(client):
    ...
