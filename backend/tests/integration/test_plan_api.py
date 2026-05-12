"""Integration — Plan API 全链路 + SSE 流"""


import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_plan_returns_200(client):
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "周末想去北京798看展然后吃烤鸭",
        "lat": 39.9, "lng": 116.4,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "plan_id" in data
    assert data["status"] in ("done", "confirming", "executing")


@pytest.mark.asyncio
async def test_create_plan_has_slots(client):
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京故宫逛逛",
        "lat": 39.9, "lng": 116.4,
    })
    data = resp.json()
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
    plan_id = resp.json()["plan_id"]

    resp2 = await client.get(f"/api/v1/plan/{plan_id}")
    assert resp2.status_code == 200
    assert resp2.json()["plan_id"] == plan_id


@pytest.mark.asyncio
async def test_sse_stream_contains_events(client):
    resp = await client.post("/api/v1/plan/create", json={
        "user_input": "想去北京798看展",
        "lat": 39.9, "lng": 116.4,
    })
    plan_id = resp.json()["plan_id"]

    async with client.stream("GET", f"/api/v1/plan/{plan_id}/stream") as stream:
        events = []
        async for line in stream.aiter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
            if len(events) >= 2:
                break

    assert "intent" in events
