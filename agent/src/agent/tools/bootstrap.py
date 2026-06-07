# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Tool Registry Bootstrap
# ────────────────────────────────────────────────────────────────────────────
# Build and populate the ToolRegistry with your domain tools.
#
# The original trip-planning registry (8 tools: amap_*, mock_*, solvers)
# has been archived to _archived/tools/bootstrap.py.
#
# Usage:
#   registry = build_registry()
#   harness = ToolHarness(registry=registry)
#
# Archived: 2026-06-07
# ────────────────────────────────────────────────────────────────────────────

from agent.tools.registry.registry import ToolRegistry


def build_registry() -> ToolRegistry:
    """Create and populate a ToolRegistry with domain tools.

    TODO: Register your tool implementations here. Example:
        from your_tools import YourTool
        registry.register(YourTool())
    """
    registry = ToolRegistry()

    # ── Register your tools below ────────────────────────────────────────
    # registry.register(YourGeocodeTool())
    # registry.register(YourSearchTool())
    # registry.register(YourSolverTool())
    # ...

    return registry
