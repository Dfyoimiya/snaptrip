"""Execution Engine —— Tool DAG 编排入口。

将 PlanDraft 的抽象时隙翻译为 Tool 调用序列，按 DAG 分层并行执行。

核心特性:
  1. DAG 依赖感知: 上游 Tool 失败时，下游依赖 Tool 自动跳过 (SKIPPED)
  2. 分层超时: per-tool 3s / total DAG 10s
  3. 超时不阻塞同层: 单 Tool 超时不影响同层其他 Tool 并行执行
  4. 结构化日志: 每个 Tool 调用输出 JSON 格式日志供前端 AgentMonitor 渲染
  5. Gateway 集成: gateway 可用时通过 MockAPIGateway 对 mock_server:8001 发 HTTP
                   gateway=None 时走本地随机 mock（单元测试兼容）

输出: ExecutionResult (含 slot_results, confirmed_bookings,
       failed_slots, layer_timings)

Author: SnapTrip Team
Date: 2026-05-13 / Gateway integration 2026-05-17
"""

from __future__ import annotations

import asyncio
import random
import time
from collections import defaultdict
from typing import Any

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.core.constants import EXEC_TIMEOUT_TOTAL_S
from app.core.logging import get_logger
from app.ports.tools import ToolGatewayPort
from app.schemas.agent.state import ExecutionState, ToolExecutionRecord
from app.schemas.plan import (
    ExecutionResult,
    FailedSlot,
    IntentSchema,
    PlanDraft,
    PlanSlot,
    SlotExecutionResult,
)
from app.schemas.tool import TOOL_REGISTRY, ToolDefinition, ToolResult

logger = get_logger(__name__)


