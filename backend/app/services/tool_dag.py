"""Tool DAG 编排器 —— 拓扑排序 + 分层并行 + 熔断 + Redis 追踪。

核心组件:
  1. build_execution_layers(): 从 PlanSlots 构建 DAG 分层
  2. ToolDAGScheduler: 兼容旧接口（mock 随机延迟）
  3. ToolDAGExecutor: 真实执行引擎（httpx → Mock Server + Redis + 熔断）

DAG 构建:
  - 根据 ToolInvocation.dependencies 构建邻接表
  - 拓扑排序检测环
  - 无依赖节点为第 1 层，可并行执行

执行策略:
  - asyncio.gather 并行执行同层
  - 每节点通过 httpx 调用 Mock Server
  - 结果写入 Redis: txn:{id}:step:{invocation_id}
  - CircuitBreaker 保护每个工具调用

Author: SnapTrip Team
Date: 2026-05-17
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from collections import defaultdict, deque
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.plan import PlanDraft, PlanSlot
from app.schemas.tool import TOOL_REGISTRY, ToolInvocation, ToolResult
from app.services.circuit_breaker import CircuitBreaker
from app.services.memory_service import MemoryService

MOCK_BASE = settings.MOCK_API_BASE_URL

TOOL_ENDPOINTS: dict[str, tuple[str, str]] = {
    "search_poi": ("GET", "/poi/search"),
    "get_user_profile": ("GET", "/user/profile"),
    "check_queue": ("GET", "/poi/queue"),
    "check_availability": ("GET", "/poi/search"),
    "check_child_facility": ("GET", "/poi/search"),
    "calculate_route": ("GET", "/route"),
    "book_table": ("POST", "/order/prepare"),
    "book_ticket": ("POST", "/order/prepare"),
    "order": ("POST", "/order/prepare"),
    "notify": ("GET", "/health"),
}


# ===== DAG 构建 =====


def build_execution_layers(slots: list[PlanSlot]) -> dict[int, list[ToolInvocation]]:
    """从 PlanSlot 列表构建分层 ToolInvocation（兼容旧接口）。"""
    layers: dict[int, list[ToolInvocation]] = defaultdict(list)
    for idx, slot in enumerate(slots):
        tool_name = slot.action if slot.action in TOOL_REGISTRY else "search_poi"
        if tool_name not in TOOL_REGISTRY:
            continue
        meta = TOOL_REGISTRY[tool_name]
        layers[meta.layer].append(
            ToolInvocation(
                tool_name=tool_name,
                params={
                    "poi_id": slot.poi.id,
                    "poi_name": slot.poi.name,
                    "guest_count": 2,
                    "time_range": str(slot.time_range),
                    "slot_index": idx,
                },
                timeout_ms=meta.default_timeout_ms,
                dependencies=meta.dependencies,
            )
        )
    return layers


def topological_layers(invocations: list[ToolInvocation]) -> list[list[ToolInvocation]]:
    """拓扑排序分层：返回 [[L0_nodes], [L1_nodes], ...]。

    Raises:
        ValueError: 检测到循环依赖
    """
    name_to_inv: dict[str, ToolInvocation] = {i.invocation_id: i for i in invocations}
    in_degree: dict[str, int] = {i.invocation_id: 0 for i in invocations}
    adj: dict[str, list[str]] = defaultdict(list)

    for inv in invocations:
        for dep in inv.dependencies:
            adj.setdefault(dep, []).append(inv.invocation_id)
            in_degree[inv.invocation_id] = in_degree.get(inv.invocation_id, 0) + 1

    queue: deque[str] = deque(k for k, v in in_degree.items() if v == 0)
    layers: list[list[ToolInvocation]] = []

    while queue:
        layer: list[ToolInvocation] = []
        for _ in range(len(queue)):
            nid = queue.popleft()
            layer.append(name_to_inv[nid])
            for neighbor in adj.get(nid, []):
                if neighbor in in_degree:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
        if layer:
            layers.append(layer)

    if sum(len(ly) for ly in layers) != len(invocations):
        raise ValueError("检测到循环依赖，无法执行 DAG")

    return layers


# ===== 旧版调度器（兼容） =====


class ToolDAGScheduler:
    """兼容旧接口的轻量调度器"""

    def __init__(self):
        self.failure_counts: dict[str, int] = defaultdict(int)
        self.circuit_open: set[str] = set()

    async def execute(self, draft: PlanDraft) -> dict[str, Any]:
        layers = build_execution_layers(draft.slots)
        confirmed: dict[int, str] = {}
        failed: list[dict[str, object]] = []
        total_ms = 0
        for layer_idx in sorted(layers.keys()):
            t0 = time.perf_counter()
            tasks = [self._mock_call(inv) for inv in layers[layer_idx]]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for r in gathered:
                if isinstance(r, BaseException):
                    continue
                si = r.data.get("slot_index", -1) if r.data else -1
                if r.status == "success" and r.data and "booking_id" in (r.data or {}):
                    confirmed[si] = r.data["booking_id"]
                elif r.status != "success":
                    failed.append({"slot_index": si, "invocation_id": r.invocation_id, "error_code": r.error_code})
            total_ms += int((time.perf_counter() - t0) * 1000)
        status = "full_success"
        if failed:
            status = "partial_success" if confirmed else "full_failure"
        return {"status": status, "confirmed_bookings": confirmed, "failed_slots": failed, "total_elapsed_ms": total_ms}

    async def _mock_call(self, inv: ToolInvocation) -> ToolResult:
        delay = random.uniform(0.02, 0.10)
        await asyncio.sleep(delay)
        si = inv.params.get("slot_index", -1)
        return ToolResult(
            invocation_id=inv.invocation_id,
            status="success",
            data={"booking_id": f"bk_{si}_{random.randint(1000, 9999)}", "slot_index": si},
            latency_ms=int(delay * 1000),
        )


# ===== 新版执行引擎 =====


class ToolDAGExecutor:
    """真实 DAG 执行引擎 —— httpx → Mock Server + Redis + 熔断"""

    def __init__(self, memory: MemoryService | None = None) -> None:
        self.transaction_id = str(uuid.uuid4())
        self._memory = memory
        self._breakers: dict[str, CircuitBreaker] = {}

    def _get_breaker(self, tool_name: str) -> CircuitBreaker:
        if tool_name not in self._breakers:
            self._breakers[tool_name] = CircuitBreaker(tool_name)
        return self._breakers[tool_name]

    async def execute(self, invocations: list[ToolInvocation]) -> dict[str, Any]:
        """执行 DAG。

        Args:
            invocations: 工具调用列表

        Returns:
            {status, transaction_id, results: dict[invocation_id, ToolResult],
             layer_timings: dict[layer, ms], total_elapsed_ms}
        """
        try:
            layers = topological_layers(invocations)
        except ValueError as e:
            return {"status": "failed", "transaction_id": self.transaction_id, "error": str(e), "results": {}}

        all_results: dict[str, ToolResult] = {}
        layer_timings: dict[int, int] = {}
        total_ms = 0
        abort = False

        for layer_idx, layer in enumerate(layers):
            if abort:
                break
            t0 = time.perf_counter()
            tasks = [self._execute_node(node) for node in layer]
            layer_results = await asyncio.gather(*tasks, return_exceptions=True)

            for node, r in zip(layer, layer_results, strict=False):
                if isinstance(r, BaseException):
                    r = ToolResult(
                        invocation_id=node.invocation_id,
                        status="failure",
                        error_code="EXECUTION_ERROR",
                        error_message=str(r),
                    )
                assert isinstance(r, ToolResult)
                all_results[node.invocation_id] = r

                if self._memory:
                    await self._persist_step(node.invocation_id, r)

                definition = TOOL_REGISTRY.get(node.tool_name)
                if definition and r.status == "failure" and definition.fallback_policy == "abort":
                    abort = True

            layer_timings[layer_idx] = int((time.perf_counter() - t0) * 1000)
            total_ms += layer_timings[layer_idx]

        success_count = sum(1 for r in all_results.values() if r.status in ("success", "degraded"))
        status = "success"
        if success_count == 0:
            status = "failure"
        elif success_count < len(all_results):
            status = "partial"

        if self._memory:
            await self._memory.set_transaction_status(self.transaction_id, status, ttl=600)

        return {
            "status": status,
            "transaction_id": self.transaction_id,
            "results": {k: v.model_dump() for k, v in all_results.items()},
            "layer_timings": layer_timings,
            "total_elapsed_ms": total_ms,
        }

    async def _execute_node(self, inv: ToolInvocation) -> ToolResult:
        breaker = self._get_breaker(inv.tool_name)

        async def _call():
            return await self._http_call(inv)

        return await breaker.call(_call)

    async def _http_call(self, inv: ToolInvocation) -> ToolResult:
        endpoint = TOOL_ENDPOINTS.get(inv.tool_name)
        if not endpoint:
            return ToolResult(
                invocation_id=inv.invocation_id,
                status="failure",
                error_code="UNKNOWN_TOOL",
                error_message=f"未注册的工具: {inv.tool_name}",
            )

        method, path = endpoint
        url = f"{MOCK_BASE}{path}"
        timeout_s = inv.timeout_ms / 1000.0

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                if method == "GET":
                    resp = await client.get(url, params=inv.params)
                else:
                    resp = await client.post(url, json=inv.params)
                elapsed = int((time.perf_counter() - t0) * 1000)

            if resp.status_code >= 500:
                return ToolResult(
                    invocation_id=inv.invocation_id,
                    status="failure",
                    error_code="UPSTREAM_ERROR",
                    error_message=f"Mock Server 返回 {resp.status_code}",
                    latency_ms=elapsed,
                )

            body = resp.json()
            return ToolResult(
                invocation_id=inv.invocation_id,
                status=body.get("status", "success"),
                data=body.get("data"),
                error_code=body.get("error_code"),
                error_message=body.get("error_message"),
                latency_ms=body.get("latency_ms", elapsed),
            )
        except httpx.TimeoutException:
            elapsed = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                invocation_id=inv.invocation_id,
                status="timeout",
                error_code="TIMEOUT",
                error_message=f"调用 {inv.tool_name} 超时 ({timeout_s}s)",
                latency_ms=elapsed,
            )
        except Exception as e:
            elapsed = int((time.perf_counter() - t0) * 1000)
            return ToolResult(
                invocation_id=inv.invocation_id,
                status="failure",
                error_code="NETWORK_ERROR",
                error_message=str(e),
                latency_ms=elapsed,
            )

    async def _persist_step(self, invocation_id: str, result: ToolResult) -> None:
        if self._memory is None:
            return
        key = f"txn:{self.transaction_id}:step:{invocation_id}"
        await self._memory.cache_set(key, result.model_dump(), ttl_s=600)
