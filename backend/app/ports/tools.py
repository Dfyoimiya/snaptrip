"""Tool gateway boundary interfaces."""

from __future__ import annotations

from typing import Protocol


class ToolGatewayPort(Protocol):
    """External tool gateway interface."""

    async def call(self, tool_name: str, params: dict) -> dict: ...
