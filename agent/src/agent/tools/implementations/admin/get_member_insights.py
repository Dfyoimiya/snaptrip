"""Get member insights tool — dashboard snapshot + member pagination."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetMemberInsightsArgs(BaseModel):
    page: int = Field(1, description="Page number for member list")
    page_size: int = Field(20, description="Members per page (max 100)")


class GetMemberInsightsTool(SmartDayBaseTool):
    name: str = "get_member_insights"
    description: str = (
        "Get member insights: total member count, new members today, recent "
        "registrations, and a page of member profiles. Fetches dashboard snapshot "
        "plus paginated member list."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetMemberInsightsArgs
    tool_timeout: float = 8.0

    async def _arun(self, **kwargs: Any) -> dict:
        page = kwargs.get("page", 1)
        page_size = min(kwargs.get("page_size", 20), 100)
        hdrs = auth_header()

        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                # 1. Dashboard for new_members count
                dash_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/dashboard",
                    headers=hdrs,
                )
                dash_resp.raise_for_status()
                dash_data = dash_resp.json()
                dash_inner = dash_data.get("data", dash_data)

                # 2. Stats overview for today_new_member_count
                overview_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/stats/overview",
                    headers=hdrs,
                )
                overview_resp.raise_for_status()
                overview_data = overview_resp.json()
                overview_inner = overview_data.get("data", overview_data)

                # 3. Paginated member list
                members_resp = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/members",
                    params={"page": page, "page_size": page_size},
                    headers=hdrs,
                )
                members_resp.raise_for_status()
                members_data = members_resp.json()
                members_inner = members_data.get("data", members_data)
                total_members = members_inner.get("total", 0)
                members = members_inner.get("items", [])

                return {
                    "total_members": total_members,
                    "new_members_today": dash_inner.get("new_members", 0),
                    "today_new_member_count": overview_inner.get(
                        "today_new_member_count", 0
                    ),
                    "current_page": page,
                    "page_size": page_size,
                    "members": [
                        {
                            "member_id": m.get("id", ""),
                            "username": m.get("username", m.get("nickname", "")),
                            "email": m.get("email", ""),
                            "is_active": m.get("is_active", True),
                            "created_at": m.get("created_at", m.get("create_time", "")),
                        }
                        for m in members
                    ],
                }
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
        except httpx.RequestError as e:
            return {"error": f"Request failed: {str(e)}"}

    def compensation(
        self, args: dict[str, Any], result: ToolResult
    ) -> CompensationAction:
        return self._noop_compensation(
            action_id=self._idem_key(args),
            tool_name=self.name,
        )
