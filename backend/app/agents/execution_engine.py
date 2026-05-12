"""Execution Engine — Tool DAG 编排器入口（委托给 tool_dag）"""

from __future__ import annotations

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.schemas.plan import ExecutionResult, PlanDraft


class ExecutionEngine(BaseAgent):
    name = "execution_engine"

    async def execute(self, context: AgentContext) -> AgentResult:
        draft = self._extract_draft(context)
        if not draft:
            return AgentResult(status="failed", error="No plan draft found")

        result = await self._execute_dag(draft)

        return AgentResult(data={"execution": result.model_dump()})

    def _extract_draft(self, context: AgentContext) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None

    async def _execute_dag(self, draft: PlanDraft) -> ExecutionResult:
        from app.schemas.tool import ToolResult, TOOL_REGISTRY
        from collections import defaultdict
        import asyncio
        import random

        slots = draft.slots
        layers: dict[int, list] = defaultdict(list)

        for i, slot in enumerate(slots):
            tool = slot.action if slot.action in TOOL_REGISTRY else "search_poi"
            if tool not in TOOL_REGISTRY:
                continue
            meta = TOOL_REGISTRY[tool]
            layers[meta.layer].append((i, slot, tool, meta))

        results: dict[int, list[ToolResult]] = {}
        confirmed: dict[int, str] = {}
        failed_slots = []
        timings = {}
        total_ms = 0

        for layer_idx in sorted(layers.keys()):
            import time
            t0 = time.perf_counter()
            tasks = []
            for i, slot, tool, meta in layers[layer_idx]:
                tasks.append(self._call_mock_tool(i, slot, tool, meta))
            layer_results = await asyncio.gather(*tasks, return_exceptions=True)

            for r in layer_results:
                if isinstance(r, Exception):
                    continue
                results.setdefault(layer_idx, []).append(r)
                if r.success and r.data and "booking_id" in (r.data or {}):
                    confirmed[r.slot_index] = r.data["booking_id"]
                elif not r.success:
                    from app.schemas.plan import FailedSlot
                    failed_slots.append(FailedSlot(
                        slot_index=r.slot_index, tool_name=r.tool_name,
                        error_code=r.error_code or "UNKNOWN",
                        error_message=r.error_message or "Tool failed",
                        poi_id=str(r.slot_index),
                    ))

            timings[layer_idx] = int((time.perf_counter() - t0) * 1000)
            total_ms += timings[layer_idx]

        status = "full_success" if not failed_slots else ("partial_success" if confirmed else "full_failure")

        from app.schemas.plan import SlotExecutionResult
        slot_results = {}
        for layer_idx, items in results.items():
            for r in items:
                slot_results[r.slot_index] = SlotExecutionResult(
                    slot_index=r.slot_index, tool_name=r.tool_name,
                    status="success" if r.success else "failed",
                    booking_id=r.data.get("booking_id") if r.data else None,
                    error_code=r.error_code, error_message=r.error_message,
                    elapsed_ms=r.elapsed_ms,
                )

        return ExecutionResult(
            plan_id=draft.plan_id, status=status,
            slot_results=slot_results, confirmed_bookings=confirmed,
            failed_slots=failed_slots, layer_timings=timings,
            total_elapsed_ms=total_ms,
        )

    async def _call_mock_tool(self, slot_index: int, slot, tool: str, meta):
        import random
        import asyncio
        from app.schemas.tool import ToolResult
        await asyncio.sleep(random.uniform(0.05, 0.2))
        if random.random() < meta.failure_rate_mock:
            return ToolResult(
                success=False, tool_name=tool, node_id=f"{tool}_{slot_index}",
                slot_index=slot_index, error_code="BOOKING_FULL",
                error_message="该时段已满", elapsed_ms=random.randint(50, 200),
            )
        return ToolResult(
            success=True, tool_name=tool, node_id=f"{tool}_{slot_index}",
            slot_index=slot_index,
            data={"booking_id": f"bk_{slot_index}_{random.randint(1000,9999)}"},
            elapsed_ms=random.randint(50, 200),
        )
