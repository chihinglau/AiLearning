"""exams 扩展 + exam_attempts/exam_answers 表（P0-27 考试作答闭环）。"""

import sqlalchemy as sa
from alembic import op

revision = "h8c9d0e1f2g3"
down_revision = "g7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("exams") as batch:
        batch.add_column(sa.Column("blueprint_id", sa.BigInteger(), nullable=True))
        batch.add_column(
            sa.Column("exam_type", sa.String(length=20), nullable=False, server_default="mock")
        )
        batch.add_column(sa.Column("chapter_ids", sa.JSON(), nullable=True))
        batch.add_column(
            sa.Column("status", sa.String(length=20), nullable=False, server_default="published")
        )
        batch.create_foreign_key(
            "fk_exams_blueprint", "exam_blueprints", ["blueprint_id"], ["id"]
        )
        batch.create_index("ix_exams_blueprint_id", ["blueprint_id"])
        batch.create_index("ix_exams_exam_type", ["exam_type"])
        batch.create_index("ix_exams_status", ["status"])

    op.create_table(
        "exam_attempts",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id"), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="in_progress"
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("objective_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("subjective_score", sa.Float(), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("submit_token", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("user_id", "exam_id", "seed", name="uq_attempt_user_exam_seed"),
    )
    op.create_index("ix_exam_attempts_user_id", "exam_attempts", ["user_id"])
    op.create_index("ix_exam_attempts_exam_id", "exam_attempts", ["exam_id"])
    op.create_index("ix_exam_attempts_status", "exam_attempts", ["status"])

    op.create_table(
        "exam_answers",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column(
            "attempt_id", sa.Integer(), sa.ForeignKey("exam_attempts.id"), nullable=False
        ),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("user_answer", sa.JSON(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("self_score", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_answer_attempt_question"),
    )
    op.create_index("ix_exam_answers_attempt_id", "exam_answers", ["attempt_id"])
    op.create_index("ix_exam_answers_question_id", "exam_answers", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_answers_question_id", table_name="exam_answers")
    op.drop_index("ix_exam_answers_attempt_id", table_name="exam_answers")
    op.drop_table("exam_answers")
    op.drop_index("ix_exam_attempts_status", table_name="exam_attempts")
    op.drop_index("ix_exam_attempts_exam_id", table_name="exam_attempts")
    op.drop_index("ix_exam_attempts_user_id", table_name="exam_attempts")
    op.drop_table("exam_attempts")
    with op.batch_alter_table("exams") as batch:
        batch.drop_index("ix_exams_status")
        batch.drop_index("ix_exams_exam_type")
        batch.drop_index("ix_exams_blueprint_id")
        batch.drop_constraint("fk_exams_blueprint", type_="foreignkey")
        batch.drop_column("status")
        batch.drop_column("chapter_ids")
        batch.drop_column("exam_type")
        batch.drop_column("blueprint_id")
