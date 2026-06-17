"""搜索建议 Schema。

GET /portal/search/suggest 返回 3 个区块:
  - autocomplete: 前缀匹配自动补全
  - trending:     热门搜索 query
  - ai_suggestions: LLM 生成的对话式搜索建议

Author: SnapTrip Team
Date: 2026-06-16
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SuggestQuery(BaseModel):
    """单条搜索建议。"""

    query: str
    type: str = "autocomplete"  # autocomplete | trending | ai | history
    frequency: int = 0
    detail: str = ""  # AI 建议的补充描述 (仅 type=ai 时有值)


class SuggestSection(BaseModel):
    """建议区块。"""

    section_type: str  # autocomplete | trending | ai_suggestions | history
    title: str
    queries: list[SuggestQuery] = Field(default_factory=list)


class SuggestResponse(BaseModel):
    """搜索建议响应。"""

    prefix: str = ""
    sections: list[SuggestSection]
    total_ms: float = 0.0  # 总延迟 (用于监控)
