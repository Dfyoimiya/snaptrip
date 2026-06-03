"""TransactionContext — per-session transaction state.

Each session has at most one active transaction. Tool calls are
attached to the active transaction by TxBeginHook.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class TxStatus(str, Enum):
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class ToolCallRecord:
    """Record of a tool call within a transaction (for rollback ordering)."""

    seq: int
    tool_name: str
    args_hash: str
    cost_cny: float


@dataclass
class TransactionContext:
    """Per-session transaction.

    Tool calls are appended in forward order and compensated in
    reverse (LIFO) order via CompensationRegistry.
    """

    tx_id: str
    session_id: str
    status: TxStatus = TxStatus.ACTIVE
    _calls: list[ToolCallRecord] = field(default_factory=list, init=False)
    _call_seq: int = field(default=0, init=False)

    @classmethod
    def new(cls, session_id: str) -> TransactionContext:
        return cls(tx_id=str(uuid.uuid4()), session_id=session_id)

    def begin_call(self, *, tool_name: str, args_hash: str, cost_cny: float = 0.0) -> ToolCallRecord:
        """Record the start of a tool call in this transaction."""
        if self.status != TxStatus.ACTIVE:
            raise RuntimeError(
                f"Transaction {self.tx_id} is {self.status.value}; "
                "cannot attach new tool calls."
            )
        rec = ToolCallRecord(
            seq=self._call_seq,
            tool_name=tool_name,
            args_hash=args_hash,
            cost_cny=cost_cny,
        )
        self._calls.append(rec)
        self._call_seq += 1
        return rec

    @property
    def calls(self) -> list[ToolCallRecord]:
        return list(self._calls)
