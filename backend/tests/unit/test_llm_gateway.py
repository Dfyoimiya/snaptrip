"""LLM 使用量日志 单元测试。

Author: SnapTrip Team
Date: 2026-05-17 / Refactored 2026-05-20
"""

from __future__ import annotations

from snaptrip_shared.core.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError


class TestLLMErrors:
    def test_llm_error_default(self):
        e = LLMError()
        assert e.code == "LLM_ERROR"
        assert e.status_code == 502

    def test_llm_error_with_details(self):
        e = LLMError("api error", details={"http_status": 429})
        assert "api error" in str(e)
        assert e.details["http_status"] == 429

    def test_llm_timeout_error(self):
        e = LLMTimeoutError()
        assert e.code == "LLM_TIMEOUT"
        assert e.status_code == 502

    def test_llm_rate_limit_error(self):
        e = LLMRateLimitError(details={"provider": "deepseek", "http_status": 429})
        assert e.code == "LLM_RATE_LIMIT"
        assert e.details["provider"] == "deepseek"
