"""Tests for build_registry()."""

from __future__ import annotations

from agent.tools.bootstrap import build_registry


class TestBuildRegistry:
    """Tests for build_registry factory function."""

    def test_returns_tool_registry(self):
        """build_registry returns a ToolRegistry instance."""
        registry = build_registry()
        from agent.tools.registry.registry import ToolRegistry
        assert isinstance(registry, ToolRegistry)

    def test_registers_all_eight_tools(self):
        """build_registry registers exactly 8 SmartDay tools."""
        registry = build_registry()
        expected = {
            "amap_poi_search",
            "amap_routing",
            "amap_geocode",
            "mock_order_create",
            "mock_payment_charge",
            "pymoo_solve_itinerary",
            "z3_verify_feasibility",
            "ortools_cpsat_solve",
        }
        assert set(registry.tool_names) == expected

    def test_all_tools_look_up_ok(self):
        """Every registered tool can be fetched by name without error."""
        registry = build_registry()
        for name in registry.tool_names:
            tool = registry.get(name)
            assert tool is not None
            assert tool.name == name

    def test_all_tools_have_args_schema(self):
        """Every registered tool has a non-None args_schema."""
        registry = build_registry()
        for name in registry.tool_names:
            tool = registry.get(name)
            assert tool.args_schema is not None, f"{name} missing args_schema"

    def test_manifests_produced(self):
        """Every registered tool produces a valid manifest."""
        registry = build_registry()
        manifests = registry.list_manifests()
        assert len(manifests) == len(registry.tool_names)
        for m in manifests:
            assert m.name
            assert m.description
            assert isinstance(m.input_schema, dict)

    def test_openai_tools_format(self):
        """list_openai_tools returns valid OpenAI function-calling format."""
        registry = build_registry()
        tools = registry.list_openai_tools()
        assert len(tools) == 8
        for t in tools:
            assert t["type"] == "function"
            assert "name" in t["function"]
            assert "description" in t["function"]
            assert "parameters" in t["function"]

    def test_read_only_tools(self):
        """Search and geocode tools are read-only; order/payment are not."""
        registry = build_registry()
        read_only = {"amap_poi_search", "amap_routing", "amap_geocode",
                     "pymoo_solve_itinerary", "z3_verify_feasibility", "ortools_cpsat_solve"}
        mutable = {"mock_order_create", "mock_payment_charge"}

        for name in read_only:
            tool = registry.get(name)
            assert tool.is_read_only is True, f"{name} should be read-only"

        for name in mutable:
            tool = registry.get(name)
            assert tool.is_read_only is False, f"{name} should be mutable"
