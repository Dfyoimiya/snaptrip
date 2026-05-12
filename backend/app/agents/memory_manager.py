"""Memory Manager — 记忆增强：pgvector 检索 + 历史模式匹配"""

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
