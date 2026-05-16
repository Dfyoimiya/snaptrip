"""Tool Schema —— Tool 调用契约与注册表。

定义执行层 10 个 Tool 的注册元数据（分层、依赖、超时、失败率）。

Tool DAG 分层:
  L0: search_poi / get_user_profile          —— 无依赖，可并行
  L1: check_queue / check_availability       —— 依赖 search_poi
      check_child_facility / calculate_route
  L2: book_table / book_ticket / order       —— 依赖 L1 结果
  L3: notify                                 —— 依赖 L2 全部完成

ToolMeta 字段:
- layer: DAG 层级
- dependencies: 上游依赖 Tool 名称列表
- is_idempotent: 是否幂等（用于缓存策略）
- timeout_ms: 单次调用超时
- failure_rate_mock: Mock 环境下的模拟失败概率

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolInvocation(BaseModel):
    node_id: str
    tool_name: str
    slot_index: int = -1
    layer: int = 0
    params: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    success: bool
    tool_name: str
    node_id: str
    slot_index: int = -1
    data: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    elapsed_ms: int = 0
    cached: bool = False


class ToolMeta(BaseModel):
    layer: int
    dependencies: list[str] = Field(default_factory=list)
    is_idempotent: bool = True
    timeout_ms: int = 3000
    failure_rate_mock: float = 0.0


# ===== Tool 注册表 =====

TOOL_REGISTRY: dict[str, ToolMeta] = {
    "search_poi": ToolMeta(
        layer=0, dependencies=[], is_idempotent=True, timeout_ms=1500,
    ),
    "get_user_profile": ToolMeta(
        layer=0, dependencies=[], is_idempotent=True, timeout_ms=500,
    ),
    "check_queue": ToolMeta(
        layer=1, dependencies=["search_poi"], is_idempotent=True, timeout_ms=1000,
    ),
    "check_availability": ToolMeta(
        layer=1, dependencies=["search_poi"], is_idempotent=True, timeout_ms=1000,
    ),
    "check_child_facility": ToolMeta(
        layer=1, dependencies=["search_poi"], is_idempotent=True, timeout_ms=800,
    ),
    "calculate_route": ToolMeta(
        layer=1, dependencies=["search_poi"], is_idempotent=True, timeout_ms=800,
    ),
    "book_table": ToolMeta(
        layer=2, dependencies=["check_queue", "check_availability"],
        is_idempotent=False, timeout_ms=2000, failure_rate_mock=0.2,
    ),
    "book_ticket": ToolMeta(
        layer=2, dependencies=["check_availability"],
        is_idempotent=False, timeout_ms=2000, failure_rate_mock=0.1,
    ),
    "order": ToolMeta(
        layer=2, dependencies=["search_poi"],
        is_idempotent=False, timeout_ms=1500, failure_rate_mock=0.05,
    ),
    "notify": ToolMeta(
        layer=3, dependencies=["book_table", "book_ticket", "order"],
        is_idempotent=True, timeout_ms=1000,
    ),
}
