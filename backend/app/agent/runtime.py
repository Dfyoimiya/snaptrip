"""AgentRuntime —— 依赖注入容器。

替代 graph.py 中的全局变量 (_gateway, _event_sink, _tool_adapter,
_cb_registry, _idempotency, _saga, _confirmator, _redis)。

所有 Agent 依赖通过 AgentRuntime 注入，消除模块级可变全局状态。

Author: SnapTrip Team
Date: 2026-05-21
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.ports.repositories import PlanRepositoryPort, UserProfileRepositoryPort


@dataclass
class AgentRuntime:
    """Agent 依赖注入容器。

    用法:
        rt = AgentRuntime(gateway=mock_gw, event_sink=sink, ...)
        graph = build_plan_graph(runtime=rt)

    所有字段均可选——缺省时 graph 节点使用兜底逻辑（default profile、跳过事件发射等）。
    """

    # ── 旧版 Gateway（向后兼容）──
    gateway: Any = None
    event_sink: Any = None

    # ── v3 安全管道 ──
    tool_adapter: Any = None
    cb_registry: Any = None
    idempotency: Any = None
    saga: Any = None
    confirmator: Any = None
    redis: Any = None

    # ── Marketplace API Client (Phase 4) ──
    marketplace_client: Any = None

    # ── Repository 端口 ──
    user_profile_repo: UserProfileRepositoryPort | None = None
    plan_repo: PlanRepositoryPort | None = None

    # ── Memory Service（向后兼容）──
    memory: Any = None
