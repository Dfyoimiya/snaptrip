"""seed CS agent RBAC permissions and roles

Revision ID: m2b3c4d5e6f7
Revises: l1a2b3c4d5e6
Create Date: 2026-06-17

This migration adds:
  - CS Agent and CS Manager roles
  - 12 CS-specific permissions
  - Assigns CS permissions to CS Manager
"""

from collections.abc import Sequence

from alembic import op

revision: str = "m2b3c4d5e6f7"
down_revision: str | None = "l1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CS_PERMISSIONS = [
    ("cs:tickets:read",      "查看工单列表",       "/admin/cs/tickets",          "GET"),
    ("cs:tickets:write",     "管理工单",           "/admin/cs/tickets/*",        "PUT"),
    ("cs:tickets:assign",    "指派工单",           "/admin/cs/tickets/*/assign", "POST"),
    ("cs:tickets:resolve",   "解决工单",           "/admin/cs/tickets/*/resolve","POST"),
    ("cs:messages:read",     "查看聊天消息",        "/admin/cs/tickets/*/messages","GET"),
    ("cs:messages:write",    "发送聊天消息",        "/admin/cs/tickets/*/messages","POST"),
    ("cs:agents:read",       "查看坐席列表",        "/admin/cs/agents",           "GET"),
    ("cs:agents:write",      "修改坐席状态",        "/admin/cs/agents/me/*",      "PUT"),
    ("cs:stats:read",        "查看客服统计",        "/admin/cs/stats",            "GET"),
    ("cs:notifications:read","查看通知",           "/admin/cs/notifications",    "GET"),
    ("cs:notifications:write","标记通知已读",       "/admin/cs/notifications/*",  "PUT"),
    ("cs:stream:read",       "订阅 SSE 消息流",     "/admin/cs/tickets/*/stream", "GET"),
]


def upgrade() -> None:
    # ── CS Agent 角色 ──
    op.execute("""
        INSERT INTO ums_roles (id, name, description, status, sort) VALUES
        (gen_random_uuid(), 'cs_agent',   '客服坐席 — 处理工单、回复消息',      1, 7),
        (gen_random_uuid(), 'cs_manager', '客服主管 — 管理工单分配、查看统计', 1, 8)
    """)

    # ── CS 权限 ──
    for name, desc, resource, method in CS_PERMISSIONS:
        op.execute(
            f"INSERT INTO ums_permissions (id, name, description, resource, method, status) "
            f"VALUES (gen_random_uuid(), '{name}', '{desc}', '{resource}', '{method}', 1)"
        )

    # ── CS Manager 获得所有 CS 权限 ──
    op.execute("""
        INSERT INTO ums_role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM ums_roles r, ums_permissions p
        WHERE r.name = 'cs_manager' AND p.name LIKE 'cs:%'
    """)

    # ── CS Agent 获得基础工单+消息+通知权限 ──
    agent_perms = [
        "cs:tickets:read", "cs:tickets:assign", "cs:tickets:resolve",
        "cs:messages:read", "cs:messages:write",
        "cs:agents:read", "cs:agents:write",
        "cs:notifications:read", "cs:notifications:write",
        "cs:stream:read",
    ]
    perm_list = ", ".join(f"'{p}'" for p in agent_perms)
    op.execute(
        f"INSERT INTO ums_role_permissions (id, role_id, permission_id) "
        f"SELECT gen_random_uuid(), r.id, p.id "
        f"FROM ums_roles r, ums_permissions p "
        f"WHERE r.name = 'cs_agent' AND p.name IN ({perm_list})"
    )

    # ── super_admin 也获得 CS 权限 ──
    op.execute("""
        INSERT INTO ums_role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM ums_roles r, ums_permissions p
        WHERE r.name = 'super_admin' AND p.name LIKE 'cs:%'
    """)


def downgrade() -> None:
    # Remove CS role-permission assignments
    op.execute("""
        DELETE FROM ums_role_permissions WHERE permission_id IN (
            SELECT id FROM ums_permissions WHERE name LIKE 'cs:%'
        )
    """)
    # Remove CS permissions
    op.execute("DELETE FROM ums_permissions WHERE name LIKE 'cs:%'")
    # Remove CS roles
    op.execute("DELETE FROM ums_roles WHERE name IN ('cs_agent', 'cs_manager')")
