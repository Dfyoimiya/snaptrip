"""Consensus Resolver —— 多利益相关者协商器 (Stub)。

当前实现: 单用户模式，直接返回 confirmed。
远期: 加权投票 + 帕累托补偿 + 锁定覆盖检测。

职责: 处理多用户场景下的偏好冲突，生成折中方案。
- 输入: {plan_id, votes[], stakeholder_weights[]}
- 输出: ConsensusDecision {status, revised_constraints, diff_slots[]}

Author: SnapTrip Team
Date: 2026-05-13
"""

from app.agents.protocol import AgentContext, AgentResult, BaseAgent


class ConsensusResolver(BaseAgent):
    name = "consensus_resolver"

    async def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(data={
            "decision": {
                "status": "confirmed",
                "revised_constraints": None,
                "diff_slots": [],
            },
        })
