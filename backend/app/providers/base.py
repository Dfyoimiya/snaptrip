"""LLM Provider 抽象基类。

所有 LLM Provider 继承 BaseLLMProvider，实现：
- chat(): 标准非流式调用
- chat_stream(): 流式调用（返回 AsyncIterator）
- get_pricing(): 返回模型定价
- supports_model(): 检查是否支持某模型

基类提供：
- HTTP 重试（指数退避 1s→2s，最多 2 次）
- 网络异常 → 领域异常自动转换
- 输入参数校验

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

import httpx

from app.core.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError
from app.schemas.llm import ChatResult, ModelPricing, StreamChunk

logger = logging.getLogger(__name__)

# 重试策略
_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 1.0  # 1s → 2s


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""

    provider_name: str = ""

    def __init__(self, api_key: str = "", base_url: str = "", timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    # ===== 抽象方法 =====

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> ChatResult:
        """非流式聊天"""
        ...

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> AsyncIterator[StreamChunk]:
        """流式聊天 —— 返回异步迭代器"""
        ...

    @abstractmethod
    def get_pricing(self, model: str) -> ModelPricing:
        """获取模型定价"""
        ...

    @abstractmethod
    def supports_model(self, model: str) -> bool:
        """检查是否支持该模型"""
        ...

    # ===== 参数校验 =====

    @staticmethod
    def _validate_chat_params(
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> None:
        """校验 chat 参数，不合法时抛出 LLMError。"""
        if not messages:
            raise LLMError("messages 不能为空")
        for i, msg in enumerate(messages):
            if "role" not in msg:
                raise LLMError(f"messages[{i}] 缺少 'role' 字段")
            if "content" not in msg:
                raise LLMError(f"messages[{i}] 缺少 'content' 字段")
        if not (0.0 <= temperature <= 2.0):
            raise LLMError(f"temperature 必须在 [0.0, 2.0] 范围内，当前值: {temperature}")
        if max_tokens < 1:
            raise LLMError(f"max_tokens 必须 >= 1，当前值: {max_tokens}")

    # ===== HTTP 重试 =====

    async def _http_post_with_retry(
        self,
        url: str,
        payload: dict,
        timeout: float,
    ) -> httpx.Response:
        """带指数退避的 HTTP POST，自动转换网络异常为领域异常。

        Retry 条件:
          - httpx.TimeoutException → LLMTimeoutError，重试
          - httpx.RequestError (网络错误) → LLMError，重试
          - HTTP 429 → LLMRateLimitError，重试
          - HTTP 5xx → LLMError，重试
          - 其他 4xx → 不重试，立即抛 LLMError

        Args:
            url: 请求 URL
            payload: JSON body
            timeout: 超时时间（秒）

        Returns:
            成功时的 httpx.Response

        Raises:
            LLMError / LLMTimeoutError / LLMRateLimitError
        """
        last_exception: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, headers=self._build_headers(), json=payload)
            except httpx.TimeoutException:
                last_exception = LLMTimeoutError(
                    details={"provider": self.provider_name, "url": url, "attempt": attempt + 1},
                )
                logger.warning("llm_timeout provider=%s attempt=%d", self.provider_name, attempt + 1)
            except httpx.RequestError as e:
                last_exception = LLMError(
                    f"网络错误: {e}",
                    details={"provider": self.provider_name, "url": url, "attempt": attempt + 1},
                )
                logger.warning(
                    "llm_network_error provider=%s error=%s attempt=%d",
                    self.provider_name,
                    str(e),
                    attempt + 1,
                )
            else:
                # HTTP 响应收到，检查状态码
                if resp.status_code == 200:
                    return resp

                if resp.status_code == 429:
                    last_exception = LLMRateLimitError(
                        details={"provider": self.provider_name, "http_status": 429, "attempt": attempt + 1},
                    )
                    logger.warning("llm_rate_limited provider=%s attempt=%d", self.provider_name, attempt + 1)
                elif resp.status_code >= 500:
                    last_exception = LLMError(
                        f"{self.provider_name} API 返回 {resp.status_code}: {resp.text[:300]}",
                        details={
                            "provider": self.provider_name,
                            "http_status": resp.status_code,
                            "attempt": attempt + 1,
                        },
                    )
                    logger.warning(
                        "llm_server_error provider=%s status=%d attempt=%d",
                        self.provider_name,
                        resp.status_code,
                        attempt + 1,
                    )
                else:
                    # 4xx (非 429)：不重试，立即抛出
                    raise LLMError(
                        f"{self.provider_name} API 返回 {resp.status_code}: {resp.text[:500]}",
                        details={"provider": self.provider_name, "http_status": resp.status_code},
                    )

            # 还有重试次数
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY * (2**attempt)  # 1s, 2s
                logger.info("llm_retry provider=%s attempt=%d delay=%.1fs", self.provider_name, attempt + 1, delay)
                await asyncio.sleep(delay)

        raise last_exception  # type: ignore[misc]

    # ===== 通用工具方法 =====

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _calculate_cost(pricing: ModelPricing, prompt_tokens: int, completion_tokens: int) -> float:
        """根据定价和用量计算成本（USD）"""
        prompt_cost = (prompt_tokens / 1000) * pricing.prompt_per_1k
        completion_cost = (completion_tokens / 1000) * pricing.completion_per_1k
        return round(prompt_cost + completion_cost, 8)
