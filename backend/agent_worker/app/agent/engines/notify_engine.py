"""Notify Engine —— 输出封装：生成分享卡片。

Plan 进入 DONE 状态后，生成可分享的 ShareCard：
  - Jinja2 渲染 HTML 分享卡片
  - 生成文字摘要消息
  - 预留 Playwright 截图为 PNG（远期）

输出: ShareCard {url, message, html}

Author: SnapTrip Team
Date: 2026-05-13 / Jinja2 integration 2026-05-18
"""

from __future__ import annotations

import logging

from snaptrip_shared.schemas.plan import PlanDraft, ShareCard

from agent_worker.app.agent.ports.prompt import PromptPort
from agent_worker.app.agent.protocol import AgentContext, AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class NotifyEngine(BaseAgent):
    name = "notify_engine"

    def __init__(self, prompt_renderer: PromptPort | None = None) -> None:
        super().__init__()
        self._prompt_renderer = prompt_renderer

    def _get_prompt_renderer(self) -> PromptPort:
        if self._prompt_renderer is None:
            from agent_worker.app.agent.adapters.prompt import JinjaPromptAdapter

            self._prompt_renderer = JinjaPromptAdapter()
        return self._prompt_renderer

    async def execute(self, context: AgentContext) -> AgentResult:
        draft = self._extract_draft(context)
        execution = self._extract_execution(context)

        message = _build_message(draft, execution)
        html = await _render_card(
            renderer=self._get_prompt_renderer(),
            plan_id=context.plan_id,
            draft=draft,
            execution=execution,
            message=message,
        )

        card = ShareCard(
            url=f"https://snaptrip.cn/cards/{context.plan_id}",
            message=message,
        )
        result = card.model_dump()
        result["html"] = html
        return AgentResult(data={"share_card": result})

    def _extract_draft(self, context: AgentContext) -> PlanDraft | None:
        for h in reversed(context.history):
            if "draft" in h.data:
                return PlanDraft(**h.data["draft"])
        return None

    def _extract_execution(self, context: AgentContext) -> dict | None:
        for h in reversed(context.history):
            if "execution" in h.data:
                return h.data["execution"]  # type: ignore[no-any-return]
        return None


# ------------------------------------------------------------------
# rendering
# ------------------------------------------------------------------


async def _render_card(
    renderer: PromptPort,
    plan_id: str,
    draft: PlanDraft | None,
    execution: dict | None,
    message: str,
) -> str:
    slots_data = [s.model_dump() if hasattr(s, "model_dump") else s for s in (draft.slots if draft else [])]
    booked_count = len(execution.get("confirmed_bookings", {})) if execution else 0

    try:
        return await renderer.render(
            "notify.j2",
            {
                "plan_id": plan_id,
                "title": "SnapTrip 计划",
                "message": message,
                "slots": slots_data,
                "total_cost": draft.total_cost if draft else 0,
                "booked_count": booked_count,
            },
        )
    except Exception:
        logger.warning("notify_render_failed", exc_info=True)
        return ""


def _build_message(draft: PlanDraft | None, execution: dict | None) -> str:
    if not draft:
        return "计划生成完成"
    count = len(draft.slots)
    booked = len(execution.get("confirmed_bookings", {})) if execution else 0
    return f"计划已生成！共 {count} 站，已预订 {booked} 项，预估 ¥{draft.total_cost}"
