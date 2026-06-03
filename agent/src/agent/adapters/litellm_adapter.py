"""LiteLLM Adapter —— OpenAI SDK 指向 litellm-proxy。

替代手写 HTTP/SSE/重试 provider 栈。
客户端侧重试 + 模型降级链，litellm-proxy 处理上游认证。

Author: SnapTrip Team
Date: 2026-05-25
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import tomllib
from openai import AsyncOpenAI
from snaptrip_shared.core.config import settings
from snaptrip_shared.core.exceptions import LLMError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from agent.ports.llm import LLMPort
from agent.schemas.llm import ModelPricing
from agent.services.llm_gateway import log_llm_usage

logger = logging.getLogger(__name__)

# 可重试的异常类型
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)


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


# 模型降级链: 主模型失败时依次尝试后备模型
_FALLBACK_CHAIN: tuple[str, ...] = (
    settings.LLM_DEFAULT_MODEL,
    # 备选模型通过 settings 注入，默认空则不降级
    *tuple(m.strip() for m in getattr(settings, "LLM_FALLBACK_MODELS", "").split(",") if m.strip()),
)


class LiteLLMAdapter(LLMPort):
    """基于 LiteLLM Proxy 的 LLM 适配器。

    使用 openai.AsyncOpenAI 指向 litellm-proxy Docker 服务。
    客户端侧提供十次重试（指数退避）+ 模型降级链。
    LiteLLM 处理上游认证、限流。
    """

    _MAX_RETRIES = 3
    _RETRY_MIN_WAIT = 1.0
    _RETRY_MAX_WAIT = 10.0

    def __init__(self) -> None:
        import httpx
        self._client = AsyncOpenAI(
            base_url=settings.LITELLM_BASE_URL,
            api_key=settings.LITELLM_API_KEY,
            timeout=httpx.Timeout(180.0, read=120.0, write=30.0, connect=10.0),
            max_retries=0,  # 客户端自行管理重试
        )
        self._pricing = _load_pricing()

    # ── 私有方法 ──────────────────────────────────────────────

    async def _collect_stream(self, stream: Any, model_alias: str) -> dict[str, Any]:
        """收集流式 chunks，返回与 chat() 兼容的统一格式 dict。

        OpenAI 流式 API 中 content、tool_calls、reasoning_content 均以增量 (delta)
        方式到达，需要逐 chunk 拼接。usage 信息在最后一个 chunk 中。
        """
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

                    # 思考链内容 (DeepSeek thinking mode)
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
                                    "function": {"name": "", "arguments": ""},
                                }
                            buf = tool_call_buffer[idx]
                            if tc_delta.id:
                                buf["id"] = tc_delta.id
                            if tc_delta.function:
                                if tc_delta.function.name:
                                    buf["function"]["name"] += tc_delta.function.name
                                if tc_delta.function.arguments:
                                    buf["function"]["arguments"] += tc_delta.function.arguments

                if chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

            if chunk.usage:
                final_usage = chunk.usage

        collected_tool_calls: list[dict[str, Any]] | None = None
        if tool_call_buffer:
            collected_tool_calls = [
                tool_call_buffer[i] for i in sorted(tool_call_buffer.keys())
            ]

        return {
            "content": collected_content or None,
            "tool_calls": collected_tool_calls,
            "reasoning_content": collected_reasoning or None,
            "model": final_model,
            "finish_reason": finish_reason or "stop",
            "usage": {
                "prompt_tokens": final_usage.prompt_tokens if final_usage else 0,
                "completion_tokens": final_usage.completion_tokens if final_usage else 0,
            } if final_usage else None,
            "_raw_usage": final_usage,
        }

    async def _record_usage(
        self,
        *,
        response_usage: Any,
        response_model: str,
        model_alias: str,
        elapsed_ms: int,
    ) -> None:
        """记录 LLM 用量和成本到数据库。"""
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

    async def _call_with_retry(
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
        response_format: dict[str, Any] | None = None,
    ) -> Any:
        """带重试的 API 调用。每个模型重试 _MAX_RETRIES 次。"""
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
                    }
                    if tools:
                        kwargs["tools"] = tools
                    if response_format:
                        kwargs["response_format"] = response_format
                    if enable_thinking:
                        kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                        if reasoning_effort:
                            kwargs["reasoning_effort"] = reasoning_effort

                    return await self._client.chat.completions.create(**kwargs)
                except RETRYABLE_EXCEPTIONS:
                    logger.warning(
                        "LLM retry attempt %s for model %s",
                        attempt.retry_state.attempt_number if attempt.retry_state else "?",
                        model_alias,
                    )
                    raise
                except Exception as e:
                    last_exception = e
                    raise

        raise last_exception or RuntimeError("unreachable")

    async def _call_with_fallback(
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
        response_format: dict[str, Any] | None = None,
    ) -> Any:
        """带模型降级链的调用。

        以 model_alias 为起点，沿 _FALLBACK_CHAIN 依次尝试。
        某个模型失败时自动切换到下一个。
        """
        # 构建降级链: 指定模型 → 默认模型 → 后备模型
        chain: list[str] = [model_alias]
        for fm in _FALLBACK_CHAIN:
            if fm and fm not in chain:
                chain.append(fm)

        last_error: Exception | None = None
        for i, model in enumerate(chain):
            try:
                logger.debug("LLM call: model=%s (attempt %d/%d)", model, i + 1, len(chain))
                return await self._call_with_retry(
                    messages=messages,
                    tools=tools,
                    model_alias=model,
                    timeout_s=timeout_s,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    enable_thinking=enable_thinking,
                    reasoning_effort=reasoning_effort,
                    response_format=response_format,
                )
            except RETRYABLE_EXCEPTIONS as e:
                last_error = e
                logger.warning("LLM model %s failed (retryable): %s", model, e)
                continue
            except Exception as e:
                last_error = e
                logger.warning("LLM model %s failed: %s", model, e)
                continue

        raise LLMError(
            f"所有模型均调用失败 (chain: {chain})",
            details={"last_error": str(last_error), "chain": chain},
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
        """流式版 _call_with_retry。收集全部 chunk 后返回统一格式 dict。"""
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
                        if reasoning_effort:
                            kwargs["reasoning_effort"] = reasoning_effort

                    stream = await self._client.chat.completions.create(**kwargs)
                    return await self._collect_stream(stream, model_alias)
                except RETRYABLE_EXCEPTIONS:
                    logger.warning(
                        "LLM stream retry attempt %s for model %s",
                        attempt.retry_state.attempt_number if attempt.retry_state else "?",
                        model_alias,
                    )
                    raise
                except Exception as e:
                    last_exception = e
                    raise

        raise last_exception or RuntimeError("unreachable")

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
        """流式版 _call_with_fallback。"""
        chain: list[str] = [model_alias]
        for fm in _FALLBACK_CHAIN:
            if fm and fm not in chain:
                chain.append(fm)

        last_error: Exception | None = None
        for i, model in enumerate(chain):
            try:
                logger.debug("LLM stream call: model=%s (attempt %d/%d)", model, i + 1, len(chain))
                return await self._call_with_retry_stream(
                    messages=messages,
                    tools=tools,
                    model_alias=model,
                    timeout_s=timeout_s,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    enable_thinking=enable_thinking,
                    reasoning_effort=reasoning_effort,
                )
            except RETRYABLE_EXCEPTIONS as e:
                last_error = e
                logger.warning("LLM stream model %s failed (retryable): %s", model, e)
                continue
            except Exception as e:
                last_error = e
                logger.warning("LLM stream model %s failed: %s", model, e)
                continue

        raise LLMError(
            f"所有流式模型均调用失败 (chain: {chain})",
            details={"last_error": str(last_error), "chain": chain},
        ) from last_error

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
        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")
        t0 = time.monotonic()

        logger.info(
            "LLM JSON REQUEST | model=%s | prompt=%s",
            model,
            prompt[:500],
        )

        response = await self._call_with_fallback(
            messages=[{"role": "user", "content": prompt}],
            tools=None,
            model_alias=model,
            timeout_s=timeout_s,
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
            reasoning_effort=reasoning_effort,
            response_format={"type": "json_object"},
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        await self._record_usage(
            response_usage=response.usage,
            response_model=response.model,
            model_alias=model,
            elapsed_ms=elapsed_ms,
        )

        content = response.choices[0].message.content or ""
        content = content.strip()
        content = content.removeprefix("```json").removesuffix("```").strip()

        logger.info(
            "LLM JSON RESPONSE | model=%s | usage=%s | content=%s",
            response.model,
            json.dumps(getattr(response, "usage", None), default=str) if hasattr(response, "usage") else "None",
            content[:500],
        )
        try:
            return json.loads(content) if content else {}
        except json.JSONDecodeError as e:
            raise LLMError(
                f"LLM 返回非 JSON 内容: {content[:200]}",
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

        Args:
            messages: OpenAI 格式消息列表 [{"role": "...", "content": "..."}]
            tools: OpenAI function-calling 工具定义列表
            model_alias: LiteLLM 模型别名
            timeout_s: 超时秒数
            temperature: 生成温度
            max_tokens: 最大输出 token
            stream: 是否启用流式传输，默认 True
            reasoning_effort: 思考强度 "high" / "max"，仅 enable_thinking=True 时生效
            enable_thinking: 是否启用 DeepSeek 思考模式

        Returns:
            {
                "content": str | None,
                "tool_calls": list[dict] | None,
                "reasoning_content": str | None,
                "model": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int},
            }
        """
        model = model_alias or settings.LLM_DEFAULT_MODEL
        if enable_thinking is None:
            enable_thinking = getattr(settings, "LLM_ENABLE_THINKING", True)
        if not reasoning_effort:
            reasoning_effort = getattr(settings, "LLM_REASONING_EFFORT", "high")
        t0 = time.monotonic()

        logger.info(
            "LLM REQUEST | model=%s | messages=%s | tools=%s",
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
                await self._record_usage(
                    response_usage=raw_usage,
                    response_model=response["model"],
                    model_alias=model,
                    elapsed_ms=elapsed_ms,
                )

            logger.info(
                "LLM RESPONSE | model=%s | finish_reason=%s | usage=%s | content=%s | tool_calls=%s | reasoning_content=%s",
                response["model"],
                response.get("finish_reason"),
                json.dumps(response.get("usage"), ensure_ascii=False),
                (response.get("content") or "")[:500],
                json.dumps(response.get("tool_calls"), ensure_ascii=False) if response.get("tool_calls") else "None",
                (response.get("reasoning_content") or "")[:500],
            )
            return response

        # 非流式路径（stream=False 时保留）
        response = await self._call_with_fallback(
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
        await self._record_usage(
            response_usage=response.usage,
            response_model=response.model,
            model_alias=model,
            elapsed_ms=elapsed_ms,
        )

        choice = response.choices[0]
        message = choice.message
        usage = response.usage

        # 提取 tool_calls
        tool_calls: list[dict[str, Any]] | None = None
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        result = {
            "content": message.content,
            "tool_calls": tool_calls,
            "reasoning_content": getattr(message, "reasoning_content", None),
            "model": response.model or model,
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
            } if usage else None,
        }

        logger.info(
            "LLM RESPONSE | model=%s | finish_reason=%s | usage=%s | content=%s | tool_calls=%s | reasoning_content=%s",
            result["model"],
            result.get("finish_reason"),
            json.dumps(result.get("usage"), ensure_ascii=False),
            (result.get("content") or "")[:500],
            json.dumps(result.get("tool_calls"), ensure_ascii=False) if result.get("tool_calls") else "None",
            (result.get("reasoning_content") or "")[:500],
        )
        return result

