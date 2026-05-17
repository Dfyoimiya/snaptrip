"""向量服务 + LLM Gateway 单元测试。

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio

import pytest

from app.services.llm_gateway import EMBEDDING_MODEL, MODEL_ALIASES, LLMError, LLMGateway


class TestEmbedding:
    def test_model_configured(self):
        assert "embedding" in EMBEDDING_MODEL or "text-embedding" in EMBEDDING_MODEL

    def test_mock_embedding(self):
        embeddings = asyncio.run(_mock_llm().embed("hello"))
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536

    def test_mock_batch_embedding(self):
        embeddings = asyncio.run(_mock_llm().embed(["a", "b", "c"]))
        assert len(embeddings) == 3
        assert all(len(e) == 1536 for e in embeddings)


class TestFallbackChain:
    def test_deepseek_primary(self):
        gw = LLMGateway(api_key="test")
        chain = gw._build_model_chain("deepseek")
        assert chain[0] == "deepseek"
        assert len(chain) >= 2

    def test_unknown_uses_full_chain(self):
        gw = LLMGateway(api_key="test")
        chain = gw._build_model_chain("unknown-model")
        assert "deepseek" in chain
        assert "gemma" in chain


class TestLLMError:
    def test_with_status_code(self):
        e = LLMError("api error", status_code=429)
        assert e.status_code == 429
        assert "api error" in str(e)

    def test_without_status_code(self):
        e = LLMError("timeout")
        assert e.status_code is None


def _mock_llm():
    class MockLLM:
        async def chat(self, *args, **kwargs):
            return {"content": "{}", "model": "mock", "usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        async def embed(self, texts, *args, **kwargs):
            if isinstance(texts, str):
                return [[0.1] * 1536]
            return [[0.1] * 1536 for _ in texts]
    return MockLLM()
