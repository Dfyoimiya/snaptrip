"""LLM Adapter —— 统一 LLM 调用入口。

使用 ProviderRegistry + ModelRegistry 解析模型 alias → Provider，
支持 chat_json、chat_stream、embed，自动记录使用量日志。

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path

from snaptrip_shared.core.config import settings
from snaptrip_shared.core.exceptions import LLMError

from agent.ports.llm import LLMPort
from agent.providers.deepseek import DeepSeekProvider
from agent.providers.kimi import KimiProvider
from agent.providers.openrouter import OpenRouterProvider
from agent.providers.registry import ModelRegistry, ProviderRegistry
from agent.schemas.llm import StreamChunk
from agent.services.llm_gateway import log_llm_usage

logger = logging.getLogger(__name__)


def _build_default_registry() -> ProviderRegistry:
    """从配置构建默认 ProviderRegistry。"""
    config_path = Path(settings.LLM_PROVIDER_CONFIG)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent.parent.parent / settings.LLM_PROVIDER_CONFIG

    model_registry = ModelRegistry(config_path)
    registry = ProviderRegistry(model_registry=model_registry)

    if settings.DEEPSEEK_API_KEY:
        registry.register(
            "deepseek",
            DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
            ),
        )

    if settings.OPENROUTER_API_KEY:
        registry.register(
            "openrouter",
            OpenRouterProvider(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
            ),
        )

    if settings.KIMI_API_KEY:
        registry.register(
            "kimi",
            KimiProvider(
                api_key=settings.KIMI_API_KEY,
                base_url=settings.KIMI_BASE_URL,
            ),
        )

    return registry


class LLMAdapter(LLMPort):
    """统一 LLM Adapter —— 实现 LLMPort 协议。

    负责：
    - 通过 ProviderRegistry 解析模型 alias
    - 调用 Provider 的 chat / chat_stream
    - JSON 解析（失败时抛 LLMError，不泄漏原生异常）
    - 自动记录使用量日志
    """

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or _build_default_registry()

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
        alias = model_alias or settings.LLM_DEFAULT_MODEL

        try:
            provider, model_cfg = self._registry.resolve(alias)
        except KeyError as e:
            raise LLMError(str(e), details={"model_alias": alias}) from e

        try:
            result = await provider.chat(
                messages=[{"role": "user", "content": prompt}],
                model=model_cfg.api_model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout_s,
            )
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(
                f"LLM 调用失败: {e}",
                details={"model_alias": alias, "provider": model_cfg.provider},
            ) from e

        pricing = self._registry.model_registry.get_pricing(alias)
        cost_usd = 0.0
        if pricing is not None:
            cost_usd = provider._calculate_cost(pricing, result.usage.prompt_tokens, result.usage.completion_tokens)
        await log_llm_usage(
            model_name=result.model,
            provider=result.provider,
            prompt_tokens=result.usage.prompt_tokens,
            completion_tokens=result.usage.completion_tokens,
            latency_ms=result.latency_ms,
            cost_usd=cost_usd,
        )

        content = result.content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        try:
            return json.loads(content) if content else {}
        except json.JSONDecodeError as e:
            raise LLMError(
                f"LLM 返回非 JSON 内容: {content[:200]}",
                details={"model_alias": alias, "provider": result.provider},
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
        alias = model_alias or settings.LLM_DEFAULT_MODEL

        try:
            provider, model_cfg = self._registry.resolve(alias)
        except KeyError as e:
            raise LLMError(str(e), details={"model_alias": alias}) from e

        t0 = time.monotonic()
        try:
            async for chunk in provider.chat_stream(
                messages=[{"role": "user", "content": prompt}],
                model=model_cfg.api_model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout_s,
            ):
                yield chunk
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(
                f"LLM 流式调用失败: {e}",
                details={"model_alias": alias, "provider": model_cfg.provider},
            ) from e
        finally:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            await log_llm_usage(
                model_name=model_cfg.api_model,
                provider=model_cfg.provider,
                latency_ms=elapsed_ms,
                endpoint="chat_stream",
            )

    async def embed(
        self,
        texts: str | list[str],
        *,
        timeout_s: float = 30.0,
    ) -> list[list[float]]:
        raise NotImplementedError("Embedding not yet implemented")
