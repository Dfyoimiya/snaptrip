"""Mock Tool Provider —— 本地开发/测试用模拟 Provider。

模拟 10 个工具的响应: search_poi, get_user_profile, check_queue, check_availability,
check_child_facility, calculate_route, book_table, book_ticket, order, notify.

物理操作模拟:
  - book_table/book_ticket: 生成假 booking_ref
  - order: 生成假 order_id
  - cancel: 标记为 CANCELLED
  - query_status: 返回 CONFIRMED（默认）

Author: SnapTrip Team
Date: 2026-05-20
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Callable, Coroutine
from typing import Any

from app.providers.tools.base import BaseToolProvider
from app.schemas.tool_provider import PhysicalActionState, ToolProviderResult

logger = logging.getLogger(__name__)

_SUPPORTED_TOOLS = frozenset(
    {
        "search_poi",
        "get_user_profile",
        "check_queue",
        "check_availability",
        "check_child_facility",
        "calculate_route",
        "book_table",
        "book_ticket",
        "order",
        "notify",
    }
)


class MockToolProvider(BaseToolProvider):
    """本地 Mock Provider —— 模拟第三方 API 响应。"""

    provider_name = "mock"

    # 模拟预订存储（内存中，用于 cancel/query_status）
    _bookings: dict[str, dict] = {}  # type: ignore[type-arg]

    # ===== 抽象方法实现 =====

    async def call(
        self,
        tool_name: str,
        params: dict,
        idempotency_key: str,
        timeout: float = 30.0,
    ) -> ToolProviderResult:
        if not self.supports_tool(tool_name):
            return ToolProviderResult(
                status="failure",
                error_code="UNSUPPORTED_TOOL",
                error_message=f"Mock Provider 不支持工具: {tool_name}",
            )

        handler = _MOCK_HANDLERS.get(tool_name)
        if handler is None:
            return ToolProviderResult(
                status="failure",
                error_code="NO_HANDLER",
                error_message=f"工具 {tool_name} 无 mock handler",
            )

        t0 = time.monotonic()
        try:
            result = await asyncio.wait_for(handler(params), timeout=timeout)
        except TimeoutError:
            elapsed = int((time.monotonic() - t0) * 1000)
            return self._unknown_result(
                tool_name,
                idempotency_key,
                latency_ms=elapsed,
                error_message=f"Mock {tool_name} 模拟超时",
            )

        result.latency_ms = int((time.monotonic() - t0) * 1000)
        return result

    async def cancel(self, tool_name: str, booking_ref: str) -> ToolProviderResult:
        if booking_ref in self._bookings:
            self._bookings[booking_ref]["state"] = PhysicalActionState.CANCELLED
            logger.info("mock_cancel_booking ref=%s tool=%s", booking_ref, tool_name)
        return ToolProviderResult(
            status="success",
            physical_state=PhysicalActionState.CANCELLED,
            data={"cancelled_ref": booking_ref},
        )

    async def query_status(self, tool_name: str, booking_ref: str) -> PhysicalActionState:
        booking = self._bookings.get(booking_ref)
        if booking:
            state = booking.get("state", PhysicalActionState.CONFIRMED)
            return PhysicalActionState(state)  # type: ignore[arg-type]
        return PhysicalActionState.CONFIRMED  # 默认: 已确认（宽松模拟）

    def supports_tool(self, tool_name: str) -> bool:
        return tool_name in _SUPPORTED_TOOLS


# ===== Mock Handlers =====


async def _mock_search_poi(params: dict) -> ToolProviderResult:
    city = params.get("city", "北京")
    category = params.get("category", "")
    await asyncio.sleep(random.uniform(0.02, 0.08))
    return ToolProviderResult(
        status="success",
        data={
            "pois": [
                {
                    "id": f"poi_{city}_{i}",
                    "name": f"{city}{category or '热门'}POI_{i}",
                    "type": category or "restaurant",
                    "lat": 39.92 + random.uniform(-0.05, 0.05),
                    "lng": 116.44 + random.uniform(-0.05, 0.05),
                    "rating": round(random.uniform(3.5, 5.0), 1),
                    "avg_price": random.randint(50, 300),
                    "child_friendly": random.choice([True, False]),
                }
                for i in range(random.randint(3, 8))
            ],
            "total": random.randint(3, 8),
        },
    )


async def _mock_get_user_profile(params: dict) -> ToolProviderResult:
    await asyncio.sleep(0.02)
    return ToolProviderResult(
        status="success",
        data={
            "preferences": {"dietary": ["中式", "日料"], "budget": "中等"},
            "travel_style": "family",
            "preference_embedding": [0.1, 0.3, 0.5],
        },
    )


async def _mock_check_queue(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.02, 0.06))
    queue = random.randint(0, 30)
    return ToolProviderResult(
        status="success",
        data={"queue_length": queue, "wait_minutes": queue * random.randint(1, 3)},
    )


async def _mock_check_availability(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.02, 0.06))
    return ToolProviderResult(
        status="success",
        data={"available": True, "next_available": "19:00"},
    )


async def _mock_check_child_facility(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.02, 0.05))
    return ToolProviderResult(
        status="success",
        data={"has_nursing_room": True, "has_child_seat": True},
    )


async def _mock_calculate_route(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.03, 0.08))
    return ToolProviderResult(
        status="success",
        data={"distance_km": round(random.uniform(0.5, 15), 1), "duration_min": random.randint(5, 45)},
    )


async def _mock_book_table(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.05, 0.15))
    booking_ref = f"bk_table_{random.randint(10000, 99999)}"
    MockToolProvider._bookings[booking_ref] = {
        "tool": "book_table",
        "state": PhysicalActionState.CONFIRMED,
        "params": params,
    }
    return ToolProviderResult(
        status="success",
        data={"booking_id": booking_ref, "table_number": f"A{random.randint(1, 20):02d}"},
        booking_ref=booking_ref,
        physical_state=PhysicalActionState.CONFIRMED,
    )


async def _mock_book_ticket(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.05, 0.15))
    booking_ref = f"bk_ticket_{random.randint(10000, 99999)}"
    MockToolProvider._bookings[booking_ref] = {
        "tool": "book_ticket",
        "state": PhysicalActionState.CONFIRMED,
        "params": params,
    }
    guest_count = params.get("guest_count", 1)
    return ToolProviderResult(
        status="success",
        data={"booking_id": booking_ref, "ticket_count": guest_count},
        booking_ref=booking_ref,
        physical_state=PhysicalActionState.CONFIRMED,
    )


async def _mock_order(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.04, 0.10))
    order_id = f"ord_{random.randint(10000, 99999)}"
    MockToolProvider._bookings[order_id] = {
        "tool": "order",
        "state": PhysicalActionState.CONFIRMED,
        "params": params,
    }
    items = params.get("items", [])
    return ToolProviderResult(
        status="success",
        data={"order_id": order_id, "total_price": len(items) * random.randint(30, 120)},
        booking_ref=order_id,
        physical_state=PhysicalActionState.CONFIRMED,
    )


async def _mock_notify(params: dict) -> ToolProviderResult:
    await asyncio.sleep(random.uniform(0.02, 0.05))
    return ToolProviderResult(
        status="success",
        data={"sent": True, "share_url": f"https://snaptrip.cn/s/plan_{random.randint(1000, 9999)}"},
    )


_MockHandler = Callable[[dict], Coroutine[Any, Any, ToolProviderResult]]

_MOCK_HANDLERS: dict[str, _MockHandler] = {
    "search_poi": _mock_search_poi,
    "get_user_profile": _mock_get_user_profile,
    "check_queue": _mock_check_queue,
    "check_availability": _mock_check_availability,
    "check_child_facility": _mock_check_child_facility,
    "calculate_route": _mock_calculate_route,
    "book_table": _mock_book_table,
    "book_ticket": _mock_book_ticket,
    "order": _mock_order,
    "notify": _mock_notify,
}
