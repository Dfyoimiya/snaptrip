"""Mock Server — shared Pydantic schemas (imports contracts)."""

from contracts.schemas.common import Result, PageResult, PaginationParams, CursorParams, GeoPoint, SortOption

# Re-export ToolResult for the tool-invocation channel (agent uses this)
from pydantic import BaseModel


class ToolResult(BaseModel):
    status: str = "success"  # "success" | "failure"
    data: dict | None = None
    error_code: str | None = None
    error_message: str | None = None
    latency_ms: int = 0


__all__ = ["Result", "PageResult", "PaginationParams", "CursorParams", "GeoPoint", "SortOption", "ToolResult"]
