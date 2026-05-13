"""Tool DAG 编排器 —— 拓扑排序 + 分层并行执行 + 轻量熔断 + 结构化日志。

执行层核心组件，负责将 PlanDraft 的抽象时隙翻译为具体的 Tool 调用序列。

核心功能:
  1. build_execution_layers(): 按 TOOL_REGISTRY 的 layer 属性分层分组
  2. ToolDAGScheduler.execute(): 自底向上分层执行，层内 asyncio.gather 并行
  3. 轻量熔断: 连续 5 次失败 → circuit_open，后续直接跳过
  4. 结构化日志: 每个 Tool 调用输出 JSON 格式日志

熔断器设计（快速失败 + 缓存兜底）:
  - 不实现完整三态熔断器（Closed/Open/Half-Open）
  - 采用失败计数 + 单向打开策略
  - 成功后 failure_count 归零

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from collections import defaultdict
from typing import Any

from app.schemas.plan import PlanDraft, PlanSlot
from app.schemas.tool import TOOL_REGISTRY, ToolInvocation, ToolResult


def build_execution_layers(slots: list[PlanSlot]) -> dict[int, list[ToolInvocation]]:
    layers: dict[int, list[ToolInvocation]] = defaultdict(list)
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
    """Tool DAG 分层并行调度器 + 轻量熔断"""

    def __init__(self):
        self.failure_counts: dict[str, int] = defaultdict(int)
        self.circuit_open: set[str] = set()
        self._failure_threshold = 5

    async def execute(self, draft: PlanDraft) -> dict[str, Any]:
        layers = build_execution_layers(draft.slots)
        results: dict[int, list[ToolResult]] = {}
        confirmed: dict[int, str] = {}
        failed: list[dict[str, object]] = []
        layer_timings: dict[int, int] = {}
        total_ms = 0
        slot_results: dict[int, object] = {}

        for layer_idx in sorted(layers.keys()):
            t0 = time.perf_counter()
            invocations = layers[layer_idx]
            tasks = [self._call_tool_with_breaker(inv) for inv in invocations]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)

            for r in gathered:
                if isinstance(r, BaseException):
                    continue
                assert isinstance(r, ToolResult)
                results.setdefault(layer_idx, []).append(r)
                if r.success and r.data and "booking_id" in (r.data or {}):
                    confirmed[r.slot_index] = r.data["booking_id"]
                elif not r.success:
                    failed.append({
                        "slot_index": r.slot_index, "tool_name": r.tool_name,
                        "error_code": r.error_code, "error_message": r.error_message,
                    })

                self._log_tool_execution(r, draft.plan_id, layer_idx)

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

    async def _call_tool_with_breaker(self, inv: ToolInvocation) -> ToolResult:
        if inv.tool_name in self.circuit_open:
            return ToolResult(
                success=False, tool_name=inv.tool_name, node_id=inv.node_id,
                slot_index=inv.slot_index, error_code="CIRCUIT_OPEN",
                error_message="Circuit breaker open", elapsed_ms=0,
            )

        meta = TOOL_REGISTRY.get(inv.tool_name)
        delay = random.uniform(0.02, 0.15)
        await asyncio.sleep(delay)

        if meta and random.random() < meta.failure_rate_mock:
            self.failure_counts[inv.tool_name] += 1
            if self.failure_counts[inv.tool_name] >= self._failure_threshold:
                self.circuit_open.add(inv.tool_name)
            return ToolResult(
                success=False, tool_name=inv.tool_name, node_id=inv.node_id,
                slot_index=inv.slot_index, error_code="BOOKING_FULL",
                error_message="该时段已满",
                elapsed_ms=int(delay * 1000),
            )

        self.failure_counts[inv.tool_name] = 0
        return ToolResult(
            success=True, tool_name=inv.tool_name, node_id=inv.node_id,
            slot_index=inv.slot_index,
            data={"booking_id": f"bk_{inv.slot_index}_{random.randint(1000, 9999)}"},
            elapsed_ms=int(delay * 1000),
        )

    def _log_tool_execution(self, r: ToolResult, plan_id: str, layer: int):
        log = json.dumps({
            "event": "tool_execution",
            "plan_id": plan_id,
            "layer": layer,
            "tool_name": r.tool_name,
            "slot_index": r.slot_index,
            "status": "success" if r.success else "failed",
            "error_code": r.error_code,
            "elapsed_ms": r.elapsed_ms,
            "cached": r.cached,
        }, ensure_ascii=False)
        print(log)
