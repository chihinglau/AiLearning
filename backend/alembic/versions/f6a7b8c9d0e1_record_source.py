"""答题记录来源拆分与掌握度来源明细（P0-24）。"""

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("student_question_records") as batch:
        batch.add_column(
            sa.Column("source", sa.String(length=20), nullable=False, server_default="practice")
        )
        batch.add_column(sa.Column("session_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("kp_weight", sa.Float(), nullable=False, server_default="1.0"))
        batch.create_foreign_key(
            "fk_records_session", "practice_sessions", ["session_id"], ["id"]
        )
        batch.create_index("ix_student_question_records_source", ["source"])
        batch.create_index("ix_student_question_records_session_id", ["session_id"])

    with op.batch_alter_table("mastery_scores") as batch:
        batch.add_column(
            sa.Column("source_breakdown", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )


def downgrade() -> None:
    with op.batch_alter_table("mastery_scores") as batch:
        batch.drop_column("source_breakdown")
    with op.batch_alter_table("student_question_records") as batch:
        batch.drop_index("ix_student_question_records_session_id")
        batch.drop_index("ix_student_question_records_source")
        batch.drop_constraint("fk_records_session", type_="foreignkey")
        batch.drop_column("kp_weight")
        batch.drop_column("session_id")
        batch.drop_column("source")
