"""Compliance node — regex-based content safety check.

Inspired by smart-cs-multi-agent two-phase compliance pattern.
Phase 1 (this node): regex rules, <2ms, zero LLM cost.
Phase 2 (future): LLM deep semantic check, triggered on medium-risk content.

Architecture: all specialist outputs → synthesize → compliance → END
Non-blocking: violations are logged + added to state but response still returned.
"""

from __future__ import annotations

import logging
import re
from typing import cast

from agent.schemas.state import PlanState

logger = logging.getLogger(__name__)

# ── PII patterns ─────────────────────────────────────────────────────────────

PII_PATTERNS: dict[str, tuple[str, str]] = {
    "phone": (r"1[3-9]\d{9}", "手机号"),
    "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "邮箱"),
    "id_card": (r"\d{17}[\dXx]", "身份证号"),
    "bank_card": (r"\d{16,19}", "银行卡号"),
}

# ── Forbidden terms (Chinese ad law + financial compliance) ──────────────────

FORBIDDEN_TERMS = [
    "保证收益",
    "稳赚不赔",
    "零风险",
    "绝对安全",
    "内部消息",
    "内部渠道",
    "独家内幕",
    "保本保息",
    "承诺收益",
    "百分百",
    "100%成功",
    "绝不",
    "永不",
]


def _mask_pii(text: str, match: re.Match) -> str:
    """Mask PII: keep first 3 + last 3 chars, middle replaced with *."""
    original = match.group()
    if len(original) <= 4:
        return "****"
    return cast(str, original[:3] + "*" * (len(original) - 6) + original[-3:])


async def compliance_node(state: PlanState) -> dict:
    """Check final AI response for PII leaks and forbidden terms.

    Scans the last assistant message in the conversation for:
    - PII patterns (phone, email, ID card, bank card)
    - Forbidden marketing/financial terms

    Returns compliance result in state. Non-blocking — violations are
    logged but the response is still returned to the user.
    """
    messages = state.get("messages", [])
    violations: list[str] = []
    risk_level = "low"

    # Scan last assistant message
    for msg in reversed(messages):
        content = ""
        if hasattr(msg, "content"):
            content = str(msg.content or "")
        elif isinstance(msg, dict):
            content = str(msg.get("content", ""))

        if not content:
            continue

        # Check forbidden terms
        for term in FORBIDDEN_TERMS:
            if term in content:
                violations.append(f"FORBIDDEN_TERM: '{term}'")

        # Check PII
        for pii_type, (pattern, label) in PII_PATTERNS.items():
            if re.search(pattern, content):
                violations.append(f"PII_LEAK: {label}")

    if violations:
        risk_level = "high" if any("PII" in v for v in violations) else "medium"
        logger.warning(
            "compliance: %d violations found, risk=%s: %s",
            len(violations),
            risk_level,
            violations,
        )
    else:
        logger.debug("compliance: passed, no violations")

    return {
        "compliance_passed": len(violations) == 0,
        "compliance_violations": violations,
        "compliance_risk": risk_level,
    }
