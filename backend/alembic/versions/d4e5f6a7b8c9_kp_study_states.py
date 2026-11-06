"""新增 kp_study_states 表（P0-20 知识点学习状态机）。"""

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "kp_study_states",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "knowledge_point_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_points.id"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="未学习"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_event", sa.String(length=20), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("mastered_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "user_id", "knowledge_point_id", name="uq_kp_state_user_kp"
        ),
    )
    op.create_index("ix_kp_study_states_user_id", "kp_study_states", ["user_id"])
    op.create_index(
        "ix_kp_study_states_knowledge_point_id", "kp_study_states", ["knowledge_point_id"]
    )
    op.create_index("ix_kp_study_states_state", "kp_study_states", ["state"])


def downgrade() -> None:
    op.drop_index("ix_kp_study_states_state", table_name="kp_study_states")
    op.drop_index("ix_kp_study_states_knowledge_point_id", table_name="kp_study_states")
    op.drop_index("ix_kp_study_states_user_id", table_name="kp_study_states")
    op.drop_table("kp_study_states")
