"""
【前台商城 - 导购 Agent API】— /api/v1/shopping-guide

C-end AI 导购 Agent 后端支持：
  - 基于 Supervisor-specialist 多 Agent 架构
  - 3 阶段并行管道：用户画像 + 商品召回/精排 + 库存过滤 + 营销文案
  - Redis 会话持久化 + LLM 摘要 + 跨会话记忆
  - SSE 流式输出

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from snaptrip_shared.core.response import APIServiceError, success
from sse_starlette.sse import EventSourceResponse

from app.schemas.shopping_guide import (
    ShoppingGuideRequest,
    ShoppingGuideSession,
    ShoppingGuideSessionList,
)
from app.utils.display import format_sale_count
from marketplace.app.core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shopping-guide", tags=["Portal - 导购Agent"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_session_service(request: Request):
    """Resolve ShoppingSessionService from app state (lazy init)."""
    if not hasattr(request.app.state, "_shopping_session_service"):
        from app.services.shopping_session_service import ShoppingSessionService

        memory = request.app.state.memory
        request.app.state._shopping_session_service = ShoppingSessionService(memory)
    return request.app.state._shopping_session_service


async def _get_supervisor(request: Request):
    """Resolve or build the shopping guide supervisor lazily."""
    if hasattr(request.app.state, "_sg_supervisor") and request.app.state._sg_supervisor is not None:
        return request.app.state._sg_supervisor

    from shared.http_client import MarketplaceClient
    from shopping_guide.adapters import get_llm_adapter
    from shopping_guide.orchestrator.supervisor import ShoppingGuideSupervisor

    from app.services.query_understanding_service import QueryUnderstandingService

    llm_adapter = get_llm_adapter()
    http_client = MarketplaceClient()

    recall_service = _get_recall_service(request)
    query_understanding = QueryUnderstandingService(
        llm_adapter=llm_adapter,
        memory=request.app.state.memory,
    )

    # Build InfoSearchSupervisor for enrichment
    info_search = await _get_info_search_supervisor(request, llm_adapter, http_client)

    supervisor = ShoppingGuideSupervisor(
        llm_adapter=llm_adapter,
        http_client=http_client,
        recall_service=recall_service,
        query_understanding=query_understanding,
        info_search_supervisor=info_search,
    )
    request.app.state._sg_supervisor = supervisor
    return supervisor


async def _get_info_search_supervisor(
    request: Request,
    llm_adapter=None,
    http_client=None,
):
    """Resolve or build the InfoSearchSupervisor lazily."""
    if hasattr(request.app.state, "_sg_info_search") and request.app.state._sg_info_search is not None:
        return request.app.state._sg_info_search

    from shopping_guide.orchestrator.info_search_supervisor import InfoSearchSupervisor

    web_client = _get_web_search_client()

    supervisor = InfoSearchSupervisor(
        llm_adapter=llm_adapter,
        http_client=http_client,
        web_search_client=web_client,
    )
    request.app.state._sg_info_search = supervisor
    return supervisor


def _get_web_search_client():
    """Build WebSearchClient from shopping guide settings (no API key → None)."""
    from shopping_guide.config.settings import get_shopping_guide_settings
    from shopping_guide.services.web_search_client import create_web_search_client

    settings = get_shopping_guide_settings()
    return create_web_search_client(settings)


def _get_recall_service(request: Request):
    """Build UnifiedRecallService from available backend services."""
    from snaptrip_shared.db.session import AsyncSessionLocal

    from app.services.recall_service import UnifiedRecallService

    es_client = getattr(request.app.state, "es_client", None)
    if es_client is None:
        try:
            from app.search.client import get_search_client
            es_client = get_search_client()
        except Exception:
            pass

    return UnifiedRecallService(
        es_client=es_client,
        vector_service=getattr(request.app.state, "vector_search_service", None),
        cf_service=getattr(request.app.state, "cf_service", None),
        trending_service=getattr(request.app.state, "trending_service", None),
        db_factory=AsyncSessionLocal,
    )


# ── Response formatting ──────────────────────────────────────────────────────


def _product_to_frontend_format(p: dict) -> dict:
    """Normalize a product dict for frontend RecommendedProduct format.

    Returns camelCase keys matching the RecommendedProduct TypeScript interface.
    This is consumed by both the Axios (non-streaming) and SSE (streaming) paths.
    - Axios: deepConvertKeys is a no-op on already-camelCase keys
    - SSE:   raw JSON keys match RecommendedProduct directly
    """
    return {
        "name": str(p.get("name", "")),
        "price": float(p.get("price", 0) or 0),
        "originalPrice": float(p.get("original_price", 0) or p.get("price", 0) or 0),
        "discount": _calc_discount(p.get("price", 0), p.get("original_price", 0)),
        "link": f"/product/{p.get('product_id', '')}",
        "highlights": list(p.get("tags", []) or [])[:3],
        "imageUrl": p.get("image_url") or (p.get("images", [None])[0] if p.get("images") else None),
        "productId": str(p.get("product_id", "")),
        "brandName": str(p.get("brand_name", "") or ""),
        "saleCount": int(p.get("sale_count", 0) or 0),
        "saleCountDisplay": format_sale_count(p.get("sale_count", 0)),
    }


def _calc_discount(price: float, original_price: float) -> str:
    """Calculate discount percentage string."""
    try:
        price = float(price or 0)
        original_price = float(original_price or 0)
        if original_price > price > 0:
            pct = int((1 - price / original_price) * 100)
            if pct > 0:
                return f"{pct}% off"
    except (ValueError, TypeError):
        pass
    return ""


def _format_reply_text(products: list[dict], copies: list[dict], user_message: str = "") -> str:
    """Format supervisor response into a natural markdown reply.

    Generates a structured response with product cards and marketing copy,
    mimicking the original LLM-generated reply format.
    """
    if not products:
        return "抱歉，我暂时没有找到符合您需求的商品。试试更具体的关键词？"

    total = len(products)
    names = [p.get("name", "") for p in products[:3]]
    price_min = min(float(p.get("price", 0) or 0) for p in products)
    price_max = max(float(p.get("price", 0) or 0) for p in products)

    parts = [f"为你找到{total}件商品"]
    if names:
        parts.append("、".join(names[:2]))
    if price_max > 0:
        parts.append(f"¥{price_min:.0f}-¥{price_max:.0f}")

    reply = "，".join(parts)
    if len(reply) > 200:
        reply = reply[:197] + "..."
    return reply


def _extract_follow_ups(products: list[dict]) -> list[dict]:
    """Generate structured follow-up prompts from product search results.

    Returns list of FollowUpItem-compatible dicts with text, options, action fields.
    """
    if not products:
        return [
            {"text": "换个关键词试试？", "action": "fill"},
            {"text": "告诉我你的预算？", "action": "fill"},
        ]

    results: list[dict] = []

    # Collect brand names for brand-preference question
    brands: list[str] = list(dict.fromkeys(
        p.get("brand_name", "") for p in products if p.get("brand_name")
    ))
    if len(brands) >= 2:
        results.append({
            "text": "你更想选哪个品牌的呢？",
            "options": brands[:8],
            "action": "send",
        })

    # Comparison question if multiple products
    if len(products) >= 2:
        results.append({
            "text": "帮你对比一下这几款？",
            "options": [p.get("name", "")[:15] for p in products[:4]],
            "action": "send",
        })

    results.append({"text": "有没有优惠券可以用？", "action": "send"})
    return results[:3]


# ── Info Search Formatting ──────────────────────────────────────────────────


def _format_info_cards(response) -> dict:
    """Convert InfoSearchResponse to frontend-friendly info card structure."""
    review_data = None
    if response.review_summary:
        review_data = {
            "average_rating": response.review_summary.average_rating,
            "total_count": response.review_summary.total_count,
            "summary_text": response.review_summary.summary_text,
            "top_reviews": [
                {
                    "review_id": r.review_id,
                    "user_name": r.user_name,
                    "rating": r.rating,
                    "content": r.content,
                    "created_at": r.created_at,
                }
                for r in response.review_summary.top_reviews[:4]
            ],
        }

    return {
        "conclusion": response.conclusion,
        "highlights": [
            {"emoji": h.emoji, "title": h.title, "description": h.description}
            for h in response.highlights
        ],
        "worth_buying": [
            {"scenario": w.scenario, "verdict": w.verdict, "reasoning": w.reasoning}
            for w in response.worth_buying
        ],
        "pitfalls": [
            {"title": p.title, "description": p.description}
            for p in response.pitfalls
        ],
        "review_summary": review_data,
        "sources_used": response.sources_used,
        "total_latency_ms": response.total_latency_ms,
    }


def _format_info_reply(response) -> str:
    """Build a short chat reply (≤300 chars) — full structured content goes to canvas."""
    lines: list[str] = []

    if response.conclusion:
        lines.append(response.conclusion)

    if response.worth_buying:
        verdicts = " | ".join(f"{w.scenario}：{w.verdict}" for w in response.worth_buying[:4])
        if verdicts:
            lines.append(verdicts)

    if response.pitfalls:
        pit = "避坑：" + "；".join(p.title for p in response.pitfalls[:3])
        lines.append(pit)

    reply = "\n".join(lines)
    if len(reply) > 300:
        reply = reply[:297] + "..."
    return reply if reply else "抱歉，暂无相关信息。"


def _extract_info_follow_ups(response) -> list[dict]:
    """Generate structured follow-up prompts from info search results.

    Returns list of FollowUpItem-compatible dicts with text, options, action fields.
    """
    qs: list[dict] = []

    if response.conclusion:
        qs.append({"text": "还有其他类似的商品推荐吗？", "action": "send"})

    if response.highlights and len(response.highlights) >= 2:
        titles = [h.title for h in response.highlights[:5]]
        qs.append({
            "text": "想深入了解哪个方面？",
            "options": titles,
            "action": "send",
        })

    if response.worth_buying:
        qs.append({"text": "有没有优惠券可以用？", "action": "send"})

    return qs[:3] if qs else [
        {"text": "换个商品问问？", "action": "fill"},
        {"text": "告诉我你的预算？", "action": "fill"},
    ]


# ── Mode Routing ────────────────────────────────────────────────────────────────


async def _resolve_effective_mode(req: ShoppingGuideRequest) -> str:
    """Determine the effective pipeline mode.

    auto → intent classification (transactional→product, informational→info)
    product → product recommendation pipeline
    info → info search pipeline (FAQ / web search / reviews)
    """
    mode = req.mode or "auto"
    if mode != "auto":
        return mode

    # ── Intent classification for auto mode ──
    query = req.message.strip()
    if not query:
        return "product"  # empty query defaults to product

    from app.services.query_understanding_service import _classify_intent_rules

    intent = _classify_intent_rules(query)
    if intent == "informational":
        return "info"
    return "product"  # transactional / navigational / unknown → product


async def _execute_product_pipeline(
    supervisor,
    req: ShoppingGuideRequest,
    user_id: str,
    auth_token: str,
    cross_context: str,
) -> tuple[str, list[dict], list[str]]:
    """Execute the product recommendation supervisor pipeline.

    Returns (reply, products_frontend, follow_ups).
    """
    from shopping_guide.models.schemas import RecommendationRequest

    rec_request = RecommendationRequest(
        user_id=user_id,
        message=req.message,
        scene=_infer_scene(req),
        num_items=5,
        context={
            "cross_session_context": cross_context,
            "current_product_id": req.context.current_product_id if req.context else None,
            "current_category": req.context.current_category if req.context else None,
            "search_query": req.context.search_query if req.context else None,
        },
    )

    response = await supervisor.recommend(rec_request)

    products_raw = [p.model_dump() for p in response.products]
    reply = _format_reply_text(products_raw, response.marketing_copies, req.message)
    products_frontend = [_product_to_frontend_format(p) for p in products_raw]
    follow_ups = _extract_follow_ups(products_raw)

    return reply, products_frontend, follow_ups


async def _execute_info_pipeline(
    supervisor,
    req: ShoppingGuideRequest,
    user_id: str,
    auth_token: str,
    cross_context: str,
) -> tuple[str, list[dict], list[str], dict | None]:
    """Execute the info search pipeline (web search + review search → structured cards).

    Returns (reply, products_frontend, follow_ups, info_cards).
    """
    from shopping_guide.models.schemas import InfoSearchRequest

    info_supervisor = getattr(supervisor, "info_search", None)
    if info_supervisor is None:
        # Fallback to product pipeline if info search not available
        reply, products, follow_ups = await _execute_product_pipeline(
            supervisor, req, user_id, auth_token, cross_context
        )
        return reply, products, follow_ups, None

    info_request = InfoSearchRequest(
        user_id=user_id,
        query=req.message,
        sources=["web", "reviews"],
        max_results_per_source=5,
        context={
            "cross_session_context": cross_context,
            "current_product_id": req.context.current_product_id if req.context else None,
        },
    )

    try:
        response = await info_supervisor.search(info_request)
        info_cards = _format_info_cards(response)

        # Build markdown reply as fallback
        reply = _format_info_reply(response)

        products_frontend = []
        follow_ups = _extract_info_follow_ups(response)

        return reply, products_frontend, follow_ups, info_cards
    except Exception as exc:
        logger.exception("Info search pipeline failed")
        reply = f"抱歉，信息搜索暂时不可用：{exc}"
        return reply, [], [{"text": "换个关键词试试？", "action": "fill"}], None


# ── Chat ─────────────────────────────────────────────────────────────────────


class ShoppingChatResponse(BaseModel):
    reply: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")
    products: list[dict] = Field(default_factory=list, description="推荐商品列表")
    follow_up_questions: list[dict] = Field(default_factory=list, description="结构化的建议追问")
    info_cards: dict | None = Field(None, description="信息搜索结构化卡片（info模式）")


@router.post("/chat", summary="导购 Agent 对话")
async def shopping_guide_chat(
    req: ShoppingGuideRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """AI 导购对话端点。

    通过 Supervisor-specialist 多 Agent 管道处理用户消息：
      - auto 模式: 意图分类 → 路由到商品推荐/信息搜索管线
      - product 模式: 商品推荐管线（多策略召回 + LLM 精排 + 营销文案）
      - info 模式: 信息搜索管线（选购建议、FAQ、web search、评价搜索）

    会话持久化到 Redis（30 分钟 TTL），自动生成 LLM 摘要用于跨会话记忆。
    """
    try:
        user_id = str(current_user.id)
        session_svc = _get_session_service(request)
        supervisor = await _get_supervisor(request)

        # Extract JWT for passthrough to backend APIs
        auth_header = request.headers.get("Authorization", "")
        auth_token = auth_header.replace("Bearer ", "") if auth_header else ""

        from shared.auth import set_auth_token
        set_auth_token(auth_token)

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

        # ── Cross-session context ──
        cross_context = ""
        if is_new_session or not req.session_id:
            cross_context = await session_svc.build_cross_session_context(user_id)

        # ── Persist user message ──
        await session_svc.append_message(session_id, "user", req.message)
        await session_svc.touch_session(session_id)

        # ── Route by mode ──
        effective_mode = await _resolve_effective_mode(req)
        logger.info("shopping_guide mode=%s→%s query=%s", req.mode or "auto", effective_mode, req.message[:80])

        info_cards = None
        if effective_mode == "info":
            reply, products_frontend, follow_ups, info_cards = await _execute_info_pipeline(
                supervisor, req, user_id, auth_token, cross_context
            )
        else:
            reply, products_frontend, follow_ups = await _execute_product_pipeline(
                supervisor, req, user_id, auth_token, cross_context
            )

        # ── Persist assistant reply ──
        await session_svc.append_message(session_id, "assistant", reply)
        await session_svc.touch_session(session_id)

        # ── Generate summary ──
        all_msgs = await session_svc.get_messages(session_id)
        await session_svc.generate_and_save_summary(session_id, user_id, all_msgs)

        return success(
            ShoppingChatResponse(
                reply=reply,
                session_id=session_id,
                products=products_frontend,
                follow_up_questions=follow_ups,
                info_cards=info_cards,
            ).model_dump()
        )

    except APIServiceError:
        raise
    except Exception as e:
        logger.exception("Shopping guide chat error")
        raise APIServiceError(
            code=5001,
            message=f"Shopping guide agent error: {str(e)}",
            status_code=500,
        ) from e


@router.post("/chat/stream", summary="导购 Agent 流式对话 (SSE)")
async def shopping_guide_chat_stream(
    req: ShoppingGuideRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """AI 导购流式对话端点 —— 通过 Server-Sent Events 逐字输出。

    SSE 事件类型:
      - mode:    {"type": "mode", "mode": "info|product"}  — 首个事件，前端据此展开 Canvas
      - token:   {"type": "token", "content": "..."}       — 逐词流式输出，打字机效果
      - done:    {"type": "done", "session_id": "...", "products": [...], "follow_up_questions": [...]}
      - error:   {"type": "error", "message": "..."}
    """
    user_id = str(current_user.id)
    session_svc = _get_session_service(request)
    supervisor = await _get_supervisor(request)

    auth_header_val = request.headers.get("Authorization", "")
    auth_token = auth_header_val.replace("Bearer ", "") if auth_header_val else ""

    from shared.auth import set_auth_token
    set_auth_token(auth_token)

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

    cross_context = ""
    if is_new_session or not req.session_id:
        cross_context = await session_svc.build_cross_session_context(user_id)

    # Persist user message
    await session_svc.append_message(session_id, "user", req.message)
    await session_svc.touch_session(session_id)

    # ── Route by mode ──
    effective_mode = await _resolve_effective_mode(req)
    logger.info("shopping_guide stream mode=%s→%s query=%s", req.mode or "auto", effective_mode, req.message[:80])

    # ── Shared state for SSE ──
    token_queue: asyncio.Queue = asyncio.Queue()
    final_reply: str = ""
    final_products: list[dict] = []
    final_follow_ups: list[dict] = []
    final_info_cards: dict | None = None

    # Send mode event immediately so frontend can expand canvas
    await token_queue.put({"type": "mode", "mode": effective_mode})

    async def run_pipeline():
        """Run the appropriate pipeline, then stream the formatted reply."""
        nonlocal final_reply, final_products, final_follow_ups, final_info_cards
        try:
            if effective_mode == "info":
                reply, products, follow_ups, info_cards = await _execute_info_pipeline(
                    supervisor, req, user_id, auth_token, cross_context
                )
                final_info_cards = info_cards
            else:
                reply, products, follow_ups = await _execute_product_pipeline(
                    supervisor, req, user_id, auth_token, cross_context
                )

            final_reply = reply
            final_products = products
            final_follow_ups = follow_ups

            # Stream word by word for typewriter effect (~30 words/sec)
            tokens = re.findall(r'\S+|\s+', final_reply)
            for token in tokens:
                await token_queue.put({"type": "token", "content": token})
                await asyncio.sleep(0.025)

            # Persist & summarise
            try:
                await session_svc.append_message(session_id, "assistant", final_reply)
                await session_svc.touch_session(session_id)
                all_msgs = await session_svc.get_messages(session_id)
                await session_svc.generate_and_save_summary(session_id, user_id, all_msgs)
            except Exception as exc:
                logger.warning("Session persist failed: %s", exc)

        except Exception as exc:
            logger.exception("Shopping guide stream pipeline error")
            await token_queue.put({"type": "error", "message": str(exc)})
        finally:
            await token_queue.put(None)  # sentinel

    async def event_generator():
        task = asyncio.create_task(run_pipeline())

        while True:
            item = await token_queue.get()
            if item is None:
                break
            yield {"data": json.dumps(item, ensure_ascii=False)}

        await task

        # Final done event
        done_data = {
            "type": "done",
            "session_id": session_id,
            "products": final_products,
            "follow_up_questions": final_follow_ups,
            "info_cards": final_info_cards,
        }
        yield {"data": json.dumps(done_data, ensure_ascii=False)}

    return EventSourceResponse(event_generator())


# ── Scene inference ──────────────────────────────────────────────────────────


def _infer_scene(req: ShoppingGuideRequest) -> str:
    """Infer recommendation scene from frontend context."""
    if req.context:
        if req.context.current_product_id:
            return "product_detail"
        if req.context.current_category:
            return "category"
        if req.context.search_query:
            return "search"
    return "homepage"


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
