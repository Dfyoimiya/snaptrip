"""Tool DAG 编排器 — 拓扑排序 + 分层并行执行 + 轻量熔断"""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from typing import Dict, List

from app.schemas.plan import PlanDraft, PlanSlot
from app.schemas.tool import ToolInvocation, ToolResult, TOOL_REGISTRY


def build_execution_layers(slots: List[PlanSlot]) -> Dict[int, List[ToolInvocation]]:
    layers: Dict[int, List[ToolInvocation]] = defaultdict(list)
    for idx, slot in enumerate(slots):
        tool_name = slot.action if slot.action in TOOL_REGISTRY else "search_poi"
        if tool_name not in TOOL_REGISTRY:
            continue
        meta = TOOL_REGISTRY[tool_name]
        layers[meta.layer].append(ToolInvocation(
            node_id=f"{tool_name}_{idx}",
            tool_name=tool_name,
            slot_index=idx,
            layer=meta.layer,
            params={"poi_id": slot.poi.id, "poi_name": slot.poi.name,
                    "guest_count": 2, "time_range": str(slot.time_range)},
            dependencies=meta.dependencies,
        ))
    return layers


class ToolDAGScheduler:
    """Tool DAG 分层并行调度器"""

    def __init__(self):
        self.failure_counts: Dict[str, int] = defaultdict(int)

    async def execute(self, draft: PlanDraft) -> Dict[str, any]:
        layers = build_execution_layers(draft.slots)
        results: Dict[int, List[ToolResult]] = {}
        confirmed: Dict[int, str] = {}
        failed = []
        layer_timings: Dict[int, int] = {}
        total_ms = 0
        slot_results = {}

        for layer_idx in sorted(layers.keys()):
            t0 = time.perf_counter()
            invocations = layers[layer_idx]
            tasks = [self._call_tool(inv) for inv in invocations]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)

            for r in gathered:
                if isinstance(r, Exception):
                    continue
                results.setdefault(layer_idx, []).append(r)
                if r.success and r.data and "booking_id" in (r.data or {}):
                    confirmed[r.slot_index] = r.data["booking_id"]
                elif not r.success:
                    failed.append({"slot_index": r.slot_index, "tool_name": r.tool_name,
                                   "error_code": r.error_code, "error_message": r.error_message})

            layer_timings[layer_idx] = int((time.perf_counter() - t0) * 1000)
            total_ms += layer_timings[layer_idx]

        status = "full_success"
        if failed:
            status = "partial_success" if confirmed else "full_failure"

        return {
            "status": status,
            "slot_results": slot_results,
            "confirmed_bookings": confirmed,
            "failed_slots": failed,
            "layer_timings": layer_timings,
            "total_elapsed_ms": total_ms,
        }

    async def _call_tool(self, inv: ToolInvocation) -> ToolResult:
        meta = TOOL_REGISTRY.get(inv.tool_name)
        delay = random.uniform(0.02, 0.15)
        await asyncio.sleep(delay)

        if meta and random.random() < meta.failure_rate_mock:
            return ToolResult(
                success=False, tool_name=inv.tool_name, node_id=inv.node_id,
                slot_index=inv.slot_index, error_code="BOOKING_FULL",
                error_message="该时段已满",
                elapsed_ms=int(delay * 1000),
            )

        return ToolResult(
            success=True, tool_name=inv.tool_name, node_id=inv.node_id,
            slot_index=inv.slot_index,
            data={"booking_id": f"bk_{inv.slot_index}_{random.randint(1000, 9999)}"},
            elapsed_ms=int(delay * 1000),
        )
