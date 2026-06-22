"""FusionWeightService — 用户分群感知的融合权重调整。

根据用户分群动态调整 5 路融合权重:
  - NEW_USER:      降低 CF 权重 (无历史), 提高 trending 权重 (发现)
  - HIGH_VALUE:    提高 CF 权重 (个性化), 轻微提高 price 权重
  - PRICE_SENSITIVE: 大幅提高 price 权重, 降低 vector 权重
  - CHURN_RISK:    提高 CF + trending 权重 (召回), 提高 price 权重 (优惠感知)
  - ACTIVE:        保持原有权重 (基准)

权重调整公式:
  segment_adjusted_weight = intent_weight × (1 + segment_delta)
  segment_delta ∈ [-0.3, +0.3], 限制总权重不变 (后续归一化)

Author: SnapTrip Team
Date: 2026-06-22
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── 分群权重调整系数 (乘法因子, 1.0 = 不变) ──

SEGMENT_WEIGHT_MODIFIERS: dict[str, dict[str, float]] = {
    "new_user": {
        "bm25": 1.10,
        "vector": 1.00,
        "cf": 0.50,       # 新用户无行为历史, CF 不可靠
        "price": 0.90,
        "category": 1.00,
        "brand": 1.05,
    },
    "active": {
        "bm25": 1.00,
        "vector": 1.00,
        "cf": 1.00,
        "price": 1.00,
        "category": 1.00,
        "brand": 1.00,
    },
    "high_value": {
        "bm25": 0.95,
        "vector": 1.05,
        "cf": 1.30,       # 高价值用户, CF 个性化更重要
        "price": 1.10,
        "category": 1.00,
        "brand": 1.05,    # 高价值用户偏好品牌商品
    },
    "price_sensitive": {
        "bm25": 1.05,
        "vector": 0.85,
        "cf": 0.90,
        "price": 1.40,    # 价格敏感用户, 价格匹配权重最高
        "category": 1.00,
        "brand": 0.85,    # 价格敏感用户品牌忠诚度较低
    },
    "churn_risk": {
        "bm25": 1.05,
        "vector": 1.00,
        "cf": 1.25,       # 流失用户, 个性化召回
        "price": 1.20,    # 优惠感知
        "category": 0.90,
        "brand": 1.10,    # 流失用户用偏好品牌召回
    },
}


def apply_segment_weights(
    intent_weights: dict[str, float],
    user_segment: str | None = None,
) -> dict[str, float]:
    """应用用户分群感知的权重调整。

    Args:
        intent_weights: 意图分类输出的融合权重 {bm25, vector, cf, price, category, brand}
        user_segment: 用户分群标签 (new_user/active/high_value/price_sensitive/churn_risk)

    Returns:
        调整后的融合权重, 所有权重之和保持 ~1.0
    """
    if not user_segment:
        return intent_weights

    modifiers = SEGMENT_WEIGHT_MODIFIERS.get(user_segment)
    if not modifiers:
        return intent_weights

    # 应用乘法调整
    adjusted: dict[str, float] = {}
    for channel, weight in intent_weights.items():
        modifier = modifiers.get(channel, 1.0)
        adjusted[channel] = weight * modifier

    # 归一化 (保证权重之和 ≈ 原有权重之和, 避免放大/缩小整体分数)
    total = sum(adjusted.values())
    if total > 0:
        original_total = sum(intent_weights.values())
        scale = original_total / total
        adjusted = {k: round(v * scale, 4) for k, v in adjusted.items()}

    logger.debug(
        "fusion_weights: segment=%s original=%s adjusted=%s",
        user_segment,
        intent_weights,
        adjusted,
    )
    return adjusted


def get_default_weights() -> dict[str, float]:
    """返回默认融合权重 (navigational 意图, active 分群)。"""
    return {"bm25": 0.35, "vector": 0.10, "cf": 0.10, "price": 0.05, "category": 0.15, "brand": 0.25}
