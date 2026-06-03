"""AgentRuntime —— 依赖注入容器。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRuntime:
    """Agent 依赖注入容器。

    所有字段均可选——缺省时使用兜底逻辑。
    """

    # LLM 适配器（优先使用，否则自动创建 LiteLLMAdapter）
    llm_adapter: Any = None

    # Redis 事件总线（SSE 跨进程推送）
    event_bus: Any = None

    # 工具适配器（高德 MCP + REST）— 旧接口，保留向后兼容
    tool_adapter: Any = None

    # ToolHarness — 工具层唯一入口（新架构）
    harness: Any = None

    # SessionContext — 工具调用会话上下文
    session_ctx: Any = None
