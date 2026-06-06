"""Tool Node —— 工具执行 + user-facing tool 检测。

所有工具调用通过此节点执行：
- user-facing 工具 (ask_user, present_plan) → 不执行，设置 hitl_payload
- internal state 工具 (update_intent, ...) → 直接更新 PlanState 字段
- execution 工具 (mock_order_create, mock_payment_charge) → 通过 SagaCoordinator 事务执行
- 标准工具 (amap_poi_search, pymoo_solve, ...) → 通过 ToolHarness 执行

Author: SnapTrip Team
Date: 2026-05-29
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage

from agent.schemas.events import RuntimeEvent
from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)


def _get_event_bus():
    from agent.graph import _runtime
    if _runtime:
        return _runtime.event_bus
    return None


async def _emit_tool_event(plan_id: str, event_type: str, payload: dict[str, Any]) -> None:
    event_bus = _get_event_bus()
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

USER_FACING_NAMES = {"ask_user", "present_plan", "present_booking"}
INTERNAL_NAMES = {"update_intent", "update_profile", "update_itinerary", "update_extract_result"}
_EXECUTION_NAMES = {"mock_order_create", "mock_payment_charge"}


def _get_harness_and_session():
    """获取 ToolHarness + SessionContext。"""
    from agent.graph import _runtime
    if _runtime:
        return _runtime.harness, _runtime.session_ctx
    return None, None


def _apply_state_update(state: PlanState, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """将 internal state tool 的参数应用到 PlanState。"""
    updates: dict[str, Any] = {}

    if tool_name == "update_extract_result":
        from agent.schemas.extract import ExtractResult, UpdateExtractResultInput

        # 获取或创建 ExtractResult
        extract_result: ExtractResult = state.get("extract_result")  # type: ignore[assignment]
        if extract_result is None:
            extract_result = ExtractResult()

        # 解析增量更新
        update = UpdateExtractResultInput(**args)
        changed = extract_result.apply_update(update)
        updates["extract_result"] = extract_result
        logger.debug("tool_node: update_extract_result → %s", changed)

    elif tool_name == "update_intent":
        intent = dict(state.get("intent", {}))
        for k in ("city", "guest_count", "budget", "date", "time_window_start",
                  "time_window_hours", "preferences", "scene_hint",
                  "dietary", "allergens", "child_age", "constraints_notes"):
            if k in args and args[k] is not None and args[k] != "" and args[k] != []:
                intent[k] = args[k]
        updates["intent"] = intent

    elif tool_name == "update_profile":
        profile = dict(state.get("user_profile", {}))
        for k in ("dietary_tendency", "budget_tendency", "travel_style", "favorite_poi_types"):
            if k in args and args[k] is not None:
                profile[k] = args[k]
        updates["user_profile"] = profile

    elif tool_name == "update_itinerary":
        itinerary: dict[str, Any] = {
            "summary": args.get("summary", ""),
            "slots": args.get("slots", []),
            "total_cost": args.get("total_cost", 0),
            "total_time_min": args.get("total_time_min", 0),
        }
        updates["itinerary"] = itinerary
        updates["selected_solution"] = {
            "activity_name": args.get("activity_name", ""),
            "restaurant_name": args.get("restaurant_name", ""),
        }

    logger.debug("tool_node: %s → %s", tool_name, list(updates.keys()))
    return updates


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
    """Execute a batch of execution tools via SagaCoordinator.

    Returns one result dict per exec_call: {tc_id, success, data, saga_status}.
    """
    from agent.tools.transaction.saga import SagaCoordinator

    coordinator = SagaCoordinator()
    steps = [{"tool_name": c["tc_name"], "args": c["tc_args"]} for c in exec_calls]

    try:
        saga_result = await coordinator.execute(harness, session_ctx, steps)
    except Exception as e:
        logger.exception("SagaCoordinator execution failed")
        return [
            {"tc_id": c["tc_id"], "success": False,
             "data": {"error": f"Saga error: {type(e).__name__}: {e}",
                      "saga_status": "error"}}
            for c in exec_calls
        ]

    batch_results = saga_result["results"]  # reserve results + confirm results
    n = len(exec_calls)
    output: list[dict[str, Any]] = []

    for i, call in enumerate(exec_calls):
        # On saga success: confirm result at index n+i
        # On saga failure: last available result for this step
        if saga_result["status"] == "done" and len(batch_results) >= 2 * n:
            confirm = batch_results[n + i]
            output.append({
                "tc_id": call["tc_id"],
                "success": confirm.success,
                "data": confirm.data,
                "saga_status": "done",
            })
        else:
            # Failure — find best available result
            found = None
            for j in range(i, len(batch_results), n):
                if j < len(batch_results):
                    found = batch_results[j]
            if found is not None:
                output.append({
                    "tc_id": call["tc_id"],
                    "success": found.success,
                    "data": found.data,
                    "saga_status": saga_result["status"],
                })
            else:
                output.append({
                    "tc_id": call["tc_id"],
                    "success": False,
                    "data": {"error": "Saga rolled back before this step",
                             "saga_status": saga_result["status"]},
                    "saga_status": saga_result["status"],
                })

    return output


async def tool_node(state: PlanState) -> dict:
    """执行 LLM 请求的 tool calls。

    Execution tools (mock_order_create, mock_payment_charge) 通过
    SagaCoordinator 事务执行 (reserve → confirm → rollback)。

    Returns:
        {
            "messages": [ToolMessage(...), ...],
            "hitl_payload": dict | None,
            # + internal state update keys
        }
    """
    harness, session_ctx = _get_harness_and_session()

    # Inject user_id from PlanState into SessionContext so AuthHook passes.
    # SessionContext is a process-level singleton; set it per-invocation.
    if session_ctx and state.get("user_id"):
        session_ctx.user_id = state["user_id"]

    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []

    results: list[ToolMessage] = []
    hitl_payload: dict[str, Any] | None = None
    state_updates: dict[str, Any] = {}

    # ── Separate tool calls by category ──
    exec_calls: list[dict[str, Any]] = []
    standard_calls: list[dict[str, Any]] = []

    for tc in tool_calls:
        tc_id, tc_name, tc_args = _parse_tool_call(tc)
        logger.debug("tool_node: dispatching %s", tc_name)

        if tc_name in USER_FACING_NAMES:
            hitl_payload = {
                "type": tc_name,
                "message": tc_args.get("message", ""),
            }
            if tc_name == "present_plan":
                hitl_payload["plan"] = tc_args.get("plan", {})
                hitl_payload["options"] = ["confirmed", "modified", "rejected"]
            elif tc_name == "present_booking":
                hitl_payload["orders"] = tc_args.get("orders", [])
                hitl_payload["total_amount"] = tc_args.get("total_amount", 0)
                hitl_payload["options"] = ["confirmed", "rejected"]
            else:
                hitl_payload["options"] = tc_args.get("options", [])

            results.append(ToolMessage(
                content=json.dumps({"status": "presented_to_user"}),
                tool_call_id=tc_id,
            ))

        elif tc_name in INTERNAL_NAMES:
            updates = _apply_state_update(state, tc_name, tc_args)
            state_updates.update(updates)
            results.append(ToolMessage(
                content=json.dumps({"status": "state_updated", "fields": list(updates.keys())}),
                tool_call_id=tc_id,
            ))

        elif tc_name in _EXECUTION_NAMES:
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

    # ── Execute execution tools via SagaCoordinator ──
    if exec_calls and harness and session_ctx:
        plan_id = state.get("plan_id", "")
        tool_names = [c["tc_name"] for c in exec_calls]
        await _emit_tool_event(plan_id, "execution", {
            "phase": "booking",
            "tools": tool_names,
        })
        saga_results = await _execute_saga(harness, session_ctx, exec_calls)
        for sr in saga_results:
            data = sr["data"] if sr["success"] else {"error": sr["data"].get("error", "unknown")}
            results.append(ToolMessage(
                content=json.dumps(data, ensure_ascii=False),
                tool_call_id=sr["tc_id"],
            ))
        session_ctx.active_tx = None
        await _emit_tool_event(plan_id, "execution_done", {
            "phase": "booking",
            "tools": tool_names,
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

    response: dict[str, Any] = {
        "messages": results,
        "hitl_payload": hitl_payload,
    }
    response.update(state_updates)

    return response
