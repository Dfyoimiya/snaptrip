"""LangChain Adapter —— 基于 LangChain + LiteLLM 的 LLM 适配器。

- 原生 AIMessage 返回 (无需手动 dict→AIMessage 转换)
- OpenAI SDK 直连 LiteLLM Proxy (settings.LITELLM_BASE_URL)
- Fallback 模型降级链
- 流式响应 + DeepSeek thinking 模式
- 定价与成本追踪

Author: SnapTrip Team
Date: 2026-06-03
"""

from __future__ import annotations

import json
import logging
import time
import tomllib
from pathlib import Path
from typing import Any

import httpx
from langchain_core.messages import AIMessage
from openai import AsyncOpenAI
from snaptrip_shared.core.config import settings
from snaptrip_shared.core.exceptions import LLMError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shopping_guide.adapters.llm_port import LLMPort
from shopping_guide.adapters.model_pricing import ModelPricing
from shopping_guide.adapters.llm_gateway import log_llm_usage

logger = logging.getLogger(__name__)

# ── 错误分类 ──
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    ConnectionError,
    TimeoutError,
    OSError,
)


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


def _load_pricing() -> dict[str, ModelPricing]:
    """从 litellm/models.toml 加载定价表（用于成本记录）。"""
    config_path = Path(settings.LLM_PROVIDER_CONFIG)
    if not config_path.is_absolute():
        config_path = _find_project_root() / settings.LLM_PROVIDER_CONFIG
    if not config_path.exists():
        logger.info("pricing_config_not_found: %s", str(config_path))
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
        logger.warning("pricing_parse_failed", exc_info=True)
        return {}


