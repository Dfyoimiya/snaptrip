"""Memory Manager —— 记忆增强：历史偏好聚合 + pgvector 语义检索。

负责增强 EnrichedIntent 中的记忆向量和偏好，用于后续 POI 语义检索。

核心逻辑:
  1. 查询用户历史 Plan → 统计高频 group_type (scene_type)
  2. 聚合历史偏好增强当前 intent 的 scene_type 权重
  3. 保留 profile_vector（由 ContextLoader 从 UserProfile 加载）
  4. 无历史或无 DB 时原样返回（兜底，不阻断链路）

位于 Context Loader 和 Retrieval Engine 之间，确保检索时已有完整的记忆增强输入。

Author: SnapTrip Team
Date: 2026-05-13 / DB integration 2026-05-18
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter

from sqlalchemy import select

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.db.session import AsyncSessionLocal
from app.models.plan import Plan
from app.schemas.plan import EnrichedIntent

logger = logging.getLogger(__name__)


class MemoryManager(BaseAgent):
    name = "memory_manager"

    async def execute(self, context: AgentContext) -> AgentResult:
        enriched = self._extract_enriched(context)
        if not enriched:
            return AgentResult(data={})

        enhanced = enriched.model_copy(deep=True)
        if not enhanced.profile_vector:
            enhanced.profile_vector = [0.1] * 1536

        uid = _parse_uuid(context.user_id)
        if uid:
            try:
                prefs = await _aggregate_user_history(uid)
                enhanced.intent.type_prefs = _merge_prefs(enhanced.intent.type_prefs, prefs.get("types", []))
                enhanced.intent.mood_prefs = _merge_prefs(enhanced.intent.mood_prefs, prefs.get("moods", []))
                dominant_scene = prefs.get("dominant_scene")
                if isinstance(dominant_scene, str) and dominant_scene and enhanced.intent.scene_type == "solo":
                    enhanced.intent.scene_type = dominant_scene
            except Exception:
                logger.warning("memory_manager_db_failed", user_id=context.user_id, exc_info=True)  # type: ignore[call-arg]

        return AgentResult(data={"enriched_intent": enhanced.model_dump()})

    def _extract_enriched(self, context: AgentContext) -> EnrichedIntent | None:
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                return EnrichedIntent(**h.data["enriched_intent"])
        return None


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _parse_uuid(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError):
        return None


def _merge_prefs(current: list[str], historical: list[str]) -> list[str]:
    seen = set(current)
    result = list(current)
    for item in historical:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


async def _aggregate_user_history(user_id: uuid.UUID) -> dict[str, list[str]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Plan).where(Plan.user_id == user_id).order_by(Plan.created_at.desc()).limit(20)
        )
        plans = result.scalars().all()

    scene_counter: Counter[str] = Counter()
    type_prefs: list[str] = []
    mood_prefs: list[str] = []

    for plan in plans:
        scene_counter[plan.group_type] += 1
        # group_type "family" → type_prefs=["activity", "restaurant"]
        # group_type "friends" → type_prefs=["restaurant", "cafe"]
        # group_type "date" → type_prefs=["cafe", "attraction"]
        type_prefs.extend(_scene_type_map.get(plan.group_type, []))
        mood_prefs.extend(_scene_mood_map.get(plan.group_type, []))

    dominant_scene = scene_counter.most_common(1)[0][0] if scene_counter else None

    return {
        "types": list(set(type_prefs)),
        "moods": list(set(mood_prefs)),
        "dominant_scene": dominant_scene,  # type: ignore[dict-item]
    }


_scene_type_map: dict[str, list[str]] = {
    "family": ["activity", "restaurant", "attraction"],
    "friends": ["restaurant", "cafe", "attraction"],
    "solo": ["cafe", "attraction", "activity"],
    "date": ["cafe", "attraction", "restaurant"],
}

_scene_mood_map: dict[str, list[str]] = {
    "family": ["亲子", "治愈", "拍照"],
    "friends": ["热闹", "聚餐", "拍照"],
    "solo": ["安静", "文艺", "治愈"],
    "date": ["浪漫", "安静", "拍照"],
}
