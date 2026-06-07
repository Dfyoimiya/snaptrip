# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Tool Execution Dispatch Node
# ────────────────────────────────────────────────────────────────────────────
# Generic tool dispatch node. Categorizes tool calls and executes them:
#   - user-facing tools → route to HITL interrupt (if hitl_node is active)
#   - standard tools     → execute via ToolHarness
#   - saga tools         → execute via SagaCoordinator (transactional)
#
# Trip-specific tool categories (USER_FACING_NAMES, INTERNAL_NAMES,
# EXECUTION_NAMES) have been generalized. Define your own tool sets
# in utils.py or override the dispatch logic.
#
# Archived: 2026-06-07 — repurposed from trip planning agent
# ────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage

from agent.schemas.events import RuntimeEvent
from agent.schemas.state import PlanState
from agent.utils import (
    EXECUTION_NAMES,
    USER_FACING_NAMES,
    get_event_bus,
)

logger = logging.getLogger(__name__)


async def _emit_tool_event(plan_id: str, event_type: str, payload: dict[str, Any]) -> None:
    """Emit a RuntimeEvent via the event bus (non-blocking, best-effort)."""
    event_bus = get_event_bus()
    if event_bus is None:
        return
    event = RuntimeEvent(
        plan_id=plan_id,
        node_name="tools",
        event_type=event_type,
        payload=payload,
    )
    try:
        await event_bus.emit(event)
    except Exception:
        logger.warning("tool_node: failed to emit %s event", event_type, exc_info=True)


def _get_harness_and_session():
    """Get ToolHarness + SessionContext from runtime."""
    from agent.graph import _runtime
    if _runtime:
        return _runtime.harness, _runtime.session_ctx
    return None, None


def _parse_tool_call(tc: dict | Any) -> tuple[str, str, dict[str, Any]]:
    """Normalize a LangChain tool call into (id, name, args dict)."""
    tc_id = tc["id"] if isinstance(tc, dict) else tc.id
    tc_name = tc["name"] if isinstance(tc, dict) else tc.name
    if isinstance(tc, dict):
        raw_args = tc.get("args", tc.get("arguments", {}))
        tc_args: dict[str, Any] = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    else:
        raw_args = getattr(tc, "args", getattr(tc, "arguments", {}))
        tc_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
    return tc_id, tc_name, tc_args


async def _execute_saga(
    harness, session_ctx, exec_calls: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Execute a batch of transactional tools via SagaCoordinator."""
    from agent.tools.transaction.saga import SagaCoordinator

    coordinator = SagaCoordinator()
    steps = [{"tool_name": c["tc_name"], "args": c["tc_args"]} for c in exec_calls]

    try:
        saga_result = await coordinator.execute(harness, session_ctx, steps)
    except Exception as e:
        logger.exception("SagaCoordinator execution failed")
        return [
            {"tc_id": c["tc_id"], "success": False,
             "data": {"error": f"Saga error: {type(e).__name__}: {e}", "saga_status": "error"}}
            for c in exec_calls
        ]

    batch_results = saga_result["results"]
    n = len(exec_calls)
    output: list[dict[str, Any]] = []

    for i, call in enumerate(exec_calls):
        if saga_result["status"] == "done" and len(batch_results) >= 2 * n:
            confirm = batch_results[n + i]
            output.append({
                "tc_id": call["tc_id"], "success": confirm.success,
                "data": confirm.data, "saga_status": "done",
            })
        else:
            found = None
            for j in range(i, len(batch_results), n):
                if j < len(batch_results):
                    found = batch_results[j]
            if found is not None:
                output.append({
                    "tc_id": call["tc_id"], "success": found.success,
                    "data": found.data, "saga_status": saga_result["status"],
                })
            else:
                output.append({
                    "tc_id": call["tc_id"], "success": False,
                    "data": {"error": "Saga rolled back before this step",
                             "saga_status": saga_result["status"]},
                    "saga_status": saga_result["status"],
                })

    return output


# ── Main dispatch ───────────────────────────────────────────────────────────


async def tool_node(state: PlanState) -> dict:
    """Execute LLM-requested tool calls.

    Dispatches by category:
      - User-facing tools → returns hitl_payload for hitl_node
      - Execution (saga) tools → SagaCoordinator
      - Standard tools → ToolHarness

    Returns:
        {"messages": [ToolMessage(...)], "hitl_payload": dict | None, ...}
    """
    harness, session_ctx = _get_harness_and_session()

    if session_ctx and state.get("user_id"):
        session_ctx.user_id = state["user_id"]

    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []

    results: list[ToolMessage] = []
    hitl_payload: dict[str, Any] | None = None

    exec_calls: list[dict[str, Any]] = []
    standard_calls: list[dict[str, Any]] = []

    for tc in tool_calls:
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        logger.debug("tool_node: dispatching %s", tc_name)

        if tc_name in USER_FACING_NAMES:
            # User-facing: set hitl_payload, don't execute
            hitl_payload = {
                "type": tc_name,
                "message": tc_args.get("message", ""),
            }
            if "options" in tc_args:
                hitl_payload["options"] = tc_args["options"]
            results.append(ToolMessage(
                content=json.dumps({"status": "presented_to_user"}),
                tool_call_id=tc_id,
            ))

        elif tc_name in EXECUTION_NAMES:
            exec_calls.append({
                "tc_id": tc_id, "tc_name": tc_name, "tc_args": tc_args,
            })

        else:
            standard_calls.append({
                "tc_id": tc_id, "tc_name": tc_name, "tc_args": tc_args,
            })

    # ── Execute standard tools individually ──
    for sc in standard_calls:
        if harness and session_ctx:
            try:
                result = await harness.execute(
                    tool_name=sc["tc_name"],
                    args=sc["tc_args"],
                    session_ctx=session_ctx,
                )
                data = result.data if result.success else {"error": result.data.get("error", "unknown")}
            except Exception as e:
                logger.exception("ToolHarness execution failed for %s", sc["tc_name"])
                data = {"error": f"{type(e).__name__}: {e}"}
        else:
            data = {"error": "ToolHarness not available"}

        results.append(ToolMessage(
            content=json.dumps(data, ensure_ascii=False),
            tool_call_id=sc["tc_id"],
        ))

    # ── Execute saga tools ──
    if exec_calls and harness and session_ctx:
        plan_id = state.get("plan_id", "")
        tool_names = [c["tc_name"] for c in exec_calls]
        await _emit_tool_event(plan_id, "execution", {"phase": "tx", "tools": tool_names})
        saga_results = await _execute_saga(harness, session_ctx, exec_calls)
        for sr in saga_results:
            data = sr["data"] if sr["success"] else {"error": sr["data"].get("error", "unknown")}
            results.append(ToolMessage(
                content=json.dumps(data, ensure_ascii=False),
                tool_call_id=sr["tc_id"],
            ))
        session_ctx.active_tx = None
        await _emit_tool_event(plan_id, "execution_done", {
            "phase": "tx", "tools": tool_names,
            "results": [
                {"tc_id": sr["tc_id"], "success": sr["success"], "saga_status": sr["saga_status"]}
                for sr in saga_results
            ],
        })
    elif exec_calls:
        for ec in exec_calls:
            results.append(ToolMessage(
                content=json.dumps({"error": "ToolHarness not available for Saga execution"}),
                tool_call_id=ec["tc_id"],
            ))

    return {
        "messages": results,
        "hitl_payload": hitl_payload,
    }
