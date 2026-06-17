"""Save session summary tool — persist compressed CS session memory (write)."""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class SaveSessionSummaryArgs(BaseModel):
    session_id: str = Field(..., description="Session ID to save summary for")
    intent: str | None = Field(None, description="CS intent of the session")
    summary_text: str = Field(..., description="LLM-compressed summary of the conversation")
    resolution_status: str = Field(default="unknown", description="resolved/escalated/abandoned/unknown")
    satisfaction_score: int | None = Field(None, description="CSAT score 1-5")
    ticket_id: str | None = Field(None, description="Support ticket ID if escalated")
    order_id: str | None = Field(None, description="Related order ID")
    conversation_turns: int = Field(default=0, description="Number of conversation turns")
    tools_called: list[str] | None = Field(None, description="List of tools called")
    emotion_trajectory: str | None = Field(None, description="Emotion change during session")


class SaveSessionSummaryTool(SmartDayBaseTool):
    name: str = "save_session_summary"
    description: str = (
        "Save a compressed summary of the current customer service conversation "
        "for long-term memory. Call this at the END of every CS session to persist "
        "context that can be loaded in future sessions. "
        "The summary should capture: what the issue was, what was done, "
        "the resolution status, and key entities (order IDs, product IDs, amounts)."
    )
    is_read_only: bool = False
    cost_model: str = "free"
    args_schema: type[BaseModel] = SaveSessionSummaryArgs
    tool_timeout: float = 10.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            payload: dict[str, Any] = {
                "session_id": kwargs["session_id"],
                "summary_text": kwargs["summary_text"],
                "resolution_status": kwargs.get("resolution_status", "unknown"),
                "conversation_turns": kwargs.get("conversation_turns", 0),
            }
            for field in ("intent", "satisfaction_score", "ticket_id",
                          "order_id", "tools_called", "emotion_trajectory"):
                if field in kwargs and kwargs[field] is not None:
                    payload[field] = kwargs[field]

            hdrs = auth_header()
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.post(
                    f"{MARKETPLACE_URL}/api/v1/portal/cs/sessions/summarize",
                    json=payload,
                    headers=hdrs,
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]
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
