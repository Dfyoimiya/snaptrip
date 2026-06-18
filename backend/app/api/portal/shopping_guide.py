"""
【前台商城 - 导购 Agent API】— /api/v1/shopping-guide

C-end AI 导购 Agent 后端支持：
  - 商品搜索 / 个性化推荐 / 商品对比
  - 优惠券查询 / 首页 Feed
  - Redis 会话持久化 + LLM 摘要 + 跨会话记忆

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

import uuid

from agent.services.agent import AgentService
from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from snaptrip_shared.core.response import APIServiceError, success

from app.schemas.shopping_guide import (
    ShoppingGuideRequest,
    ShoppingGuideSession,
    ShoppingGuideSessionList,
)
from marketplace.app.core.security import get_current_user
from marketplace.app.models.users import User

router = APIRouter(prefix="/shopping-guide", tags=["Portal - 导购Agent"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_session_service(request: Request):
    """Resolve ShoppingSessionService from app state (lazy init)."""
    if not hasattr(request.app.state, "_shopping_session_service"):
        from app.services.shopping_session_service import ShoppingSessionService

        memory = request.app.state.memory  # MemoryService from lifespan
        request.app.state._shopping_session_service = ShoppingSessionService(memory)
    return request.app.state._shopping_session_service


async def _get_agent_service(request: Request) -> AgentService:
    """Resolve the shopping guide AgentService from app state or build lazily."""
    if hasattr(request.app.state, "_shopping_agent_service") and request.app.state._shopping_agent_service is not None:
        return request.app.state._shopping_agent_service

    from agent.graphs.shopping_guide import build_shopping_guide_graph
    from agent.runtime import AgentRuntime
    from agent.tools.bootstrap_shopping import build_shopping_guide_registry
    from agent.tools.harness.context import SessionContext
    from agent.tools.harness.harness import ToolHarness
    from agent.utils import get_llm_adapter

    runtime = AgentRuntime()
    runtime.harness = ToolHarness(registry=build_shopping_guide_registry())
    runtime.session_ctx = SessionContext()
    runtime.llm_adapter = get_llm_adapter()

    request.app.state._shopping_agent_service = AgentService(await build_shopping_guide_graph(runtime=runtime))
    return request.app.state._shopping_agent_service


async def _build_shopping_state(
    req: ShoppingGuideRequest,
    user_id: str,
    auth_token: str = "",
    cross_session_context: str = "",
) -> dict:
    """Build initial PlanState for the shopping guide agent.

    Injects frontend context and cross-session memory into the first message.
    The auth_token (JWT) is stored in working_memory so tool_node can inject it.
    """
    plan_id = str(uuid.uuid4())[:8]

    # Build enriched first message
    parts: list[str] = []

    # Cross-session memory from previous conversations
    if cross_session_context:
        parts.append(cross_session_context)

    # Frontend context
    if req.context:
        if req.context.current_product_id:
            parts.append(f"[User is viewing product {req.context.current_product_id}]")
        if req.context.current_category:
            parts.append(f"[User is browsing category: {req.context.current_category}]")
        if req.context.search_query:
            parts.append(f"[User searched for: {req.context.search_query}]")

    parts.append(req.message)
    message_text = "\n".join(parts)

    return {
        "plan_id": plan_id,
        "user_id": f"user_{user_id}",
        "session_id": req.session_id or plan_id,
        "status": "running",
        "messages": [HumanMessage(content=message_text)],
        "intent": "product_search",
        "current_agent": "shopping_guide",
        "working_memory": {"auth_token": auth_token},
    }


# ── Response parsing ─────────────────────────────────────────────────────────


def _parse_llm_reply(raw: str) -> tuple[str, list[dict], list[str]]:
    """Parse the LLM's JSON response into reply text, products, and follow-ups.

    Returns (reply, products, follow_up_questions).
    If the response is not valid JSON, returns the raw text as reply.
    """
    import json

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            answer = data.get("answer", raw)
            products = data.get("products", [])
            if not isinstance(products, list):
                products = []
            follow_ups = data.get("follow_up_questions", [])
            if not isinstance(follow_ups, list):
                follow_ups = []
            # Limit to 3
            return str(answer), products, follow_ups[:3]
    except (json.JSONDecodeError, TypeError):
        pass
    return raw, [], []


# ── Chat ─────────────────────────────────────────────────────────────────────


class ShoppingChatResponse(BaseModel):
    reply: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")
    products: list[dict] = Field(default_factory=list, description="推荐商品列表")
    follow_up_questions: list[str] = Field(default_factory=list, description="建议追问")


@router.post("/chat", summary="导购 Agent 对话")
async def shopping_guide_chat(
    req: ShoppingGuideRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """AI 导购对话端点。

    通过独立的 shopping guide LangGraph 管道处理用户消息。
    支持商品搜索、个性化推荐、商品对比、优惠查询等只读操作。

    会话持久化到 Redis（30 分钟 TTL），自动生成 LLM 摘要用于跨会话记忆。
    """
    try:
        user_id = str(current_user.id)
        session_svc = _get_session_service(request)
        agent_svc = await _get_agent_service(request)

        # Extract JWT for passthrough to tools
        auth_header = request.headers.get("Authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

        # ── Session resolution ──
        session_id = req.session_id
        is_new_session = False
        if not session_id:
            session_id = await session_svc.create_session(user_id)
            is_new_session = True
        else:
            existing = await session_svc.get_session(session_id)
            if not existing or existing.get("user_id") != user_id:
                session_id = await session_svc.create_session(user_id)
                is_new_session = True

        # ── Cross-session context (for new sessions) ──
        cross_context = ""
        if is_new_session or not req.session_id:
            cross_context = await session_svc.build_cross_session_context(user_id)

        # ── Persist user message ──
        await session_svc.append_message(session_id, "user", req.message)
        await session_svc.touch_session(session_id)

        # ── Build state & invoke agent ──
        initial_state = await _build_shopping_state(
            req,
            user_id=user_id,
            auth_token=auth_token,
            cross_session_context=cross_context,
        )
        plan_id = initial_state["plan_id"]

        result = await agent_svc.invoke(initial_state, plan_id)

        # ── Extract reply ──
        messages = result.get("messages", [])
        reply = ""
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
            reply = "我找到了相关商品信息。您可以点击商品链接查看详情。如需进一步帮助，请随时告诉我您的需求。"

        # ── Persist assistant reply ──
        await session_svc.append_message(session_id, "assistant", reply)
        await session_svc.touch_session(session_id)

        # ── Parse structured reply ──
        clean_reply, products, follow_ups = _parse_llm_reply(reply)

        # ── Generate summary (async, best-effort) ──
        all_msgs = await session_svc.get_messages(session_id)
        await session_svc.generate_and_save_summary(session_id, user_id, all_msgs)

        return success(
            ShoppingChatResponse(
                reply=clean_reply,
                session_id=session_id,
                products=products,
                follow_up_questions=follow_ups,
            ).model_dump()
        )

    except APIServiceError:
        raise
    except Exception as e:
        raise APIServiceError(
            code=5001,
            message=f"Shopping guide agent error: {str(e)}",
            status_code=500,
        ) from e


# ── Sessions ─────────────────────────────────────────────────────────────────


@router.get("/sessions", summary="获取用户导购会话列表")
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的导购会话列表（从 Redis 读取）。"""
    session_svc = _get_session_service(request)
    user_id = str(current_user.id)
    sessions = await session_svc.list_user_sessions(user_id)

    result = [
        ShoppingGuideSession(
            id=s.get("id", ""),
            user_id=s.get("user_id", user_id),
            message_count=s.get("message_count", 0),
        )
        for s in sessions
    ]
    return success(ShoppingGuideSessionList(sessions=result, total=len(result)).model_dump())


@router.get("/sessions/{session_id}", summary="获取导购会话详情")
async def get_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """获取特定会话的状态和消息历史。"""
    session_svc = _get_session_service(request)
    s = await session_svc.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问")

    msgs = await session_svc.get_messages(session_id)

    return success(
        {
            "id": session_id,
            "user_id": s["user_id"],
            "message_count": s.get("message_count", 0),
            "messages": msgs,
            "summary": await session_svc.get_summary(session_id),
        }
    )


@router.delete("/sessions/{session_id}", summary="清除导购会话")
async def delete_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """清除指定的导购会话。会话摘要保留用于跨会话记忆。"""
    session_svc = _get_session_service(request)
    s = await session_svc.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="无权访问")

    await session_svc.delete_session(session_id)
    return success({"deleted": True, "session_id": session_id})
