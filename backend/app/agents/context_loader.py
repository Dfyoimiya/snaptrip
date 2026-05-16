"""Context Loader —— 用户画像加载。

从 PostgreSQL + pgvector 加载用户偏好向量和家庭画像，
增强 IntentSchema 为 EnrichedIntent。

当前实现: Mock 模式，返回默认画像。
远期: 接入 pgvector 语义检索，跨会话记忆复用。

输入: IntentSchema + user_id
输出: EnrichedIntent (含 profile_vector, family_profile, historical_rejections)

Author: SnapTrip Team
Date: 2026-05-13
"""

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
