"""A/B 测试引擎 —— 一致性哈希分桶 + Thompson Sampling 动态分配。

参考 multi-agent-ecommerce-system 的 ABTestEngine 实现:
  - MD5 一致性哈希: 同一用户始终落入同一桶 (确定性分配)
  - Thompson Sampling: Beta 分布动态调整流量分配 (探索-利用平衡)
  - 默认实验: rec_strategy (control vs llm_rerank), copy_style (formal vs casual)

用法:
    engine = ABTestEngine()
    group = engine.assign(user_id, "rec_strategy")  # → "control" or "treatment_llm"
    engine.record_outcome("rec_strategy", group, success=True)

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ExperimentGroup:
    """实验组定义。"""
    name: str
    weight: int = 50
    config: dict[str, Any] = field(default_factory=dict)
    successes: int = 1   # Beta prior α (成功次数)
    failures: int = 1    # Beta prior β (失败次数)


@dataclass
class Experiment:
    """实验定义。"""
    id: str
    name: str
    groups: list[ExperimentGroup]
    enabled: bool = True
    start_time: float = 0.0
    end_time: float = 0.0


class ABTestEngine:
    """A/B 测试引擎。

    支持两种分配策略:
      1. hash_based: MD5 一致性哈希分桶 (默认)
      2. thompson_sampling: Beta 分布动态分配 (探索-利用)
    """

    BUCKET_COUNT = 100  # 分桶数

    def __init__(self) -> None:
        self._experiments: dict[str, Experiment] = {}
        self._metric_store: dict[str, dict[str, list[dict]]] = {}  # {exp_id: {group: [metrics]}}

        # 注册默认实验
        self._register_default_experiments()

    def _register_default_experiments(self) -> None:
        """注册默认实验。"""
        # 实验1: 推荐策略
        self.register_experiment(Experiment(
            id="rec_strategy",
            name="推荐策略对比",
            groups=[
                ExperimentGroup(
                    name="control",
                    weight=50,
                    config={"rerank": "rule_based"},
                ),
                ExperimentGroup(
                    name="treatment_llm",
                    weight=50,
                    config={"rerank": "llm"},
                ),
            ],
        ))

        # 实验2: 文案风格
        self.register_experiment(Experiment(
            id="copy_style",
            name="文案风格对比",
            groups=[
                ExperimentGroup(name="formal", weight=50),
                ExperimentGroup(name="casual", weight=50),
            ],
        ))

    # ── 实验管理 ──

    def register_experiment(self, exp: Experiment) -> None:
        self._experiments[exp.id] = exp
        self._metric_store[exp.id] = {g.name: [] for g in exp.groups}
        logger.info("AB: registered experiment '%s' with %d groups", exp.id, len(exp.groups))

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    # ── 分配 ──

    def assign(self, user_id: str, experiment_id: str = "rec_strategy") -> str:
        """为用户分配实验组 (一致性哈希)。"""
        exp = self._experiments.get(experiment_id)
        if not exp or not exp.enabled:
            return "control"

        bucket = self._hash_bucket(user_id, experiment_id)
        group = self._bucket_to_group(exp, bucket)
        return group.name

    def assign_thompson(self, user_id: str, experiment_id: str = "rec_strategy") -> str:
        """Thompson Sampling 分配 (Beta 分布采样)。"""
        exp = self._experiments.get(experiment_id)
        if not exp or not exp.enabled:
            return "control"

        samples = [
            np.random.beta(g.successes, g.failures)
            for g in exp.groups
        ]
        best_idx = int(np.argmax(samples))
        return exp.groups[best_idx].name

    # ── 结果记录 ──

    def record_outcome(
        self, experiment_id: str, group_name: str, success: bool,
    ) -> None:
        """记录实验结果 (更新 Thompson 后验分布)。"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        for group in exp.groups:
            if group.name == group_name:
                if success:
                    group.successes += 1
                else:
                    group.failures += 1
                return

    def record_metric(
        self, experiment_id: str, group_name: str, metric_name: str,
        value: float, user_id: str = "",
    ) -> None:
        """记录业务指标。"""
        store = self._metric_store.get(experiment_id)
        if store is None:
            return
        if group_name not in store:
            store[group_name] = []
        store[group_name].append({
            "metric": metric_name,
            "value": value,
            "user_id": user_id,
        })

    # ── 统计 ──

    def get_stats(self, experiment_id: str) -> dict[str, Any] | None:
        """获取实验统计信息。"""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        store = self._metric_store.get(experiment_id, {})

        groups_info = []
        for g in exp.groups:
            metrics = store.get(g.name, [])
            group_data = {
                "name": g.name,
                "weight": g.weight,
                "successes": g.successes,
                "failures": g.failures,
                "conversion_rate": g.successes / (g.successes + g.failures) if (g.successes + g.failures) > 0 else 0,
                "metric_count": len(metrics),
            }
            # 按指标名分组统计
            by_metric: dict[str, list[float]] = {}
            for m in metrics:
                by_metric.setdefault(m["metric"], []).append(m["value"])
            group_data["metrics"] = {
                name: {
                    "count": len(vals),
                    "mean": float(np.mean(vals)) if vals else 0,
                    "std": float(np.std(vals)) if vals else 0,
                }
                for name, vals in by_metric.items()
            }
            groups_info.append(group_data)

        return {
            "experiment_id": experiment_id,
            "experiment_name": exp.name,
            "enabled": exp.enabled,
            "groups": groups_info,
        }

    # ── 内部方法 ──

    @staticmethod
    def _hash_bucket(user_id: str, experiment_id: str) -> int:
        """MD5 一致性哈希 → 桶编号 [0, BUCKET_COUNT)。"""
        key = f"{user_id}:{experiment_id}"
        digest = hashlib.md5(key.encode()).hexdigest()[:8]
        return int(digest, 16) % ABTestEngine.BUCKET_COUNT

    @staticmethod
    def _bucket_to_group(exp: Experiment, bucket: int) -> ExperimentGroup:
        """桶编号 → 实验组 (按 cumulative weight 分配)。"""
        total_weight = sum(g.weight for g in exp.groups)
        if total_weight <= 0:
            return exp.groups[0]

        normalized = bucket / ABTestEngine.BUCKET_COUNT
        cumulative = 0.0
        for group in exp.groups:
            cumulative += group.weight / total_weight
            if normalized < cumulative:
                return group

        return exp.groups[-1]
