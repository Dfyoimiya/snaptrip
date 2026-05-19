"""Integration test fixtures —— mock LLM gateway for fast test execution.

LLM calls (intent_parser, planning_engine Phase 2) are mocked to fail immediately,
triggering fast keyword/template fallback paths.
"""

from __future__ import annotations

import pytest

from app.services.llm_gateway import LLMError


@pytest.fixture(autouse=True)
def _mock_llm_gateway(monkeypatch):
    """Mock LLMGateway.chat to raise immediately → fast keyword/sort fallbacks."""

    async def _fast_fail(
        self,
        messages,
        model_alias="deepseek",
        max_tokens=1024,
        temperature=0.7,
        timeout=30.0,
    ):
        raise LLMError("LLM mocked for fast integration testing", status_code=503)

    monkeypatch.setattr(
        "app.services.llm_gateway.LLMGateway.chat",
        _fast_fail,
    )
