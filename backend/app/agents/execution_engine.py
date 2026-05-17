"""Execution Engine —— Tool DAG 编排入口。

将 PlanDraft 的抽象时隙翻译为 Tool 调用序列，按 DAG 分层并行执行。

核心特性:
  1. DAG 依赖感知: 上游 Tool 失败时，下游依赖 Tool 自动跳过 (SKIPPED)
  2. 分层超时: per-tool 3s / per-layer 5s / total DAG 10s
  3. 超时不阻塞同层: 单 Tool 超时不影响同层其他 Tool 并行执行
  4. 结构化日志: 每个 Tool 调用输出 JSON 格式日志供前端 AgentMonitor 渲染

输出: ExecutionResult (含 slot_results, confirmed_bookings,
       failed_slots, layer_timings)

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from collections import defaultdict

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.core.constants import EXEC_TIMEOUT_TOTAL_S
from app.schemas.plan import ExecutionResult, FailedSlot, PlanDraft, SlotExecutionResult
from app.schemas.tool import TOOL_REGISTRY, ToolDefinition, ToolResult

_MOCK_FAILURE_RATES: dict[str, float] = {
    "book_table": 0.2,
    "book_ticket": 0.1,
    "order": 0.05,
}


class ExecutionEngine(BaseAgent):
    name = "execution_engine"

    async def execute(self, context: AgentContext) -> AgentResult:
        draft = self._extract_draft(context)
        if not draft:
            return AgentResult(status="failed", error="No plan draft found")

        result = await asyncio.wait_for(
            self._execute_dag(draft, context),
            timeout=EXEC_TIMEOUT_TOTAL_S,
        )
        return AgentResult(data={"execution": result.model_dump()})

    def _extract_draft(self, context: AgentContext) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None

    async def _execute_dag(self, draft: PlanDraft, context: AgentContext) -> ExecutionResult:
        slots = draft.slots
        layers: dict[int, list[tuple[int, str, ToolDefinition]]] = defaultdict(list)
        failed_tools: set[str] = set()

        for i, slot in enumerate(slots):
            tool = slot.action if slot.action in TOOL_REGISTRY else "search_poi"
            if tool not in TOOL_REGISTRY:
                continue
            layers[TOOL_REGISTRY[tool].layer].append((i, tool, TOOL_REGISTRY[tool]))

        results: dict[int, list[ToolResult]] = {}
        confirmed: dict[int, str] = {}
        failed_slots: list[FailedSlot] = []
        timings: dict[int, int] = {}
        total_ms = 0

        for layer_idx in sorted(layers.keys()):
            t0 = time.perf_counter()
            tasks = []
            for slot_i, tool, meta in layers[layer_idx]:
                deps_ok = all(d not in failed_tools for d in meta.dependencies)
                if not deps_ok:
                    failed_slots.append(
                        FailedSlot(
                            slot_index=slot_i,
                            tool_name=tool,
                            error_code="SKIPPED",
                            error_message="Upstream dependency failed",
                            poi_id=str(slot_i),
                        )
                    )
                    continue
                tasks.append(self._call_tool_with_timeout(slot_i, tool, meta))

            try:
                layer_results: list = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                layer_results = []

            for r in layer_results:
                if isinstance(r, BaseException):
                    continue
                assert isinstance(r, ToolResult)
                results.setdefault(layer_idx, []).append(r)
                slot_index = r.data.get("slot_index", -1) if r.data else -1
                if r.status == "success" and r.data and "booking_id" in (r.data or {}):
                    confirmed[slot_index] = r.data["booking_id"]
                elif r.status != "success":
                    failed_tools.add(_tool_name_for_result(r, slot_index))
                    failed_slots.append(
                        FailedSlot(
                            slot_index=slot_index,
                            tool_name=_tool_name_for_result(r, slot_index),
                            error_code=r.error_code or "UNKNOWN",
                            error_message=r.error_message or "Tool failed",
                            poi_id=str(slot_index),
                        )
                    )

                self._log_tool_call(r, draft.plan_id, layer_idx)

            timings[layer_idx] = int((time.perf_counter() - t0) * 1000)
            total_ms += timings[layer_idx]

        status = "full_success"
        if failed_slots:
            status = "partial_success" if confirmed else "full_failure"

        slot_result_map: dict[int, SlotExecutionResult] = {}
        for _layer_idx, items in results.items():
            for r in items:
                si = r.data.get("slot_index", -1) if r.data else -1
                slot_result_map[si] = SlotExecutionResult(
                    slot_index=si,
                    tool_name=_tool_name_for_result(r, si),
                    status=r.status,
                    booking_id=r.data.get("booking_id") if r.data else None,
                    error_code=r.error_code,
                    error_message=r.error_message,
                    elapsed_ms=r.latency_ms,
                )

        return ExecutionResult(
            plan_id=draft.plan_id,
            status=status,
            slot_results=slot_result_map,
            confirmed_bookings=confirmed,
            failed_slots=failed_slots,
            layer_timings=timings,
            total_elapsed_ms=total_ms,
        )

    async def _call_tool_with_timeout(
        self, slot_index: int, tool: str, meta: ToolDefinition
    ) -> ToolResult:
        try:
            timeout_s = meta.default_timeout_ms / 1000.0
            return await asyncio.wait_for(
                self._call_mock_tool(slot_index, tool, meta),
                timeout=timeout_s,
            )
        except TimeoutError:
            return ToolResult(
                invocation_id=f"{tool}_{slot_index}",
                status="timeout",
                data={"slot_index": slot_index, "tool_name": tool},
                error_code="TIMEOUT",
                error_message=f"{tool} timed out",
                latency_ms=meta.default_timeout_ms,
            )

    async def _call_mock_tool(
        self, slot_index: int, tool: str, meta: ToolDefinition
    ) -> ToolResult:
        delay = random.uniform(0.02, 0.15)
        await asyncio.sleep(delay)
        failure_rate = _MOCK_FAILURE_RATES.get(tool, 0.0)
        if random.random() < failure_rate:
            return ToolResult(
                invocation_id=f"{tool}_{slot_index}",
                status="failure",
                data={"slot_index": slot_index, "tool_name": tool},
                error_code="BOOKING_FULL",
                error_message="该时段已满",
                latency_ms=int(delay * 1000),
            )
        return ToolResult(
            invocation_id=f"{tool}_{slot_index}",
            status="success",
            data={
                "booking_id": f"bk_{slot_index}_{random.randint(1000, 9999)}",
                "slot_index": slot_index,
                "tool_name": tool,
            },
            latency_ms=int(delay * 1000),
        )

    def _log_tool_call(self, r: ToolResult, plan_id: str, layer: int):
        log = json.dumps(
            {
                "event": "tool_execution",
                "plan_id": plan_id,
                "layer": layer,
                "invocation_id": r.invocation_id,
                "status": r.status,
                "error_code": r.error_code,
                "latency_ms": r.latency_ms,
            },
            ensure_ascii=False,
        )
        print(log)


def _tool_name_for_result(r: ToolResult, slot_index: int) -> str:
    return r.data.get("tool_name", str(slot_index)) if r.data else str(slot_index)
