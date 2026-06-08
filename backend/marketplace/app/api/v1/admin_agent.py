"""Admin Agent API — B-end AI assistant endpoint.

Provides a chat endpoint for admin users to query analytics data through
the LangGraph agent pipeline, routed through the admin_analyst specialist node.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agent.services.agent import AgentService
from snaptrip_shared.core.response import APIServiceError, success

router = APIRouter(prefix="/admin/agent", tags=["admin-agent"])


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User's question")
    session_id: str = Field("default", description="Session ID for context")


class AgentChatResponse(BaseModel):
    reply: str
    intent: str = ""
    data: dict | None = None


def _build_admin_state(req: AgentChatRequest) -> dict:
    """Build initial PlanState dict for admin agent chat."""
    plan_id = str(uuid.uuid4())[:8]
    return {
        "plan_id": plan_id,
        "user_id": f"admin_{req.session_id or 'default'}",
        "session_id": req.session_id or "default",
        "status": "running",
        "messages": [HumanMessage(content=req.message)],
        "intent": "admin_analytics",
        "current_agent": "admin_analyst",
    }


def _get_agent_service(request: Request) -> AgentService:
    """Resolve AgentService from lifespan or build fallback."""
    if (
        not hasattr(request.app.state, "_agent_service")
        or request.app.state._agent_service is None
    ):
        if (
            hasattr(request.app.state, "plan_graph")
            and request.app.state.plan_graph is not None
        ):
            request.app.state._agent_service = AgentService(
                request.app.state.plan_graph
            )
        else:
            # Fallback: build graph synchronously
            from agent.graph import build_graph as _build
            import asyncio

            request.app.state._agent_service = AgentService(
                asyncio.get_event_loop().run_until_complete(_build())
            )
    return request.app.state._agent_service


@router.post("/chat", response_model=AgentChatResponse)
async def admin_agent_chat(req: AgentChatRequest, request: Request):
    """Admin AI chat — analyze admin data and answer questions.

    Routes through the admin_analyst node to fetch sales reports,
    inventory alerts, order trends, member insights, generate product
    descriptions, and analyze coupon effectiveness.

    Uses the same LangGraph pipeline as the C-end agent with the
    admin_analyst specialist node.
    """
    try:
        service = _get_agent_service(request)
        initial_state = _build_admin_state(req)
        plan_id = initial_state["plan_id"]

        result = await service.invoke(initial_state, plan_id)

        # Extract the final synthesized message
        messages = result.get("messages", [])
        reply = ""
        intent = result.get("intent", "admin_analytics")

        # Find the last AI message with content
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai":
                content = getattr(msg, "content", "")
                if content:
                    reply = str(content)
                    break
            elif isinstance(msg, dict) and msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content:
                    reply = str(content)
                    break

        if not reply:
            reply = "Analysis complete. Check the conversation for details."

        # Extract relevant data from state
        data = {
            "phase": result.get("phase", ""),
            "status": result.get("status", "done"),
            "current_agent": result.get("current_agent", "admin_analyst"),
        }

        return AgentChatResponse(reply=reply, intent=intent, data=data)

    except APIServiceError:
        raise
    except Exception as e:
        raise APIServiceError(
            code=5001,
            message=f"Admin agent error: {str(e)}",
            status_code=500,
        )
