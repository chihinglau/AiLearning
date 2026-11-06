"""RBAC 数据表上线与存量回填（P2-01，D-03 §9.1/§9.2 阶段 A/B）。

Revision ID: m3n4o5p6q7r8
Revises: l2g3h4i5j6k7
Create Date: 2026-11-07

升级内容：
1. 创建 `roles` / `permissions` / `role_permissions` / `user_roles` 四张表；
2. 按常量表写入角色、权限点、角色-权限关系（`admin` 历史角色映射 `super_admin`）；
3. 按 `users.role` 回填 `user_roles`（存量用户不受影响，缺失角色跳过）。
"""

from datetime import datetime
from typing import List, Optional, Tuple

import sqlalchemy as sa

from alembic import op
from app.core.permissions import (
    ALL_PERMISSIONS,
    PERMISSIONS,
    ROLE_ALIASES,
    ROLE_INFO,
    ROLE_PERMISSIONS,
)

revision = "m3n4o5p6q7r8"
down_revision = "l2g3h4i5j6k7"
branch_labels = None
depends_on = None


def _permission_catalog() -> List[Tuple[str, str, Optional[str]]]:
    rows = [(code, code.split(":")[0], None) for code in PERMISSIONS]
    rows.append((ALL_PERMISSIONS, "system", "全部权限（通配）"))
    return rows


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)
    op.create_index("ix_permissions_domain", "permissions", ["domain"])

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column(
            "permission_id", sa.BigInteger(), sa.ForeignKey("permissions.id"), primary_key=True
        ),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.BigInteger(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("granted_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("granted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    _seed_catalog()
    _backfill_user_roles()


def _seed_catalog() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()

    roles_table = sa.table(
        "roles",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("level", sa.String),
        sa.column("is_system", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    bind.execute(
        roles_table.insert(),
        [
            {
                "code": code,
                "name": name,
                "level": level,
                "is_system": True,
                "created_at": now,
            }
            for code, (name, level) in ROLE_INFO.items()
        ],
    )

    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("domain", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    bind.execute(
        permissions_table.insert(),
        [
            {
                "code": code,
                "domain": domain,
                "description": description,
                "created_at": now,
            }
            for code, domain, description in _permission_catalog()
        ],
    )

    role_ids = {
        code: int(role_id)
        for role_id, code in bind.execute(sa.text("SELECT id, code FROM roles")).fetchall()
    }
    permission_ids = {
        code: int(permission_id)
        for permission_id, code in bind.execute(
            sa.text("SELECT id, code FROM permissions")
        ).fetchall()
    }
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.BigInteger),
        sa.column("permission_id", sa.BigInteger),
    )
    bind.execute(
        role_permissions_table.insert(),
        [
            {"role_id": role_ids[role_code], "permission_id": permission_ids[permission_code]}
            for role_code, permission_codes in ROLE_PERMISSIONS.items()
            for permission_code in permission_codes
        ],
    )


def _backfill_user_roles() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    role_ids = {
        code: int(role_id)
        for role_id, code in bind.execute(sa.text("SELECT id, code FROM roles")).fetchall()
    }
    users = bind.execute(sa.text("SELECT id, role FROM users")).fetchall()
    user_roles_table = sa.table(
        "user_roles",
        sa.column("user_id", sa.BigInteger),
        sa.column("role_id", sa.BigInteger),
        sa.column("is_primary", sa.Boolean),
        sa.column("granted_at", sa.DateTime),
    )
    rows = [
        {
            "user_id": int(user_id),
            "role_id": role_ids[ROLE_ALIASES.get(role, role)],
            "is_primary": True,
            "granted_at": now,
        }
        for user_id, role in users
        if ROLE_ALIASES.get(role, role) in role_ids
    ]
    if rows:
        bind.execute(user_roles_table.insert(), rows)


def downgrade() -> None:
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_domain", table_name="permissions")
    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")
