# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 ARCHIVED — TRIP PLANNING AGENT                      ║
# ║  Archived: 2026-06-07                                                        ║
# ║  Reason: Agent repurposed from local trip planning to new domain             ║
# ║  This file is preserved for reference but NOT imported by the framework.     ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

"""Build the default tool registry with all SmartDay tools.

Called once at startup. Tools are registered as singletons in the registry.

Tool inventory:
  - 地理信息: AmapPOI, AmapRouting, AmapGeocode (高德 MCP + REST)
  - 业务执行: MockOrder, MockPayment (预订/支付)
  - 求解器: PymooSolver, Z3Verifier, ORToolsCPSAT (行程优化)
"""

from __future__ import annotations

from agent.tools.implementations.amap_geocode import AmapGeocodeTool
from agent.tools.implementations.amap_poi import AmapPOITool
from agent.tools.implementations.amap_routing import AmapRoutingTool
from agent.tools.implementations.mock_order import MockOrderTool
from agent.tools.implementations.mock_payment import MockPaymentTool
from agent.tools.implementations.or_cpsat import ORToolsCPSATTool
from agent.tools.implementations.pymoo_solver import PymooSolverTool
from agent.tools.implementations.z3_verifier import Z3VerifierTool
from agent.tools.registry.registry import ToolRegistry


def build_registry() -> ToolRegistry:
    """Build and register all SmartDay tools.

    Returns a ToolRegistry with all tools registered.
    Call once at application startup.
    """
    registry = ToolRegistry()
    # 地理信息
    registry.register(AmapPOITool())
    registry.register(AmapRoutingTool())
    registry.register(AmapGeocodeTool())
    # 业务执行
    registry.register(MockOrderTool())
    registry.register(MockPaymentTool())
    # 求解器 (只读，无副作用)
    registry.register(PymooSolverTool())
    registry.register(Z3VerifierTool())
    registry.register(ORToolsCPSATTool())
    return registry
