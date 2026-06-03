"""LLM boundary interfaces."""

from __future__ import annotations

from typing import Any, Protocol


class LLMPort(Protocol):
    """Typed LLM adapter interface."""

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
        enable_thinking: bool = False,
        stream: bool = True,
    ) -> dict[str, Any]: ...

    async def chat_json(
        self,
        *,
        prompt: str,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        reasoning_effort: str = "",
        enable_thinking: bool = False,
    ) -> dict: ...
