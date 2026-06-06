"""ToolRegistry — thread-safe, hot-reloadable tool registry.

Manages tool instances and their manifests for MCP tools/list + tools/call.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from agent.tools.registry.schema import ToolManifest

if TYPE_CHECKING:
    from agent.tools.implementations.base import SmartDayBaseTool


class ToolRegistry:
    """Thread-safe, hot-reloadable registry of SmartDayBaseTool instances.

    Usage:
        registry = ToolRegistry()
        registry.register(AmapPOITool())
        tool = registry.get("amap_poi_search")
        manifests = registry.list_manifests()  # → sent to LLM via tools/list
    """

    def __init__(self) -> None:
        self._tools: dict[str, "SmartDayBaseTool"] = {}
        self._manifests: dict[str, ToolManifest] = {}
        self._lock = threading.Lock()

    def register(self, tool: "SmartDayBaseTool") -> None:
        """Register a tool and generate its manifest."""
        input_schema: dict = {}
        if tool.args_schema:
            try:
                input_schema = tool.args_schema.model_json_schema()
            except AttributeError:
                input_schema = tool.args_schema.schema()
        manifest = ToolManifest(
            name=tool.name,
            description=tool.description,
            input_schema=input_schema,
            is_read_only=tool.is_read_only,
            cost_model=tool.cost_model,
        )
        with self._lock:
            self._tools[tool.name] = tool
            self._manifests[tool.name] = manifest

    def get(self, name: str) -> "SmartDayBaseTool":
        """Look up a tool by name. Raises KeyError if not found."""
        with self._lock:
            if name not in self._tools:
                available = list(self._tools)
                raise KeyError(
                    f"Tool '{name}' not registered. Available: {available}"
                )
            return self._tools[name]

    def list_manifests(self) -> list[ToolManifest]:
        """Return all tool manifests (for MCP tools/list)."""
        with self._lock:
            return list(self._manifests.values())

    def list_openai_tools(self, strict: bool = False) -> list[dict]:
        """Return all tools in OpenAI function-calling format."""
        with self._lock:
            return [m.to_openai_tool(strict=strict) for m in self._manifests.values()]

    def unregister(self, name: str) -> None:
        """Hot-reload support: remove a tool without restarting."""
        with self._lock:
            self._tools.pop(name, None)
            self._manifests.pop(name, None)

    @property
    def tool_names(self) -> list[str]:
        with self._lock:
            return list(self._tools)
