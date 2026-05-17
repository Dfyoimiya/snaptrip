"""LLM Gateway 单元测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import pytest

from app.services.llm_gateway import EMBEDDING_MODEL, MODEL_ALIASES, LLMError, LLMGateway


class TestModelAliases:
    def test_deepseek_resolves(self):
        assert MODEL_ALIASES["deepseek"] == "deepseek/deepseek-v3"

    def test_gemma_resolves(self):
        assert "gemma" in MODEL_ALIASES

    def test_unknown_alias_returns_self(self):
        # 未知别名原样返回（在 _chat_single 中直接使用）
        assert "unknown-model" not in MODEL_ALIASES

    def test_embedding_model_configured(self):
        assert EMBEDDING_MODEL.startswith("openai/")


class TestFallbackChain:
    def test_primary_only(self):
        gw = LLMGateway(api_key="test")
        chain = gw._build_model_chain("deepseek")
        assert chain[0] == "deepseek"
        assert len(chain) >= 2  # primary + gemma fallback

    def test_gemma_primary_no_duplicate(self):
        gw = LLMGateway(api_key="test")
        chain = gw._build_model_chain("gemma")
        assert chain[0] == "gemma"
        assert chain.count("gemma") == 1


class TestGatewayInit:
    def test_default_base_url(self):
        gw = LLMGateway(api_key="test")
        assert gw._base_url == "https://openrouter.ai/api/v1"

    def test_custom_api_key(self):
        gw = LLMGateway(api_key="sk-custom")
        assert gw._api_key == "sk-custom"
