"""LiteLLM Adapter —— OpenAI SDK 指向 litellm-proxy。

替代手写 HTTP/SSE/重试 provider 栈。
重试、限流、认证由 litellm-proxy Docker 服务处理。

Author: SnapTrip Team
Date: 2026-05-25
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

import tomllib
from openai import AsyncOpenAI
from snaptrip_shared.core.config import settings
from snaptrip_shared.core.exceptions import LLMError

from agent.ports.llm import LLMPort
from agent.schemas.llm import ModelPricing, StreamChunk
from agent.services.llm_gateway import log_llm_usage

logger = logging.getLogger(__name__)


def _load_pricing() -> dict[str, ModelPricing]:
    """从 litellm/models.toml 加载定价表（仅用于 DB 成本记录）。"""
    config_path = Path(settings.LLM_PROVIDER_CONFIG)
    if not config_path.is_absolute():
        config_path = _find_project_root() / settings.LLM_PROVIDER_CONFIG
    if not config_path.exists():
        logger.info("litellm_pricing_config_not_found: %s", str(config_path))
        return {}
    try:
        data = tomllib.loads(config_path.read_text())
        pricing: dict[str, ModelPricing] = {}
        for alias, cfg in data.get("models", {}).items():
            pricing[alias] = ModelPricing(
                prompt_per_1k=cfg.get("prompt_per_1k", 0.0),
                completion_per_1k=cfg.get("completion_per_1k", 0.0),
            )
        return pricing
    except Exception:
        logger.warning("litellm_pricing_parse_failed", exc_info=True)
        return {}


def _find_project_root() -> Path:
    """向上查找 pyproject.toml 确定 monorepo 根目录。"""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return Path.cwd()


class LiteLLMAdapter(LLMPort):
    """基于 LiteLLM Proxy 的 LLM 适配器。

    使用 openai.AsyncOpenAI 指向 litellm-proxy Docker 服务。
    LiteLLM 处理上游认证、重试、限流。
    """

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.LITELLM_BASE_URL,
            api_key=settings.LITELLM_API_KEY,
            timeout=60.0,
            max_retries=2,
        )
        self._pricing = _load_pricing()

    # ── LLMPort 实现 ──────────────────────────────────────────

    async def chat_json(
        self,
        *,
        prompt: str,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict:
        model = model_alias or settings.LLM_DEFAULT_MODEL
        t0 = time.monotonic()

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_s,
            )
        except Exception as e:
            raise LLMError(
                f"LiteLLM 调用失败: {e}",
                details={"model_alias": model},
            ) from e

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        usage = response.usage
        if usage:
            pricing = self._pricing.get(model)
            cost_usd = 0.0
            if pricing:
                prompt_tokens = usage.prompt_tokens or 0
                completion_tokens = usage.completion_tokens or 0
                cost_usd = round(
                    (prompt_tokens / 1000) * pricing.prompt_per_1k
                    + (completion_tokens / 1000) * pricing.completion_per_1k,
                    8,
                )
            await log_llm_usage(
                model_name=response.model or model,
                provider="litellm",
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                latency_ms=elapsed_ms,
                cost_usd=cost_usd,
            )

        content = response.choices[0].message.content or ""
        content = content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        try:
            return json.loads(content) if content else {}
        except json.JSONDecodeError as e:
            raise LLMError(
                f"LLM 返回非 JSON 内容: {content[:200]}",
                details={"model_alias": model},
            ) from e

    async def chat_stream(
        self,
        *,
        prompt: str,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncIterator[StreamChunk]:
        model = model_alias or settings.LLM_DEFAULT_MODEL
        t0 = time.monotonic()

        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_s,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta:
                    yield StreamChunk(
                        content=chunk.choices[0].delta.content or "",
                        finish_reason=chunk.choices[0].finish_reason,
                        model=chunk.model or model,
                    )
        except Exception as e:
            raise LLMError(
                f"LiteLLM 流式调用失败: {e}",
                details={"model_alias": model},
            ) from e
        finally:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            await log_llm_usage(
                model_name=model,
                provider="litellm",
                latency_ms=elapsed_ms,
                endpoint="chat_stream",
            )

    async def embed(
        self,
        texts: str | list[str],
        *,
        timeout_s: float = 30.0,
    ) -> list[list[float]]:
        raise NotImplementedError("Embedding not yet implemented via LiteLLM")
