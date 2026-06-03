"""Saga 协调器 —— 长事务补偿机制。

在 DAG 执行过程中，记录已完成的步骤。当某个节点失败时，
根据 fallback_policy 决定是否回滚（执行补偿）。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from app.schemas.tool import ToolInvocation, ToolResult


class SagaCoordinator:
    """Saga 协调器 —— 记录步骤 + 失败补偿"""

    def __init__(self) -> None:
        self.transaction_id: str = str(uuid.uuid4())
        self._completed: list[tuple[ToolInvocation, ToolResult]] = []
        self._compensations: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}

    def register_compensation(self, tool_name: str, compensate_fn: Callable[..., Coroutine[Any, Any, None]]) -> None:
        """为工具注册补偿函数"""
        self._compensations[tool_name] = compensate_fn

    def record_step(self, invocation: ToolInvocation, result: ToolResult) -> None:
        """记录已完成的步骤"""
        self._completed.append((invocation, result))

    async def compensate(self) -> list[str]:
        """按逆序执行补偿，每一步失败继续执行剩余补偿。

        Returns:
            失败的补偿步骤列表
        """
        errors: list[str] = []
        for inv, _result in reversed(self._completed):
            compensate_fn = self._compensations.get(inv.tool_name)
            if compensate_fn is None:
                continue
            try:
                await compensate_fn(inv.tool_name, inv.params)
            except Exception as e:
                errors.append(f"{inv.tool_name}: {e}")
        return errors
