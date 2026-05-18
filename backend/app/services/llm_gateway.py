"""LLM 网关 —— DeepSeek 官网 API + Embedding + Token 统计。

封装 DeepSeek API 的 chat 端点，提供：
- 自动降级（主模型超时/失败 → retry）
- 结构化日志记录到 llm_usage_logs 表

Author: SnapTrip Team
Date: 2026-05-17 / DeepSeek migration 2026-05-18
"""

from __future__ import annotations

import asyncio
import time

import httpx

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.llm_usage_log import LLMUsageLog


class LLMError(Exception):
    """LLM 调用异常"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMGateway:
    """DeepSeek LLM 网关"""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key or settings.DEEPSEEK_API_KEY
        self._base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")

    # ===== Chat =====

    async def chat(
        self,
        messages: list[dict[str, str]],
        model_alias: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 5.0,
    ) -> dict:
        """发送聊天请求到 DeepSeek API。

        Args:
            messages: [{"role": "user", "content": "..."}]
            model_alias: 模型名（空字符串默认使用 settings.LLM_MODEL）
            max_tokens: 最大输出 token
            temperature: 采样温度
            timeout: 超时（秒）

        Returns:
            {"content": str, "model": str, "usage": {"prompt_tokens": int, "completion_tokens": int}}

        Raises:
            LLMError: 调用失败
        """
        model = model_alias or settings.LLM_MODEL

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return await self._chat_single(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                )
            except (TimeoutError, LLMError, httpx.HTTPError) as e:
                last_error = e
                if attempt == 0:
                    await asyncio.sleep(1.0)

        raise LLMError(
            f"DeepSeek API 调用失败: {last_error}",
            status_code=getattr(last_error, "status_code", None),
        )

    async def _chat_single(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> dict:
        """单次 LLM 调用"""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code != 200:
            detail = resp.text[:500]
            await self._log_usage(
                model_name=model,
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=elapsed_ms,
                endpoint="chat",
            )
            raise LLMError(
                f"LLM API 返回 {resp.status_code}: {detail}",
                status_code=resp.status_code,
            )

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        await self._log_usage(
            model_name=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=elapsed_ms,
            endpoint="chat",
        )

        return {
            "content": content,
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        }

    # ===== 内部 =====

    async def _log_usage(
        self,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        endpoint: str,
    ) -> None:
        """异步写入 llm_usage_logs 表（失败时静默忽略）"""
        try:
            async with AsyncSessionLocal() as db:
                log = LLMUsageLog(
                    model_name=model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    endpoint=endpoint,
                )
                db.add(log)
                await db.commit()
        except Exception:
            pass
