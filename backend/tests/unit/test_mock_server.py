"""Mock Server 契约测试 —— 验证各路由返回 ToolResult 格式。

使用 httpx 直连 Mock Server 进程（需提前启动在 localhost:8001）。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import pytest
import httpx

MOCK_URL = "http://localhost:8001"


def _is_server_running():
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8001/health", timeout=2)
        return resp.status == 200
    except Exception:
        return False


requires_mock = pytest.mark.skipif(
    not _is_server_running(),
    reason="Mock Server not running on localhost:8001",
)


@pytest.fixture
async def mock_client():
    async with httpx.AsyncClient(base_url=MOCK_URL, timeout=5.0) as c:
        yield c


@requires_mock
@pytest.mark.asyncio
async def test_health(mock_client):
    resp = await mock_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@requires_mock
@pytest.mark.asyncio
async def test_poi_search_format(mock_client):
    resp = await mock_client.get("/poi/search", params={"lat": 39.9, "lng": 116.4, "limit": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "data" in body
    assert "latency_ms" in body


@requires_mock
@pytest.mark.asyncio
async def test_queue_format(mock_client):
    resp = await mock_client.get("/poi/queue", params={"poi_id": "bj-001"})
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "data" in body


@requires_mock
@pytest.mark.asyncio
async def test_weather_format(mock_client):
    resp = await mock_client.get("/weather", params={"city": "北京"})
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body and "data" in body


@requires_mock
@pytest.mark.asyncio
async def test_route_format(mock_client):
    resp = await mock_client.get("/route", params={
        "from_lat": 39.9, "from_lng": 116.4, "to_lat": 40.0, "to_lng": 116.5, "mode": "walk",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body and "data" in body


@requires_mock
@pytest.mark.asyncio
async def test_order_prepare_format(mock_client):
    resp = await mock_client.post("/order/prepare", json={"poi_id": "bj-003", "items": []})
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body and "data" in body


@requires_mock
@pytest.mark.asyncio
async def test_order_submit_invalid(mock_client):
    resp = await mock_client.post("/order/submit", json={"prepare_id": "invalid"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failure"
    assert body["error_code"] == "INVALID_PREPARE_ID"


@requires_mock
@pytest.mark.asyncio
async def test_delivery_format(mock_client):
    resp = await mock_client.post("/delivery/schedule", json={
        "item_type": "cake", "from_poi_id": "bj-007", "to_poi_id": "sh-001",
        "expected_time": "2026-05-17T14:00:00", "recipient_phone": "13800138000",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    if body["status"] == "success":
        assert "delivery_id" in body["data"]
        assert "fee" in body["data"]
