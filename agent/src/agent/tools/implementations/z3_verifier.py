"""Z3VerifierTool —— 硬约束可行性预检工具。

使用 Z3 SMT 求解器快速检查"给定候选 POI 和约束，是否存在至少一个可行解"。
不求解最优，仅回答 feasible: true/false。

用于 nsga2_solve 之前的快速预检，避免在不可能有解的情况下浪费计算。
也可用于单个解的约束后验证。

Author: SnapTrip Team
Date: 2026-05-29
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)


class Z3VerifierInput(BaseModel):
    """Input schema for Z3 feasibility check."""

    activities: list[dict] = Field(default_factory=list,
                                   description="Candidate activities with avg_price/child_friendly/avg_duration")
    restaurants: list[dict] = Field(default_factory=list,
                                    description="Candidate restaurants with avg_price/child_friendly/dietary_tags")
    budget: float = Field(default=500, description="Total budget in CNY")
    time_window_min: float = Field(default=300, description="Total available time in minutes")
    guest_count: int = Field(default=2, ge=1, description="Number of guests")
    child_friendly_required: bool = Field(default=False, description="Must be child-friendly")
    dietary_restrictions: list[str] = Field(default_factory=list, description="Dietary restrictions")


class Z3VerifierTool(SmartDayBaseTool):
    """Z3 SMT 硬约束可行性验证工具。

    只回答 feasible: bool，不返回具体解。
    """

    name: str = "z3_verify_feasibility"
    description: str = (
        "使用 Z3 SMT 求解器检查给定候选 POI 列表是否满足所有硬约束（预算、时间、亲子友好、饮食限制）。"
        "返回 feasible: true/false。用于求解前的快速预检。"
    )
    args_schema: type[BaseModel] = Z3VerifierInput
    is_read_only: bool = True
    cost_model: str = "free"
    tool_timeout: float = 10.0

    def compensation(self, args: dict, result: ToolResult) -> CompensationAction:
        return SmartDayBaseTool._noop_compensation("z3_noop", self.name)

    async def _arun(
        self,
        activities: list[dict] | None = None,
        restaurants: list[dict] | None = None,
        budget: float = 500,
        time_window_min: float = 300,
        guest_count: int = 2,
        child_friendly_required: bool = False,
        dietary_restrictions: list[str] | None = None,
        activity_duration_min: float = 150.0,
        meal_duration_min: float = 90.0,
        **kwargs,
    ) -> ToolResult:
        """Z3 可行性检查。"""
        try:
            import z3
        except ImportError:
            return ToolResult(
                success=False,
                data={"error": "z3-solver not installed. Run: pip install z3-solver", "feasible": None},
            )

        if not activities or not restaurants:
            return ToolResult(success=False, data={"error": "activities and restaurants are required", "feasible": None})
        if dietary_restrictions is None:
            dietary_restrictions = []

        n_act = len(activities)
        n_rst = len(restaurants)

        act_vars = [z3.Bool(f"act_{i}") for i in range(n_act)]
        rst_vars = [z3.Bool(f"rst_{i}") for i in range(n_rst)]

        solver = z3.Solver()
        solver.set("timeout", 5000)

        # 恰好选一个活动、一个餐厅
        solver.add(z3.PbEq([(v, 1) for v in act_vars], 1))
        solver.add(z3.PbEq([(v, 1) for v in rst_vars], 1))

        # 预算约束
        act_costs = [(activities[i].get("avg_price", 0) or 0) * guest_count for i in range(n_act)]
        rst_costs = [(restaurants[i].get("avg_price", 100) or 100) * guest_count for i in range(n_rst)]
        total_cost = z3.Sum(
            [z3.If(act_vars[i], int(act_costs[i]), 0) for i in range(n_act)] +
            [z3.If(rst_vars[i], int(rst_costs[i]), 0) for i in range(n_rst)]
        )
        solver.add(total_cost <= int(budget))

        # 亲子友好约束
        if child_friendly_required:
            for i in range(n_act):
                if not activities[i].get("child_friendly"):
                    solver.add(z3.Not(act_vars[i]))
            for i in range(n_rst):
                if not restaurants[i].get("child_friendly"):
                    solver.add(z3.Not(rst_vars[i]))

        # 饮食限制约束
        if dietary_restrictions:
            dietary_ok = []
            for i in range(n_rst):
                tags = restaurants[i].get("dietary_tags", []) or []
                if all(d in tags for d in dietary_restrictions):
                    dietary_ok.append(rst_vars[i])
            if dietary_ok:
                solver.add(z3.Or(*dietary_ok))

        # 时间窗口约束
        act_durations = [
            int(activities[i].get("avg_duration", 120) or 120) for i in range(n_act)
        ]
        rst_durations = [
            int(restaurants[i].get("avg_duration", 90) or 90) for i in range(n_rst)
        ]
        total_time = z3.Sum(
            [z3.If(act_vars[i], act_durations[i], 0) for i in range(n_act)] +
            [z3.If(rst_vars[i], rst_durations[i], 0) for i in range(n_rst)]
        )
        solver.add(total_time <= int(time_window_min))

        result = solver.check()

        if result == z3.sat:
            return ToolResult(success=True, data={"feasible": True, "solver": "z3"})
        elif result == z3.unsat:
            # 诊断：哪个约束导致不可行
            reasons = []
            # 尝试去掉预算约束
            s2 = z3.Solver()
            s2.set("timeout", 2000)
            s2.add(z3.PbEq([(v, 1) for v in act_vars], 1))
            s2.add(z3.PbEq([(v, 1) for v in rst_vars], 1))
            if s2.check() == z3.sat:
                reasons.append("budget_too_low")
            # 尝试去掉亲子约束
            if child_friendly_required:
                s3 = z3.Solver()
                s3.set("timeout", 2000)
                s3.add(z3.PbEq([(v, 1) for v in act_vars], 1))
                s3.add(z3.PbEq([(v, 1) for v in rst_vars], 1))
                s3.add(total_cost <= int(budget))
                if s3.check() == z3.sat:
                    reasons.append("child_friendly_too_restrictive")
            if dietary_restrictions:
                s4 = z3.Solver()
                s4.set("timeout", 2000)
                s4.add(z3.PbEq([(v, 1) for v in act_vars], 1))
                s4.add(z3.PbEq([(v, 1) for v in rst_vars], 1))
                s4.add(total_cost <= int(budget))
                if s4.check() == z3.sat:
                    reasons.append("dietary_too_restrictive")
            if not reasons:
                reasons.append("insufficient_candidates")

            return ToolResult(success=True, data={
                "feasible": False,
                "solver": "z3",
                "reasons": reasons,
            })
        else:
            return ToolResult(success=True, data={
                "feasible": None,
                "solver": "z3",
                "reason": f"Z3 returned unknown (timeout or insufficient data). n_act={n_act}, n_rst={n_rst}",
            })
