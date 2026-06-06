"""SSE 流式输出 —— 由 LangGraph astream_events 驱动。

通过 Server-Sent Events 将 Agent 思考过程实时推送到前端 AgentMonitor。

事件映射（LangGraph event → SSE event）:
  on_chain_start  intent_parser     → intent
  on_chain_start  retrieval_engine  → retrieval
  on_chain_start  planning_engine   → planning
  on_chain_end    planning_engine   → planning_done
  on_chain_start  execution_engine  → execution
  on_chain_end    execution_engine  → execution_done
  on_chain_start  fallback_engine   → fallback
  on_chain_start  consensus_        → consensus
  on_chain_start  notify_engine     → notify
  on_chain_end    __end__           → done

Author: SnapTrip Team
Date: 2026-05-13 / Refactored 2026-05-17
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from sse_starlette.sse import EventSourceResponse

from app.agents.graph import plan_graph

NODE_SSE_EVENT: dict[str, str] = {
    "intent_parser": "intent",
    "retrieval_engine": "retrieval",
    "planning_engine": "planning",
    "execution_engine": "execution",
    "fallback_engine": "fallback",
    "consensus_resolver": "consensus",
    "notify_engine": "notify",
}

NODE_DONE_EVENT: dict[str, str] = {
    "planning_engine": "planning_done",
    "execution_engine": "execution_done",
}


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


async def stream_plan(plan_id: str, initial_state: dict):
    async def event_generator() -> AsyncGenerator[dict, None]:
        config = {"configurable": {"thread_id": plan_id}}
        streamed_nodes: set[str] = set()

        yield _sse("intent", {"plan_id": plan_id, "status": "started"})
        await asyncio.sleep(0.1)

        async for event in plan_graph.astream_events(initial_state, config, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chain_start" and name in NODE_SSE_EVENT:
                streamed_nodes.add(name)
                yield _sse(NODE_SSE_EVENT[name], {
                    "plan_id": plan_id,
                    "node": name,
                    "status": "running",
                })
                await asyncio.sleep(0.05)

            elif kind == "on_chain_end" and name in NODE_DONE_EVENT:
                output = event.get("data", {}).get("output", {})
                payload: dict = {"plan_id": plan_id, "node": name}
                if name == "planning_engine":
                    draft = output.get("draft", {}) or {}
                    payload["slots"] = len(draft.get("slots", []))
                    payload["total_cost"] = draft.get("total_cost", 0)
                elif name == "execution_engine":
                    exec_data = output.get("execution", {}) or {}
                    payload["failed_count"] = len(exec_data.get("failed_slots", []))
                yield _sse(NODE_DONE_EVENT[name], payload)
                await asyncio.sleep(0.05)

        yield _sse("notify", {"plan_id": plan_id, "card_url": f"https://snaptrip.cn/cards/{plan_id}"})
        await asyncio.sleep(0.1)

        yield _sse("done", {"plan_id": plan_id})

    return EventSourceResponse(event_generator())
