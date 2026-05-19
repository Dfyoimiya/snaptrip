"""Integration — Plan API 全链路 + SSE 流 + Interrupt/Resume + Fallback exhaustion"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    # Manually trigger lifespan so app.state is fully initialized
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _managed_client():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Ensure lifespan events are sent if not already
            if not hasattr(app.state, "runtime_events"):
                from app.adapters.persistence.runtime_event_repository import SQLRuntimeEventRepository
                from app.agent_runtime import RuntimeEventStore
                app.state.runtime_events = RuntimeEventStore(repository=SQLRuntimeEventRepository())
            if not hasattr(app.state, "plan_graph") or app.state.plan_graph is None:
                from app.agent_runtime.graph import build_plan_graph
                app.state.plan_graph = build_plan_graph()
            # Sync the graph's event sink with the current runtime_events instance
            from app.agents.graph import set_event_sink
            set_event_sink(app.state.runtime_events)
            yield c

    async with _managed_client() as c:
        yield c


@pytest.mark.asyncio
async def test_create_plan_returns_200(client):
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "周末想去北京798看展然后吃烤鸭",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["code"] == 0
    data = payload["data"]
    assert "plan_id" in data
    assert data["status"] in ("done", "confirming", "executing")


@pytest.mark.asyncio
async def test_create_plan_has_slots(client):
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京故宫逛逛",
        "lat": 39.9, "lng": 116.4,
    })
    payload = resp.json()
    data = payload["data"]
    assert len(data["slots"]) > 0
    for slot in data["slots"]:
        assert "poi" in slot
        assert "action" in slot


@pytest.mark.asyncio
async def test_get_plan_by_id(client):
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去喝咖啡",
        "lat": 39.9, "lng": 116.4,
    })
    plan_id = resp.json()["data"]["plan_id"]

    resp2 = await client.get(f"/api/v1/plan/{plan_id}")
    assert resp2.status_code == 200
    assert resp2.json()["data"]["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_sse_stream_contains_events(client):
    """Test that stream_plan produces correct SSE events for a created plan.

    Note: We test stream_plan directly rather than through HTTP because
    httpx's ASGITransport does not reliably consume EventSourceResponse
    chunks in test fixtures.
    """
    from app.api.v1.session import stream_plan

    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京798看展",
        "lat": 39.9, "lng": 116.4,
    })
    plan_id = resp.json()["data"]["plan_id"]

    event_store = client.app.state.runtime_events
    response = await stream_plan(plan_id, event_store)

    chunks: list[str] = []
    async for chunk in response.body_iterator:
        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk)
        chunks.append(text)
        if len(chunks) >= 3:
            break

    events = []
    for text in chunks:
        for line in text.splitlines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())

    assert "intent" in events


@pytest.mark.asyncio
async def test_confirm_plan_interrupt_resume(client):
    """人机协同：创建计划后通过 confirm API 恢复图执行到完成。"""
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京798看展然后喝咖啡",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 200
    plan_id = resp.json()["data"]["plan_id"]

    # Confirm the plan to resume execution
    confirm_resp = await client.post(
        f"/api/v1/plan/{plan_id}/confirm",
        json={"decision": "confirmed", "locked_slots": [0]},
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()["data"]
    assert data["plan_id"] == plan_id
    # After confirmation the graph should proceed to execution / notify
    assert data["status"] in ("done", "executing", "confirming")


@pytest.mark.asyncio
async def test_confirm_plan_partial_change(client):
    """人机协同：用户局部修改（拒绝某个 slot）后重规划。"""
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京798看展然后喝咖啡",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 200
    plan_id = resp.json()["data"]["plan_id"]
    slots = resp.json()["data"]["slots"]
    assert len(slots) > 0

    # Reject the last slot to trigger replan
    reject_idx = len(slots) - 1
    confirm_resp = await client.post(
        f"/api/v1/plan/{plan_id}/confirm",
        json={
            "decision": "partial_change",
            "rejected_slots": [reject_idx],
            "instruction": "换一个类似的",
        },
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()["data"]
    assert data["plan_id"] == plan_id
    # Partial change should return a revised plan (still confirming or done)
    assert data["status"] in ("confirming", "done", "executing")


@pytest.mark.asyncio
async def test_confirm_plan_rejected(client):
    """人机协同：用户拒绝计划，返回到 planning_engine 重新生成。"""
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京798看展然后喝咖啡",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 200
    plan_id = resp.json()["data"]["plan_id"]

    confirm_resp = await client.post(
        f"/api/v1/plan/{plan_id}/confirm",
        json={"decision": "rejected", "instruction": "预算太低了，重新规划"},
    )
    assert confirm_resp.status_code == 200
    data = confirm_resp.json()["data"]
    assert data["plan_id"] == plan_id
    # Rejected plan routes back to planning_engine
    assert data["status"] in ("confirming", "done", "executing")


@pytest.mark.asyncio
async def test_fallback_exhaustion_ends_graph(client, monkeypatch):
    """Fallback 重试耗尽后图应正常结束，不陷入死循环。"""
    from app.core.constants import FALLBACK_MAX_RETRY

    # Monkeypatch FALLBACK_MAX_RETRY to 1 so exhaustion happens quickly
    monkeypatch.setattr("app.agents.graph.FALLBACK_MAX_RETRY", 1)
    monkeypatch.setattr("app.core.constants.FALLBACK_MAX_RETRY", 1)

    # Monkeypatch execution_engine_node to always return partial_success
    async def _fake_execution_node(state):
        return {
            "execution": {
                "status": "partial_success",
                "confirmed_bookings": {},
                "failed_slots": [{"slot_index": 0, "error_code": "MOCK_FAIL"}],
            },
            "execution_state": {"status": "partial_success", "failed_slot_indices": [0]},
            "status": "executing",
        }

    import app.agents.graph as graph_mod
    orig_exec = graph_mod.execution_engine_node
    graph_mod.execution_engine_node = _fake_execution_node

    # Rebuild graph so the patched node is picked up
    from app.agent_runtime.graph import build_plan_graph
    app.state.plan_graph = build_plan_graph()

    try:
        resp = await client.post("/api/v1/plan/create", json={
            "user_input": "想去北京798看展然后喝咖啡",
            "lat": 39.9, "lng": 116.4,
        })
        assert resp.status_code == 200
        plan_id = resp.json()["data"]["plan_id"]

        # Confirm to enter execution
        confirm_resp = await client.post(
            f"/api/v1/plan/{plan_id}/confirm",
            json={"decision": "confirmed"},
        )
        assert confirm_resp.status_code == 200
        data = confirm_resp.json()["data"]
        assert data["plan_id"] == plan_id
        # With exhausted fallback the graph should end (done or failed)
        assert data["status"] in ("done", "failed")
    finally:
        graph_mod.execution_engine_node = orig_exec
