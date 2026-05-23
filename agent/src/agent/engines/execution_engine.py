"""Execution Engine —— Tool DAG 编排入口。

将 PlanDraft 的抽象时隙翻译为 Tool 调用序列，按 DAG 分层并行执行。

核心特性:
  1. DAG 依赖感知: 上游 Tool 失败时，下游依赖 Tool 自动跳过 (SKIPPED)
  2. 分层超时: per-tool 3s / total DAG 10s
  3. 超时不阻塞同层: 单 Tool 超时不影响同层其他 Tool 并行执行
  4. 安全管道 (v3): 幂等检查 → 双层熔断 → Provider 调用 → Saga 记录 → UNKNOWN 异步确认
  5. 并发控制: Session/User 双层 Redis 锁
  6. 结构化日志: 每个 Tool 调用输出 JSON 格式日志供前端 AgentMonitor 渲染

v3 更新: 注入 ToolAdapter + IdempotencyService + CircuitBreakerRegistry
         + SagaCoordinator + PhysicalConfirmator + Redis 锁

Author: SnapTrip Team
Date: 2026-05-13 / v3 update 2026-05-20
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from snaptrip_shared.core.constants import EXEC_TIMEOUT_TOTAL_S
from snaptrip_shared.core.logging import get_logger
from snaptrip_shared.schemas.plan import (
    ExecutionResult,
    FailedSlot,
    IntentSchema,
    PlanDraft,
    PlanSlot,
    SlotExecutionResult,
)

from agent.ports.tools import ToolGatewayPort
from agent.protocol import AgentContext, AgentResult, BaseAgent
from agent.schemas.state import ExecutionState, ToolExecutionRecord
from agent.schemas.tool import TOOL_REGISTRY, ToolDefinition, ToolResult
from agent.schemas.tool_provider import PhysicalActionState, SagaStep, ToolProviderResult

logger = get_logger(__name__)


class ExecutionEngine(BaseAgent):
    """Execution Engine —— 将 PlanDraft 编译为 DAG 并安全执行。

    v3 安全管道:
      1. 并发锁 (Session + User)
      2. 双层熔断检查 (L1 Provider + L2 Tool)
      3. 幂等键生成 + 获取
      4. ToolAdapter.call()
      5. Saga 步骤记录 (物理操作)
      6. UNKNOWN → PhysicalConfirmator 异步确认
    """

    name = "execution_engine"

    def __init__(
        self,
        # ── v3 安全管道依赖 ──
        tool_adapter: Any | None = None,  # ToolAdapter (避免循环导入用 Any)
        circuit_breaker_registry: Any | None = None,  # CircuitBreakerRegistry
        idempotency: Any | None = None,  # IdempotencyService
        saga: Any | None = None,  # SagaCoordinator
        confirmator: Any | None = None,  # PhysicalConfirmator
        redis_client: Any | None = None,
        # ── 旧版兼容 ──
        gateway: ToolGatewayPort | None = None,
    ) -> None:
        super().__init__()
        self._tool_adapter = tool_adapter
        self._cb_registry = circuit_breaker_registry
        self._idempotency = idempotency
        self._saga = saga
        self._confirmator = confirmator
        self._redis = redis_client
        self._gateway = gateway

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    async def execute(self, context: AgentContext) -> AgentResult:
        draft = self._extract_draft(context)
        if not draft:
            return AgentResult(status="failed", error="No plan draft found")

        # ── v3 并发锁: Session + User 双层 ──
        session_lock_key: str | None = None
        user_lock_key: str | None = None

        if self._redis:
            session_lock_key = f"exec_lock:session:{context.session_id}"
            user_lock_key = f"exec_lock:user:{context.user_id}"

            # 先抢 Session 锁（细粒度）
            if not await self._acquire_lock(session_lock_key, draft.plan_id):
                return AgentResult(
                    status="failed",
                    error="当前 Session 有 plan 正在执行",
                )
            try:
                # 再抢 User 锁（粗粒度，防止跨 Session 并发）
                if not await self._acquire_lock(user_lock_key, draft.plan_id):
                    return AgentResult(
                        status="failed",
                        error="当前用户有 plan 正在执行，请稍候",
                    )
                try:
                    return await self._execute_timed(draft, context)
                finally:
                    await self._release_lock(user_lock_key)
            finally:
                await self._release_lock(session_lock_key)
        else:
            return await self._execute_timed(draft, context)

    async def _execute_timed(self, draft: PlanDraft, context: AgentContext) -> AgentResult:
        try:
            result = await asyncio.wait_for(
                self._execute_dag(draft, context),
                timeout=EXEC_TIMEOUT_TOTAL_S,
            )
        except TimeoutError:
            # DAG 整体超时 → 补偿已执行的物理操作
            if self._saga:
                compensate_errors = await self._saga.compensate()
                if compensate_errors:
                    logger.error("execution_timeout_compensate_errors", errors=compensate_errors)
            return AgentResult(
                status="timeout",
                error=f"DAG execution exceeded {EXEC_TIMEOUT_TOTAL_S}s limit",
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
            meta = self._get_tool_definition(tool)
            if meta is None:
                continue
            layers[meta.layer].append((i, tool, meta))

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
                plan_slot = slots_by_idx.get(slot_i)
                tasks.append(self._execute_single_tool(slot_i, tool, meta, plan_slot, context))

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
                    failed_slots.append(
                        FailedSlot(
                            slot_index=si,
                            tool_name=_tool_name_for_result(r, si),
                            error_code=r.error_code or "UNKNOWN",
                            error_message=r.error_message or "Tool failed",
                            poi_id=str(si),
                        )
                    )

                self._log_tool_call(r, draft.plan_id, layer_idx)

            timings[layer_idx] = int((time.perf_counter() - t0) * 1000)
            total_ms += timings[layer_idx]

        status = "full_success"
        if failed_slots:
            status = "partial_success" if confirmed else "full_failure"

        # ── v3 失败补偿: 部分/全部失败时逆序补偿物理操作 ──
        if failed_slots and self._saga and self._saga.has_physical_steps:
            compensate_errors = await self._saga.compensate()
            if compensate_errors:
                logger.error("dag_compensate_errors", errors=compensate_errors)

        slot_result_map: dict[int, SlotExecutionResult] = {}
        for _layer_idx, items in results.items():
            for r in items:
                si = r.data.get("slot_index", -1) if r.data else -1
                booking_ref_val = r.data.get("booking_ref") if r.data else None
                physical_state_val = r.data.get("physical_state", "pending") if r.data else "pending"
                slot_result_map[si] = SlotExecutionResult(
                    slot_index=si,
                    tool_name=_tool_name_for_result(r, si),
                    status=r.status,
                    booking_id=r.data.get("booking_id") if r.data else None,
                    booking_ref=booking_ref_val,
                    physical_state=physical_state_val,
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
    # single tool execution (v3 safety pipeline)
    # ------------------------------------------------------------------

    async def _execute_single_tool(
        self,
        slot_index: int,
        tool: str,
        meta: ToolDefinition,
        slot: PlanSlot | None = None,
        context: AgentContext | None = None,
    ) -> ToolResult:
        """执行单个工具调用 —— v3 安全管道入口。

        优先走 ToolAdapter 安全管道（熔断 + 幂等 + Saga + 确认），
        ToolAdapter 不可用时回退到旧版 gateway / mock 路径。
        """
        # ── v3 安全管道路径 ──
        if self._tool_adapter is not None:
            return await self._execute_via_adapter(slot_index, tool, meta, slot, context)

        # ── 旧版兼容路径 ──
        timeout_s = meta.default_timeout_ms / 1000.0
        try:
            return await asyncio.wait_for(
                self._call_tool_legacy(slot_index, tool, meta, slot, context),
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

    # ------------------------------------------------------------------
    # v3 adapter pipeline
    # ------------------------------------------------------------------

    async def _execute_via_adapter(
        self,
        slot_index: int,
        tool: str,
        meta: ToolDefinition,
        slot: PlanSlot | None,
        context: AgentContext | None,
    ) -> ToolResult:
        """v3 安全管道: 熔断 → 幂等 → 调用 → Saga → 确认"""
        # mypy 类型收窄: caller 保证 tool_adapter 非 None
        assert self._tool_adapter is not None, "tool_adapter required for v3 path"

        invocation_id = f"{tool}_{slot_index}"
        t_start = time.perf_counter()

        # 1. 双层熔断检查 (L1 Provider + L2 Tool)
        provider = self._get_provider_for_tool(tool)
        if self._cb_registry and self._cb_registry.is_open(tool, provider):
            return ToolResult(
                invocation_id=invocation_id,
                status="failure",
                data={"slot_index": slot_index, "tool_name": tool},
                error_code="CIRCUIT_OPEN",
                error_message=f"熔断器已打开: {tool} (provider={provider})",
                latency_ms=0,
            )

        # 2. 构建参数
        params = self._build_tool_params(slot, context) if slot else {}

        # 3. 幂等键 (仅物理操作)
        idempotency_key: str | None = None
        if meta.physical_impact and self._idempotency:
            idempotency_key = self._build_idempotency_key(context, tool, slot, slot_index)

        # 4. 调用 ToolAdapter (幂等检查内置于 adapter.call)
        try:
            result: ToolProviderResult = await self._tool_adapter.call(
                tool_name=tool,
                params=params,
                idempotency_key=idempotency_key,
            )
        except Exception as e:
            logger.exception("tool_adapter_call_failed tool=%s", tool)
            if self._cb_registry:
                self._cb_registry.on_failure(tool, provider)
            return ToolResult(
                invocation_id=invocation_id,
                status="failure",
                data={"slot_index": slot_index, "tool_name": tool},
                error_code="ADAPTER_ERROR",
                error_message=str(e),
                latency_ms=int((time.perf_counter() - t_start) * 1000),
            )

        latency_ms = int((time.perf_counter() - t_start) * 1000)

        # 5. 熔断器反馈
        if result.status in ("success", "degraded"):
            if self._cb_registry:
                self._cb_registry.on_success(tool, provider)
        else:
            if self._cb_registry:
                self._cb_registry.on_failure(tool, provider)

        # 6. Saga 记录 (物理操作成功)
        if result.status == "success" and meta.physical_impact and self._saga:
            step = SagaStep(
                step_id=str(uuid.uuid4()),
                tool_name=tool,
                booking_ref=result.booking_ref,
                physical_impact=True,
                params=params,
                executed_at=datetime.now(UTC),
            )
            self._saga.record_step(step)

        # 7. UNKNOWN 异步确认
        if result.physical_state == PhysicalActionState.UNKNOWN and self._confirmator and result.booking_ref:
            # 需要 record_id —— 这里用 booking_ref 作为临时标识
            # 正式集成时替换为 BookingRecord 的实际 ID
            await self._confirmator.schedule_confirmation(
                record_id=result.booking_ref,
                tool_name=tool,
                booking_ref=result.booking_ref,
            )

        # 8. 转换 ToolProviderResult → ToolResult
        return ToolResult(
            invocation_id=invocation_id,
            status=self._normalize_provider_status(result.status),
            data={
                "slot_index": slot_index,
                "tool_name": tool,
                "booking_id": result.booking_ref or result.data.get("booking_id") if result.data else None,
                "booking_ref": result.booking_ref,
                "physical_state": result.physical_state.value
                if isinstance(result.physical_state, PhysicalActionState)
                else result.physical_state,
                "provider_data": result.data,
            },
            error_code=result.error_code,
            error_message=result.error_message,
            latency_ms=latency_ms or result.latency_ms,
        )

    # ------------------------------------------------------------------
    # legacy tool calling (backward compat)
    # ------------------------------------------------------------------

    async def _call_tool_legacy(
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

    def _build_tool_params(self, slot: PlanSlot | None, context: AgentContext | None) -> dict[str, object]:
        if slot is None:
            return {}
        intent = self._extract_intent(context) if context else None
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
        elif slot.action == "search_poi" and context:
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

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _get_tool_definition(self, tool_name: str) -> ToolDefinition | None:
        """获取工具元数据。优先从 ToolAdapter，回退到 TOOL_REGISTRY。"""
        if self._tool_adapter:
            meta = self._tool_adapter.get_tool_metadata(tool_name)  # type: ignore[no-any-return]
            if meta:
                return meta  # type: ignore[no-any-return]
        return TOOL_REGISTRY.get(tool_name)

    def _get_provider_for_tool(self, tool_name: str) -> str:
        """获取工具的 provider 名称（用于熔断器 L1 检查）。"""
        if self._tool_adapter:
            cfg = self._tool_adapter.get_config(tool_name)  # type: ignore[no-any-return]
            if cfg:
                return cfg.provider  # type: ignore[no-any-return]
        return ""

    def _build_idempotency_key(
        self,
        context: AgentContext | None,
        tool: str,
        slot: PlanSlot | None,
        slot_index: int,
    ) -> str:
        """生成幂等键: idempotent:{plan_id}:{tool_name}:{poi_id}:{slot_index}"""
        plan_id = context.plan_id if context else "unknown"
        poi_id = slot.poi.id if slot else "unknown"
        return f"idempotent:{plan_id}:{tool}:{poi_id}:{slot_index}"

    @staticmethod
    def _normalize_provider_status(status: str) -> str:
        """将 ToolProviderResult.status 映射到 ToolResult.status"""
        if status in ("success", "degraded"):
            return status
        if status == "unknown":
            return "degraded"
        return "failure"

    # ── logging ──

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

    # ── locking ──

    async def _acquire_lock(self, key: str, plan_id: str) -> bool:
        """获取 Redis 锁 (SET NX EX 300)。"""
        assert self._redis is not None, "redis required for locking"
        try:
            acquired = await self._redis.set(key, plan_id, nx=True, ex=300)
            return bool(acquired)
        except Exception as e:
            logger.warning("execution_lock_acquire_failed key=%s error=%s", key, e)
            return True  # Redis 不可用时允许降级

    async def _release_lock(self, key: str | None) -> None:
        """释放 Redis 锁。"""
        if not key:
            return
        assert self._redis is not None, "redis required for locking"
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning("execution_lock_release_failed key=%s error=%s", key, e)

    # ------------------------------------------------------------------
    # state conversion
    # ------------------------------------------------------------------

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
            from agent.adapters.mock_tool_gateway import MockToolGatewayAdapter

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
