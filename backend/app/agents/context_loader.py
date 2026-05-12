"""Context Loader — 用户画像加载（Mock Profile）"""

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.schemas.plan import EnrichedIntent, IntentSchema


class ContextLoader(BaseAgent):
    name = "context_loader"

    async def execute(self, context: AgentContext) -> AgentResult:
        intent_data = context.history[-1].data.get("intent", {}) if context.history else {}
        intent = IntentSchema(**intent_data) if intent_data else IntentSchema()

        enriched = EnrichedIntent(
            intent=intent,
            profile_vector=[0.1] * 1536,
            family_profile={"child_age": None, "diet": "无偏好", "allergens": []},
            historical_rejections=[],
            preferred_pace="normal",
            user_id=context.user_id,
        )
        return AgentResult(data={"enriched_intent": enriched.model_dump()})
