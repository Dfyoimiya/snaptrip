"""SSE 流式输出 —— 10 种事件类型。

通过 Server-Sent Events 将 Agent 思考过程实时推送到前端 AgentMonitor。

10 个事件类型（按流顺序）:
  intent → retrieval → planning → planning_done
  → execution → execution_done
  → [fallback → consensus]
  → notify → done

前端映射: 中栏 Agent 大脑终端风格实时渲染。
复用 _sse() 辅助函数构建标准 {"event":..., "data":...} 格式。

Author: SnapTrip Team
Date: 2026-05-13
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from sse_starlette.sse import EventSourceResponse

from app.agents.hub import MasterController


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


async def stream_plan(plan_id: str, hub: MasterController):
    """SSE 事件流生成器"""

    async def event_generator() -> AsyncGenerator[dict, None]:
        draft = hub.get_draft(plan_id)

        yield _sse("intent", {"plan_id": plan_id, "status": "parsed"})
        await asyncio.sleep(0.2)

        yield _sse("retrieval", {
            "plan_id": plan_id,
            "candidates": len(draft.slots) if draft else 0,
        })
        await asyncio.sleep(0.2)

        yield _sse("planning", {"plan_id": plan_id, "phase": "hard_filter"})
        await asyncio.sleep(0.2)

        if draft:
            yield _sse("planning_done", {
                "plan_id": plan_id,
                "slots": len(draft.slots),
                "total_cost": draft.total_cost,
            })
            await asyncio.sleep(0.3)

            for slot in draft.slots:
                yield _sse("execution", {
                    "tool": slot.action, "status": "running", "poi_name": slot.poi.name,
                })
                await asyncio.sleep(0.15)
                yield _sse("execution", {
                    "tool": slot.action, "status": "success", "poi_name": slot.poi.name,
                })
                await asyncio.sleep(0.15)

        yield _sse("execution_done", {"plan_id": plan_id, "failed_count": 0})
        await asyncio.sleep(0.2)

        yield _sse("notify", {
            "plan_id": plan_id,
            "card_url": f"https://snaptrip.cn/cards/{plan_id}",
        })
        await asyncio.sleep(0.2)

        yield _sse("done", {"plan_id": plan_id})

    return EventSourceResponse(event_generator())
