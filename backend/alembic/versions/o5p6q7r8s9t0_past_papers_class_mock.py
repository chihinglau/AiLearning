"""真题库字段与班级同卷模考（P2-07）。

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-11-07
"""

import sqlalchemy as sa

from alembic import op

revision = "o5p6q7r8s9t0"
down_revision = "n4o5p6q7r8s9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.add_column(sa.Column("region", sa.String(length=40), nullable=True))
        batch.add_column(
            sa.Column(
                "is_past_paper",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch.add_column(
            sa.Column(
                "class_id",
                sa.BigInteger(),
                sa.ForeignKey("classes.id", name="fk_exams_class_id_classes"),
                nullable=True,
            )
        )
        batch.create_index("ix_exams_region", ["region"])
        batch.create_index("ix_exams_is_past_paper", ["is_past_paper"])
        batch.create_index("ix_exams_class_id", ["class_id"])


def downgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.drop_index("ix_exams_class_id")
        batch.drop_index("ix_exams_is_past_paper")
        batch.drop_index("ix_exams_region")
        batch.drop_column("class_id")
        batch.drop_column("is_past_paper")
        batch.drop_column("region")
