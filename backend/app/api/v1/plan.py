"""Plan API — 对接 MasterController"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.agents.consensus_resolver import ConsensusResolver
from app.agents.context_loader import ContextLoader
from app.agents.execution_engine import ExecutionEngine
from app.agents.fallback_engine import FallbackEngine
from app.agents.hub import MasterController
from app.agents.intent_parser import IntentParser
from app.agents.memory_manager import MemoryManager
from app.agents.notify_engine import NotifyEngine
from app.agents.planning_engine import PlanningEngine
from app.agents.protocol import AgentContext
from app.agents.retrieval_engine import RetrievalEngine
from app.api.v1.session import stream_plan
from app.core.state import StateEvent
from app.schemas.plan import PlanCreateRequest, PlanResponse, PlanSlot, ShareCard

router = APIRouter(prefix="/api/v1/plan", tags=["plan"])


def get_hub(request: Request) -> MasterController:
    if not hasattr(request.app.state, "hub"):
        request.app.state.hub = MasterController()
    return request.app.state.hub  # type: ignore[no-any-return]


@router.post("/create", response_model=PlanResponse)
async def create_plan(req: PlanCreateRequest, request: Request):
    hub = get_hub(request)
    context = AgentContext(
        user_input=req.user_input, user_id=req.user_id,
        lat=req.lat, lng=req.lng,
    )
    plan_id = context.plan_id

    record = hub.init_plan(plan_id, context)

    # Agent chain: Intent → Context → Retrieval → Planning → Confirm → Execute → Notify
    intent_parser = IntentParser()
    result = await intent_parser.execute(context)
    context.history.append(result)
    hub.store_result(plan_id, "intent_parser", result)

    hub.decide(record, StateEvent.INTENT_READY, {"intent": result.data.get("intent")})

    context_loader = ContextLoader()
    result = await context_loader.execute(context)
    context.history.append(result)
    hub.store_result(plan_id, "context_loader", result)

    memory_manager = MemoryManager()
    result = await memory_manager.execute(context)
    context.history.append(result)
    hub.store_result(plan_id, "memory_manager", result)

    retrieval = RetrievalEngine()
    result = await retrieval.execute(context)
    context.history.append(result)
    hub.store_result(plan_id, "retrieval_engine", result)

    planning = PlanningEngine()
    result = await planning.execute(context)
    context.history.append(result)
    hub.store_result(plan_id, "planning_engine", result)

    hub.decide(record, StateEvent.PLAN_DRAFT_READY, {
        "slots": result.data.get("draft", {}).get("slots", []),
        "total_cost": result.data.get("draft", {}).get("total_cost", 0),
        "budget": float("inf"),
    })

    # Auto confirmation (single user)
    consensus = ConsensusResolver()
    result = await consensus.execute(context)
    context.history.append(result)

    hub.decide(record, StateEvent.USER_CONFIRM_ALL)

    # Execution
    execution = ExecutionEngine()
    result = await execution.execute(context)
    context.history.append(result)
    hub.store_result(plan_id, "execution_engine", result)

    exec_data = result.data.get("execution", {})
    if exec_data.get("status") == "full_success":
        hub.decide(record, StateEvent.EXECUTION_SUCCESS)
    else:
        # Try fallback
        fallback = FallbackEngine()
        fb_result = await fallback.execute(context)
        context.history.append(fb_result)
        hub.decide(record, StateEvent.EXECUTION_PARTIAL_FAIL)

    # Notify
    notify = NotifyEngine()
    result = await notify.execute(context)
    context.history.append(result)

    hub.decide(record, StateEvent.EXECUTION_SUCCESS)

    draft = hub.get_draft(plan_id)
    slots_raw = draft.get("slots", []) if isinstance(draft, dict) else (draft.slots if draft else [])
    total_cost = draft.get("total_cost", 0) if isinstance(draft, dict) else (draft.total_cost if draft else 0)
    total_time = draft.get("total_time_min", 0) if isinstance(draft, dict) else (draft.total_time_min if draft else 0)
    slots = [PlanSlot(**s) if isinstance(s, dict) else s for s in slots_raw]
    share_data = result.data.get("share_card", {})

    return PlanResponse(
        plan_id=plan_id,
        query_text=req.user_input,
        status=record.state,
        total_cost=total_cost,
        total_time_min=total_time,
        slots=slots,
        share_card=ShareCard(**share_data) if share_data else None,
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, request: Request):
    hub = get_hub(request)
    draft_raw = hub.get_draft(plan_id)
    record = hub.get_state(plan_id)

    slots_raw = (draft_raw.get("slots", []) if isinstance(draft_raw, dict)
                 else (draft_raw.slots if draft_raw else []))
    slots = [PlanSlot(**s) if isinstance(s, dict) else s for s in slots_raw]
    total_cost = (draft_raw.get("total_cost", 0) if isinstance(draft_raw, dict)
                  else (draft_raw.total_cost if draft_raw else 0))
    total_time = (draft_raw.get("total_time_min", 0) if isinstance(draft_raw, dict)
                  else (draft_raw.total_time_min if draft_raw else 0))

    return PlanResponse(
        plan_id=plan_id,
        query_text="", status=record.state,
        total_cost=total_cost,
        total_time_min=total_time,
        slots=slots,
    )


@router.get("/{plan_id}/stream")
async def plan_stream(plan_id: str, request: Request):
    hub = get_hub(request)
    record = hub.get_state(plan_id)
    if not record:
        raise HTTPException(status_code=404, detail="plan not found")
    return await stream_plan(plan_id, hub)
