"""Tests for TransactionContext and TxStatus."""

from __future__ import annotations

import pytest

from agent.tools.transaction.context import TransactionContext, TxStatus, ToolCallRecord


class TestTxStatus:
    """Tests for TxStatus enum."""

    def test_enum_values(self):
        assert TxStatus.ACTIVE.value == "active"
        assert TxStatus.COMMITTED.value == "committed"
        assert TxStatus.ROLLING_BACK.value == "rolling_back"
        assert TxStatus.ROLLED_BACK.value == "rolled_back"


class TestTransactionContext:
    """Tests for TransactionContext."""

    def test_new_creates_transaction(self):
        """TransactionContext.new() creates a valid ACTIVE transaction."""
        tx = TransactionContext.new(session_id="s1")
        assert tx.tx_id is not None
        assert len(tx.tx_id) > 0
        assert tx.session_id == "s1"
        assert tx.status == TxStatus.ACTIVE
        assert tx.calls == []

    def test_unique_tx_ids(self):
        """Each new transaction gets a unique tx_id."""
        tx1 = TransactionContext.new(session_id="s1")
        tx2 = TransactionContext.new(session_id="s1")
        assert tx1.tx_id != tx2.tx_id

    def test_begin_call_adds_record(self):
        """begin_call adds a ToolCallRecord."""
        tx = TransactionContext.new(session_id="s1")
        rec = tx.begin_call(tool_name="tool_a", args_hash="abc123")
        assert rec.tool_name == "tool_a"
        assert rec.args_hash == "abc123"
        assert rec.seq == 0
        assert len(tx.calls) == 1

    def test_call_sequence_increments(self):
        """Each call increments the sequence counter."""
        tx = TransactionContext.new(session_id="s1")
        r1 = tx.begin_call(tool_name="t1", args_hash="h1")
        r2 = tx.begin_call(tool_name="t2", args_hash="h2")
        assert r1.seq == 0
        assert r2.seq == 1

    def test_calls_returns_copy(self):
        """calls property returns a copy, not a reference."""
        tx = TransactionContext.new(session_id="s1")
        tx.begin_call(tool_name="t1", args_hash="h1")
        calls = tx.calls
        calls.append(ToolCallRecord(seq=99, tool_name="fake", args_hash="ff", cost_cny=0))
        assert len(tx.calls) == 1  # Original unchanged

    def test_begin_call_fails_on_non_active(self):
        """begin_call raises RuntimeError if tx is not ACTIVE."""
        tx = TransactionContext.new(session_id="s1")
        tx.status = TxStatus.COMMITTED
        with pytest.raises(RuntimeError, match="cannot attach"):
            tx.begin_call(tool_name="t1", args_hash="h1")

    def test_begin_call_fails_on_rolling_back(self):
        tx = TransactionContext.new(session_id="s1")
        tx.status = TxStatus.ROLLING_BACK
        with pytest.raises(RuntimeError):
            tx.begin_call(tool_name="t1", args_hash="h1")

    def test_begin_call_fails_on_rolled_back(self):
        tx = TransactionContext.new(session_id="s1")
        tx.status = TxStatus.ROLLED_BACK
        with pytest.raises(RuntimeError):
            tx.begin_call(tool_name="t1", args_hash="h1")

    def test_cost_cny_is_recorded(self):
        """begin_call records cost_cny."""
        tx = TransactionContext.new(session_id="s1")
        rec = tx.begin_call(tool_name="t1", args_hash="h1", cost_cny=15.50)
        assert rec.cost_cny == 15.50
