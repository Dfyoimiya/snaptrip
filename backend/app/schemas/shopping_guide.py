"""Shopping Guide Pydantic Schemas — Request/Response models for C-end AI shopping guide.

Author: SnapTrip Team
Date: 2026-06-17
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ShoppingContext(BaseModel):
    """Context from the frontend about what the user is currently viewing."""

    current_product_id: str | None = Field(None, description="Product the user is currently browsing")
    current_category: str | None = Field(None, description="Category the user is currently browsing")
    search_query: str | None = Field(None, description="Current search query in the search bar")


class ShoppingGuideRequest(BaseModel):
    """Request body for shopping guide chat."""

    message: str = Field(..., description="User's message to the shopping guide")
    session_id: str | None = Field(None, description="Session ID for conversation continuity. None = new session")
    context: ShoppingContext | None = Field(None, description="Frontend context about what the user is viewing")


class ShoppingGuideSession(BaseModel):
    """Session metadata returned to the frontend."""

    id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_count: int = 0
    summary: str | None = None


class ShoppingGuideSessionList(BaseModel):
    """List of user's shopping guide sessions."""

    sessions: list[ShoppingGuideSession] = Field(default_factory=list)
    total: int = 0
