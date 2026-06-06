"""Tracing layer — event emission and audit log.

tracer.py: ToolTracer wraps LangChain's BaseCallbackHandler for tool lifecycle events.
audit_log.py: AuditStore with tamper-evident hash chain.
"""

from agent.tools.tracing.audit_log import AuditEntry, AuditStore
from agent.tools.tracing.tracer import ToolTracer

__all__ = ["AuditEntry", "AuditStore", "ToolTracer"]
