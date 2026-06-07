# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""PymooSolverTool —— NSGA-II 多目标行程优化工具。

通过 ToolHarness 暴露给 LLM。LLM 通过 function-calling 调用此工具，
获得 Pareto 前沿上的多个非支配解，然后从中语义选择最符合用户偏好的方案。

Author: SnapTrip Team
Date: 2026-05-29
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from pydantic import BaseModel, Field

from agent.solver.problem import ItineraryProblem
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)


class PymooSolverInput(BaseModel):
    """Input schema for NSGA-II itinerary optimization."""

    activities: list[dict] = Field(default_factory=list,
                                   description="Candidate activities with lat/lng/avg_price/rating/child_friendly")
    restaurants: list[dict] = Field(default_factory=list,
                                    description="Candidate restaurants with lat/lng/avg_price/rating/child_friendly/dietary_tags")
    budget: float = Field(default=500, description="Total budget in CNY")
    time_window_min: float = Field(default=300, description="Total available time in minutes")
    guest_count: int = Field(default=2, ge=1, description="Number of guests")
    child_friendly_required: bool = Field(default=False, description="Must be child-friendly")
    dietary_restrictions: list[str] = Field(default_factory=list, description="Dietary restrictions")
    origin_lat: float | None = Field(default=None, description="Starting point latitude for transit calculation")
    origin_lng: float | None = Field(default=None, description="Starting point longitude for transit calculation")
    activity_location: dict | None = Field(default=None, description="(deprecated) Anchor location {lat, lng} — prefer origin_lat/origin_lng")


class PymooSolverTool(SmartDayBaseTool):
    """pymoo NSGA-II 多目标行程优化工具。

    输入: 候选 POI 列表 + 约束条件
    输出: Pareto 前沿 (最多 10 个非支配解)，每解含 activity/restaurant/cost/transit/score
    """

    name: str = "pymoo_solve_itinerary"
    description: str = (
        "使用 NSGA-II 多目标进化算法求解行程规划问题。"
        "给定候选活动列表、餐厅列表、预算、时间窗口等约束，"
        "返回 Pareto 前沿上最多 10 个非支配解，每个解包含活动、餐厅、费用、转场时间、评分等。"
    )
    args_schema: type[BaseModel] = PymooSolverInput
    is_read_only: bool = True
    cost_model: str = "free"
    tool_timeout: float = 30.0

    def compensation(self, args: dict, result: ToolResult) -> CompensationAction:
        return SmartDayBaseTool._noop_compensation("pymoo_noop", self.name)

    async def _arun(
        self,
        activities: list[dict] | None = None,
        restaurants: list[dict] | None = None,
        budget: float = 500,
        time_window_min: float = 300,  # 5 hours
        guest_count: int = 2,
        child_friendly_required: bool = False,
        dietary_restrictions: list[str] | None = None,
        origin_lat: float = 39.9219,
        origin_lng: float = 116.4435,
        pop_size: int = 100,
        n_generations: int = 50,
        **kwargs,
    ) -> ToolResult:
        """执行 NSGA-II 优化。"""
        if not activities or not restaurants:
            return ToolResult(
                success=False,
                data={"error": "activities and restaurants are required and must be non-empty"},
            )
        if dietary_restrictions is None:
            dietary_restrictions = []

        # Resolve origin: explicit params first, fallback to activity_location (legacy compat)
        _origin_lat = origin_lat
        _origin_lng = origin_lng
        if _origin_lat is None and _origin_lng is None:
            loc = kwargs.get("activity_location") or {}
            if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                _origin_lat = float(loc["lat"])
                _origin_lng = float(loc["lng"])
        _origin_lat = _origin_lat if _origin_lat is not None else 39.9219
        _origin_lng = _origin_lng if _origin_lng is not None else 116.4435

        problem = ItineraryProblem(
            activities=activities,
            restaurants=restaurants,
            budget=budget,
            time_window_min=time_window_min,
            guest_count=guest_count,
            child_friendly_required=child_friendly_required,
            dietary_restrictions=dietary_restrictions,
            origin_lat=_origin_lat,
            origin_lng=_origin_lng,
        )

        algorithm = NSGA2(
            pop_size=min(pop_size, max(20, len(activities) * len(restaurants) * 5)),
            sampling=IntegerRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=0.2, eta=20),
        )

        termination = get_termination("n_gen", min(n_generations, 50))

        try:
            res = minimize(problem, algorithm, termination, seed=42, verbose=False)
        except Exception as e:
            logger.exception("NSGA-II optimization failed")
            return ToolResult(success=False, data={"error": f"pymoo optimization failed: {e}"})

        if res.X is None:
            logger.warning("NSGA-II returned no feasible solutions")
            return ToolResult(success=False, data={
                "error": "Pareto optimization returned no solutions — problem may be infeasible with current constraints",
                "suggestion": "Try relaxing budget or time constraints, or expanding candidate pool",
            })

        pareto_X = res.X.astype(int)
        pareto_F = res.F

        solutions = []
        for i in range(len(pareto_X)):
            act_idx = int(pareto_X[i, 0])
            rst_idx = int(pareto_X[i, 1])

            if act_idx >= len(activities) or rst_idx >= len(restaurants):
                continue

            act = activities[act_idx]
            rst = restaurants[rst_idx]

            constraint_violation = float(res.G[i].sum()) if res.G is not None else 0.0

            solutions.append({
                "rank": i + 1,
                "activity": {
                    "id": act.get("id"),
                    "name": act.get("name"),
                    "rating": act.get("rating"),
                    "avg_price": act.get("avg_price"),
                    "lat": act.get("lat"),
                    "lng": act.get("lng"),
                },
                "restaurant": {
                    "id": rst.get("id"),
                    "name": rst.get("name"),
                    "rating": rst.get("rating"),
                    "avg_price": rst.get("avg_price"),
                    "lat": rst.get("lat"),
                    "lng": rst.get("lng"),
                },
                "objectives": {
                    "rating_score": round(float(-pareto_F[i, 0]), 2),
                    "total_cost": round(float(pareto_F[i, 1])),
                    "transit_time_min": round(float(pareto_F[i, 2]), 1),
                    "preference_match": round(float(-pareto_F[i, 3]), 2),
                },
                "feasible": constraint_violation <= 1e-6,
            })

        # 优先返回 feasible 解
        feasible = [s for s in solutions if s["feasible"]]
        result_solutions = (feasible or solutions)[:10]

        logger.info(
            "PymooSolver: %d total, %d feasible, returning %d",
            len(solutions), len(feasible), len(result_solutions),
        )

        return ToolResult(success=True, data={
            "solver": "pymoo_nsga2",
            "pareto_solutions": result_solutions,
            "total_generated": len(solutions),
            "feasible_count": len(feasible),
        })
