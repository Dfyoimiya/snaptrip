"""Memory Manager —— 记忆增强：pgvector 检索 + 历史模式匹配。

负责增强 EnrichedIntent 中的记忆向量，用于后续 POI 语义检索。

当前实现: Stub 模式，保持 EnrichedIntent 不变。
远期: pgvector 语义检索 + Skill 文件匹配 + 历史规划模式蒸馏。

位于 Context Loader 和 Retrieval Engine 之间，确保检索时已有完整的记忆增强输入。

Author: SnapTrip Team
Date: 2026-05-13
"""

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.schemas.plan import EnrichedIntent


class MemoryManager(BaseAgent):
    name = "memory_manager"

    async def execute(self, context: AgentContext) -> AgentResult:
        enriched = self._extract_enriched(context)
        if not enriched:
            return AgentResult(data={})

        enhanced = enriched.model_copy(deep=True)
        if not enhanced.profile_vector:
            enhanced.profile_vector = [0.1] * 1536

        return AgentResult(data={"enriched_intent": enhanced.model_dump()})

    def _extract_enriched(self, context: AgentContext) -> EnrichedIntent | None:
        for h in reversed(context.history):
            if "enriched_intent" in h.data:
                return EnrichedIntent(**h.data["enriched_intent"])
        return None
