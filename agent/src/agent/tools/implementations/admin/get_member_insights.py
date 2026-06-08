"""Get member insights tool — aggregate member statistics from marketplace."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class GetMemberInsightsArgs(BaseModel):
    pass  # no filters needed for basic insights


class GetMemberInsightsTool(SmartDayBaseTool):
    name: str = "get_member_insights"
    description: str = (
        "Get member insights: total members, recent registrations, member activity. "
        "Returns aggregate member statistics for the B-end dashboard."
    )
    is_read_only: bool = True
    cost_model: str = "free"
    args_schema: type[BaseModel] = GetMemberInsightsArgs
    tool_timeout: float = 5.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.get(
                    f"{MARKETPLACE_URL}/api/v1/admin/members",
                    params={"page": 1, "page_size": 100},
                )
                response.raise_for_status()
                data = response.json()

                inner = data.get("data", data)
                members = inner.get("items", inner.get("members", []))
                total_members = inner.get("total", len(members))

                # Compute recent registrations (last 7 days)
                now = datetime.now(timezone.utc)
                week_ago = now - timedelta(days=7)
                recent_count = 0
                active_count = 0

                for member in members:
                    created = member.get("created_at", member.get("create_time", ""))
                    if created:
                        try:
                            created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                            if created_dt >= week_ago:
                                recent_count += 1
                        except (ValueError, TypeError):
                            pass

                    if member.get("is_active", True):
                        active_count += 1

                return {
                    "total_members": total_members,
                    "recent_registrations_7d": recent_count,
                    "active_members": active_count,
                    "sampled_members": [
                        {
                            "member_id": m.get("id"),
                            "username": m.get("username", m.get("nickname", "")),
                            "email": m.get("email", ""),
                            "created_at": m.get("created_at", m.get("create_time", "")),
                        }
                        for m in members[:10]
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
