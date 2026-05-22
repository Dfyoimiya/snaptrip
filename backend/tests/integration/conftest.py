"""Integration test fixtures —— mock LLM adapter for fast test execution.

LLM calls (intent_parser, planning_engine Phase 2) are mocked to fail immediately,
triggering fast keyword/template fallback paths.
"""

from __future__ import annotations

import pytest

from shared.core.exceptions import LLMError


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
        "agent_worker.app.agent.adapters.llm.LLMAdapter.chat_json",
        _fast_fail,
    )
