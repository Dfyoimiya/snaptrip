"""Mock Server — in-memory state store (zero-dependency, restart clears all)."""

from __future__ import annotations

import uuid
from collections import defaultdict

# ── Users & Sessions ──
_users: dict[str, dict] = {}          # user_id → {user_id, phone, password_hash, nickname, avatar, ...}
_sessions: dict[str, dict] = {}       # token → {user_id, role, expires_at}
_admin_users: dict[str, dict] = {}    # admin_id → {id, username, password, roles, ...}
_admin_sessions: dict[str, dict] = {} # token → {admin_id, roles, expires_at}

# ── Commerce ──
_carts: dict[str, list[dict]] = {}             # user_id → [CartItem]
_orders: dict[str, dict] = {}                   # order_id → Order
_order_items: dict[str, list[dict]] = {}        # order_id → [OrderItem]
_order_status_logs: dict[str, list[dict]] = {}  # order_id → [StatusLog]
_addresses: dict[str, list[dict]] = {}          # user_id → [Address]
_favorites: dict[str, list[dict]] = {}          # user_id → [Favorite]
_reviews: list[dict] = []                       # [Review]
_search_history: dict[str, list[dict]] = {}     # user_id → [{keyword, created_at}]

# ── ID counters ──
_counters: dict[str, int] = defaultdict(int)


def next_id(prefix: str) -> str:
    _counters[prefix] += 1
    return f"{prefix}-{_counters[prefix]:04d}"


def gen_uuid() -> str:
    return uuid.uuid4().hex[:12]


def gen_order_no() -> str:
    from datetime import datetime
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    seq = _counters["ORDER"]
    return f"{ts}{seq:04d}"


def reset_all():
    """Clear all in-memory state (useful for test teardown)."""
    for d in [_users, _sessions, _admin_users, _admin_sessions, _carts, _orders,
              _order_items, _order_status_logs, _addresses, _favorites, _reviews,
              _search_history, _counters]:
        d.clear()
    _reviews.clear()
