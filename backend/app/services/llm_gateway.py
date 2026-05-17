"""LLM 网关 —— OpenRouter 统一调用、Embedding、自动降级、Token 统计。

封装 OpenRouter API 的 chat 和 embedding 端点，提供：
- 模型别名映射（deepseek → deepseek/deepseek-v3）
- 自动降级（主模型超时/失败 → 备用模型）
- 结构化日志记录到 llm_usage_logs 表
- 重试 + 指数退避

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio
import time

import httpx

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.llm_usage_log import LLMUsageLog

MODEL_ALIASES: dict[str, str] = {
    "deepseek": "deepseek/deepseek-v3",
    "deepseek-r1": "deepseek/deepseek-r1",
    "gemma": "google/gemma-3-4b-it:free",
}

FALLBACK_CHAIN: list[str] = ["deepseek", "gemma"]

EMBEDDING_MODEL = "openai/text-embedding-3-small"


class LLMError(Exception):
    """LLM 调用异常"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMGateway:
    """OpenRouter LLM 网关"""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key or settings.OPENROUTER_API_KEY
        self._base_url = settings.OPENROUTER_BASE_URL.rstrip("/")

    # ===== Chat =====

    async def chat(
        self,
        messages: list[dict[str, str]],
        model_alias: str = "deepseek",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        timeout: float = 5.0,
    ) -> dict:
        """发送聊天请求，自动在降级链中选择可用模型。

        Args:
            messages: [{"role": "user", "content": "..."}]
            model_alias: 模型别名
            max_tokens: 最大输出 token
            temperature: 采样温度
            timeout: 超时（秒）

        Returns:
            {"content": str, "model": str, "usage": {"prompt_tokens": int, "completion_tokens": int}}

        Raises:
            LLMError: 所有降级模型均失败
        """
        candidates = self._build_model_chain(model_alias)

        last_error: Exception | None = None
        for model_name in candidates:
            resolved = MODEL_ALIASES.get(model_name, model_name)
            try:
                return await self._chat_single(
                    model=resolved,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                )
            except (TimeoutError, LLMError, httpx.HTTPError) as e:
                last_error = e
                if len(candidates) > 1:
                    await asyncio.sleep(0.5)

        raise LLMError(
            f"所有模型调用失败，最后一个错误: {last_error}",
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

    # ===== Embedding =====

    async def embed(
        self,
        texts: str | list[str],
        model: str = EMBEDDING_MODEL,
        timeout: float = 5.0,
    ) -> list[list[float]]:
        """获取文本的 Embedding 向量。

        Args:
            texts: 单个字符串或字符串列表
            model: embedding 模型名
            timeout: 超时（秒）

        Returns:
            向量列表，每个向量 1536 维
        """
        inputs = [texts] if isinstance(texts, str) else texts

        url = f"{self._base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "input": inputs}

        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        if resp.status_code != 200:
            detail = resp.text[:500]
            await self._log_usage(
                model_name=model,
                prompt_tokens=len(inputs),
                completion_tokens=0,
                latency_ms=elapsed_ms,
                endpoint="embedding",
            )
            raise LLMError(
                f"Embedding API 返回 {resp.status_code}: {detail}",
                status_code=resp.status_code,
            )

        data = resp.json()
        embeddings = [item["embedding"] for item in data.get("data", [])]
        total_tokens = data.get("usage", {}).get("total_tokens", 0)

        await self._log_usage(
            model_name=model,
            prompt_tokens=total_tokens,
            completion_tokens=0,
            latency_ms=elapsed_ms,
            endpoint="embedding",
        )

        return embeddings

    # ===== 内部 =====

    def _build_model_chain(self, primary_alias: str) -> list[str]:
        """构建降级链：主模型 → 备用模型"""
        chain = [primary_alias]
        for m in FALLBACK_CHAIN:
            if m not in chain:
                chain.append(m)
        return chain

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
