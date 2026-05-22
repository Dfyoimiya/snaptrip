"""SnapTrip Agent 离线评估运行器。

评估指标:
  1. Intent Accuracy — city/scene_type/guest_count 精确匹配率
  2. Type Coverage    — type_prefs 在结果中的覆盖率
  3. Mood Coverage    — mood_prefs 在增强结果中的覆盖率

运行:
  cd backend && uv run python tests/eval/eval_runner.py

Author: SnapTrip Team
Date: 2026-05-18
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

EVAL_DIR = Path(__file__).parent


# ===== Intent Eval =====


@dataclass
class IntentMetrics:
    total: int = 0
    city_correct: int = 0
    scene_correct: int = 0
    guest_correct: int = 0
    type_coverage_ratio: float = 0.0
    mood_coverage_ratio: float = 0.0

    @property
    def city_acc(self) -> float:
        return self.city_correct / self.total if self.total else 0

    @property
    def scene_acc(self) -> float:
        return self.scene_correct / self.total if self.total else 0

    @property
    def guest_acc(self) -> float:
        return self.guest_correct / self.total if self.total else 0


def eval_intent(golden_path: Path | None = None) -> IntentMetrics:
    """运行意图解析评估"""
    path = golden_path or EVAL_DIR / "golden_intent.json"
    cases = json.loads(path.read_text(encoding="utf-8"))

    from agent_worker.app.agent.engines.intent_parser import IntentParser
    from agent_worker.app.agent.protocol import AgentContext

    parser = IntentParser()
    m = IntentMetrics(total=len(cases))

    for case in cases:
        user_input = case["user_input"]
        expected = case["expected"]

        context = AgentContext(user_input=user_input, lat=39.9, lng=116.4)
        result = asyncio.run(parser.execute(context))
        intent = result.data.get("intent", {})

        actual_city = intent.get("city", "")
        actual_scene = intent.get("scene_type", "solo")
        actual_guest = intent.get("guest_count", 2)
        actual_types = intent.get("type_prefs", [])
        actual_moods = intent.get("mood_prefs", [])

        # city
        exp_city = expected.get("city", "")
        if not exp_city or actual_city == exp_city:
            m.city_correct += 1

        # scene
        if actual_scene == expected.get("scene_type", ""):
            m.scene_correct += 1

        # guest
        if actual_guest == expected.get("guest_count", 2):
            m.guest_correct += 1

        # type coverage
        exp_types = expected.get("type_prefs", [])
        if exp_types:
            covered = sum(1 for t in exp_types if t in actual_types)
            m.type_coverage_ratio += covered / len(exp_types)

        # mood coverage
        exp_moods = expected.get("mood_prefs", [])
        if exp_moods:
            covered = sum(1 for t in exp_moods if t in actual_moods)
            m.mood_coverage_ratio += covered / len(exp_moods)

    m.type_coverage_ratio = m.type_coverage_ratio / m.total if m.total else 0
    m.mood_coverage_ratio = m.mood_coverage_ratio / m.total if m.total else 0

    return m


# ===== Plan Eval =====


@dataclass
class PlanMetrics:
    total: int = 0
    slot_count_ok: int = 0
    type_covered: int = 0
    budget_ok: int = 0

    @property
    def slot_ok_rate(self) -> float:
        return self.slot_count_ok / self.total if self.total else 0

    @property
    def type_cover_rate(self) -> float:
        return self.type_covered / self.total if self.total else 0

    @property
    def budget_ok_rate(self) -> float:
        return self.budget_ok / self.total if self.total else 0


def eval_plan(golden_path: Path | None = None) -> PlanMetrics:
    """运行规划质量评估"""
    path = golden_path or EVAL_DIR / "golden_plan.json"
    cases = json.loads(path.read_text(encoding="utf-8"))

    from agent_worker.app.agent.engines.intent_parser import IntentParser
    from agent_worker.app.agent.engines.planning_engine import PlanningEngine
    from agent_worker.app.agent.engines.retrieval_engine import RetrievalEngine
    from agent_worker.app.agent.protocol import AgentContext, AgentResult

    parser = IntentParser()
    planner = PlanningEngine()
    retriever = RetrievalEngine()

    m = PlanMetrics(total=len(cases))

    for case in cases:
        user_input = case["user_input"]
        expected = case.get("expected", {})

        context = AgentContext(user_input=user_input, lat=39.9, lng=116.4)

        intent_result = asyncio.run(parser.execute(context))
        intent = intent_result.data.get("intent", {})

        context.history = [
            AgentResult(agent_name="intent_parser", status="success", data={"intent": intent}),
            AgentResult(agent_name="context_loader", status="success", data={"enriched_intent": {"intent": intent}}),
        ]
        candidates_result = asyncio.run(retriever.execute(context))
        candidates = candidates_result.data.get("candidate_pool", {})

        context.history = [
            AgentResult(agent_name="intent_parser", status="success", data={"intent": intent}),
            AgentResult(agent_name="context_loader", status="success", data={"enriched_intent": {"intent": intent}}),
            AgentResult(agent_name="retrieval_engine", status="success", data={"candidate_pool": candidates}),
        ]
        plan_result = asyncio.run(planner.execute(context))
        draft = plan_result.data.get("draft", {})
        slots = draft.get("slots", [])

        # slot count
        lo = expected.get("slots_min", 1)
        hi = expected.get("slots_max", 4)
        if lo <= len(slots) <= hi:
            m.slot_count_ok += 1

        # type coverage
        must_types = expected.get("must_contain_type", [])
        flat_types: list[str] = []
        for s in slots:
            poi = s.get("poi", {}) if isinstance(s, dict) else getattr(s, "poi", None)
            if poi:
                flat_types.append(poi.get("type", "") if isinstance(poi, dict) else getattr(poi, "type", ""))
        if all(t in flat_types for t in must_types) or not must_types:
            m.type_covered += 1

        # budget
        total_cost = draft.get("total_cost", 0)
        budget_max = expected.get("total_cost_max", float("inf"))
        if total_cost <= budget_max:
            m.budget_ok += 1

    return m


# ===== Main =====


def main():
    print("=" * 60)
    print("  SnapTrip Agent 离线评估")
    print("=" * 60)

    # Intent
    print("\n--- 意图解析 (golden_intent.json) ---")
    im = eval_intent()
    print(f"  样本数:       {im.total}")
    print(f"  City 准确率:  {im.city_acc:.1%}")
    print(f"  Scene 准确率: {im.scene_acc:.1%}")
    print(f"  Guest 准确率: {im.guest_acc:.1%}")
    print(f"  Type 覆盖率:  {im.type_coverage_ratio:.1%}")
    print(f"  Mood 覆盖率:  {im.mood_coverage_ratio:.1%}")

    # Plan
    print("\n--- 规划质量 (golden_plan.json) ---")
    pm = eval_plan()
    print(f"  样本数:       {pm.total}")
    print(f"  Slot 合理率:  {pm.slot_ok_rate:.1%}")
    print(f"  Type 覆盖率:  {pm.type_cover_rate:.1%}")
    print(f"  Budget 合理率:{pm.budget_ok_rate:.1%}")

    # Summary
    overall = (
        im.city_acc * 0.15
        + im.scene_acc * 0.15
        + im.guest_acc * 0.10
        + im.type_coverage_ratio * 0.15
        + im.mood_coverage_ratio * 0.10
        + pm.slot_ok_rate * 0.15
        + pm.type_cover_rate * 0.10
        + pm.budget_ok_rate * 0.10
    )
    print("\n--- 综合分数 ---")
    print(f"  Overall:      {overall:.1%}")
    print("=" * 60)

    # exit code for CI: fail if < 50%
    if overall < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
