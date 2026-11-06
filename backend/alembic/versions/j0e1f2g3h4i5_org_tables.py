"""学校/班级/成员/授课分配表（P1-01，D-03 §9.1）。"""

import sqlalchemy as sa
from alembic import op

revision = "j0e1f2g3h4i5"
down_revision = "i9d0e1f2g3h4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("region", sa.String(length=20), nullable=False, server_default="shenzhen"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "classes",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("school_id", sa.BigInteger(), sa.ForeignKey("schools.id"), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("head_teacher_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("school_year", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("school_id", "grade", "name", name="uq_class"),
    )
    op.create_index("ix_classes_school_id", "classes", ["school_id"])
    op.create_index("ix_classes_head_teacher_id", "classes", ["head_teacher_id"])

    op.create_table(
        "class_members",
        sa.Column("class_id", sa.BigInteger(), sa.ForeignKey("classes.id"), primary_key=True),
        sa.Column("student_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_class_members_class_id", "class_members", ["class_id"])
    op.create_index("ix_class_members_student_id", "class_members", ["student_id"])

    op.create_table(
        "teacher_class_assignments",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("teacher_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("class_id", sa.BigInteger(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("subject", sa.String(length=20), nullable=False),
        sa.Column(
            "role_in_class", sa.String(length=20), nullable=False, server_default="subject_teacher"
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "teacher_id", "class_id", "subject", name="uq_teacher_class_subject"
        ),
    )
    op.create_index(
        "ix_teacher_class_assignments_teacher_id", "teacher_class_assignments", ["teacher_id"]
    )
    op.create_index(
        "ix_teacher_class_assignments_class_id", "teacher_class_assignments", ["class_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_teacher_class_assignments_class_id", table_name="teacher_class_assignments"
    )
    op.drop_index(
        "ix_teacher_class_assignments_teacher_id", table_name="teacher_class_assignments"
    )
    op.drop_table("teacher_class_assignments")
    op.drop_index("ix_class_members_student_id", table_name="class_members")
    op.drop_index("ix_class_members_class_id", table_name="class_members")
    op.drop_table("class_members")
    op.drop_index("ix_classes_head_teacher_id", table_name="classes")
    op.drop_index("ix_classes_school_id", table_name="classes")
    op.drop_table("classes")
    op.drop_table("schools")
