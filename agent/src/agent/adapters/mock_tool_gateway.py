"""Adapter facade over the existing mock API gateway."""

from __future__ import annotations

from typing import Any

from agent.adapters.mock_gateway import MockAPIGateway
from agent.ports.tools import ToolGatewayPort


class MockToolGatewayAdapter(ToolGatewayPort):
    """Port adapter that delegates to the existing gateway implementation."""

    def __init__(self, gateway: MockAPIGateway | None = None) -> None:
        self._gateway = gateway or MockAPIGateway()

    async def call(self, tool_name: str, params: dict) -> dict:
        result: dict[Any, Any] = await self._gateway.call(tool_name, params)
        return result

    async def call_idempotent(
        self, tool_name: str, params: dict, idempotency_key: str
    ) -> dict:
        result: dict[Any, Any] = await self._gateway.call(tool_name, params)
        return result

    async def cancel(self, tool_name: str, booking_ref: str) -> dict:
        return {"status": "success", "data": {"cancelled": booking_ref}}

    async def query_status(self, tool_name: str, booking_ref: str) -> dict:
        return {"status": "success", "physical_state": "confirmed"}
