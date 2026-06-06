"""Tool manifest — the shape returned to the LLM by MCP tools/list.

Must be serialisable to JSON without loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolManifest:
    """Tool description for LLM tool selection (MCP tools/list compatible).

    Rules:
      - name: snake_case, globally unique within the registry
      - description: >= 2 sentences (WHAT + WHEN + optionally WHEN-NOT)
      - input_schema: valid JSON Schema (draft-07), 'required' always present
    """

    name: str
    description: str
    input_schema: dict
    is_read_only: bool
    cost_model: str  # "free" | "per_call:¥0.001" | "mock"

    def to_openai_tool(self, strict: bool = False) -> dict:
        """Convert to OpenAI function-calling format for LLM tools parameter."""
        func_def: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }
        if strict:
            func_def["strict"] = True
        return {
            "type": "function",
            "function": func_def,
        }
