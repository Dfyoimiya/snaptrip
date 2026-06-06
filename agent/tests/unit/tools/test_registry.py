"""Tests for ToolRegistry and ToolManifest."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from agent.tools.registry.registry import ToolRegistry
from agent.tools.registry.schema import ToolManifest


class TestToolManifest:
    """Test ToolManifest frozen dataclass and serialization."""

    def test_manifest_creation_minimal(self):
        """A minimal manifest can be created."""
        m = ToolManifest(
            name="test_tool",
            description="A test tool. Use when testing.",
            input_schema={},
            is_read_only=True,
            cost_model="free",
        )
        assert m.name == "test_tool"
        assert m.description == "A test tool. Use when testing."
        assert m.input_schema == {}
        assert m.is_read_only is True
        assert m.cost_model == "free"

    def test_manifest_to_openai_tool(self):
        """to_openai_tool returns the correct OpenAI function-calling format."""
        m = ToolManifest(
            name="my_tool",
            description="My test tool. Use for tests.",
            input_schema={"type": "object", "properties": {}},
            is_read_only=False,
            cost_model="per_call:¥0.001",
        )
        result = m.to_openai_tool()
        assert result == {
            "type": "function",
            "function": {
                "name": "my_tool",
                "description": "My test tool. Use for tests.",
                "parameters": {"type": "object", "properties": {}},
            },
        }

    def test_manifest_is_frozen(self):
        """ToolManifest is frozen and cannot be mutated."""
        m = ToolManifest(
            name="test", description="desc", input_schema={},
            is_read_only=True, cost_model="free",
        )
        with pytest.raises(Exception):
            m.name = "new_name"

    def test_manifest_with_complex_schema(self):
        """Manifest handles a complex JSON Schema input_schema."""
        schema = {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude"},
                "lng": {"type": "number", "description": "Longitude"},
            },
            "required": ["lat", "lng"],
        }
        m = ToolManifest(
            name="geo", description="Geocode tool. Converts addresses.",
            input_schema=schema, is_read_only=True, cost_model="free",
        )
        assert m.input_schema == schema
        openai = m.to_openai_tool()
        assert openai["function"]["parameters"] == schema


class TestToolRegistry:
    """Test ToolRegistry thread-safe registry operations."""

    class DummySchema(BaseModel):
        lat: float = 0.0

    def test_register_and_get(self, registry: ToolRegistry, make_mock_tool):
        """Register a tool and retrieve it by name."""
        tool = make_mock_tool("test_tool")
        registry.register(tool)
        retrieved = registry.get("test_tool")
        assert retrieved is tool

    def test_register_creates_manifest(self, registry: ToolRegistry, make_mock_tool):
        """Register creates a ToolManifest entry."""
        tool = make_mock_tool("my_tool", read_only=False, cost_model="mock")
        registry.register(tool)
        manifests = registry.list_manifests()
        assert len(manifests) == 1
        assert manifests[0].name == "my_tool"
        assert manifests[0].is_read_only is False

    def test_list_manifests(self, registry: ToolRegistry, make_mock_tool):
        """list_manifests returns all registered manifests."""
        for i in range(3):
            tool = make_mock_tool(f"tool_{i}")
            registry.register(tool)

        manifests = registry.list_manifests()
        assert len(manifests) == 3
        names = {m.name for m in manifests}
        assert names == {"tool_0", "tool_1", "tool_2"}

    def test_list_openai_tools(self, registry: ToolRegistry, make_mock_tool):
        """list_openai_tools returns OpenAI-compatible dicts."""
        tool = make_mock_tool("my_tool")
        registry.register(tool)

        result = registry.list_openai_tools()
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "my_tool"

    def test_get_unknown_tool_raises(self, registry: ToolRegistry):
        """get with an unregistered name raises KeyError."""
        with pytest.raises(KeyError, match="Tool 'nonexistent' not registered"):
            registry.get("nonexistent")

    def test_get_unknown_with_other_tools_present(self, registry: ToolRegistry, make_mock_tool):
        """Error message includes available tools when one tool is registered."""
        tool = make_mock_tool("existing_tool")
        registry.register(tool)

        with pytest.raises(KeyError) as exc:
            registry.get("missing_tool")
        assert "existing_tool" in str(exc.value)

    def test_unregister_removes_tool(self, registry: ToolRegistry, make_mock_tool):
        """unregister removes the tool and its manifest."""
        tool = make_mock_tool("removable")
        registry.register(tool)
        assert "removable" in registry.tool_names

        registry.unregister("removable")
        assert "removable" not in registry.tool_names
        with pytest.raises(KeyError):
            registry.get("removable")

    def test_unregister_unknown_is_noop(self, registry: ToolRegistry):
        """unregister with unknown name does nothing (no exception)."""
        registry.unregister("ghost")

    def test_register_overwrites_existing(self, registry: ToolRegistry, make_mock_tool):
        """Re-registering the same name overwrites the existing tool."""
        tool1 = make_mock_tool("t1", read_only=True)
        tool2 = make_mock_tool("t1", read_only=False, cost_model="per_call:¥0.001")

        registry.register(tool1)
        registry.register(tool2)

        retrieved = registry.get("t1")
        assert retrieved is tool2

    def test_tool_names_property(self, registry: ToolRegistry, make_mock_tool):
        """tool_names returns names of all registered tools."""
        for name in ["a", "b", "c"]:
            tool = make_mock_tool(name)
            registry.register(tool)

        assert sorted(registry.tool_names) == sorted(["a", "b", "c"])

    def test_tool_names_empty(self, registry: ToolRegistry):
        """An empty registry has an empty tool_names list."""
        assert registry.tool_names == []

    def test_thread_safety_concurrent_register_and_get(self, registry: ToolRegistry):
        """Concurrent register/get operations do not race."""
        errors: list[Exception] = []

        def register_tool(name: str):
            try:
                tool = MagicMock()
                tool.name = name
                tool.description = f"{name}. Use it."
                tool.args_schema = TestToolRegistry.DummySchema
                tool.is_read_only = True
                tool.cost_model = "free"
                registry.register(tool)
                _ = registry.get(name)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=register_tool, args=(f"thread_tool_{i}",))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(registry.tool_names) == 20
