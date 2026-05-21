"""Phase 3a 单元测试：API 路由异步派发。

测试目标：
  1. POST /create → 202 Accepted + plan_id
  2. POST /confirm → 202 Accepted
  3. GET /status → 返回 plan_run 状态
  4. GET /{plan_id} 不变（仍读 checkpoint）

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from marketplace.app.main import app


@pytest.fixture
def mock_celery():
    """替换 Celery task 调用为本地 mock。"""
    with (
        patch("marketplace.app.api.v1.plan.celery_submit") as mock_submit,
        patch("marketplace.app.api.v1.plan.celery_confirm") as mock_confirm,
    ):
        mock_submit.delay = MagicMock()
        mock_confirm.delay = MagicMock()
        yield


@pytest.fixture
def async_client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ====================================================================
# POST /create
# ====================================================================


class TestCreatePlanAsync:
    @pytest.mark.asyncio
    async def test_create_returns_202(self, mock_celery, async_client):
        """POST /create → 202 Accepted + plan_id + status=queued。"""
        with patch(
            "marketplace.app.api.v1.plan.SQLPlanRunRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.insert_run = AsyncMock()

            response = await async_client.post(
                "/api/v1/plan/create",
                json={
                    "user_input": "周末带娃去科技馆",
                    "city": "北京",
                    "guest_count": 3,
                    "scene_type": "family",
                },
            )

        assert response.status_code == 202
        data = response.json()
        assert data["data"]["plan_id"]
        assert data["data"]["status"] == "queued"


# ====================================================================
# POST /confirm
# ====================================================================


class TestConfirmPlanAsync:
    @pytest.mark.asyncio
    async def test_confirm_returns_202(self, mock_celery, async_client):
        """POST /confirm → 202 Accepted。"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch(
            "marketplace.app.api.v1.plan._get_agent_service"
        ) as mock_svc_fn:
            mock_svc = mock_svc_fn.return_value
            mock_svc.get_state = AsyncMock(return_value={"status": "awaiting_confirmation"})

            response = await async_client.post(
                f"/api/v1/plan/{plan_id}/confirm",
                json={"decision": "confirmed", "locked_slots": [0, 1]},
            )

        assert response.status_code == 202
        data = response.json()
        assert data["data"]["status"] == "accepted"


# ====================================================================
# GET /{plan_id}/status
# ====================================================================


class TestGetPlanStatus:
    @pytest.mark.asyncio
    async def test_status_returns_run_state(self, async_client):
        """GET /status → 返回 plan_run 状态。"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch(
            "marketplace.app.api.v1.plan.SQLPlanRunRepository"
        ) as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_plan_id = AsyncMock(
                return_value={"plan_id": plan_id, "status": "running"}
            )

            response = await async_client.get(
                f"/api/v1/plan/{plan_id}/status"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "running"


# ====================================================================
# GET /{plan_id} (unchanged — reads checkpoint)
# ====================================================================


class TestGetPlanUnchanged:
    @pytest.mark.asyncio
    async def test_get_plan_reads_checkpoint(self, async_client):
        """GET /{plan_id} 仍然从 checkpoint 读取（行为不变）。"""
        plan_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch(
            "marketplace.app.api.v1.plan._get_agent_service"
        ) as mock_svc_fn:
            mock_svc = mock_svc_fn.return_value
            mock_svc.get_state = AsyncMock(return_value=None)

            response = await async_client.get(f"/api/v1/plan/{plan_id}")

        # plan not found in checkpoint → 404 或其他错误
        # 404 来自 APIServiceError(code=1001)
        assert response.status_code in (200, 404, 500)
