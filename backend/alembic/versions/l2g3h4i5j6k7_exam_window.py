"""P1-08：考试窗口字段（window_start / window_end）。

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-11-07
"""

import sqlalchemy as sa

from alembic import op

revision = "l2g3h4i5j6k7"
down_revision = "k1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exams", sa.Column("window_start", sa.DateTime(), nullable=True))
    op.add_column("exams", sa.Column("window_end", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("exams", "window_end")
    op.drop_column("exams", "window_start")
