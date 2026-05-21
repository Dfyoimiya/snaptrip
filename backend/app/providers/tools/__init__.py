"""Tool Provider —— 本地生活服务工具抽象层。

Provider 模式（与 LLM Provider 对齐）:
  BaseToolProvider → MockToolProvider (本地) / MeituanToolProvider / ...

Registry 模式（与 ModelRegistry 对齐）:
  ToolRegistry → 从 tools.toml 加载运行时配置

Author: SnapTrip Team
Date: 2026-05-20
"""

from app.providers.tools.base import BaseToolProvider, ToolProviderError, ToolTimeoutError
from app.providers.tools.mock import MockToolProvider
from app.providers.tools.registry import ToolRegistry

__all__ = [
    "BaseToolProvider",
    "MockToolProvider",
    "ToolRegistry",
    "ToolProviderError",
    "ToolTimeoutError",
]
