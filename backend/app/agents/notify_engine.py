"""Notify Engine — 输出封装：生成分享卡片"""

from app.agents.protocol import AgentContext, AgentResult, BaseAgent
from app.schemas.plan import ShareCard


class NotifyEngine(BaseAgent):
    name = "notify_engine"

    async def execute(self, context: AgentContext) -> AgentResult:
        card = ShareCard(
            url=f"https://snaptrip.cn/cards/{context.plan_id}",
            message=f"计划已生成！共 {len(context.history)} 步完成。",
        )
        return AgentResult(data={"share_card": card.model_dump()})
