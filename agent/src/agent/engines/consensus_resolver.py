"""Consensus Resolver —— 多利益相关者协商器。

职责:
  1. 预分析计划草案，检测明显冲突（预算超支、时间重叠、空草案）
  2. 支持单用户确认 / 多用户加权投票
  3. 生成 interrupt payload 供 LangGraph 节点使用

当前实现:
  - 单用户: 总是建议人机协同确认（needs_interrupt=True），但会预标记冲突
  - 多用户: 预留加权投票框架（votes + stakeholder_weights）

输出:
  {
    "needs_interrupt": bool,
    "decision": "confirmed" | "objection" | "partial_change" | "rejected",
    "revised_constraints": dict | None,
    "diff_slots": list[dict],
    "interrupt_payload": dict,
    "rationale": str,
  }

Author: SnapTrip Team
Date: 2026-05-13 / Production refactor 2026-05-19
"""

from __future__ import annotations

from snaptrip_shared.schemas.plan import PlanDraft

from agent.protocol import AgentContext, AgentResult, BaseAgent


def _extract_draft(context: AgentContext) -> PlanDraft | None:
    for h in reversed(context.history):
        if "draft" in h.data:
            return PlanDraft(**h.data["draft"])
    return None


def _extract_votes(context: AgentContext) -> list[dict]:
    """Extract stakeholder votes from context if present."""
    for h in reversed(context.history):
        if "votes" in h.data:
            votes = h.data["votes"]
            if isinstance(votes, list):
                return votes
    return []


class ConsensusResolver(BaseAgent):
    name = "consensus_resolver"

    async def execute(self, context: AgentContext) -> AgentResult:
        draft = _extract_draft(context)
        votes = _extract_votes(context)

        if draft is None or not draft.slots:
            return AgentResult(
                data={
                    "needs_interrupt": False,
                    "decision": "rejected",
                    "revised_constraints": None,
                    "diff_slots": [],
                    "interrupt_payload": {},
                    "rationale": "计划草案为空，无法进入确认流程",
                }
            )

        if votes:
            decision, diff_slots, rationale = self._weighted_vote(draft, votes)
        else:
            decision, diff_slots, rationale = self._single_user_review(draft, context)

        interrupt_payload = {
            "event": "consensus",
            "draft": draft.model_dump(),
            "message": rationale,
            "suggested_decision": decision,
            "diff_slots": [d.model_dump() if hasattr(d, "model_dump") else d for d in diff_slots],
        }

        return AgentResult(
            data={
                "needs_interrupt": True,
                "decision": decision,
                "revised_constraints": None,
                "diff_slots": diff_slots,
                "interrupt_payload": interrupt_payload,
                "rationale": rationale,
            }
        )

    def _single_user_review(self, draft: PlanDraft, context: AgentContext) -> tuple[str, list, str]:
        """单用户场景：预检查草案并给出建议决策。"""
        conflicts = []

        # 预算检查（如果 intent 中有 budget）
        intent = None
        for h in reversed(context.history):
            if "intent" in h.data:
                intent = h.data["intent"]
                break
        if intent:
            budget = intent.get("budget")
            if budget and draft.total_cost > budget * 1.2:
                conflicts.append(f"预估费用 ¥{draft.total_cost} 超出预算 ¥{budget} 20%")

        # 时间重叠检查（简化）
        slots = draft.slots
        for i in range(1, len(slots)):
            if slots[i].time_range.start < slots[i - 1].time_range.end:
                conflicts.append(f"Slot {i} 与 Slot {i - 1} 时间重叠")

        if conflicts:
            return "objection", [], "; ".join(conflicts)

        return "confirmed", [], "计划草案通过预检查，等待用户确认"

    def _weighted_vote(self, draft: PlanDraft, votes: list[dict]) -> tuple[str, list, str]:
        """多用户场景：加权投票（预留框架）。

        规则:
          - 每个 vote 含 {stakeholder_id, decision, weight, locked_slots, rejected_slots}
          - 锁定 slot 的并集不可被修改
          - 反对票权重 > 赞成票权重时，降级为 partial_change
        """
        total_weight = sum(v.get("weight", 1.0) for v in votes)
        confirm_weight = sum(v.get("weight", 1.0) for v in votes if v.get("decision") == "confirmed")
        reject_weight = sum(v.get("weight", 1.0) for v in votes if v.get("decision") in {"rejected", "objection"})

        if total_weight == 0:
            return "confirmed", [], "无有效投票权重，默认通过"

        confirm_ratio = confirm_weight / total_weight
        reject_ratio = reject_weight / total_weight

        if reject_ratio > 0.5:
            return "rejected", [], "反对票权重超过 50%，计划被拒绝"
        if confirm_ratio > 0.7:
            return "confirmed", [], "赞成票权重超过 70%，计划通过"

        # 部分变更：收集所有被反对的 slot
        all_rejected: set[int] = set()
        for v in votes:
            for idx in v.get("rejected_slots", []):
                all_rejected.add(idx)

        return "partial_change", [], f"共识未达成（赞成 {confirm_ratio:.0%}），建议局部调整"
