"""Emotion detector — lightweight keyword-based sentiment analysis for CS agent.

Used by the customer_service node to detect user emotional state and adjust tone.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Emotion keyword sets ────────────────────────────────────────────────────

EMOTION_KEYWORDS: dict[str, tuple[list[str], list[str]]] = {
    "angry": (
        # Chinese
        ["太过分了", "混蛋", "垃圾", "坑人", "骗子", "投诉到底", "315",
         "曝光", "差到", "极差", "愤怒", "气死", "气死我了", "火大",
         "什么破", "太烂了", "恶心的", "无语死了", "白痴", "傻逼"],
        # English
        ["terrible", "awful", "scam", "fraud", "ridiculous", "outrageous",
         "unacceptable", "horrible", "worst", "garbage", "pathetic"],
    ),
    "frustrated": (
        # Chinese
        ["等了", "还没", "又是", "怎么又", "还是没", "到底", "什么时候才能",
         "反复", "一次又", "又来了", "真麻烦", "啰嗦", "能不能快", "效率",
         "怎么还没", "还没好", "究竟", "几天了", "很久了"],
        # English
        ["waiting", "still not", "again", "when will", "taking too long",
         "frustrated", "annoying", "slow", "hurry up", "how long"],
    ),
    "anxious": (
        # Chinese
        ["急", "着急", "担心", "不会", "会不会", "能不能退", "怎么办",
         "有问题", "不确定", "能不能", "帮我看看", "麻烦看一下", "帮我查"],
        # English
        ["worried", "concerned", "anxious", "not sure", "help me",
         "can you check", "what if", "afraid", "nervous"],
    ),
    "satisfied": (
        # Chinese
        ["谢谢", "感谢", "很好", "太好了", "满意", "解决了", "好的谢谢",
         "明白了", "清楚", "感谢你", "帮大忙", "好评", "辛苦", "多谢",
         "好的好的", "OK", "ok", "好的"],
        # English
        ["thank", "thanks", "great", "perfect", "awesome", "helpful",
         "resolved", "appreciate", "wonderful", "excellent"],
    ),
    "neutral": (
        # Chinese
        ["你好", "想问", "请问", "咨询", "了解", "查一下", "看一下",
         "能帮", "麻烦", "你好在吗"],
        # English
        ["hello", "hi", "question", "inquire", "wondering",
         "could you", "can you", "i need", "looking for"],
    ),
}

# ── Emotion trajectory patterns ─────────────────────────────────────────────

TRAJECTORY_PATTERNS = {
    ("angry", "satisfied"): "angry→calm",
    ("angry", "frustrated"): "angry→frustrated",
    ("frustrated", "satisfied"): "frustrated→calm",
    ("anxious", "satisfied"): "anxious→calm",
    ("neutral", "satisfied"): "neutral→satisfied",
    ("angry", "neutral"): "angry→neutral",
    ("frustrated", "neutral"): "frustrated→neutral",
}


# ── Public API ───────────────────────────────────────────────────────────────


def detect_emotion(text: str) -> tuple[str, float]:
    """Detect the dominant emotion in user text.

    Returns (emotion_label, confidence) where:
      - emotion_label: "angry" | "frustrated" | "anxious" | "satisfied" | "neutral"
      - confidence: 0.0 - 1.0 (higher = stronger signal)
    """
    if not text:
        return ("neutral", 0.0)

    text_lower = text.lower()
    scores: dict[str, int] = {}

    for emotion, (cn_keywords, en_keywords) in EMOTION_KEYWORDS.items():
        score = 0
        all_kw = cn_keywords + en_keywords
        for kw in all_kw:
            if kw.lower() in text_lower:
                score += 1
                # Bonus for "strong" keywords (longer, more specific)
                if len(kw) >= 3:
                    score += 1
        scores[emotion] = score

    if not scores or max(scores.values()) == 0:
        return ("neutral", 0.1)

    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = scores[best] / total if total > 0 else 0.0

    return (best, round(confidence, 2))


def detect_emotion_trajectory(
    messages: list[Any], window: int = 5,
) -> str | None:
    """Detect emotion trajectory across recent user messages.

    Returns a trajectory string like "angry→calm" or None if unchanged.
    """
    texts: list[str] = []
    for msg in messages:
        role = getattr(msg, "type", None)
        content = getattr(msg, "content", "") or ""
        if role == "human" and content:
            texts.append(str(content))
        elif isinstance(msg, dict) and msg.get("type") == "human":
            texts.append(str(msg.get("content", "")))

    if len(texts) < 2:
        return None

    recent = texts[-window:]
    first_emotion, _ = detect_emotion(recent[0])
    last_emotion, _ = detect_emotion(recent[-1])

    if first_emotion == last_emotion:
        return None

    trajectory = TRAJECTORY_PATTERNS.get((first_emotion, last_emotion))
    if trajectory:
        logger.info(
            "emotion_trajectory: %s (from %s to %s)",
            trajectory, first_emotion, last_emotion,
        )
    return trajectory


def emotion_to_tone_hint(emotion: str) -> str:
    """Convert detected emotion to a tone adjustment hint for the CS agent."""
    hints = {
        "angry": "The user is ANGRY. Be extra empathetic, apologize sincerely, "
                 "and focus on concrete solutions. Do NOT be defensive.",
        "frustrated": "The user is FRUSTRATED. Acknowledge their patience, "
                      "provide a clear timeline, and show urgency.",
        "anxious": "The user is ANXIOUS. Provide reassurance, clear next steps, "
                   "and offer to follow up.",
        "satisfied": "The user seems SATISFIED. Wrap up efficiently and "
                     "ask if they need anything else.",
        "neutral": "",
    }
    return hints.get(emotion, "")
