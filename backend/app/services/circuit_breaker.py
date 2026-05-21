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
from collections.abc import Awaitable, Callable
from typing import Any

from app.schemas.tool import ToolResult
from app.schemas.tool_provider import ToolProviderConfig


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

    async def call(self, func: Callable[..., Awaitable[ToolResult]], *args: Any, **kwargs: Any) -> ToolResult:
        """受熔断保护地执行函数。

        Args:
            func: 要保护的异步函数，返回 ToolResult
            *args, **kwargs: 传递给 func 的参数

        Returns:
            ToolResult
        """
        self._try_transition()

        if self._state == CircuitState.OPEN:
            return ToolResult(
                invocation_id="cb",
                status="failure",
                error_code="CIRCUIT_OPEN",
                error_message=f"熔断器 {self.tool_name} 已打开",
                latency_ms=0,
            )

        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            result = ToolResult(
                invocation_id="cb",
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

    @property
    def failure_count(self) -> int:
        return self._failure_count


class CircuitBreakerRegistry:
    """双层熔断器注册表。

    L1 Provider 级: 同一 Provider 的所有 tools 共享熔断。
        美团 API 整体异常时，所有美团 tools 快速失败。

    L2 Tool 级: 单个 tool 的业务逻辑错误单独熔断。
        （如特定 POI 不可预订、参数非法等）
    """

    def __init__(self) -> None:
        self._provider_cbs: dict[str, CircuitBreaker] = {}
        self._tool_cbs: dict[str, CircuitBreaker] = {}

    def register_provider(
        self,
        provider: str,
        failure_threshold: int = 15,
        recovery_timeout: float = 60.0,
    ) -> None:
        """注册 Provider 级熔断器。

        Provider 级阈值更宽松（共享配额，个别 tool 失败不影响全局）。
        """
        self._provider_cbs[provider] = CircuitBreaker(
            tool_name=f"provider:{provider}",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def register_tool(
        self,
        tool_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        """注册 Tool 级熔断器。"""
        self._tool_cbs[tool_name] = CircuitBreaker(
            tool_name=tool_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def is_open(self, tool_name: str, provider: str = "") -> bool:
        """检查是否已熔断（先 L1 后 L2）。"""
        if provider and provider in self._provider_cbs and self._provider_cbs[provider].state == CircuitState.OPEN:
            return True
        if tool_name in self._tool_cbs:
            return self._tool_cbs[tool_name].state == CircuitState.OPEN
        return False

    def on_success(self, tool_name: str, provider: str = "") -> None:
        """记录成功，关闭两层熔断。"""
        if provider and provider in self._provider_cbs:
            self._provider_cbs[provider]._on_success()
        if tool_name in self._tool_cbs:
            self._tool_cbs[tool_name]._on_success()

    def on_failure(self, tool_name: str, provider: str = "") -> None:
        """记录失败，可能需要打开熔断。"""
        if provider and provider in self._provider_cbs:
            self._provider_cbs[provider]._on_failure()
        if tool_name in self._tool_cbs:
            self._tool_cbs[tool_name]._on_failure()

    def get_tool_state(self, tool_name: str) -> CircuitState:
        """获取 Tool 级熔断状态。"""
        cb = self._tool_cbs.get(tool_name)
        return cb.state if cb else CircuitState.CLOSED

    def get_provider_state(self, provider: str) -> CircuitState:
        """获取 Provider 级熔断状态。"""
        cb = self._provider_cbs.get(provider)
        return cb.state if cb else CircuitState.CLOSED


def build_circuit_breaker_registry(
    tool_configs: dict[str, ToolProviderConfig] | None = None,
) -> CircuitBreakerRegistry:
    """工厂函数：从 tools.toml 配置构建双层熔断器注册表。

    Args:
        tool_configs: {tool_name: ToolProviderConfig} 字典

    Returns:
        已注册所有 tools 和 providers 的 CircuitBreakerRegistry
    """
    registry = CircuitBreakerRegistry()

    if not tool_configs:
        return registry

    providers_seen: set[str] = set()

    for name, cfg in tool_configs.items():
        registry.register_tool(
            tool_name=name,
            failure_threshold=cfg.circuit_breaker_threshold,
            recovery_timeout=float(cfg.circuit_recovery_s),
        )

        if cfg.provider and cfg.provider not in providers_seen:
            providers_seen.add(cfg.provider)
            registry.register_provider(provider=cfg.provider)

    return registry
