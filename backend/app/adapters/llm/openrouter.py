"""OpenRouter-backed LLM adapter."""

from __future__ import annotations

import json

from app.ports.llm import LLMPort
from app.services.llm_gateway import LLMGateway


class OpenRouterLLMAdapter(LLMPort):
    """Adapter that normalizes gateway output for agent consumers."""

    def __init__(self, gateway: LLMGateway | None = None) -> None:
        self._gateway = gateway or LLMGateway()

    async def chat_json(
        self,
        *,
        prompt: str,
        model_alias: str,
        timeout_s: float,
        temperature: float,
        max_tokens: int = 1024,
    ) -> dict:
        result = await self._gateway.chat(
            messages=[{"role": "user", "content": prompt}],
            model_alias=model_alias,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout_s,
        )
        content = result.get("content", "").strip()
        content = content.removeprefix("```json").removesuffix("```").strip()
        return json.loads(content) if content else {}

    async def embed(
        self,
        texts: str | list[str],
        *,
        timeout_s: float,
    ) -> list[list[float]]:
        return await self._gateway.embed(texts, timeout=timeout_s)
