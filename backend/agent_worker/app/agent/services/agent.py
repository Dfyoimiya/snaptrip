"""AgentService —— LangGraph 图执行服务层。

封装 CompiledStateGraph 的 ainvoke/aget_state，隐藏所有 LangGraph 类型
（Command, GraphInterrupt, StateSnapshot），对外只暴露纯 dict 和
InterruptError。

用于 Phase 2：API 路由解耦 LangGraph，为 Gateway 独立部署做准备。

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from langgraph.errors import GraphInterrupt
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command


class InterruptError(Exception):
    """Graph 暂停等待人机协同确认。"""


class AgentService:
    """封装编译后的 LangGraph StateGraph。

    隐藏所有 langgraph 类型，调用方只看到纯 dict 和 InterruptError。
    """

    def __init__(self, graph: CompiledStateGraph) -> None:
        self._graph = graph

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def invoke(self, initial_state: dict, plan_id: str) -> dict:
        """执行首次图调用。

        Args:
            initial_state: 初始状态 dict（含 plan_id, user_input 等）
            plan_id: 计划 ID，用作 checkpoint thread_id

        Returns:
            最终状态 dict

        Raises:
            InterruptError: 图在 consensus 节点暂停（人机协同）
        """
        config = self._config(plan_id)
        try:
            return await self._graph.ainvoke(initial_state, config)  # type: ignore[no-any-return,call-overload]
        except GraphInterrupt:
            raise InterruptError() from None

    async def resume(self, resume_data: dict, plan_id: str) -> dict:
        """从中断点恢复图执行（人机协同确认）。

        Args:
            resume_data: 用户决策 dict（decision, slot_index, locked_slots 等）
            plan_id: 计划 ID

        Returns:
            最终状态 dict

        Raises:
            InterruptError: 图再次暂停
        """
        cmd: Command = Command(resume=resume_data)
        config = self._config(plan_id)
        try:
            return await self._graph.ainvoke(cmd, config)  # type: ignore[no-any-return,call-overload]
        except GraphInterrupt:
            raise InterruptError() from None

    async def get_state(self, plan_id: str) -> dict | None:
        """读取 checkpoint 中的当前状态。

        Args:
            plan_id: 计划 ID

        Returns:
            state.values dict，若 checkpoint 不存在或 values 为空则返回 None
        """
        config = self._config(plan_id)
        state = await self._graph.aget_state(config)  # type: ignore[arg-type]
        if state is None or not state.values:
            return None
        return state.values  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    @staticmethod
    def _config(plan_id: str) -> dict:
        return {"configurable": {"thread_id": plan_id}}
