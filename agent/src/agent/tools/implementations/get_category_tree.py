"""Get category tree tool — browse product category hierarchy."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetCategoryTreeArgs(BaseModel):
    """No required args — fetches the full category tree."""


class GetCategoryTreeTool(SmartDayBaseTool):
    name: str = "get_category_tree"
    description: str = (
        "Browse the full product category hierarchy as a tree. "
        "Returns top-level categories with their children, so users can "
        "explore what types of products are available on SnapTrip."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetCategoryTreeArgs
    tool_timeout: float = 4.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/portal/categories/tree",
                )
                response.raise_for_status()
                data = response.json()

            inner = data.get("data", data)
            tree = inner if isinstance(inner, list) else inner.get("tree", [])

            return {
                "total_categories": self._count_nodes(tree),
                "tree": tree,
            }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def _count_nodes(self, tree: list[dict]) -> int:
        count = 0
        for node in tree:
            count += 1
            children = node.get("children", [])
            if isinstance(children, list):
                count += self._count_nodes(children)
        return count

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
