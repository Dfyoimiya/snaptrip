"""熔断器 —— 三态熔断 (CLOSED / OPEN / HALF_OPEN)。

标准熔断器实现：
- CLOSED: 正常执行，累计失败次数
- OPEN: 熔断打开，拒绝请求，等待 recovery_timeout
- HALF_OPEN: 尝试恢复，允许 1 次探测请求

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import enum
import time
from collections.abc import Callable
from typing import Any

from app.schemas.tool import ToolResult


class CircuitState(enum.StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """三态熔断器"""

    def __init__(
        self,
        tool_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.tool_name = tool_name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> CircuitState:
        self._try_transition()
        return self._state

    async def call(
        self, func: Callable, *args: Any, invocation_id: str = "", **kwargs: Any,
    ) -> ToolResult:
        """受熔断保护地执行函数。

        Args:
            func: 要保护的异步函数，返回 ToolResult
            invocation_id: 用于错误结果的 invocation_id
            *args, **kwargs: 传递给 func 的参数

        Returns:
            ToolResult
        """
        self._try_transition()

        if self._state == CircuitState.OPEN:
            return ToolResult(
                invocation_id=invocation_id or "cb",
                status="failure",
                error_code="CIRCUIT_OPEN",
                error_message=f"熔断器 {self.tool_name} 已打开",
                latency_ms=0,
            )

        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            result = ToolResult(
                invocation_id=invocation_id or "cb",
                status="failure",
                error_code="EXECUTION_ERROR",
                error_message=str(e),
                latency_ms=0,
            )

        if result.status in ("success", "degraded"):
            self._on_success()
        else:
            self._on_failure()

        return result

    def _try_transition(self) -> None:
        now = time.monotonic()
        if self._state == CircuitState.OPEN and now - self._last_failure_time >= self._recovery_timeout:
            self._state = CircuitState.HALF_OPEN

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._state = CircuitState.OPEN
