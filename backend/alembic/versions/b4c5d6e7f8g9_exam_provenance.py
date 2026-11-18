"""exams 真题溯源三列：来源名称 / 授权说明 / 改编来源（D-09 §7.1，EX-06）。

Revision ID: b4c5d6e7f8g9
Revises: a2b3c4d5e6f7
Create Date: 2026-11-14

背景：D-08 合规红线要求题源台账（来源/授权凭证/录入/审核），D-01 要求公开真题
注明来源；原 Exam 只有 source 枚举，真题库页无法展示来源。新增三列均为 nullable，
存量卷不受影响，由内容教研按 R-07《题源与授权台账》补录，不猜测来源。

回滚：downgrade() 直接 drop 三列，不影响试卷与作答业务数据。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b4c5d6e7f8g9"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.add_column(sa.Column("source_name", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("license_note", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("adapted_from", sa.String(length=200), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.drop_column("adapted_from")
        batch.drop_column("license_note")
        batch.drop_column("source_name")
