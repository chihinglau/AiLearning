"""用户名登录与注册：users 增加 username，phone 放开非空。

Revision ID: e7f8g9h0a1b2
Revises: d6e7f8g9h0a1
Create Date: 2026-11-24

背景：App 原先只允许手机号注册/登录，账号体系被手机号绑死（测试账号、
无手机号的学生账号都无法登录）。本次允许以用户名注册并登录：

- 新增 `username`（唯一、可空），供用户名登录/注册；
- `phone` 改为可空（用户名注册可不填手机号），保留唯一约束，存量手机号
  账号不受影响；
- 登录按 phone 或 username 任一命中；注册要求二者至少填一个。

回滚：phone 恢复非空（若存在无手机号账号会失败，需先补齐数据），
并删除 username 列。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "e7f8g9h0a1b2"
down_revision: Union[str, None] = "d6e7f8g9h0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("username", sa.String(length=50), nullable=True))
        batch.alter_column(
            "phone",
            existing_type=sa.String(length=20),
            nullable=True,
        )
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("username")
        batch.alter_column(
            "phone",
            existing_type=sa.String(length=20),
            nullable=False,
        )
