"""端到端集成测试 —— 完整用户流程。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from marketplace.app.main import app


@pytest.fixture(scope="module")
async def e2e_client():
    # Ensure app.state is fully initialized (lifespan may not have run in test)
    from agent.adapters.persistence.runtime_event import SQLRuntimeEventRepository
    from agent.events.store import RuntimeEventStore

    if not hasattr(app.state, "runtime_events"):
        app.state.runtime_events = RuntimeEventStore(repository=SQLRuntimeEventRepository())
    if not hasattr(app.state, "plan_graph") or app.state.plan_graph is None:
        from agent.graph import build_plan_graph

        app.state.plan_graph = build_plan_graph()
    from agent.graph import set_event_sink

    set_event_sink(app.state.runtime_events)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(scope="module")
async def _e2e_user(e2e_client):
    suffix = uuid.uuid4().hex[:8]
    email = f"e2e-{suffix}@snaptrip.cn"
    password = "test123456"
    resp = await e2e_client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return email, password, headers


# @pytest.mark.asyncio(loop_scope="module")
# async def test_full_user_flow(e2e_client, _e2e_user):
#     """跳过：依赖真实 LLM API，CI 中无有效 key 会超时。"""
#     email, password, headers = _e2e_user
#
#     resp = await e2e_client.get("/api/v1/user/profile", headers=headers)
#     assert resp.status_code == 200
#     assert "nickname" in resp.json()["data"]
#
#     resp = await e2e_client.put(
#         "/api/v1/user/profile", headers=headers,
#         json={"nickname": "E2E-User", "travel_style": "relaxed"},
#     )
#     assert resp.status_code == 200
#     assert resp.json()["data"]["nickname"] == "E2E-User"
#
#     resp = await e2e_client.get("/api/v1/user/plans", headers=headers)
#     assert resp.status_code == 200
#     assert "items" in resp.json()["data"]
#
#     resp = await e2e_client.post(
#         "/api/v1/plan/create",
#         json={"user_input": "帮我在北京规划一个2人周末行程", "user_id": "test", "lat": 39.9, "lng": 116.4},
#     )
#     assert resp.status_code in (200, 500)
#     body = resp.json()
#     if "data" in body and body["data"]:
#         plan_id = body["data"].get("plan_id")
#         if plan_id:
#             resp = await e2e_client.get(f"/api/v1/plan/{plan_id}")
#             assert resp.status_code == 200
#
#             resp = await e2e_client.get(f"/api/v1/plan/{plan_id}/stream")
#             assert resp.status_code == 200


@pytest.mark.asyncio(loop_scope="module")
async def test_health_check(e2e_client):
    resp = await e2e_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
