"""Shopping Guide LLM Adapters — LangChain-based LLM integration.

Provides the LangChainAdapter and a factory get_llm_adapter() for the
shopping_guide agent system.
"""

from __future__ import annotations

import logging

from shopping_guide.adapters.langchain_adapter import LangChainAdapter
from shopping_guide.adapters.llm_port import LLMPort

logger = logging.getLogger(__name__)

__all__ = [
    "LangChainAdapter",
    "LLMPort",
    "get_llm_adapter",
]


def get_llm_adapter() -> LLMPort:
    """Resolve the LLM adapter, creating a new LangChainAdapter if not cached."""
    return LangChainAdapter()
