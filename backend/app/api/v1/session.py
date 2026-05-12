"""SSE 流式输出 — 10 种事件类型"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from sse_starlette.sse import EventSourceResponse

from app.agents.hub import MasterController
from app.agents.protocol import AgentContext
from app.schemas.plan import PlanDraft


async def stream_plan(plan_id: str, hub: MasterController):
    """SSE 事件流生成器"""

    async def event_generator() -> AsyncGenerator[dict, None]:
        record = hub.get_state(plan_id)
        draft = hub.get_draft(plan_id)
        execution = hub.get_execution(plan_id)

        # intent
        yield {"event": "intent", "data": json.dumps({"plan_id": plan_id, "status": "parsed"}, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        # retrieval
        yield {"event": "retrieval", "data": json.dumps({"plan_id": plan_id, "candidates": len(draft.slots) if draft else 0}, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        # planning
        yield {"event": "planning", "data": json.dumps({"plan_id": plan_id, "phase": "hard_filter"}, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        if draft:
            yield {
                "event": "planning_done",
                "data": json.dumps({"plan_id": plan_id, "slots": len(draft.slots), "total_cost": draft.total_cost}, ensure_ascii=False),
            }
            await asyncio.sleep(0.3)

            # execution simulation
            for slot in draft.slots:
                yield {
                    "event": "execution",
                    "data": json.dumps({"tool": slot.action, "status": "running", "poi_name": slot.poi.name}, ensure_ascii=False),
                }
                await asyncio.sleep(0.15)
                yield {
                    "event": "execution",
                    "data": json.dumps({"tool": slot.action, "status": "success", "poi_name": slot.poi.name}, ensure_ascii=False),
                }
                await asyncio.sleep(0.15)

        yield {"event": "execution_done", "data": json.dumps({"plan_id": plan_id, "failed_count": 0}, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        # notify
        yield {"event": "notify", "data": json.dumps({"plan_id": plan_id, "card_url": f"https://snaptrip.cn/cards/{plan_id}"}, ensure_ascii=False)}
        await asyncio.sleep(0.2)

        # done
        yield {"event": "done", "data": json.dumps({"plan_id": plan_id}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
