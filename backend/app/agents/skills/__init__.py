"""Skill loader —— 解析 agents/skills/*.md 并按条件注入 Prompt。

Skill 文件格式（与 docs/skills 对齐）:
  ## 触发条件
  - 条件1
  - 条件2

  ## 执行步骤
  1. 步骤1
  2. 步骤2

  ## 示例
  ...
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SKILLS_DIR = Path(__file__).parent


def _parse_skill(text: str) -> dict[str, Any]:
    """Parse a skill markdown file into structured dict."""

    skill = {"title": "", "triggers": [], "steps": [], "examples": []}
    lines = text.splitlines()
    if lines:
        skill["title"] = lines[0].lstrip("# ").strip()

    current_section = None
    buffer: list[str] = []

    def _flush() -> None:
        if current_section == "triggers":
            skill["triggers"] = [line.lstrip("- ").strip() for line in buffer if line.strip()]
        elif current_section == "steps":
            skill["steps"] = [re.sub(r"^\d+\.\s*", "", line).strip() for line in buffer if line.strip()]
        elif current_section == "examples":
            skill["examples"] = [line for line in buffer if line.strip()]

    for line in lines[1:]:
        s = line.strip()
        if s.startswith("## 触发条件"):
            _flush()
            current_section = "triggers"
            buffer = []
        elif s.startswith("## 执行步骤"):
            _flush()
            current_section = "steps"
            buffer = []
        elif s.startswith("## 示例"):
            _flush()
            current_section = "examples"
            buffer = []
        else:
            buffer.append(line)
    _flush()
    return skill


def load_all_skills() -> list[dict[str, Any]]:
    """Load all skill markdown files from the skills directory."""

    skills: list[dict[str, Any]] = []
    for path in sorted(_SKILLS_DIR.glob("*.md")):
        skills.append(_parse_skill(path.read_text(encoding="utf-8")))
    return skills


def match_skills(*, scene_type: str | None = None, type_prefs: list[str] | None = None) -> list[dict[str, Any]]:
    """Return skills whose triggers match the given context.

    Matching rules (best-effort keyword search):
      - If scene_type contains 'fallback' -> plan-fallback
      - If type_prefs contains 'restaurant' or 'cafe' -> restaurant-recommend
      - If scene_type contains 'time' or type_prefs is empty -> time-negotiation
    """

    all_skills = load_all_skills()
    matched: list[dict[str, Any]] = []
    keywords = []
    if scene_type:
        keywords.append(scene_type.lower())
    for tp in type_prefs or []:
        keywords.append(tp.lower())

    for skill in all_skills:
        triggers = " ".join(skill.get("triggers", [])).lower()
        title = skill.get("title", "").lower()
        # heuristic matching
        if any(kw in triggers or kw in title for kw in keywords):
            matched.append(skill)

    # Always include time-negotiation as a baseline planning skill
    time_skill = next((s for s in all_skills if "时间" in s.get("title", "")), None)
    if time_skill and time_skill not in matched:
        matched.append(time_skill)

    return matched


def build_skill_prompt(skills: list[dict[str, Any]]) -> str:
    """Render matched skills into a prompt appendix for the Planning Engine."""

    if not skills:
        return ""

    parts = ["\n# 规划策略技能\n"]
    for skill in skills:
        parts.append(f"## {skill['title']}\n")
        if skill["steps"]:
            parts.append("执行步骤:\n")
            for step in skill["steps"]:
                parts.append(f"- {step}\n")
        parts.append("\n")
    return "".join(parts)
