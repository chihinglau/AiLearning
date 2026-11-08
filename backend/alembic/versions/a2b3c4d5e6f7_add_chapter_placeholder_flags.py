"""给 chapters 加占位标记列：区分「教材真实章节」与「历史占位/旧样章」。

Revision ID: a2b3c4d5e6f7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-08

背景：第八轮评审 C 项——库内 39 个「占位/旧样章」（来自 2026-11-07 试跑批次与
早期 templates/*.json）与教材真实章节同级并列、order_index 撞号，app 端「教材
完整性」会直接看到教材上没有的章节。清理立项（见
`docs/content-templates/exports/automation_20261108_codebuddy/05-占位章节清理立项.md`）
先加两列做可标记、可过滤的底座：

- `is_placeholder`：1 = 占位/旧样章（app 端按教材目录过滤掉），0 = 教材真实章节。
- `placeholder_note`：占位原因与归属建议（待业务确认时写在这里）。

回滚：`downgrade()` 直接 drop 这两列，不影响 questions.chapter_id 等业务数据。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("chapters") as batch:
        batch.add_column(
            sa.Column(
                "is_placeholder",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch.add_column(sa.Column("placeholder_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chapters") as batch:
        batch.drop_column("placeholder_note")
        batch.drop_column("is_placeholder")
