"""Phase 3a 单元测试：Celery 任务异步执行。

测试目标：
  1. submit_plan — 调用 AgentService.invoke，处理 InterruptError
  2. confirm_plan — 调用 AgentService.resume，处理 InterruptError
  3. 任务异常 → plan_run status=failed
  4. _get_worker_agent_service 懒加载缓存

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agent.services.agent import InterruptError

# ── helpers ──


def _mock_service(invoke_result=None, invoke_side_effect=None):
    """构造 mock AgentService。"""
    svc = MagicMock()
    svc.invoke = AsyncMock(return_value=invoke_result, side_effect=invoke_side_effect)
    svc.resume = AsyncMock(return_value=invoke_result, side_effect=invoke_side_effect)
    svc.get_state = AsyncMock(return_value=None)
    return svc


# ====================================================================
# submit_plan
# ====================================================================


class TestSubmitPlan:
    def test_submit_plan_success(self):
        """正常执行 → 返回 state dict，更新 status=completed。"""
        from agent.tasks.plan_tasks import submit_plan

        svc = _mock_service(invoke_result={"status": "completed", "plan_id": "p1"})

        with (
            patch("agent.tasks.plan_tasks._get_worker_agent_service", return_value=svc),
            patch("agent.tasks.plan_tasks._update_status") as mock_update,
        ):
            result = submit_plan({"plan_id": "p1"}, "p1")

        assert result["status"] == "completed"
        mock_update.assert_any_call("p1", "running")
        mock_update.assert_any_call("p1", "completed")

    def test_submit_plan_interrupted(self):
        """InterruptError → status=awaiting_confirmation，任务正常结束。"""
        from agent.tasks.plan_tasks import submit_plan

        svc = _mock_service(invoke_side_effect=InterruptError())

        with (
            patch("agent.tasks.plan_tasks._get_worker_agent_service", return_value=svc),
            patch("agent.tasks.plan_tasks._update_status") as mock_update,
        ):
            result = submit_plan({"plan_id": "p2"}, "p2")

        assert result["status"] == "awaiting_confirmation"
        mock_update.assert_any_call("p2", "awaiting_confirmation")

    def test_submit_plan_failure(self):
        """其他异常 → status=failed，re-raise。"""
        from agent.tasks.plan_tasks import submit_plan

        svc = _mock_service(invoke_side_effect=RuntimeError("boom"))

        with (
            patch("agent.tasks.plan_tasks._get_worker_agent_service", return_value=svc),
            patch("agent.tasks.plan_tasks._update_status") as mock_update,
            pytest.raises(RuntimeError, match="boom"),
        ):
            submit_plan({"plan_id": "p3"}, "p3")

        mock_update.assert_any_call("p3", "failed", error_message="boom")


# ====================================================================
# confirm_plan
# ====================================================================


class TestConfirmPlan:
    def test_confirm_plan_success(self):
        """正常 resume → 返回 state dict。"""
        from agent.tasks.plan_tasks import confirm_plan

        svc = _mock_service(invoke_result={"status": "completed", "plan_id": "p4"})

        with (
            patch("agent.tasks.plan_tasks._get_worker_agent_service", return_value=svc),
            patch("agent.tasks.plan_tasks._update_status") as mock_update,
        ):
            result = confirm_plan({"decision": "confirmed"}, "p4")

        assert result["status"] == "completed"
        mock_update.assert_any_call("p4", "completed")

    def test_confirm_plan_interrupted(self):
        """resume InterruptError → status=awaiting_confirmation。"""
        from agent.tasks.plan_tasks import confirm_plan

        svc = _mock_service(invoke_side_effect=InterruptError())

        with (
            patch("agent.tasks.plan_tasks._get_worker_agent_service", return_value=svc),
            patch("agent.tasks.plan_tasks._update_status") as mock_update,
        ):
            result = confirm_plan({"decision": "confirmed"}, "p5")

        assert result["status"] == "awaiting_confirmation"
        mock_update.assert_any_call("p5", "awaiting_confirmation")


# ====================================================================
# module-level cache
# ====================================================================


class TestWorkerAgentServiceCache:
    def test_cache_reuses_instance(self):
        """模块级缓存：第二次调用返回同一实例。"""
        from agent.tasks import plan_tasks

        plan_tasks._worker_agent_service = None

        svc = _mock_service()
        with patch("agent.tasks.plan_tasks._build_worker_agent_service", return_value=svc) as mock_build:
            first = plan_tasks._get_worker_agent_service()
            second = plan_tasks._get_worker_agent_service()

            assert first is second
            mock_build.assert_called_once()
