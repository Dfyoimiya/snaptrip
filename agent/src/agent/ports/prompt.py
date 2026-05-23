"""Prompt rendering boundary interfaces."""

from __future__ import annotations

from typing import Protocol


class PromptPort(Protocol):
    """Interface for loading and rendering prompt templates."""

    async def render(self, template_name: str, context: dict) -> str: ...
