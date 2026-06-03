"""SmartDay 工具层。

  harness/     — ToolHarness + hook chain (唯一工具调用入口)
  registry/    — ToolRegistry + ToolManifest
  transaction/ — TransactionContext + CompensationRegistry + SagaCoordinator
  tracing/     — AuditStore + ToolTracer
  implementations/ — SmartDayBaseTool 子类
"""

# ── 新架构导出 ──
from agent.tools.implementations.base import SmartDayBaseTool, ToolResult
from agent.tools.harness.harness import ToolHarness
from agent.tools.harness.context import SessionContext, ToolExecutionContext
from agent.tools.registry.registry import ToolRegistry
from agent.tools.registry.schema import ToolManifest
from agent.tools.transaction.context import TransactionContext, TxStatus
from agent.tools.transaction.compensation import CompensationAction, CompensationRegistry
from agent.tools.transaction.saga import SagaCoordinator
from agent.tools.tracing.audit_log import AuditEntry, AuditStore
from agent.tools.tracing.tracer import ToolTracer
from agent.tools.bootstrap import build_registry

__all__ = [
    "AuditEntry",
    "AuditStore",
    "CompensationAction",
    "CompensationRegistry",
    "SagaCoordinator",
    "SessionContext",
    "SmartDayBaseTool",
    "ToolExecutionContext",
    "ToolHarness",
    "ToolManifest",
    "ToolRegistry",
    "ToolResult",
    "ToolTracer",
    "TransactionContext",
    "TxStatus",
    "build_registry",
]
