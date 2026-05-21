"""BaseToolProvider —— 本地生活工具 Provider 抽象基类。

所有 Tool Provider 继承 BaseToolProvider，实现:
  - call(): 标准非流式调用
  - cancel(): 取消预订/订单
  - query_status(): 查询物理操作状态
  - supports_tool(): 检查是否支持某工具

基类提供:
  - HTTP 重试（per-tool 配置，指数退避）
  - 网络异常 → 领域异常自动转换
  - 超时自动标记 UNKNOWN 物理状态

与 BaseLLMProvider 的关键差异:
  - 不提供 chat_stream()（工具调用不需要流式）
  - 新增 cancel() 和 query_status()（物理操作独有）
  - 超时返回 UNKNOWN 而非抛异常（物理操作不可假定失败）

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod

import httpx

from app.core.exceptions import GatewayError
from app.schemas.tool_provider import PhysicalActionState, ToolProviderResult

logger = logging.getLogger(__name__)


class ToolProviderError(GatewayError):
    """Tool Provider 专用异常。"""

    def __init__(
        self,
        message: str = "工具调用失败",
        details: dict | None = None,
        code: str = "TOOL_PROVIDER_ERROR",
    ) -> None:
        super().__init__(code=code, message=message, details=details)


class ToolTimeoutError(ToolProviderError):
    """工具调用超时 —— 物理操作返回 UNKNOWN 而非抛出此异常。"""

    def __init__(self, message: str = "工具调用超时", details: dict | None = None) -> None:
        super().__init__(code="TOOL_TIMEOUT", message=message, details=details)


class BaseToolProvider(ABC):
    """本地生活工具 Provider 抽象基类。

    每个子类对应一个外部 API 供应商（美团、猫眼、点评等）。
    """

    provider_name: str = ""

    def __init__(self, base_url: str = "", timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ===== 抽象方法 =====

    @abstractmethod
    async def call(
        self,
        tool_name: str,
        params: dict,
        idempotency_key: str,
        timeout: float = 30.0,
    ) -> ToolProviderResult:
        """执行单个工具调用。

        Args:
            tool_name: 工具名 (search_poi, book_table, ...)
            params: 工具参数
            idempotency_key: 幂等键（由 ExecutionEngine 生成）
            timeout: 超时时间（秒）

        Returns:
            ToolProviderResult
        """
        ...

    @abstractmethod
    async def cancel(self, tool_name: str, booking_ref: str) -> ToolProviderResult:
        """取消预订/订单（Saga 补偿用）。

        Args:
            tool_name: 工具名
            booking_ref: 第三方返回的预订凭证

        Returns:
            ToolProviderResult
        """
        ...

    @abstractmethod
    async def query_status(self, tool_name: str, booking_ref: str) -> PhysicalActionState:
        """查询物理操作状态（UNKNOWN 异步确认用）。

        Args:
            tool_name: 工具名
            booking_ref: 第三方返回的预订凭证

        Returns:
            PhysicalActionState
        """
        ...

    @abstractmethod
    def supports_tool(self, tool_name: str) -> bool:
        """检查是否支持该工具。"""
        ...

    # ===== HTTP 重试（基类提供） =====

    async def _http_post_with_retry(
        self,
        url: str,
        payload: dict,
        timeout: float,
        max_retries: int = 2,
        retry_delay_ms: int = 1000,
    ) -> httpx.Response:
        """带指数退避的 HTTP POST，自动转换网络异常。

        Retry 条件:
          - httpx.TimeoutException → 重试
          - httpx.RequestError (网络错误) → 重试
          - HTTP 429 → 重试
          - HTTP 5xx → 重试
          - 其他 4xx → 不重试，立即抛 ToolProviderError

        Args:
            url: 请求 URL
            payload: JSON body
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            retry_delay_ms: 基础重试延迟（毫秒）

        Returns:
            成功时的 httpx.Response

        Raises:
            ToolProviderError / ToolTimeoutError
        """
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, json=payload)
            except httpx.TimeoutException:
                last_exception = ToolTimeoutError(
                    details={"provider": self.provider_name, "url": url, "attempt": attempt + 1},
                )
                logger.warning("tool_timeout provider=%s attempt=%d", self.provider_name, attempt + 1)
            except httpx.RequestError as e:
                last_exception = ToolProviderError(
                    f"网络错误: {e}",
                    details={"provider": self.provider_name, "url": url, "attempt": attempt + 1},
                )
                logger.warning(
                    "tool_network_error provider=%s error=%s attempt=%d",
                    self.provider_name,
                    str(e),
                    attempt + 1,
                )
            else:
                if resp.status_code == 200:
                    return resp

                if resp.status_code == 429:
                    last_exception = ToolProviderError(
                        f"{self.provider_name} API 速率限制",
                        details={"provider": self.provider_name, "http_status": 429, "attempt": attempt + 1},
                        code="TOOL_RATE_LIMIT",
                    )
                elif resp.status_code >= 500:
                    last_exception = ToolProviderError(
                        f"{self.provider_name} API 返回 {resp.status_code}: {resp.text[:300]}",
                        details={
                            "provider": self.provider_name,
                            "http_status": resp.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                else:
                    raise ToolProviderError(
                        f"{self.provider_name} API 返回 {resp.status_code}: {resp.text[:500]}",
                        details={"provider": self.provider_name, "http_status": resp.status_code},
                    )

            # 还有重试次数
            if attempt < max_retries:
                delay = retry_delay_ms / 1000.0 * (2**attempt)
                logger.info(
                    "tool_retry provider=%s attempt=%d delay=%.1fs",
                    self.provider_name,
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)

        raise last_exception  # type: ignore[misc]

    # ===== 通用工具方法 =====

    @staticmethod
    def _unknown_result(
        tool_name: str,
        idempotency_key: str,
        latency_ms: int = 0,
        error_message: str = "",
    ) -> ToolProviderResult:
        """构建 UNKNOWN 物理状态的结果 —— HTTP 超时/网络错误时使用。"""
        return ToolProviderResult(
            status="unknown",
            physical_state=PhysicalActionState.UNKNOWN,
            error_code="UNKNOWN",
            error_message=error_message or f"{tool_name} 调用超时，状态不明",
            latency_ms=latency_ms,
            retryable=False,  # 物理操作超时不自动重试，交给 PhysicalConfirmator
        )

    @staticmethod
    def _timing() -> float:
        """返回当前 monotonic 时间（秒），用于延迟计算。"""
        return time.monotonic()