class ExecutionEngine(BaseAgent):
    name = "execution_engine"

    def __init__(self, gateway: ToolGatewayPort | None = None) -> None:
        super().__init__()
        self._gateway = gateway

    async def execute(self, context: AgentContext) -> AgentResult:
        draft = self._extract_draft(context)
        if not draft:
            return AgentResult(status="failed", error="No plan draft found")

        result = await asyncio.wait_for(
            self._execute_dag(draft, context),
            timeout=EXEC_TIMEOUT_TOTAL_S,
        )
        execution_state = self.to_execution_state(result)
        return AgentResult(
            data={
                "execution": result.model_dump(),
                "execution_state": execution_state.model_dump(),
            }
        )

    # ------------------------------------------------------------------
    # data extraction
    # ------------------------------------------------------------------

    def _extract_draft(self, context: AgentContext) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None

    def _extract_intent(self, context: AgentContext) -> IntentSchema | None:
        for h in reversed(context.history):
            if "intent" in h.data:
                return IntentSchema(**h.data["intent"])
            if "enriched_intent" in h.data:
                ei = h.data["enriched_intent"]
                if "intent" in ei:
                    return IntentSchema(**ei["intent"])
        return None

    # ------------------------------------------------------------------
    # DAG orchestration
    # ------------------------------------------------------------------

    async def _execute_dag(self, draft: PlanDraft, context: AgentContext) -> ExecutionResult:
        slots = draft.slots
        slots_by_idx: dict[int, PlanSlot] = {i: s for i, s in enumerate(slots)}

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
            tasks: list = []
            for slot_i, tool, meta in layers[layer_idx]:
                deps_ok = all(d not in failed_tools for d in meta.dependencies)
                if not deps_ok:
                    failed_slots.append(FailedSlot(
                        slot_index=slot_i, tool_name=tool,
                        error_code="SKIPPED",
                        error_message="Upstream dependency failed",
                        poi_id=str(slot_i),
                    ))
                    continue
                slot = slots_by_idx.get(slot_i)
                tasks.append(self._call_tool_with_timeout(slot_i, tool, meta, slot, context))

            try:
                layer_results: list = await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                layer_results = []

            for r in layer_results:
                if isinstance(r, BaseException):
                    continue
                assert isinstance(r, ToolResult)
                results.setdefault(layer_idx, []).append(r)
                si = r.data.get("slot_index", -1) if r.data else -1
                if r.status == "success" and r.data and "booking_id" in (r.data or {}):
                    confirmed[si] = r.data["booking_id"]
                elif r.status in {"failure", "timeout"}:
                    failed_tools.add(_tool_name_for_result(r, si))
                    failed_slots.append(FailedSlot(
                        slot_index=si, tool_name=_tool_name_for_result(r, si),
                        error_code=r.error_code or "UNKNOWN",
                        error_message=r.error_message or "Tool failed",
                        poi_id=str(si),
                    ))

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

    # ------------------------------------------------------------------
    # tool calling
    # ------------------------------------------------------------------

    async def _call_tool_with_timeout(
        self,
        slot_index: int,
        tool: str,
        meta: ToolDefinition,
        slot: PlanSlot | None = None,
        context: AgentContext | None = None,
    ) -> ToolResult:
        try:
            timeout_s = meta.default_timeout_ms / 1000.0
            return await asyncio.wait_for(
                self._call_tool(slot_index, tool, meta, slot, context),
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

    async def _call_tool(
        self,
        slot_index: int,
        tool: str,
        meta: ToolDefinition,
        slot: PlanSlot | None = None,
        context: AgentContext | None = None,
    ) -> ToolResult:
        if slot and context:
            gateway = self._get_gateway()
            if gateway is not None:
                return await self._call_via_gateway(gateway, slot_index, tool, slot, context)
        return await self._call_mock_tool(slot_index, tool)

    async def _call_via_gateway(
        self,
        gateway: ToolGatewayPort,
        slot_index: int,
        tool: str,
        slot: PlanSlot,
        context: AgentContext,
    ) -> ToolResult:
        params = self._build_tool_params(slot, context)
        resp = await gateway.call(tool, params)
        normalized = self._normalize_gateway_response(tool, slot_index, resp)

        return ToolResult(
            invocation_id=f"{tool}_{slot_index}",
            status=normalized["status"],
            data={
                **(normalized.get("data") or {}),
                "slot_index": slot_index,
                "tool_name": tool,
            },
            error_code=normalized.get("error_code"),
            error_message=normalized.get("error_message"),
            latency_ms=normalized.get("latency_ms", 0),
        )

    def _build_tool_params(self, slot: PlanSlot, context: AgentContext) -> dict[str, object]:
        intent = self._extract_intent(context)
        guest_count = intent.guest_count if intent else 2

        params: dict[str, object] = {
            "poi_id": slot.poi.id,
            "poi_name": slot.poi.name,
        }

        if slot.action == "book_table":
            params["guest_count"] = guest_count
            params["time_slot"] = str(slot.time_range.start.time())
        elif slot.action == "book_ticket":
            params["guest_count"] = guest_count
            params["date"] = str(slot.time_range.start.date())
        elif slot.action == "order":
            params["items"] = [{"name": "signature_dish", "quantity": guest_count}]
        elif slot.action == "check_queue":
            params["guest_count"] = guest_count
        elif slot.action == "search_poi":
            params["city"] = slot.poi.city
            params["lat"] = context.lat
            params["lng"] = context.lng
            params["radius_km"] = 15

        return params

    async def _call_mock_tool(self, slot_index: int, tool: str) -> ToolResult:
        delay = random.uniform(0.02, 0.15)
        await asyncio.sleep(delay)
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

    def _log_tool_call(self, r: ToolResult, plan_id: str, layer: int) -> None:
        logger.info(
            "tool_execution",
            plan_id=plan_id,
            layer=layer,
            invocation_id=r.invocation_id,
            status=r.status,
            error_code=r.error_code,
            latency_ms=r.latency_ms,
        )

    def to_execution_state(self, result: ExecutionResult) -> ExecutionState:
        """Convert execution output into the new typed runtime state."""

        tool_records: list[ToolExecutionRecord] = []
        for layer, slot_result in self._iter_slot_results(result):
            tool_records.append(
                ToolExecutionRecord(
                    invocation_id=f"{slot_result.tool_name}_{slot_result.slot_index}",
                    slot_index=slot_result.slot_index,
                    tool_name=slot_result.tool_name,
                    layer=layer,
                    status=self._normalize_tool_status(slot_result.status),
                    error_code=slot_result.error_code,
                    error_message=slot_result.error_message,
                    booking_id=slot_result.booking_id,
                    latency_ms=slot_result.elapsed_ms,
                )
            )

        for failed in result.failed_slots:
            if any(
                record.slot_index == failed.slot_index and record.tool_name == failed.tool_name
                for record in tool_records
            ):
                continue
            tool_records.append(
                ToolExecutionRecord(
                    invocation_id=f"{failed.tool_name}_{failed.slot_index}",
                    slot_index=failed.slot_index,
                    tool_name=failed.tool_name,
                    layer=-1,
                    status="skipped" if failed.error_code == "SKIPPED" else "failure",
                    error_code=failed.error_code,
                    error_message=failed.error_message,
                )
            )

        return ExecutionState(
            run_id=result.plan_id,
            status=result.status,
            tool_records=tool_records,
            confirmed_bookings=result.confirmed_bookings,
            failed_slot_indices=[failed.slot_index for failed in result.failed_slots],
            total_elapsed_ms=result.total_elapsed_ms,
            raw_result=result,
        )

    def _get_gateway(self) -> ToolGatewayPort | None:
        if self._gateway is not None:
            return self._gateway
        try:
            from app.adapters.tools.mock_gateway import MockToolGatewayAdapter

            self._gateway = MockToolGatewayAdapter()
        except Exception:
            logger.warning("execution_engine_gateway_unavailable", exc_info=True)
            self._gateway = None
        return self._gateway

    @staticmethod
    def _normalize_gateway_response(tool: str, slot_index: int, resp: dict[str, Any]) -> dict[str, Any]:
        """Normalize legacy gateway responses into ToolResult-compatible fields."""

        if "status" in resp:
            status = resp.get("status", "failure")
            if status not in {"success", "failure", "timeout", "degraded"}:
                status = "failure"
            return {
                "status": status,
                "data": resp.get("data") or {},
                "error_code": resp.get("error_code"),
                "error_message": resp.get("error_message"),
                "latency_ms": resp.get("latency_ms", 0),
            }

        success = bool(resp.get("success"))
        error_message = resp.get("error_message") or resp.get("error")
        data = resp.get("data") or {}
        if success and not data.get("booking_id"):
            data = {
                **data,
                "booking_id": f"gw_{tool}_{slot_index}",
            }
        return {
            "status": "success" if success else "failure",
            "data": data,
            "error_code": None if success else "GATEWAY_ERROR",
            "error_message": error_message,
            "latency_ms": resp.get("latency_ms", 0),
        }

    @staticmethod
    def _normalize_tool_status(status: str) -> str:
        if status in {"success", "failure", "timeout"}:
            return status
        if status == "degraded":
            return "success"
        return "failure"

    @staticmethod
    def _iter_slot_results(result: ExecutionResult) -> list[tuple[int, SlotExecutionResult]]:
        layered_results: list[tuple[int, SlotExecutionResult]] = []
        for slot_result in result.slot_results.values():
            layer = -1
            tool_meta = TOOL_REGISTRY.get(slot_result.tool_name)
            if tool_meta is not None:
                layer = tool_meta.layer
            layered_results.append((layer, slot_result))
        return layered_results


def _tool_name_for_result(r: ToolResult, slot_index: int) -> str:
    return r.data.get("tool_name", str(slot_index)) if r.data else str(slot_index)
