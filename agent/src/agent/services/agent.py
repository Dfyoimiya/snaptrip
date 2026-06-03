"""AgentService —— LangGraph 图执行服务层。

封装 CompiledStateGraph 的 ainvoke/aget_state，隐藏所有 LangGraph 类型
（Command, GraphInterrupt, StateSnapshot），对外只暴露纯 dict 和
InterruptError。

LangGraph >=1.2 的 ainvoke 不再抛出 GraphInterrupt —— 而是在返回的 dict
中注入 __interrupt__ 键。本模块负责剥离该内部键并转换为 InterruptError。

用于 Phase 2：API 路由解耦 LangGraph，为 Gateway 独立部署做准备。

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from langgraph.constants import INTERRUPT
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command


class InterruptError(Exception):
    """Graph 暂停等待人机协同确认。"""


def _strip_interrupts(result: dict, *, plan_id: str, context: str) -> dict:
    """从 ainvoke 返回的 dict 中剥离 __interrupt__ 私有键。

    LangGraph >=1.2 的 ainvoke 不再抛出 GraphInterrupt，而是将
    Interrupt 对象注入返回 dict 的 __interrupt__ 键中。
    该对象不可 JSON 序列化，必须先剥离再返回给 Celery/API。

    Returns:
        剥离后的纯 dict（不含 __interrupt__）
    Raises:
        InterruptError: 如果存在 pending interrupts（人机协同暂挂）
    """
    if not isinstance(result, dict) or INTERRUPT not in result:
        return result

    interrupts = result.pop(INTERRUPT)
    if interrupts:
        raise InterruptError(
            f"{context}: {len(interrupts)} pending interrupt(s) for {plan_id}"
        )
    return result


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

        LangGraph >=1.2 的 ainvoke 不会抛出 GraphInterrupt —— 中断信息
        通过返回 dict 的 __interrupt__ 键传递。本方法剥离该键并转为
        InterruptError。

        Args:
            initial_state: 初始状态 dict（含 plan_id, user_input 等）
            plan_id: 计划 ID，用作 checkpoint thread_id

        Returns:
            最终状态 dict（不含 LangGraph 内部键）

        Raises:
            InterruptError: 图在 consensus 节点暂停（人机协同）
        """
        config = self._config(plan_id)
        result: dict = await self._graph.ainvoke(initial_state, config)  # type: ignore[no-any-return,call-overload]
        return _strip_interrupts(result, plan_id=plan_id, context="invoke")

    async def resume(self, resume_data: dict, plan_id: str) -> dict:
        """从中断点恢复图执行（人机协同确认）。

        Args:
            resume_data: 用户决策 dict（decision, slot_index, locked_slots 等）
            plan_id: 计划 ID

        Returns:
            最终状态 dict（不含 LangGraph 内部键）

        Raises:
            InterruptError: 图再次暂停
        """
        cmd: Command = Command(resume=resume_data)
        config = self._config(plan_id)
        result: dict = await self._graph.ainvoke(cmd, config)  # type: ignore[no-any-return,call-overload]
        return _strip_interrupts(result, plan_id=plan_id, context="resume")

    async def get_state(self, plan_id: str) -> dict | None:
        """读取 checkpoint 中的当前状态。

        Args:
            plan_id: 计划 ID

        Returns:
            state.values dict（不含 LangGraph 内部键），
            若 checkpoint 不存在或 values 为空则返回 None
        """
        config = self._config(plan_id)
        state = await self._graph.aget_state(config)  # type: ignore[arg-type]
        if state is None or not state.values:
            return None
        values: dict = state.values  # type: ignore[no-any-return]
        return _strip_interrupts(values, plan_id=plan_id, context="get_state")

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    @staticmethod
    def _config(plan_id: str) -> dict:
        return {
            "configurable": {"thread_id": plan_id},
            "recursion_limit": 15,
        }
