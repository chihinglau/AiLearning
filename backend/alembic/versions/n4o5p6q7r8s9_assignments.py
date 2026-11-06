"""班级作业与教师批改字段（P2-03）。

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-11-07
"""

import sqlalchemy as sa

from alembic import op

revision = "n4o5p6q7r8s9"
down_revision = "m3n4o5p6q7r8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("teacher_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.BigInteger(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("exam_id", sa.BigInteger(), sa.ForeignKey("exams.id"), nullable=False),
        sa.Column("subject", sa.String(length=20), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="published",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("exam_id", name="uq_assignment_exam"),
    )
    op.create_index("ix_assignments_teacher_id", "assignments", ["teacher_id"])
    op.create_index("ix_assignments_class_id", "assignments", ["class_id"])
    op.create_index("ix_assignments_exam_id", "assignments", ["exam_id"])
    op.create_index("ix_assignments_subject", "assignments", ["subject"])
    op.create_index("ix_assignments_status", "assignments", ["status"])

    with op.batch_alter_table("exam_answers") as batch:
        batch.add_column(sa.Column("teacher_comment", sa.String(length=500), nullable=True))
        batch.add_column(
            sa.Column(
                "graded_by",
                sa.BigInteger(),
                sa.ForeignKey("users.id", name="fk_exam_answers_graded_by_users"),
                nullable=True,
            )
        )
        batch.add_column(sa.Column("graded_at", sa.DateTime(), nullable=True))
        batch.create_index("ix_exam_answers_graded_by", ["graded_by"])


def downgrade() -> None:
    with op.batch_alter_table("exam_answers") as batch:
        batch.drop_index("ix_exam_answers_graded_by")
        batch.drop_column("graded_at")
        batch.drop_column("graded_by")
        batch.drop_column("teacher_comment")

    op.drop_index("ix_assignments_status", table_name="assignments")
    op.drop_index("ix_assignments_subject", table_name="assignments")
    op.drop_index("ix_assignments_exam_id", table_name="assignments")
    op.drop_index("ix_assignments_class_id", table_name="assignments")
    op.drop_index("ix_assignments_teacher_id", table_name="assignments")
    op.drop_table("assignments")
