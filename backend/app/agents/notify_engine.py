"""Notify Engine —— 输出封装：生成分享卡片。

Plan 进入 DONE 状态后，生成可分享的 ShareCard。

输出: ShareCard {url, message, ics_event}
远景: Jinja2 渲染 HTML → Playwright 截图 → 微信分享卡片

Author: SnapTrip Team
Date: 2026-05-13
"""

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
