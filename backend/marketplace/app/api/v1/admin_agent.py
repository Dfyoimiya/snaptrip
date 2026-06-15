"""Admin Agent API — B-end AI assistant endpoint.

Provides a chat endpoint for admin users to query analytics data through
the LangGraph agent pipeline, routed through the admin_analyst specialist node.

JWT passthrough: the user's JWT token from the incoming request is stored in
PlanState.working_memory["auth_token"], then injected into SessionContext by
tool_node, so tool implementations can add Authorization headers to their
HTTP calls to the marketplace backend.
"""

from __future__ import annotations

import uuid

from agent.services.agent import AgentService
from fastapi import APIRouter, Depends, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from snaptrip_shared.core.response import APIServiceError, success

from marketplace.app.core.security import get_current_user  # JWT 认证

router = APIRouter(prefix="/admin/agent", tags=["admin-agent"])


class AgentChatRequest(BaseModel):
    message: str = Field(..., description="User's question")
    session_id: str = Field("default", description="Session ID for context")


class AgentChatResponse(BaseModel):
    reply: str
    intent: str = ""
    data: dict | None = None


def _build_admin_state(req: AgentChatRequest, auth_token: str = "") -> dict:
    """Build initial PlanState dict for admin agent chat.

    The auth_token (JWT from browser) is stored in working_memory so
    tool_node can inject it into the tool execution context.
    """
    plan_id = str(uuid.uuid4())[:8]
    return {
        "plan_id": plan_id,
        "user_id": f"admin_{req.session_id or 'default'}",
        "session_id": req.session_id or "default",
        "status": "running",
        "messages": [HumanMessage(content=req.message)],
        "intent": "admin_analytics",
        "current_agent": "admin_analyst",
        "working_memory": {"auth_token": auth_token},
    }


def _get_agent_service(request: Request) -> AgentService:
    """Resolve AgentService from lifespan or build fallback."""
    if not hasattr(request.app.state, "_agent_service") or request.app.state._agent_service is None:
        if hasattr(request.app.state, "plan_graph") and request.app.state.plan_graph is not None:
            request.app.state._agent_service = AgentService(request.app.state.plan_graph)
        else:
            import asyncio

            from agent.graph import build_graph as _build

            request.app.state._agent_service = AgentService(asyncio.run(_build()))
    return request.app.state._agent_service


@router.post("/chat")
async def admin_agent_chat(
    req: AgentChatRequest,
    request: Request,
    _current_user=Depends(get_current_user),
):
    """Admin AI chat — analyze admin data and answer questions.

    Routes through the admin_analyst node to fetch sales reports,
    inventory alerts, order trends, member insights, generate product
    descriptions, and analyze coupon effectiveness.

    Requires JWT authentication. The user's token is forwarded to
    admin API calls made by the agent tools.
    """
    try:
        service = _get_agent_service(request)

        # Extract JWT from incoming request for passthrough to tools
        auth_header = request.headers.get("Authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

        initial_state = _build_admin_state(req, auth_token=auth_token)
        plan_id = initial_state["plan_id"]

        result = await service.invoke(initial_state, plan_id)

        # Extract the final synthesized message
        messages = result.get("messages", [])
        reply = ""
        intent = result.get("intent", "admin_analytics")

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

        data = {
            "phase": result.get("phase", ""),
            "status": result.get("status", "done"),
            "current_agent": result.get("current_agent", "admin_analyst"),
        }

        return success(AgentChatResponse(reply=reply, intent=intent, data=data).model_dump())

    except APIServiceError:
        raise
    except Exception as e:
        raise APIServiceError(
            code=5001,
            message=f"Admin agent error: {str(e)}",
            status_code=500,
        ) from e
