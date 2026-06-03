"""AmapRoutingTool — travel time estimation and route planning via Amap API.

Read-only tool; compensation is cache invalidation (no-op).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction


class RoutingInput(BaseModel):
    """Input schema for Amap routing estimation."""

    from_lat: float = Field(description="Origin latitude")
    from_lng: float = Field(description="Origin longitude")
    to_lat: float = Field(description="Destination latitude")
    to_lng: float = Field(description="Destination longitude")
    mode: str = Field(default="driving", description="Travel mode: driving/walking/transit/cycling")


class AmapRoutingTool(SmartDayBaseTool):
    """Estimate travel time/distance via Amap API."""

    name: str = "amap_routing"
    description: str = (
        "Estimate travel time and distance between two points. "
        "Use this tool when you need to know how long it takes to get from one place "
        "to another. Supports driving, walking, transit, and cycling modes."
    )
    args_schema: type[BaseModel] = RoutingInput
    is_read_only: bool = True
    cost_model: str = "free"
    tool_timeout: float = 8.0

    async def _arun(
        self,
        from_lat: float,
        from_lng: float,
        to_lat: float,
        to_lng: float,
        mode: str = "driving",
        **kwargs: Any,
    ) -> ToolResult:
        try:
            from agent.adapters.amap_adapter import get_adapter
            adapter = get_adapter()
            origin = f"{from_lng},{from_lat}"
            destination = f"{to_lng},{to_lat}"
            result = await adapter.estimate_travel_time(origin, destination, mode)
            return ToolResult(
                success=True,
                data={
                    "distance_km": result.get("distance_km", 5.0),
                    "duration_min": result.get("duration_min", 15.0),
                    "mode": mode,
                },
                idempotency_key=self._idem_key({
                    "from_lat": from_lat, "from_lng": from_lng,
                    "to_lat": to_lat, "to_lng": to_lng, "mode": mode,
                }),
            )
        except Exception:
            dist = ((from_lat - to_lat) ** 2 + (from_lng - to_lng) ** 2) ** 0.5 * 111
            speeds = {"driving": 40, "walking": 5, "transit": 25, "cycling": 15}
            speed = speeds.get(mode, 40)
            duration = max(5, round(dist / speed * 60))
            return ToolResult(
                success=True,
                data={"distance_km": round(dist, 1), "duration_min": duration, "mode": mode},
                idempotency_key=self._idem_key({
                    "from_lat": from_lat, "from_lng": from_lng,
                    "to_lat": to_lat, "to_lng": to_lng, "mode": mode,
                }),
            )

    def compensation(self, args: dict[str, Any], result: ToolResult) -> CompensationAction:
        return self._noop_compensation(
            action_id=f"route_cache:{result.idempotency_key}",
            tool_name=self.name,
        )
