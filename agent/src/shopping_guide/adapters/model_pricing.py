"""LLM model pricing dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPricing:
    prompt_per_1k: float = 0.0
    completion_per_1k: float = 0.0
