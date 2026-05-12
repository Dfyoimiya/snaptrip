"""Consensus Resolver — Stub：单用户模式直接确认"""

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
