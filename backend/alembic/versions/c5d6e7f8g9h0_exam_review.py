"""exams 审核发布留痕列（D-09 §7.2 / EX-09 / CR-005）。

Revision ID: c5d6e7f8g9h0
Revises: b4c5d6e7f8g9
Create Date: 2026-11-14

CR-005 采纳 D-09 §5.7 P2「真题草稿 -> 复核 -> 发布」审核流。新增列全部 nullable，
不改存量卷状态；存量真题由 EX-11 脚本按 R-07 台账处置。

回滚：downgrade() 直接 drop 五列，不影响试卷与作答业务数据。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "c5d6e7f8g9h0"
down_revision: Union[str, None] = "b4c5d6e7f8g9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.add_column(sa.Column("reviewed_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("published_by", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("published_at", sa.DateTime(), nullable=True))
        batch.add_column(sa.Column("review_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.drop_column("review_note")
        batch.drop_column("published_at")
        batch.drop_column("published_by")
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by")
