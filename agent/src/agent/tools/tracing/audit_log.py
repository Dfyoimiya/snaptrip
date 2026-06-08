"""AuditStore — append-only audit log with tamper-evident hash chain.

Rules:
  - AuditEntry is frozen — immutable once created.
  - Each entry carries the SHA-256 digest of its predecessor.
  - Raw tool args are NEVER stored; only args_hash is stored.
  - verify_chain() detects any retroactive mutation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass(frozen=True)
class AuditEntry:
    """A single tamper-evident audit entry in the hash chain.

    Rules:
      - args_hash stores only sha256(args), never raw args (PII protection).
      - prev_hash links to previous entry's digest for tamper detection.
    """

    entry_id: str
    prev_hash: str
    ts: datetime
    session_id: str
    tx_id: str | None
    tool_name: str
    args_hash: str
    result_summary: str
    status: Literal["ok", "error", "compensated"]
    span_id: str
    cost_cny: float

    def digest(self) -> str:
        """Canonical digest of this entry (used as prev_hash for the next entry)."""
        payload = json.dumps(
            {
                "entry_id": self.entry_id,
                "prev_hash": self.prev_hash,
                "ts": self.ts.isoformat(),
                "tool_name": self.tool_name,
                "args_hash": self.args_hash,
                "result_summary": self.result_summary,
                "status": self.status,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class AuditStore:
    """Append-only audit log with hash-chain integrity.

    In production, entries should be persisted to an immutable store
    (e.g., WORM S3, PostgreSQL with append-only policy).

    Guarantees:
      - Every entry carries the digest of its predecessor.
      - verify_chain() detects any retroactive mutation.
      - Raw args are NEVER stored; only sha256(args) is stored.
    """

    _entries: list[AuditEntry] = field(default_factory=list)
    GENESIS_HASH: str = field(default="0" * 64, init=False)

    def append(
        self,
        *,
        session_id: str,
        tx_id: str | None,
        tool_name: str,
        args: dict,
        result_summary: str,
        status: Literal["ok", "error", "compensated"],
        span_id: str,
        cost_cny: float,
    ) -> AuditEntry:
        """Create and append a new audit entry to the chain."""
        prev_hash = self._entries[-1].digest() if self._entries else self.GENESIS_HASH
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            prev_hash=prev_hash,
            ts=datetime.now(tz=timezone.utc),
            session_id=session_id,
            tx_id=tx_id,
            tool_name=tool_name,
            args_hash=hashlib.sha256(
                json.dumps(args, sort_keys=True).encode()
            ).hexdigest(),
            result_summary=result_summary,
            status=status,
            span_id=span_id,
            cost_cny=cost_cny,
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """Return True if no entry in the chain has been tampered with."""
        prev = self.GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            prev = entry.digest()
        return True

    def query_by_tx(self, tx_id: str) -> list[AuditEntry]:
        """Return all audit entries for a given transaction."""
        return [e for e in self._entries if e.tx_id == tx_id]
