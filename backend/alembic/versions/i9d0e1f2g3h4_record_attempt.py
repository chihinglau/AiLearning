"""student_question_records 增加 attempt_id（P0-30 考试数据回流）。"""

import sqlalchemy as sa
from alembic import op

revision = "i9d0e1f2g3h4"
down_revision = "h8c9d0e1f2g3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("student_question_records") as batch:
        batch.add_column(sa.Column("attempt_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_records_exam_attempt", "exam_attempts", ["attempt_id"], ["id"]
        )
        batch.create_index("ix_student_question_records_attempt_id", ["attempt_id"])


def downgrade() -> None:
    with op.batch_alter_table("student_question_records") as batch:
        batch.drop_index("ix_student_question_records_attempt_id")
        batch.drop_constraint("fk_records_exam_attempt", type_="foreignkey")
        batch.drop_column("attempt_id")
