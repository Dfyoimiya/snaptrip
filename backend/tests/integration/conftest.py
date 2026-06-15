"""Integration test fixtures —— mock external dependencies for fast test execution.

Mocked:
  - LLM adapter: fail immediately → trigger keyword/template fallback paths
  - Rate limiter: no-op → skip Redis-dependent rate limiting (no Redis in CI)
"""

from __future__ import annotations

import pytest
from snaptrip_shared.core.exceptions import LLMError


@pytest.fixture(autouse=True)
def _mock_llm_adapter(monkeypatch):
    """Mock LLMAdapter.chat_json to raise immediately → fast keyword/sort fallbacks."""

    async def _fast_fail(
        self,
        *,
        prompt: str,
        model_alias: str = "",
        timeout_s: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> dict:
        raise LLMError("LLM mocked for fast integration testing")

    monkeypatch.setattr(
        "agent.adapters.langchain_adapter.LangChainAdapter.chat_json",
        _fast_fail,
    )


@pytest.fixture(autouse=True)
def _mock_rate_limiter(monkeypatch):
    """Mock RateLimiter.__call__ → no-op (skip Redis in test env)."""

    async def _noop(self, request):
        return None

    monkeypatch.setattr(
        "marketplace.app.core.rate_limit.RateLimiter.__call__",
        _noop,
    )
