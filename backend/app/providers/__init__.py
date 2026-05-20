"""LLM Provider 层。

提供统一的 LLM Provider 抽象，支持：
- OpenRouter（多模型聚合）
- DeepSeek 官方 API
- Kimi / Moonshot API
- 可扩展的 Provider 注册机制

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

from app.providers.base import BaseLLMProvider
from app.providers.registry import ModelRegistry, ProviderRegistry

__all__ = [
    "BaseLLMProvider",
    "ModelRegistry",
    "ProviderRegistry",
]
