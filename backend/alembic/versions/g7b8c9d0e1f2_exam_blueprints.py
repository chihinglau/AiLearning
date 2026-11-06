"""新增 exam_blueprints 表（P0-25 试卷蓝图）。"""

import sqlalchemy as sa
from alembic import op

revision = "g7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exam_blueprints",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("subject", sa.String(length=20), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=True),
        sa.Column("exam_type", sa.String(length=20), nullable=False, server_default="unit"),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("time_limit_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("kp_coverage_min", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("difficulty_mix", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_exam_blueprints_code", "exam_blueprints", ["code"], unique=True)
    op.create_index("ix_exam_blueprints_subject", "exam_blueprints", ["subject"])
    op.create_index("ix_exam_blueprints_grade", "exam_blueprints", ["grade"])
    op.create_index("ix_exam_blueprints_exam_type", "exam_blueprints", ["exam_type"])


def downgrade() -> None:
    op.drop_index("ix_exam_blueprints_exam_type", table_name="exam_blueprints")
    op.drop_index("ix_exam_blueprints_grade", table_name="exam_blueprints")
    op.drop_index("ix_exam_blueprints_subject", table_name="exam_blueprints")
    op.drop_index("ix_exam_blueprints_code", table_name="exam_blueprints")
    op.drop_table("exam_blueprints")
