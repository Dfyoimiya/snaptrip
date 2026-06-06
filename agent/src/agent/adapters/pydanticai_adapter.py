"""PydanticAI Adapter —— 基于 PydanticAI 的 LLM 适配器。

替代 LiteLLMAdapter，提供:
- FallbackModel 自动模型降级 (deepseek-v4-pro → flash → kimi)
- Pydantic 工具 Schema 类型安全生成
- 结构化 JSON 输出校验 (chat_json)
- 流式响应 + DeepSeek thinking 模式

保持 LLMPort 接口兼容。

Author: SnapTrip Team
Date: 2026-05-30
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.settings import ModelSettings
from snaptrip_shared.core.config import settings
from snaptrip_shared.core.exceptions import LLMError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agent.ports.llm import LLMPort
from agent.services.llm_gateway import log_llm_usage

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)


def _build_fallback_model() -> FallbackModel:
    """构建带降级链的模型。

    降级顺序: deepseek-v4-pro → flash → kimi-k2.6 → kimi-k2.5
    """
    provider = OpenAIProvider(
        base_url=settings.LITELLM_BASE_URL,
        api_key=settings.LITELLM_API_KEY,
    )

    primary = OpenAIModel(settings.LLM_DEFAULT_MODEL, provider=provider)

    fallback_chain: list[str] = (
        getattr(settings, "LLM_FALLBACK_MODELS", "")
        .split(",")
    )
    fallback_models: list[OpenAIModel] = []
    for name in fallback_chain:
        name = name.strip()
        if name and name != settings.LLM_DEFAULT_MODEL:
            fallback_models.append(OpenAIModel(name, provider=provider))

    if not fallback_models:
        fallback_models = [
            OpenAIModel("deepseek-v4-flash", provider=provider),
            OpenAIModel("kimi-k2.6", provider=provider),
            OpenAIModel("kimi-k2.5", provider=provider),
        ]

    return FallbackModel(primary, *fallback_models)


def _messages_to_model_requests(
    messages: list[dict[str, Any]],
) -> list[ModelRequest]:
    """将 OpenAI 格式 messages 转换为 PydanticAI ModelRequest 列表。

    每个 role 对应一种 Part 类型:
      system    → SystemPromptPart
      user      → UserPromptPart
      assistant → TextPart + ToolCallPart (可选)
      tool      → ToolReturnPart
    """
    parts: list[Any] = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            parts.append(SystemPromptPart(content=str(content) if content else ""))
        elif role == "user":
            parts.append(UserPromptPart(content=str(content) if content else ""))
        elif role == "assistant":
            if content:
                parts.append(TextPart(content=str(content)))
            # tool_calls
            for tc in msg.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                parts.append(ToolCallPart(
                    tool_name=fn.get("name", ""),
                    args=args,
                    tool_call_id=tc.get("id", ""),
                ))
            # reasoning_content (DeepSeek thinking)
            rc = msg.get("reasoning_content")
            if rc:
                parts.append(ThinkingPart(content=str(rc)))
        elif role == "tool":
            parts.append(ToolReturnPart(
                tool_name="",
                content=str(content) if content else "",
                tool_call_id=msg.get("tool_call_id", ""),
            ))

    return [ModelRequest(parts=parts)]


def _response_to_dict(
    response: ModelResponse,
    model_alias: str,
    usage: Any | None = None,
) -> dict[str, Any]:
    """将 PydanticAI ModelResponse 转换为统一返回格式。"""
    content: str | None = None
    tool_calls: list[dict[str, Any]] = []
    reasoning_content: str | None = None

    for part in response.parts:
        if isinstance(part, TextPart):
            content = (content or "") + part.content
        elif isinstance(part, ToolCallPart):
            tool_calls.append({
                "id": part.tool_call_id or "",
                "type": "function",
                "function": {
                    "name": part.tool_name,
                    "arguments": json.dumps(part.args, ensure_ascii=False),
                },
            })
        elif isinstance(part, ThinkingPart):
            reasoning_content = part.content

    usage_dict = None
    if usage:
        usage_dict = {
            "prompt_tokens": getattr(usage, "request_tokens", 0) or 0,
            "completion_tokens": getattr(usage, "response_tokens", 0) or 0,
        }

    return {
        "content": content,
        "tool_calls": tool_calls if tool_calls else None,
        "reasoning_content": reasoning_content,
        "model": model_alias,
        "finish_reason": "stop",
        "usage": usage_dict,
    }


class PydanticAIAdapter(LLMPort):
    """基于 PydanticAI 的 LLM 适配器。

    使用 PydanticAI FallbackModel 提供自动模型降级，
    同时保留 OpenAI SDK 客户端用于流式 API 调用
    （因为 PydanticAI 的 stream API 与 DeepSeek thinking 模式兼容性有限）。
    """

    _MAX_RETRIES = 3
    _RETRY_MIN_WAIT = 1.0
    _RETRY_MAX_WAIT = 10.0

    def __init__(self) -> None:
        # ── PydanticAI 模型 (用于非流式 + fallback) ──
        self._pai_model = _build_fallback_model()
        logger.info(
            "PydanticAI FallbackModel initialized: %s",
            settings.LLM_DEFAULT_MODEL,
        )

        # ── OpenAI SDK 客户端 (用于流式 API) ──
        # 方案: 因为 DeepSeek thinking 模式需要 extra_body,
        # PydanticAI ModelSettings 不直接支持, 所以流式路径继续用 OpenAI SDK
        self._client = AsyncOpenAI(
            base_url=settings.LITELLM_BASE_URL,
            api_key=settings.LITELLM_API_KEY,
            timeout=httpx.Timeout(180.0, read=120.0, write=30.0, connect=10.0),
            max_retries=0,
        )

    # ── LLMPort 实现 ──────────────────────────────────────────

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
        """JSON 模式调用 —— 使用 PydanticAI 结构化输出。

        通过 PydanticAI Model.request() 调用，自动处理 JSON 格式校验。
        """
        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")

        t0 = time.monotonic()

        model_requests = _messages_to_model_requests([
            {"role": "user", "content": prompt},
        ])

        model_settings = ModelSettings(
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(
            "LLM JSON REQUEST (PydanticAI) | model=%s | prompt=%s",
            model,
            prompt[:500],
        )

        response, usage = await self._pai_model.request(
            model_requests,
            model_settings=model_settings,
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        await log_llm_usage(
            model_name=model,
            prompt_tokens=getattr(usage, "request_tokens", 0) or 0,
            completion_tokens=getattr(usage, "response_tokens", 0) or 0,
            latency_ms=elapsed_ms,
            endpoint="chat_json",
        )

        # 提取文本内容并解析 JSON
        content_parts = [
            p.content for p in response.parts if isinstance(p, TextPart)
        ]
        raw_content = "".join(content_parts).strip()
        raw_content = (
            raw_content.removeprefix("```json")
            .removesuffix("```")
            .strip()
        )

        logger.info(
            "LLM JSON RESPONSE (PydanticAI) | model=%s | content=%s",
            model,
            raw_content[:500],
        )

        try:
            return json.loads(raw_content) if raw_content else {}
        except json.JSONDecodeError as e:
            raise LLMError(
                f"LLM 返回非 JSON 内容: {raw_content[:200]}",
                details={"model_alias": model},
            ) from e

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = True,
        reasoning_effort: str = "",
        enable_thinking: bool | None = None,
    ) -> dict[str, Any]:
        """通用 chat 方法 —— 支持多轮消息 + function-calling + 思考模式。

        流式路径使用 OpenAI SDK (兼容 DeepSeek thinking extra_body)。
        非流式路径使用 PydanticAI FallbackModel。
        """
        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")

        t0 = time.monotonic()

        logger.info(
            "LLM REQUEST (PydanticAI) | model=%s | messages=%s | tools=%s",
            model,
            json.dumps(messages, ensure_ascii=False),
            json.dumps(tools, ensure_ascii=False) if tools else "None",
        )

        if stream:
            response = await self._call_with_fallback_stream(
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
            raw_usage = response.pop("_raw_usage", None)
            if raw_usage:
                await log_llm_usage(
                    model_name=response["model"],
                    prompt_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
                    completion_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
                    latency_ms=elapsed_ms,
                    endpoint="chat",
                )

            logger.info(
                "LLM RESPONSE (PydanticAI) | model=%s | finish_reason=%s | "
                "usage=%s | content=%s | tool_calls=%s | reasoning_content=%s",
                response["model"],
                response.get("finish_reason"),
                json.dumps(response.get("usage"), ensure_ascii=False),
                (response.get("content") or "")[:500],
                json.dumps(response.get("tool_calls"), ensure_ascii=False)
                if response.get("tool_calls") else "None",
                (response.get("reasoning_content") or "")[:500],
            )
            return response

        # 非流式: 使用 PydanticAI FallbackModel
        model_requests = _messages_to_model_requests(messages)
        model_settings = ModelSettings(
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response, usage = await self._pai_model.request(
            model_requests,
            model_settings=model_settings,
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        await log_llm_usage(
            model_name=model,
            prompt_tokens=getattr(usage, "request_tokens", 0) or 0,
            completion_tokens=getattr(usage, "response_tokens", 0) or 0,
            latency_ms=elapsed_ms,
            endpoint="chat",
        )

        result = _response_to_dict(response, model, usage)

        logger.info(
            "LLM RESPONSE (PydanticAI) | model=%s | finish_reason=%s | "
            "usage=%s | content=%s | tool_calls=%s | reasoning_content=%s",
            result["model"],
            result.get("finish_reason"),
            json.dumps(result.get("usage"), ensure_ascii=False),
            (result.get("content") or "")[:500],
            json.dumps(result.get("tool_calls"), ensure_ascii=False)
            if result.get("tool_calls") else "None",
            (result.get("reasoning_content") or "")[:500],
        )
        return result

    # ── 流式路径 (OpenAI SDK, 保留 DeepSeek thinking 兼容) ──

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
    ) -> dict[str, Any]:
        """流式版 fallback —— 沿降级链依次尝试。

        复用 PydanticAI FallbackModel 的降级链逻辑，
        但使用 OpenAI SDK 执行实际流式调用。
        """
        # 构建降级链: 从 PydanticAI FallbackModel 获取模型名
        chain_names = [model_alias]
        fallback_str = getattr(settings, "LLM_FALLBACK_MODELS", "")
        for name in fallback_str.split(","):
            name = name.strip()
            if name and name not in chain_names:
                chain_names.append(name)
        # 确保至少有两个备选
        for fb in ("deepseek-v4-flash", "kimi-k2.6", "kimi-k2.5"):
            if fb not in chain_names:
                chain_names.append(fb)

        last_error: Exception | None = None
        for i, model_name in enumerate(chain_names):
            try:
                logger.debug(
                    "LLM stream call (PydanticAI): model=%s (attempt %d/%d)",
                    model_name, i + 1, len(chain_names),
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
                    "LLM stream model %s failed (retryable): %s",
                    model_name, e,
                )
                continue
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM stream model %s failed: %s",
                    model_name, e,
                )
                continue

        raise LLMError(
            f"所有流式模型均调用失败 (chain: {chain_names})",
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
    ) -> dict[str, Any]:
        """流式调用 + tenacity 重试 (OpenAI SDK)。"""
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
                        kwargs["extra_body"] = {
                            "thinking": {"type": "enabled"},
                        }
                        if reasoning_effort:
                            kwargs["reasoning_effort"] = reasoning_effort

                    stream = await self._client.chat.completions.create(
                        **kwargs,
                    )
                    return await self._collect_stream(stream, model_alias)
                except RETRYABLE_EXCEPTIONS:
                    logger.warning(
                        "LLM stream retry attempt %s for model %s",
                        (
                            attempt.retry_state.attempt_number
                            if attempt.retry_state else "?"
                        ),
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
    ) -> dict[str, Any]:
        """收集流式 chunks → 统一返回格式。"""
        collected_content = ""
        collected_reasoning = ""
        tool_call_buffer: dict[int, dict[str, Any]] = {}
        final_usage: Any = None
        final_model = model_alias
        finish_reason: str | None = None

        async for chunk in stream:
            if chunk.model:
                final_model = chunk.model

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
                                    buf["function"]["name"] += (
                                        tc_delta.function.name
                                    )
                                if tc_delta.function.arguments:
                                    buf["function"]["arguments"] += (
                                        tc_delta.function.arguments
                                    )

                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

            if chunk.usage:
                final_usage = chunk.usage

        collected_tool_calls: list[dict[str, Any]] | None = None
        if tool_call_buffer:
            collected_tool_calls = [
                tool_call_buffer[i]
                for i in sorted(tool_call_buffer.keys())
            ]

        return {
            "content": collected_content or None,
            "tool_calls": collected_tool_calls,
            "reasoning_content": collected_reasoning or None,
            "model": final_model,
            "finish_reason": finish_reason or "stop",
            "usage": (
                {
                    "prompt_tokens": final_usage.prompt_tokens
                    if final_usage else 0,
                    "completion_tokens": final_usage.completion_tokens
                    if final_usage else 0,
                }
                if final_usage else None
            ),
            "_raw_usage": final_usage,
        }
