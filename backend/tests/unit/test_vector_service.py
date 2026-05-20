"""LLM Error 类单元测试。

Author: SnapTrip Team
Date: 2026-05-17 / Refactored 2026-05-20
"""

from __future__ import annotations

from app.core.exceptions import LLMError


class TestLLMError:
    def test_with_details(self):
        e = LLMError("api error", details={"http_status": 429})
        assert e.status_code == 502  # GatewayError default
        assert "api error" in str(e)
        assert e.details["http_status"] == 429

    def test_default_message(self):
        e = LLMError()
        assert e.code == "LLM_ERROR"
        assert e.status_code == 502
