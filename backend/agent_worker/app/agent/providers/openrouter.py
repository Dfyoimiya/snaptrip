"""OpenRouter Provider —— 多模型聚合网关。

OpenAI-compatible 格式，endpoint: {base_url}/chat/completions
支持通过 HTTP Header (HTTP-Referer, X-Title) 传递应用标识。

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator

import httpx

from agent_worker.app.agent.providers.base import BaseLLMProvider
from agent_worker.app.agent.schemas.llm import ChatResult, ModelPricing, StreamChunk, TokenUsage
from shared.core.exceptions import LLMError, LLMRateLimitError

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter 聚合网关 Provider"""

    provider_name = "openrouter"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 30.0,
        app_name: str = "SnapTrip",
        app_url: str = "https://snaptrip.cn",
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, timeout=timeout)
        self._app_name = app_name
        self._app_url = app_url

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._app_url,
            "X-Title": self._app_name,
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek/deepseek-chat",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> ChatResult:
        self._validate_chat_params(messages, temperature, max_tokens)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        url = f"{self._base_url}/chat/completions"

        t0 = time.monotonic()
        resp = await self._http_post_with_retry(url, payload, timeout)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        try:
            data = resp.json()
        except json.JSONDecodeError as e:
            raise LLMError(
                f"OpenRouter API 返回非 JSON 响应: {resp.text[:500]}",
                details={"provider": "openrouter", "http_status": resp.status_code},
            ) from e

        choice = data.get("choices", [{}])[0]
        usage_raw = data.get("usage", {})

        return ChatResult(
            content=choice.get("message", {}).get("content", ""),
            model=data.get("model", model),
            usage=TokenUsage(
                prompt_tokens=usage_raw.get("prompt_tokens", 0),
                completion_tokens=usage_raw.get("completion_tokens", 0),
                total_tokens=usage_raw.get("total_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason", "stop"),
            latency_ms=elapsed_ms,
            provider="openrouter",
        )

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str = "deepseek/deepseek-chat",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> AsyncIterator[StreamChunk]:
        self._validate_chat_params(messages, temperature, max_tokens)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        url = f"{self._base_url}/chat/completions"

        try:
            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream("POST", url, headers=self._build_headers(), json=payload) as resp,
            ):
                if resp.status_code == 429:
                    raise LLMRateLimitError(details={"provider": "openrouter", "http_status": 429})
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise LLMError(
                        f"OpenRouter API 返回 {resp.status_code}: {body.decode('utf-8', errors='replace')[:500]}",
                        details={"provider": "openrouter", "http_status": resp.status_code},
                    )

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    yield StreamChunk(
                        content=delta.get("content", ""),
                        finish_reason=chunk.get("choices", [{}])[0].get("finish_reason"),
                        model=chunk.get("model", model),
                    )
        except httpx.TimeoutException as e:
            raise LLMError("OpenRouter 流式调用超时", details={"provider": "openrouter"}) from e
        except httpx.RequestError as e:
            raise LLMError(f"OpenRouter 网络错误: {e}", details={"provider": "openrouter"}) from e

    def get_pricing(self, model: str) -> ModelPricing:
        return ModelPricing(prompt_per_1k=0.0, completion_per_1k=0.0)

    def supports_model(self, model: str) -> bool:
        return bool(model and "/" in model)
