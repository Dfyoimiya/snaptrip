# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""ORToolsCPSATTool —— OR-Tools CP-SAT 约束求解/验证工具。

用于:
  1. 硬约束可行性预检 (替代 Z3，对整数约束更快)
  2. 单目标最优解 (作为 pymoo Pareto 前沿的 baseline)
  3. Pareto 解的后验证

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


class CPSATSolverInput(BaseModel):
    """Input schema for OR-Tools CP-SAT constraint solving."""

    activities: list[dict] = Field(default_factory=list,
                                   description="Candidate activities with avg_price/child_friendly/avg_duration")
    restaurants: list[dict] = Field(default_factory=list,
                                    description="Candidate restaurants with avg_price/child_friendly/dietary_tags/avg_duration")
    budget: float = Field(default=500, description="Total budget in CNY")
    time_window_min: float = Field(default=300, description="Total available time in minutes")
    guest_count: int = Field(default=2, ge=1, description="Number of guests")
    child_friendly_required: bool = Field(default=False, description="Must be child-friendly")
    dietary_restrictions: list[str] = Field(default_factory=list, description="Dietary restrictions")
    mode: str = Field(default="feasibility", description="Mode: 'feasibility', 'optimize', or 'verify'")
    candidate_solution: dict | None = Field(default=None, description="Candidate solution to verify (mode='verify')")


class ORToolsCPSATTool(SmartDayBaseTool):
    """OR-Tools CP-SAT 行程求解/验证工具。"""

    name: str = "ortools_cpsat_solve"
    description: str = (
        "使用 OR-Tools CP-SAT 求解器对行程规划做约束求解。"
        "支持 mode='feasibility' 做预检，mode='optimize' 做单目标最优，"
        "mode='verify' 后验证某个候选解是否满足约束。"
    )
    args_schema: type[BaseModel] = CPSATSolverInput
    is_read_only: bool = True
    cost_model: str = "free"
    tool_timeout: float = 10.0

    def compensation(self, args: dict, result: ToolResult) -> CompensationAction:
        return SmartDayBaseTool._noop_compensation("cpsat_noop", self.name)

    async def _arun(
        self,
        activities: list[dict] | None = None,
        restaurants: list[dict] | None = None,
        budget: float = 500,
        time_window_min: float = 300,
        guest_count: int = 2,
        child_friendly_required: bool = False,
        dietary_restrictions: list[str] | None = None,
        mode: str = "feasibility",
        candidate_solution: dict | None = None,
        **kwargs,
    ) -> ToolResult:
        """CP-SAT 求解。"""
        try:
            from ortools.sat.python import cp_model
        except ImportError:
            return ToolResult(
                success=False,
                data={"error": "ortools not installed. Run: pip install ortools"},
            )

        if not activities or not restaurants:
            return ToolResult(success=False, data={"error": "activities and restaurants required"})
        if dietary_restrictions is None:
            dietary_restrictions = []

        n_act = len(activities)
        n_rst = len(restaurants)

        model = cp_model.CpModel()

        act_vars = [model.NewBoolVar(f"act_{i}") for i in range(n_act)]
        rst_vars = [model.NewBoolVar(f"rst_{i}") for i in range(n_rst)]

        model.Add(sum(act_vars) == 1)
        model.Add(sum(rst_vars) == 1)

        # Budget
        act_costs = [int((activities[i].get("avg_price", 0) or 0) * guest_count) for i in range(n_act)]
        rst_costs = [int((restaurants[i].get("avg_price", 100) or 100) * guest_count) for i in range(n_rst)]
        total_cost_expr = (
            sum(act_vars[i] * act_costs[i] for i in range(n_act)) +
            sum(rst_vars[i] * rst_costs[i] for i in range(n_rst))
        )
        model.Add(total_cost_expr <= int(budget))

        # Child friendly
        if child_friendly_required:
            for i in range(n_act):
                if not activities[i].get("child_friendly"):
                    model.Add(act_vars[i] == 0)
            for i in range(n_rst):
                if not restaurants[i].get("child_friendly"):
                    model.Add(rst_vars[i] == 0)

        # Dietary
        if dietary_restrictions:
            dietary_ok = []
            for i in range(n_rst):
                tags = restaurants[i].get("dietary_tags", []) or []
                if all(d in tags for d in dietary_restrictions):
                    dietary_ok.append(rst_vars[i])
            if dietary_ok:
                model.Add(sum(dietary_ok) >= 1)

        # Time window
        act_durations = [int(activities[i].get("avg_duration", 120) or 120) for i in range(n_act)]
        rst_durations = [int(restaurants[i].get("avg_duration", 90) or 90) for i in range(n_rst)]
        total_time_expr = (
            sum(act_vars[i] * act_durations[i] for i in range(n_act)) +
            sum(rst_vars[i] * rst_durations[i] for i in range(n_rst))
        )
        model.Add(total_time_expr <= int(time_window_min))

        # Mode: verify
        if mode == "verify" and candidate_solution:
            act_name = (candidate_solution.get("activity") or {}).get("name", "")
            rst_name = (candidate_solution.get("restaurant") or {}).get("name", "")
            for i, a in enumerate(activities):
                if (a.get("name") or "") == act_name:
                    model.Add(act_vars[i] == 1)
            for i, r in enumerate(restaurants):
                if (r.get("name") or "") == rst_name:
                    model.Add(rst_vars[i] == 1)

        # Mode: optimize (minimize cost)
        if mode == "optimize":
            model.Minimize(total_cost_expr)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0

        status = solver.Solve(model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            chosen_act = next((i for i in range(n_act) if solver.Value(act_vars[i]) == 1), 0)
            chosen_rst = next((i for i in range(n_rst) if solver.Value(rst_vars[i]) == 1), 0)

            return ToolResult(success=True, data={
                "feasible": True,
                "solver": "ortools_cpsat",
                "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
                "activity": {
                    "name": activities[chosen_act].get("name"),
                    "id": activities[chosen_act].get("id"),
                },
                "restaurant": {
                    "name": restaurants[chosen_rst].get("name"),
                    "id": restaurants[chosen_rst].get("id"),
                },
                "total_cost": int(solver.Value(total_cost_expr)),
            })
        else:
            return ToolResult(success=True, data={
                "feasible": False,
                "solver": "ortools_cpsat",
                "status": "INFEASIBLE",
            })
