"""Tests for AuditEntry and AuditStore."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent.tools.tracing.audit_log import AuditEntry, AuditStore


class TestAuditEntry:
    """Tests for AuditEntry frozen dataclass."""

    def test_entry_creation(self):
        """An AuditEntry can be created with all fields."""
        ts = datetime.now(tz=timezone.utc)
        entry = AuditEntry(
            entry_id="entry-1",
            prev_hash="0" * 64,
            ts=ts,
            session_id="s1",
            tx_id="tx-1",
            tool_name="test_tool",
            args_hash="abc123",
            result_summary="completed",
            status="ok",
            span_id="span-1",
            cost_cny=5.0,
        )
        assert entry.entry_id == "entry-1"
        assert entry.prev_hash == "0" * 64
        assert entry.tool_name == "test_tool"
        assert entry.status == "ok"
        assert entry.cost_cny == 5.0

    def test_entry_is_frozen(self):
        """AuditEntry is frozen and cannot be mutated."""
        ts = datetime.now(tz=timezone.utc)
        entry = AuditEntry(
            entry_id="e", prev_hash="0" * 64, ts=ts,
            session_id="s", tx_id=None, tool_name="t",
            args_hash="a", result_summary="r", status="ok",
            span_id="s", cost_cny=0.0,
        )
        with pytest.raises(Exception):
            entry.args_hash = "new"

    def test_digest_is_deterministic(self):
        """digest() produces the same value for the same entry."""
        ts = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        entry1 = AuditEntry(
            entry_id="e1", prev_hash="0" * 64, ts=ts,
            session_id="s", tx_id=None, tool_name="t",
            args_hash="a", result_summary="r", status="ok",
            span_id="s", cost_cny=0.0,
        )
        entry2 = AuditEntry(
            entry_id="e1", prev_hash="0" * 64, ts=ts,
            session_id="s", tx_id=None, tool_name="t",
            args_hash="a", result_summary="r", status="ok",
            span_id="s", cost_cny=0.0,
        )
        assert entry1.digest() == entry2.digest()

    def test_digest_changes_on_mutation(self):
        """digest() changes when any field changes."""
        ts = datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc)
        entry1 = AuditEntry(
            entry_id="e1", prev_hash="0" * 64, ts=ts,
            session_id="s", tx_id=None, tool_name="t",
            args_hash="a", result_summary="r", status="ok",
            span_id="s", cost_cny=0.0,
        )
        entry2 = AuditEntry(
            entry_id="e1", prev_hash="0" * 64, ts=ts,
            session_id="s", tx_id=None, tool_name="t",
            args_hash="different_hash", result_summary="r", status="ok",
            span_id="s", cost_cny=0.0,
        )
        assert entry1.digest() != entry2.digest()


class TestAuditStore:
    """Tests for AuditStore append-only log with hash chain."""

    def test_empty_store_verifies(self, audit_store: AuditStore):
        """An empty store passes chain verification."""
        assert audit_store.verify_chain() is True

    def test_single_entry_verifies(self, audit_store: AuditStore):
        """A single entry passes chain verification."""
        entry = audit_store.append(
            session_id="s1", tx_id=None,
            tool_name="t", args={}, result_summary="ok",
            status="ok", span_id="s1", cost_cny=0.0,
        )
        assert audit_store.verify_chain() is True
        assert entry.prev_hash == audit_store.GENESIS_HASH

    def test_chain_linking(self, audit_store: AuditStore):
        """Each entry links to previous entry's digest."""
        e1 = audit_store.append(
            session_id="s1", tx_id=None,
            tool_name="t", args={}, result_summary="ok1",
            status="ok", span_id="s1", cost_cny=0.0,
        )
        e2 = audit_store.append(
            session_id="s1", tx_id=None,
            tool_name="t", args={}, result_summary="ok2",
            status="ok", span_id="s2", cost_cny=0.0,
        )
        assert e2.prev_hash == e1.digest()
        assert audit_store.verify_chain() is True

    def test_multi_entry_chain_verifies(self, audit_store: AuditStore):
        """A chain with 10 entries passes verification."""
        for i in range(10):
            audit_store.append(
                session_id="s1", tx_id=f"tx-{i}",
                tool_name="t", args={}, result_summary=f"ok-{i}",
                status="ok", span_id=f"s{i}", cost_cny=0.0,
            )
        assert audit_store.verify_chain() is True

    def test_tampered_chain_detected(self, audit_store: AuditStore):
        """verify_chain returns False if an entry is tampered with."""
        for i in range(5):
            audit_store.append(
                session_id="s1", tx_id="tx",
                tool_name="t", args={}, result_summary=f"ok-{i}",
                status="ok", span_id=f"s{i}", cost_cny=0.0,
            )

        # Tamper with the first entry by directly modifying it
        # (Frozen dataclass prevents attribute mutation, but we can replace the whole entry)
        old_entry = audit_store._entries[0]
        ts = datetime.now(tz=timezone.utc)
        tampered = AuditEntry(
            entry_id=old_entry.entry_id,
            prev_hash=old_entry.prev_hash,
            ts=ts,
            session_id=old_entry.session_id,
            tx_id=old_entry.tx_id,
            tool_name=old_entry.tool_name,
            args_hash="TAMPERED_HASH",
            result_summary="TAMPERED",
            status=old_entry.status,
            span_id=old_entry.span_id,
            cost_cny=old_entry.cost_cny,
        )
        audit_store._entries[0] = tampered

        assert audit_store.verify_chain() is False

    def test_query_by_tx(self, audit_store: AuditStore):
        """query_by_tx returns entries for a specific transaction."""
        for i in range(3):
            audit_store.append(
                session_id="s1", tx_id="tx-a",
                tool_name="t", args={}, result_summary=f"a-{i}",
                status="ok", span_id=f"s{i}", cost_cny=0.0,
            )
        for i in range(2):
            audit_store.append(
                session_id="s1", tx_id="tx-b",
                tool_name="t", args={}, result_summary=f"b-{i}",
                status="ok", span_id=f"s{3+i}", cost_cny=0.0,
            )

        a_entries = audit_store.query_by_tx("tx-a")
        b_entries = audit_store.query_by_tx("tx-b")
        none_entries = audit_store.query_by_tx("non-existent")

        assert len(a_entries) == 3
        assert len(b_entries) == 2
        assert len(none_entries) == 0

    def test_args_hash_not_raw_args(self, audit_store: AuditStore):
        """Raw args are hashed, never stored directly."""
        sensitive_args = {"credit_card": "4111-1111-1111-1111", "cvv": "123"}
        entry = audit_store.append(
            session_id="s1", tx_id=None,
            tool_name="payment", args=sensitive_args,
            result_summary="ok", status="ok", span_id="s1", cost_cny=100.0,
        )
        # args_hash is a hex string, not containing raw PII
        assert "4111" not in entry.args_hash
        assert len(entry.args_hash) == 64  # full sha256
