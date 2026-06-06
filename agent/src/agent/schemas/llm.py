"""LLM 相关 schema —— 最小保留。

Author: SnapTrip Team
Date: 2026-05-26
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPricing:
    prompt_per_1k: float = 0.0
    completion_per_1k: float = 0.0
