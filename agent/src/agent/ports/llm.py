"""LLM boundary interfaces."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from agent.schemas.llm import StreamChunk


class LLMPort(Protocol):
    """Typed LLM adapter interface."""

    async def chat_json(
        self,
        *,
        prompt: str,
        model_alias: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int = 1024,
    ) -> dict: ...

    def chat_stream(
        self,
        *,
        prompt: str,
        model_alias: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncIterator[StreamChunk]: ...

    async def embed(
        self,
        texts: str | list[str],
        *,
        timeout_s: float,
    ) -> list[list[float]]: ...
