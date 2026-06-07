# ────────────────────────────────────────────────────────────────────────────
# 🔵 FRAMEWORK — Tool Implementations
# ────────────────────────────────────────────────────────────────────────────
# Trip-specific implementations (amap_*, mock_*, or_cpsat, pymoo_solver,
# z3_verifier) have been archived to _archived/tools/implementations/.
#
# SmartDayBaseTool in base.py is the base class for all tools.
# Create your own tool implementations in this package.
# Archived: 2026-06-07
# ────────────────────────────────────────────────────────────────────────────

from agent.tools.implementations.base import SmartDayBaseTool, ToolResult

__all__ = ["SmartDayBaseTool", "ToolResult"]
