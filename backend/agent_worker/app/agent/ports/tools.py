"""Tool gateway boundary interfaces.

Two separate interfaces:
  - ToolDefinitionPort: 只读，向 LLM 暴露工具定义（function-calling schema）
  - ToolGatewayPort: 执行，有副作用，由 ExecutionEngine 调用
"""

from __future__ import annotations

from typing import Any, Protocol

from agent_worker.app.agent.schemas.tool import ToolDefinition


class ToolDefinitionPort(Protocol):
    """向 LLM 暴露工具定义的只读接口。

    与 ToolGatewayPort（执行接口）完全分离：
    - ToolDefinitionPort → LLM function-calling（只读，无副作用）
    - ToolGatewayPort → ExecutionEngine（执行，有副作用）
    """

    def get_function_definitions(self) -> list[dict[str, Any]]:
        """返回 OpenAI function-calling 格式的工具列表。

        仅返回 LLM 需要知道的字段: name, description, parameters
        不暴露: layer, dependencies, fallback_policy, is_idempotent, physical_impact
        """
        ...

    def get_tool_metadata(self, tool_name: str) -> ToolDefinition | None:
        """获取单个工具的完整元数据（ExecutionEngine 使用）"""
        ...


class ToolGatewayPort(Protocol):
    """External tool gateway interface."""

    async def call(self, tool_name: str, params: dict) -> dict: ...
    async def call_idempotent(self, tool_name: str, params: dict, idempotency_key: str) -> dict: ...
    async def cancel(self, tool_name: str, booking_ref: str) -> dict: ...
    async def query_status(self, tool_name: str, booking_ref: str) -> dict: ...
