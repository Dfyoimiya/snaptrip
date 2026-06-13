"""Tests for build_registry()."""

from __future__ import annotations

from agent.tools.bootstrap import build_commerce_registry, build_admin_registry, build_full_registry


class TestBuildRegistry:
    """Tests for build_registry factory functions."""

    def test_returns_tool_registry(self):
        """build_full_registry returns a ToolRegistry instance."""
        registry = build_full_registry()
        from agent.tools.registry.registry import ToolRegistry
        assert isinstance(registry, ToolRegistry)

    def test_registers_all_twelve_tools(self):
        """build_full_registry registers exactly 12 tools (6 commerce + 6 admin)."""
        registry = build_full_registry()
        expected = {
            "cancel_order",
            "get_coupons",
            "get_product_detail",
            "query_order",
            "search_knowledge",
            "search_products",
            "analyze_coupon_effect",
            "generate_product_desc",
            "get_low_stock_alert",
            "get_member_insights",
            "get_order_trends",
            "get_sales_report",
        }
        assert set(registry.tool_names) == expected

    def test_commerce_registry_has_six_tools(self):
        """Commerce registry has exactly 6 tools."""
        registry = build_commerce_registry()
        assert len(registry.tool_names) == 6

    def test_admin_registry_has_six_tools(self):
        """Admin registry has exactly 6 tools."""
        registry = build_admin_registry()
        assert len(registry.tool_names) == 6

    def test_all_tools_look_up_ok(self):
        """Every registered tool can be fetched by name without error."""
        registry = build_full_registry()
        for name in registry.tool_names:
            tool = registry.get(name)
            assert tool is not None
            assert tool.name == name

    def test_all_tools_have_args_schema(self):
        """Every registered tool has a non-None args_schema."""
        registry = build_full_registry()
        for name in registry.tool_names:
            tool = registry.get(name)
            assert tool.args_schema is not None, f"{name} missing args_schema"

    def test_manifests_produced(self):
        """Every registered tool produces a valid manifest."""
        registry = build_full_registry()
        manifests = registry.list_manifests()
        assert len(manifests) == len(registry.tool_names)
        for m in manifests:
            assert m.name
            assert m.description
            assert isinstance(m.input_schema, dict)

    def test_openai_tools_format(self):
        """list_openai_tools returns valid OpenAI function-calling format."""
        registry = build_full_registry()
        tools = registry.list_openai_tools()
        assert len(tools) == 12
        for t in tools:
            assert t["type"] == "function"
            assert "name" in t["function"]
            assert "description" in t["function"]
            assert "parameters" in t["function"]

    def test_read_only_tools(self):
        """Commerce search tools are read-only; mutation tools are not."""
        registry = build_full_registry()
        read_only = {"search_products", "get_product_detail", "get_coupons",
                     "query_order", "search_knowledge", "get_sales_report",
                     "get_order_trends", "get_member_insights", "get_low_stock_alert",
                     "analyze_coupon_effect"}
        mutable = {"cancel_order", "generate_product_desc"}

        for name in read_only:
            tool = registry.get(name)
            assert tool.is_read_only is True, f"{name} should be read-only"

        for name in mutable:
            tool = registry.get(name)
            assert tool.is_read_only is False, f"{name} should be mutable"
