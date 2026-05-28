"""create commerce rbac tables

Revision ID: a1b2c3d4e5f6
Revises: 7c7974cb12bd
Create Date: 2026-05-26 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7c7974cb12bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 1 — 创建 RBAC 表 + 系统角色权限 + 管理账号"""

    # ── ums_roles ──
    op.create_table(
        'ums_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('sort', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_ums_roles_name'),
    )

    # ── ums_permissions ──
    op.create_table(
        'ums_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('resource', sa.String(128), nullable=False),
        sa.Column('method', sa.String(16), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── ums_role_permissions ──
    op.create_table(
        'ums_role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['ums_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['ums_permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', 'role_id', 'permission_id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    # ── ums_user_roles ──
    op.create_table(
        'ums_user_roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['role_id'], ['ums_roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uq_user_role'),
    )
    op.create_index('ix_ums_user_roles_user_id', 'ums_user_roles', ['user_id'])
    op.create_index('ix_ums_user_roles_role_id', 'ums_user_roles', ['role_id'])

    # ── Seed: 系统角色 ──
    seed_roles = """
    INSERT INTO ums_roles (id, name, description, status, sort) VALUES
    (gen_random_uuid(), 'super_admin',     '超级管理员 — 拥有所有权限',            1, 0),
    (gen_random_uuid(), 'product_admin',   '商品管理员 — 管理商品/分类/品牌',       1, 1),
    (gen_random_uuid(), 'order_admin',     '订单管理员 — 管理订单/退货',           1, 2),
    (gen_random_uuid(), 'member_admin',    '会员管理员 — 管理会员/积分',           1, 3),
    (gen_random_uuid(), 'promotion_admin', '营销管理员 — 管理优惠券/秒杀/活动',      1, 4),
    (gen_random_uuid(), 'content_admin',   '内容管理员 — 管理轮播/专题/帮助',       1, 5),
    (gen_random_uuid(), 'viewer',          '只读角色 — 仅查看, 无编辑权限',         1, 6);
    """
    op.execute(seed_roles)

    # ── Seed: 系统权限 (按模块划分) ──
    seed_permissions = """
    INSERT INTO ums_permissions (id, name, description, resource, method, status) VALUES
    -- 商品分类
    (gen_random_uuid(), 'category:list',   '查看分类列表',    '/admin/categories',          'GET',    1),
    (gen_random_uuid(), 'category:create', '创建分类',       '/admin/categories',          'POST',   1),
    (gen_random_uuid(), 'category:update', '编辑分类',       '/admin/categories/{id}',     'PUT',    1),
    (gen_random_uuid(), 'category:delete', '删除分类',       '/admin/categories/{id}',     'DELETE', 1),
    -- 商品品牌
    (gen_random_uuid(), 'brand:list',      '查看品牌列表',    '/admin/brands',              'GET',    1),
    (gen_random_uuid(), 'brand:create',    '创建品牌',       '/admin/brands',              'POST',   1),
    (gen_random_uuid(), 'brand:update',    '编辑品牌',       '/admin/brands/{id}',         'PUT',    1),
    (gen_random_uuid(), 'brand:delete',    '删除品牌',       '/admin/brands/{id}',         'DELETE', 1),
    -- 商品管理
    (gen_random_uuid(), 'product:list',    '查看商品列表',    '/admin/products',            'GET',    1),
    (gen_random_uuid(), 'product:create',  '创建商品',       '/admin/products',            'POST',   1),
    (gen_random_uuid(), 'product:update',  '编辑商品',       '/admin/products/{id}',       'PUT',    1),
    (gen_random_uuid(), 'product:delete',  '删除商品',       '/admin/products/{id}',       'DELETE', 1),
    (gen_random_uuid(), 'product:status',  '上下架商品',      '/admin/products/{id}/status', 'PATCH', 1),
    (gen_random_uuid(), 'product:verify',  '审核商品',       '/admin/products/{id}/verify', 'PATCH', 1),
    -- 订单管理
    (gen_random_uuid(), 'order:list',      '查看订单列表',    '/admin/orders',              'GET',    1),
    (gen_random_uuid(), 'order:detail',    '查看订单详情',    '/admin/orders/{id}',         'GET',    1),
    (gen_random_uuid(), 'order:close',     '关闭订单',       '/admin/orders/{id}/close',   'POST',   1),
    (gen_random_uuid(), 'order:delivery',  '订单发货',       '/admin/orders/{id}/delivery', 'POST',  1),
    (gen_random_uuid(), 'order:modify',    '修改订单',       '/admin/orders/{id}/modify*',  'POST',   1),
    -- 退货管理
    (gen_random_uuid(), 'return:list',     '查看退单列表',    '/admin/returns',             'GET',    1),
    (gen_random_uuid(), 'return:handle',   '处理退单',       '/admin/returns/{id}/*',      'POST',   1),
    -- 会员管理
    (gen_random_uuid(), 'member:list',     '查看会员列表',    '/admin/members',             'GET',    1),
    (gen_random_uuid(), 'member:detail',   '查看会员详情',    '/admin/members/{id}',        'GET',    1),
    (gen_random_uuid(), 'member:status',   '启用/封禁会员',   '/admin/members/{id}/status',  'PATCH', 1),
    (gen_random_uuid(), 'member:integration', '修改积分',    '/admin/members/{id}/integration', 'PUT', 1),
    -- 优惠券
    (gen_random_uuid(), 'coupon:list',     '查看优惠券列表',  '/admin/coupons',             'GET',    1),
    (gen_random_uuid(), 'coupon:create',   '创建优惠券',     '/admin/coupons',             'POST',   1),
    (gen_random_uuid(), 'coupon:update',   '编辑优惠券',     '/admin/coupons/{id}',        'PUT',    1),
    (gen_random_uuid(), 'coupon:delete',   '删除优惠券',     '/admin/coupons/{id}',        'DELETE', 1),
    -- 秒杀
    (gen_random_uuid(), 'flash:list',      '查看秒杀列表',    '/admin/flash-promotions',    'GET',    1),
    (gen_random_uuid(), 'flash:manage',    '管理秒杀',       '/admin/flash-promotions/*',  'POST',   1),
    -- 内容
    (gen_random_uuid(), 'banner:list',     '查看轮播图',     '/admin/banners',             'GET',    1),
    (gen_random_uuid(), 'banner:manage',   '管理轮播图',     '/admin/banners/*',           'POST',   1),
    (gen_random_uuid(), 'cms:list',        '查看内容',       '/admin/cms*',                'GET',    1),
    (gen_random_uuid(), 'cms:manage',      '管理内容',       '/admin/cms*',                'POST',   1),
    -- 统计
    (gen_random_uuid(), 'stats:view',      '查看统计报表',    '/admin/stats/*',             'GET',    1),
    -- 系统
    (gen_random_uuid(), 'system:role',     '角色管理',       '/admin/roles*',              'ALL',    1),
    (gen_random_uuid(), 'system:user',     '用户管理',       '/admin/users*',              'ALL',    1);
    """
    op.execute(seed_permissions)

    # ── Seed: 为 super_admin 授予所有权限 ──
    seed_super_admin_permissions = """
    INSERT INTO ums_role_permissions (id, role_id, permission_id)
    SELECT gen_random_uuid(), r.id, p.id
    FROM ums_roles r, ums_permissions p
    WHERE r.name = 'super_admin';
    """
    op.execute(seed_super_admin_permissions)

    # ── Seed: 为 viewer 授予只读权限 ──
    seed_viewer_permissions = """
    INSERT INTO ums_role_permissions (id, role_id, permission_id)
    SELECT gen_random_uuid(), r.id, p.id
    FROM ums_roles r, ums_permissions p
    WHERE r.name = 'viewer' AND p.method = 'GET';
    """
    op.execute(seed_viewer_permissions)


def downgrade() -> None:
    """回滚 — 删除 RBAC 表"""
    op.drop_index('ix_ums_user_roles_role_id', table_name='ums_user_roles')
    op.drop_index('ix_ums_user_roles_user_id', table_name='ums_user_roles')
    op.drop_table('ums_user_roles')
    op.drop_table('ums_role_permissions')
    op.drop_table('ums_permissions')
    op.drop_table('ums_roles')
