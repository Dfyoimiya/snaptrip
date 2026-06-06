"""ItineraryProblem —— pymoo NSGA-II 多目标行程优化问题定义。

决策变量:
  x[0] = 活动 POI 索引 (0..N_activities-1)
  x[1] = 餐厅 POI 索引 (0..N_restaurants-1)

目标 (全部最小化):
  f1 = -rating_score         (最大化评分)
  f2 = total_cost            (最小化费用)
  f3 = transit_time_min      (最小化转场时间)
  f4 = -preference_match     (最大化偏好匹配)

约束 (g(x) <= 0):
  g1 = total_cost - budget
  g2 = total_time - time_window
  g3 = child_friendly violations (if required)
  g4 = dietary violations (if required)

Author: SnapTrip Team
Date: 2026-05-29
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from pymoo.core.problem import Problem


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class ItineraryProblem(Problem):
    """NSGA-II 行程优化问题。

    2 个整数决策变量，4 个目标，2-4 个约束。
    """

    def __init__(
        self,
        activities: list[dict[str, Any]],
        restaurants: list[dict[str, Any]],
        budget: float,
        time_window_min: float,
        guest_count: int,
        child_friendly_required: bool = False,
        dietary_restrictions: list[str] | None = None,
        origin_lat: float = 39.9219,
        origin_lng: float = 116.4435,
        activity_duration_min: float = 150.0,
        meal_duration_min: float = 90.0,
    ):
        self.activities = activities
        self.restaurants = restaurants
        self.budget = budget
        self.time_window_min = time_window_min
        self.guest_count = guest_count
        self.child_friendly_required = child_friendly_required
        self.dietary_restrictions = dietary_restrictions or []
        self.origin_lat = origin_lat
        self.origin_lng = origin_lng
        self.activity_duration_min = activity_duration_min
        self.meal_duration_min = meal_duration_min

        n_act = len(activities)
        n_rst = len(restaurants)

        # 计算约束数量
        n_constr = 2  # budget + time_window (always)
        if child_friendly_required:
            n_constr += 1
        if self.dietary_restrictions:
            n_constr += 1

        super().__init__(
            n_var=2,
            n_obj=4,
            n_constr=n_constr,
            xl=[0, 0],
            xu=[n_act - 1 if n_act > 0 else 0, n_rst - 1 if n_rst > 0 else 0],
            type_var=int,
        )

    def _evaluate(self, X, out, *args, **kwargs):
        n = X.shape[0]
        F = np.zeros((n, 4))
        G_list = []

        for i in range(n):
            act_idx = int(X[i, 0])
            rst_idx = int(X[i, 1])

            act = self.activities[act_idx] if act_idx < len(self.activities) else {}
            rst = self.restaurants[rst_idx] if rst_idx < len(self.restaurants) else {}

            # 目标
            act_rating = act.get("rating", 3.5) or 3.5
            rst_rating = rst.get("rating", 3.5) or 3.5
            F[i, 0] = -(act_rating * 0.5 + rst_rating * 0.5)

            act_cost = (act.get("avg_price", 0) or 0) * self.guest_count
            rst_cost = (rst.get("avg_price", 100) or 100) * self.guest_count
            F[i, 1] = float(act_cost + rst_cost)

            transit = self._est_total_transit(act, rst)
            F[i, 2] = transit

            act_rel = act.get("relevance", 0.5) or 0.5
            rst_rel = rst.get("relevance", 0.5) or 0.5
            F[i, 3] = -(act_rel * 0.4 + rst_rel * 0.6)

            # 约束
            constraints: list[float] = []

            # g1: budget
            total = act_cost + rst_cost
            constraints.append(max(0.0, total - self.budget))

            # g2: time window
            total_time = self.activity_duration_min + transit + self.meal_duration_min
            constraints.append(max(0.0, total_time - self.time_window_min))

            # g3: child_friendly
            if self.child_friendly_required:
                violations = 0.0
                if not act.get("child_friendly"):
                    violations += 1.0
                if not rst.get("child_friendly"):
                    violations += 1.0
                constraints.append(violations)

            # g4: dietary
            if self.dietary_restrictions:
                violations = 0.0
                rst_tags = rst.get("dietary_tags", []) or []
                for d in self.dietary_restrictions:
                    if d not in rst_tags:
                        violations += 1.0
                constraints.append(violations)

            G_list.append(constraints)

        out["F"] = F
        out["G"] = np.array(G_list)

    def _est_total_transit(self, act: dict, rst: dict) -> float:
        """估算总转场时间 (min): home→act + act→rst + rst→home。"""
        home_lat, home_lng = self.origin_lat, self.origin_lng
        act_lat = act.get("lat", home_lat) or home_lat
        act_lng = act.get("lng", home_lng) or home_lng
        rst_lat = rst.get("lat", home_lat) or home_lat
        rst_lng = rst.get("lng", home_lng) or home_lng

        d1 = _haversine_km(home_lat, home_lng, act_lat, act_lng)
        d2 = _haversine_km(act_lat, act_lng, rst_lat, rst_lng)
        d3 = _haversine_km(rst_lat, rst_lng, home_lat, home_lng)

        total_km = d1 + d2 + d3
        return (total_km / 40) * 60  # 平均车速 40km/h
