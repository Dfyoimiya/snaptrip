"""Memory Manager —— 记忆增强：历史偏好聚合 + pgvector 语义检索。

负责增强 EnrichedIntent 中的记忆向量和偏好，用于后续 POI 语义检索。

注入模式（推荐）:
  manager = MemoryManager(plan_repo=repo)
  → 通过 repo.get_user_history(user_id) 获取历史聚合

兜底模式（无 repo）:
  manager = MemoryManager()
  → 跳过历史查询，原样返回 enriched

位于 Context Loader 和 Retrieval Engine 之间，确保检索时已有完整的记忆增强输入。

Author: SnapTrip Team
Date: 2026-05-13 / DI refactor 2026-05-21
"""

from __future__ import annotations

import logging
import uuid

from snaptrip_shared.schemas.plan import EnrichedIntent

from agent.protocol import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class MemoryManager(BaseAgent):
    name = "memory_manager"

    def __init__(self, plan_repo=None):
        """注入 PlanRepositoryPort。

        Args:
            plan_repo: 可选。实现 get_user_history(user_id) -> dict | None 的端口。
                       为 None 时跳过历史查询（原样返回 enriched）。
        """
        super().__init__()
        self._plan_repo = plan_repo

    async def execute(self, context: AgentContext) -> AgentResult:
        enriched = self._extract_enriched(context)
        if not enriched:
            return AgentResult(data={})

        enhanced = enriched.model_copy(deep=True)
        if not enhanced.profile_vector:
            enhanced.profile_vector = [0.1] * 1536

        uid = _parse_uuid(context.user_id)
        if uid and self._plan_repo is not None:
            try:
                prefs = await self._plan_repo.get_user_history(str(uid))
                if prefs:
                    enhanced.intent.type_prefs = _merge_prefs(enhanced.intent.type_prefs, prefs.get("types", []))
                    enhanced.intent.mood_prefs = _merge_prefs(enhanced.intent.mood_prefs, prefs.get("moods", []))
                    dominant_scene = prefs.get("dominant_scene")
                    if isinstance(dominant_scene, str) and dominant_scene and enhanced.intent.scene_type == "solo":
                        enhanced.intent.scene_type = dominant_scene
            except Exception:
                logger.warning("memory_manager_repo_failed user_id=%s", context.user_id, exc_info=True)

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
