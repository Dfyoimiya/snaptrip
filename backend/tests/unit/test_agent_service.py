"""Phase 2 单元测试：AgentService 封装 LangGraph 类型。

测试目标：
  1. AgentService.invoke — 封装 graph.ainvoke，GraphInterrupt → InterruptError
  2. AgentService.resume — 内部构造 Command(resume=...)，拦截 GraphInterrupt
  3. AgentService.get_state — 封装 graph.aget_state，隐藏 StateSnapshot
  4. plan.py 不 import langgraph 类型（GraphInterrupt / Command）

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from agent_worker.app.agent.services.agent import AgentService, InterruptError


def _mock_state_snapshot(values: dict | None):
    """构造 fake langgraph StateSnapshot，只带 .values 属性。"""
    snap = MagicMock()
    snap.values = values
    return snap


# ====================================================================
# invoke
# ====================================================================


class TestAgentServiceInvoke:
    @pytest.mark.asyncio
    async def test_invoke_returns_state(self):
        """正常执行 → 返回 state dict。"""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={"status": "completed", "plan_id": "p1"})

        svc = AgentService(mock_graph)
        result = await svc.invoke({"plan_id": "p1"}, "p1")

        assert result == {"status": "completed", "plan_id": "p1"}
        mock_graph.ainvoke.assert_awaited_once_with({"plan_id": "p1"}, {"configurable": {"thread_id": "p1"}})

    @pytest.mark.asyncio
    async def test_invoke_raises_interrupted(self):
        """GraphInterrupt → InterruptError。"""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=GraphInterrupt("need confirm"))

        svc = AgentService(mock_graph)
        with pytest.raises(InterruptError):
            await svc.invoke({"plan_id": "p2"}, "p2")


# ====================================================================
# resume
# ====================================================================


class TestAgentServiceResume:
    @pytest.mark.asyncio
    async def test_resume_returns_state(self):
        """resume 正常执行 → 返回 state dict。"""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={"status": "confirmed", "plan_id": "p3"})

        svc = AgentService(mock_graph)
        resume_data = {"decision": "confirmed", "slot_index": 0, "locked_slots": [0]}
        result = await svc.resume(resume_data, "p3")

        assert result == {"status": "confirmed", "plan_id": "p3"}

        # 验证内部构造了 Command(resume=resume_data)
        call_args = mock_graph.ainvoke.await_args
        assert call_args is not None
        cmd = call_args[0][0]
        assert isinstance(cmd, Command)
        assert cmd.resume == resume_data

    @pytest.mark.asyncio
    async def test_resume_raises_interrupted(self):
        """resume 时 GraphInterrupt → InterruptError。"""
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=GraphInterrupt("need confirm"))

        svc = AgentService(mock_graph)
        with pytest.raises(InterruptError):
            await svc.resume({"decision": "confirmed"}, "p4")


# ====================================================================
# get_state
# ====================================================================


class TestAgentServiceGetState:
    @pytest.mark.asyncio
    async def test_get_state_returns_dict(self):
        """checkpoint 存在 → 返回 state.values dict。"""
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=_mock_state_snapshot({"status": "interrupted", "plan_id": "p5"}))

        svc = AgentService(mock_graph)
        result = await svc.get_state("p5")

        assert result == {"status": "interrupted", "plan_id": "p5"}
        mock_graph.aget_state.assert_awaited_once_with({"configurable": {"thread_id": "p5"}})

    @pytest.mark.asyncio
    async def test_get_state_returns_none(self):
        """checkpoint 不存在 → 返回 None。"""
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=None)

        svc = AgentService(mock_graph)
        result = await svc.get_state("p6")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_state_returns_none_for_null_values(self):
        """checkpoint 存在但 values 为 None → 返回 None。"""
        mock_graph = MagicMock()
        mock_graph.aget_state = AsyncMock(return_value=_mock_state_snapshot(None))

        svc = AgentService(mock_graph)
        result = await svc.get_state("p7")

        assert result is None
