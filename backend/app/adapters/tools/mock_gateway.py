"""Adapter facade over the existing mock API gateway."""

from __future__ import annotations

from app.ports.tools import ToolGatewayPort
from app.services.mock_gateway import MockAPIGateway


class MockToolGatewayAdapter(ToolGatewayPort):
    """Port adapter that delegates to the existing gateway implementation."""

    def __init__(self, gateway: MockAPIGateway | None = None) -> None:
        self._gateway = gateway or MockAPIGateway()

    async def call(self, tool_name: str, params: dict) -> dict:
        return await self._gateway.call(tool_name, params)
