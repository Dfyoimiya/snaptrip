"""LLM Gateway 错误类单元测试。

Author: SnapTrip Team
Date: 2026-05-17 / Updated 2026-05-18
"""

from __future__ import annotations

from app.services.llm_gateway import LLMError


class TestLLMError:
    def test_with_status_code(self):
        e = LLMError("api error", status_code=429)
        assert e.status_code == 429
        assert "api error" in str(e)

    def test_without_status_code(self):
        e = LLMError("timeout")
        assert e.status_code is None
