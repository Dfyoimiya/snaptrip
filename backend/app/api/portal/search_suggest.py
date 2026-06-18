"""搜索建议 API —— GET /api/v1/portal/search/suggest

返回 3 个区块:
  - autocomplete: 前缀匹配自动补全 (prefix ≥ 1)
  - trending:     热门搜索 (始终展示)
  - ai_suggestions: AI 搜索推荐 (prefix ≥ 2, 从 Redis 缓存读取)

在线延迟 < 30ms (纯 Redis 查询, 无 LLM)。

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from snaptrip_shared.core.response import success

from app.schemas.search_suggest import SuggestResponse, SuggestSection
from app.services.autocomplete_service import AutocompleteService
from app.services.memory_service import MemoryService
from app.services.trending_service import TrendingService

router = APIRouter(prefix="/portal/search", tags=["Portal - 搜索建议"])


def _get_memory(request: Request) -> MemoryService:
    return request.app.state.memory


def _get_trending(request: Request) -> TrendingService:
    svc = request.app.state.trending_service
    if svc is None:
        raise RuntimeError("TrendingService not initialized")
    return svc


def _get_autocomplete(request: Request) -> AutocompleteService:
    svc = request.app.state.autocomplete_service
    if svc is None:
        raise RuntimeError("AutocompleteService not initialized")
    return svc


def _resolve_user_id(request: Request) -> UUID | None:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        from marketplace.app.core.security import decode_access_token

        token = auth.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        sub = payload.get("sub", "")
        return UUID(sub) if sub else None
    except Exception:
        return None


@router.get("/suggest", summary="搜索框智能建议")
async def search_suggest(
    request: Request,
    prefix: str = Query("", description="搜索前缀 (空字符串 = 仅显示热门)"),
    limit: int = Query(8, ge=1, le=20),
    memory: MemoryService = Depends(_get_memory),
    trending: TrendingService = Depends(_get_trending),
    autocomplete: AutocompleteService = Depends(_get_autocomplete),
    user_id: UUID | None = Depends(_resolve_user_id),
    x_session_id: str = Header("", alias="X-Session-Id"),
):
    """搜索框智能建议。

    前缀为空时: 返回搜索历史 + 热门搜索
    前缀 ≥ 1 时: 返回自动补全 + 热门搜索
    前缀 ≥ 2 时: 额外返回 AI 推荐 (若有缓存)
    """
    from app.services.suggestion_service import SuggestionService

    svc = SuggestionService(
        autocomplete_service=autocomplete,
        trending_service=trending,
        memory=memory,
    )
    result = await svc.suggest(
        prefix=prefix.strip(),
        user_id=str(user_id) if user_id else None,
        session_id=x_session_id or None,
        limit=limit,
    )

    sections = [
        SuggestSection(
            section_type=s["section_type"],
            title=s["title"],
            queries=s["queries"],
        )
        for s in result["sections"]
    ]

    return success(
        SuggestResponse(
            prefix=result["prefix"],
            sections=sections,
            total_ms=result["total_ms"],
        ).model_dump()
    )


@router.post("/suggest/generate", summary="离线生成 AI 搜索建议")
async def generate_ai_suggestions(
    request: Request,
    query: str = Query(..., min_length=2, description="搜索词"),
    limit: int = Query(5, ge=1, le=10),
    memory: MemoryService = Depends(_get_memory),
):
    """离线接口: 为指定 query 生成 AI 搜索建议并缓存。

    由定时任务或后台脚本调用, 不面向前端。
    """
    from app.services.suggestion_service import SuggestionService

    supervisor = getattr(request.app.state, "recommendation_supervisor", None)
    llm = getattr(supervisor, "_llm", None) if supervisor else None

    svc = SuggestionService(
        memory=memory,
        llm_adapter=llm,
    )
    suggestions = await svc.generate_ai_suggestions(query, limit=limit)
    return success({"query": query, "suggestions": suggestions, "cached": len(suggestions) > 0})
