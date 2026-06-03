"""AmapGeocodeTool — geocoding via Amap API.

Read-only tool; compensation is no-op.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction


class GeocodeInput(BaseModel):
    """Input schema for geocoding."""

    address: str = Field(default="", description="Address to geocode")
    city: str = Field(default="", description="City for disambiguation")
    location: str = Field(default="", description="'lng,lat' for reverse geocode")
    ip: str = Field(default="", description="IP address for IP location")


class AmapGeocodeTool(SmartDayBaseTool):
    """Geocode addresses, reverse-geocode coordinates, IP-locate.

    Contract:
      - read-only: never mutates external state
      - compensation: no-op
      - timeout: 5 s
    """

    name: str = "amap_geocode"
    description: str = (
        "Convert addresses to coordinates (geocode), coordinates to addresses "
        "(reverse geocode), or locate a user by IP address. "
        "Use this tool to determine a user's city or find coordinates for a place name."
    )
    args_schema: type[BaseModel] = GeocodeInput
    is_read_only: bool = True
    cost_model: str = "free"
    tool_timeout: float = 5.0

    async def _arun(
        self,
        address: str = "",
        city: str = "",
        location: str = "",
        ip: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        from agent.adapters.amap_adapter import get_adapter
        adapter = get_adapter()

        if ip or (not address and not location):
            try:
                result = await adapter.ip_location(ip)
                city_name = result.get("city", "北京")
                geo = await adapter.geocode(city_name)
                return ToolResult(
                    success=True,
                    data={
                        "lat": geo.get("lat", 39.9219),
                        "lng": geo.get("lng", 116.4435),
                        "city": city_name,
                        "address": geo.get("address", ""),
                    },
                    idempotency_key=self._idem_key({"ip": ip}),
                )
            except Exception:
                return ToolResult(
                    success=True,
                    data={"lat": 39.9219, "lng": 116.4435, "city": "北京"},
                    idempotency_key=self._idem_key({"ip": ip}),
                )

        if address:
            result = await adapter.geocode(address, city)
            return ToolResult(
                success=True, data=result,
                idempotency_key=self._idem_key({"address": address, "city": city}),
            )

        if location:
            result = await adapter.reverse_geocode(location)
            return ToolResult(
                success=True, data=result,
                idempotency_key=self._idem_key({"location": location}),
            )

        return ToolResult(success=False, data={"error": "Must provide address, location, or ip"})

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=f"geo_cache:{result.idempotency_key}",
            tool_name=self.name,
        )