# ── 错误分类 ──
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class LangChainAdapter(LLMPort):
    """基于 LangChain 的 LLM 适配器。

    使用 OpenAI SDK 客户端进行流式 API 调用，
    返回原生 LangChain AIMessage，无需节点手动转换。
    """

    _MAX_RETRIES = 3
    _RETRY_MIN_WAIT = 1.0
    _RETRY_MAX_WAIT = 10.0

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.LITELLM_BASE_URL,
            api_key=settings.LITELLM_API_KEY,
            timeout=httpx.Timeout(180.0, read=120.0, write=30.0, connect=10.0),
            max_retries=0,
        )
        self._pricing = _load_pricing()
        logger.info(
            "LangChainAdapter initialized (model=%s)", settings.LLM_DEFAULT_MODEL
        )

    # ── LLMPort 实现 ──────────────────────────────────────────

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        reasoning_effort: str = "",
        enable_thinking: bool | None = None,
        stream: bool = True,
    ) -> AIMessage:
        """通用 chat 方法 —— 返回原生 AIMessage。

        Args:
            messages: OpenAI 格式消息列表 [{"role": ..., "content": ...}]
            tools: OpenAI 格式工具定义列表
            model_alias: 模型别名 (覆盖默认模型)
            timeout_s: 请求超时 (秒)
            temperature: 温度参数
            max_tokens: 最大 token 数
            reasoning_effort: 推理强度 (low/medium/high)
            enable_thinking: 启用 DeepSeek 思考模式
            stream: 始终流式 (忽略此参数)
        """
        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not enable_thinking:
            reasoning_effort = "none"  # Explicitly disable reasoning
        elif not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")

        t0 = time.monotonic()

        logger.info(
            "LLM REQUEST (LangChain) | model=%s | messages=%s | tools=%s",
            model,
            json.dumps(messages, ensure_ascii=False),
            json.dumps(tools, ensure_ascii=False) if tools else "None",
        )

        ai_msg, raw_usage = await self._call_with_fallback_stream(
            messages=messages,
            tools=tools,
            model_alias=model,
            timeout_s=timeout_s,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            reasoning_effort=reasoning_effort,
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        if raw_usage:
            await self._record_usage(
                response_usage=raw_usage,
                response_model=model,
                model_alias=model,
                elapsed_ms=elapsed_ms,
            )

        logger.info(
            "LLM RESPONSE (LangChain) | model=%s | finish_reason=%s | "
            "usage=%s | content=%s | tool_calls=%s | reasoning_content=%s",
            model,
            getattr(ai_msg, "response_metadata", {}).get("finish_reason", "stop"),
            json.dumps(
                raw_usage.__dict__ if raw_usage else None,
                ensure_ascii=False,
                default=str,
            ),
            (ai_msg.content or "")[:500] if isinstance(ai_msg.content, str) else "",
            json.dumps(ai_msg.tool_calls, ensure_ascii=False)
            if ai_msg.tool_calls
            else "None",
            (ai_msg.additional_kwargs.get("reasoning_content", "") or "")[:500],
        )
        return ai_msg

    async def chat_stream(
        self,
        *,
        messages: list[dict[str, Any]],
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        reasoning_effort: str = "",
        enable_thinking: bool | None = None,
    ):
        """流式 chat —— 异步生成器，逐 token yield 文本内容。

        与 chat() 使用相同的降级链和重试逻辑，但不收集完整 AIMessage，
        而是 yield 每个文本 chunk，适合 SSE 流式输出。
        """
        import asyncio

        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not enable_thinking:
            reasoning_effort = "none"  # Explicitly disable reasoning
        elif not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")

        # 构建降级链
        chain_names = [model]
        fallback_str = getattr(settings, "LLM_FALLBACK_MODELS", "")
        for name in fallback_str.split(","):
            name = name.strip()
            if name and name not in chain_names:
                chain_names.append(name)
        for fb in ("deepseek-v4-flash",):
            if fb not in chain_names:
                chain_names.append(fb)

        last_error: Exception | None = None
        for model_name in chain_names:
            try:
                kwargs: dict[str, Any] = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": timeout_s,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }
                if enable_thinking:
                    kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                if reasoning_effort:
                    kwargs["reasoning_effort"] = reasoning_effort

                stream = await self._client.chat.completions.create(**kwargs)
                collected = ""
                async for chunk in stream:
                    if chunk.choices:
                        delta = chunk.choices[0].delta
                        if delta and delta.content:
                            collected += delta.content
                            yield delta.content
                return  # 成功，结束生成器

            except Exception as e:
                last_error = e
                logger.warning(
                    "chat_stream: model=%s failed (%s), trying next in chain",
                    model_name, e,
                )
                await asyncio.sleep(0.5)
                continue

        # 所有模型都失败
        raise last_error or RuntimeError("chat_stream: all models in chain failed")

    async def chat_json(
        self,
        *,
        prompt: str,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        reasoning_effort: str = "",
        enable_thinking: bool | None = None,
    ) -> dict:
        """JSON 模式调用。(简化实现)"""
        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not enable_thinking:
            reasoning_effort = "none"  # Explicitly disable reasoning
        elif not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout_s,
            "stream": False,
            "response_format": {"type": "json_object"},
        }
        if enable_thinking:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        return json.loads(content)  # type: ignore[no-any-return]

    async def _record_usage(
        self,
        *,
        response_usage: Any,
        response_model: str,
        model_alias: str,
        elapsed_ms: int,
    ) -> None:
        """Record LLM usage and cost to database."""
        usage = response_usage
        if not usage:
            return
        pricing = self._pricing.get(model_alias)
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
            model_name=response_model or model_alias,
            provider="litellm",
            prompt_tokens=usage.prompt_tokens or 0,
            completion_tokens=usage.completion_tokens or 0,
            latency_ms=elapsed_ms,
            cost_usd=cost_usd,
        )

    # ── 流式调用 + 降级链 ─────────────────────────────────────

    async def _call_with_fallback_stream(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model_alias: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int,
        enable_thinking: bool = False,
        reasoning_effort: str = "",
    ) -> tuple[AIMessage, Any]:
        """沿降级链依次尝试流式调用。"""
        chain_names = [model_alias]
        fallback_str = getattr(settings, "LLM_FALLBACK_MODELS", "")
        for name in fallback_str.split(","):
            name = name.strip()
            if name and name not in chain_names:
                chain_names.append(name)
        for fb in ("deepseek-v4-flash", "kimi-k2.6", "kimi-k2.5"):
            if fb not in chain_names:
                chain_names.append(fb)

        last_error: Exception | None = None
        for i, model_name in enumerate(chain_names):
            try:
                logger.debug(
                    "LLM stream call (LangChain): model=%s (attempt %d/%d)",
                    model_name,
                    i + 1,
                    len(chain_names),
                )
                return await self._call_with_retry_stream(
                    messages=messages,
                    tools=tools,
                    model_alias=model_name,
                    timeout_s=timeout_s,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    enable_thinking=enable_thinking,
                    reasoning_effort=reasoning_effort,
                )
            except RETRYABLE_EXCEPTIONS as e:
                last_error = e
                logger.warning(
                    "LLM stream model %s failed (retryable): %s", model_name, e
                )
                continue
            except Exception as e:
                last_error = e
                logger.warning("LLM stream model %s failed: %s", model_name, e)
                continue

        raise LLMError(
            f"All stream models failed (chain: {chain_names})",
            details={"last_error": str(last_error), "chain": chain_names},
        ) from last_error

    async def _call_with_retry_stream(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model_alias: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int,
        enable_thinking: bool = False,
        reasoning_effort: str = "",
    ) -> tuple[AIMessage, Any]:
        """流式调用 + tenacity 重试。"""
        last_exception: Exception | None = None

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._MAX_RETRIES),
            wait=wait_exponential(
                multiplier=self._RETRY_MIN_WAIT,
                max=self._RETRY_MAX_WAIT,
            ),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            reraise=True,
        ):
            with attempt:
                try:
                    kwargs: dict[str, Any] = {
                        "model": model_alias,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "timeout": timeout_s,
                        "stream": True,
                        "stream_options": {"include_usage": True},
                    }
                    if tools:
                        kwargs["tools"] = tools
                    if enable_thinking:
                        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                    else:
                        # 显式关闭思考模式 — 否则 qwen3.6-plus 等模型默认生成
                        # reasoning tokens，导致响应延迟从 ~1s 膨胀到 ~35s
                        kwargs["extra_body"] = {"enable_thinking": False}
                    if reasoning_effort:
                        kwargs["reasoning_effort"] = reasoning_effort

                    stream = await self._client.chat.completions.create(**kwargs)
                    return await self._collect_stream(stream, model_alias)
                except RETRYABLE_EXCEPTIONS:
                    logger.warning(
                        "LLM stream retry attempt %s for model %s",
                        attempt.retry_state.attempt_number
                        if attempt.retry_state
                        else "?",
                        model_alias,
                    )
                    raise
                except Exception as e:
                    last_exception = e
                    raise

        raise last_exception or RuntimeError("unreachable")

    async def _collect_stream(
        self,
        stream: Any,
        model_alias: str,
    ) -> tuple[AIMessage, Any]:
        """收集流式 chunks → AIMessage (LangChain 原生格式)。"""
        collected_content = ""
        collected_reasoning = ""
        tool_call_buffer: dict[int, dict[str, Any]] = {}
        final_usage: Any = None
        finish_reason: str | None = None

        async for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta:
                    if delta.content:
                        collected_content += delta.content

                    rc = getattr(delta, "reasoning_content", None)
                    if rc:
                        collected_reasoning += rc

                    if delta.tool_calls:
                        for tc_delta in delta.tool_calls:
                            idx = tc_delta.index
                            if idx not in tool_call_buffer:
                                tool_call_buffer[idx] = {
                                    "id": "",
                                    "type": "function",
                                    "function": {
                                        "name": "",
                                        "arguments": "",
                                    },
                                }
                            buf = tool_call_buffer[idx]
                            if tc_delta.id:
                                buf["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    buf["function"]["name"] += tc_delta.function.name
                                if tc_delta.function.arguments:
                                    buf["function"]["arguments"] += (
                                        tc_delta.function.arguments
                                    )

                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

            if chunk.usage:
                final_usage = chunk.usage

        # 将收集的工具调用转换为 LangChain 格式
        tool_calls: list[dict[str, Any]] = []
        if tool_call_buffer:
            for i in sorted(tool_call_buffer.keys()):
                tc = tool_call_buffer[i]
                fn = tc["function"]
                raw_args = fn["arguments"]
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    {
                        "name": fn["name"],
                        "args": args,
                        "id": tc["id"],
                    }
                )

        # 构建 AIMessage — content 永远有值，Pydantic v2 不允许 None
        additional_kwargs: dict[str, Any] = {}
        if collected_reasoning:
            additional_kwargs["reasoning_content"] = collected_reasoning

        ai_kwargs: dict[str, Any] = {
            "content": collected_content or "",
            "additional_kwargs": additional_kwargs,
            "response_metadata": {
                "model": model_alias,
                "finish_reason": finish_reason or "stop",
            },
        }
        # Only pass tool_calls when non-empty — Pydantic rejects None/[]
        if tool_calls:
            ai_kwargs["tool_calls"] = tool_calls

        ai_msg = AIMessage(**ai_kwargs)

        return ai_msg, final_usage
