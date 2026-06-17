"""Create support ticket tool — escalate to human agent (write, Saga)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

from agent.tools.auth import auth_header
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.transaction.compensation import CompensationAction

logger = logging.getLogger(__name__)

MARKETPLACE_URL = os.getenv("SNAPTRIP_MARKETPLACE_URL", "http://localhost:8000")


class CreateSupportTicketArgs(BaseModel):
    title: str = Field(..., description="Ticket title summarizing the issue")
    description: str = Field(..., description="Detailed description of the problem")
    order_id: str | None = Field(None, description="Related order ID if applicable")
    type: str = Field(
        default="inquiry",
        description="Ticket type: complaint, refund, inquiry, or other",
    )
    priority: str = Field(
        default="normal",
        description="Priority: normal, urgent, or critical",
    )


class CreateSupportTicketTool(SmartDayBaseTool):
    name: str = "create_support_ticket"
    description: str = (
        "Create a support ticket to escalate an issue to human customer service. "
        "Use when the AI cannot resolve the problem (complex disputes, legal threats, "
        "severe complaints, or situations requiring manual intervention). "
        "Returns the ticket ID for tracking."
    )
    is_read_only: bool = False
    cost_model: str = "free"
    args_schema: type[BaseModel] = CreateSupportTicketArgs
    tool_timeout: float = 10.0

    async def _arun(self, **kwargs: Any) -> dict:
        try:
            payload: dict[str, Any] = {
                "title": kwargs["title"],
                "description": kwargs["description"],
                "type": kwargs.get("type", "inquiry"),
                "priority": kwargs.get("priority", "normal"),
            }
            if kwargs.get("order_id"):
                payload["order_id"] = kwargs["order_id"]

            hdrs = auth_header()
            async with httpx.AsyncClient(timeout=self.tool_timeout) as client:
                response = await client.post(
                    f"{MARKETPLACE_URL}/api/v1/portal/cs/tickets",
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
        """Ticket creation is irreversible — admin must manually close the ticket."""
        title = args.get("title", "unknown")

        async def _ticket_rollback() -> None:
            logger.warning(
                "CreateSupportTicket compensation: ticket '%s' creation is irreversible. "
                "Admin must manually close the ticket.",
                title,
            )

        return CompensationAction(
            action_id=self._idem_key(args),
            tool_name=self.name,
            description=f"Support-ticket rollback for '{title}' (no-op: requires manual admin action)",
            execute=_ticket_rollback,
        )
