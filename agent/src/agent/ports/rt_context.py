"""Real-time context boundary interface.

RTContextPort provides real-time environmental data (weather, traffic, peak
pricing) and POI-level status. Implementations may call Amap, weather APIs,
or fall back to cached/stale data.  The Protocol is consumed by context_loader
(during planning) and monitor_engine (post-execution).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from agent.schemas.state import (
    PeakCalendar,
    POIRealTimeStatus,
    RealTimeContext,
    TrafficIndex,
    WeatherSnapshot,
)


class RTContextPort(Protocol):
    """Real-time context adapter — weather, traffic, peak calendar, POI status.

    All methods are async to allow network calls.  Implementations should
    respect the provider's rate limits and handle timeouts gracefully.
    """

    async def get_weather(self, lat: float, lng: float) -> WeatherSnapshot:
        """Fetch current weather snapshot for a location.

        Returns:
            WeatherSnapshot with condition, temperature, outdoor_score.
            outdoor_score >= 0.7 → excellent for outdoor activities.
            outdoor_score < 0.3  → outdoor POIs should be gated out.
        """
        ...

    async def get_traffic_index(
        self,
        lat: float,
        lng: float,
        *,
        radius_km: float = 10.0,
    ) -> TrafficIndex:
        """Fetch real-time traffic congestion index for an area.

        Returns:
            TrafficIndex with overall 0.0–1.0 score and per-corridor breakdown.
        """
        ...

    async def get_peak_calendar(
        self,
        lat: float,
        lng: float,
        *,
        date: datetime | None = None,
    ) -> PeakCalendar:
        """Fetch peak-hour pricing multipliers and special events.

        Returns:
            PeakCalendar with hourly multipliers (e.g. 18→1.5×) and
            a list of special event names (e.g. "五一假期", "周杰伦演唱会").
        """
        ...

    async def get_poi_realtime(self, poi_id: str) -> POIRealTimeStatus | None:
        """Fetch real-time status for a single POI.

        Returns None if the POI is not found or the data source is unavailable.
        """
        ...

    async def get_poi_realtime_batch(
        self, poi_ids: list[str]
    ) -> dict[str, POIRealTimeStatus]:
        """Bulk fetch real-time status for multiple POIs.

        POIs whose status cannot be fetched are silently omitted from the result.
        """
        ...

    async def get_real_time_context(self, lat: float, lng: float) -> RealTimeContext:
        """Convenience: fetch weather + traffic + peak calendar in one call.

        Implementations may make parallel requests internally.
        """
        ...

    async def health_check(self) -> bool:
        """Return True if the underlying provider is reachable."""
        ...
