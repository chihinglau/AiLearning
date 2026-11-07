"""R-07 内容举报表迁移。

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "s9t0u1v2w3x4"
down_revision: Union[str, None] = "r8s9t0u1v2w3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_reports",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            nullable=False,
        ),
        sa.Column("reporter_id", sa.BigInteger(), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("handled_by", sa.BigInteger(), nullable=True),
        sa.Column("handled_at", sa.DateTime(), nullable=True),
        sa.Column("handle_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["handled_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_reports_reporter_id", "content_reports", ["reporter_id"]
    )
    op.create_index(
        "ix_content_reports_target_type", "content_reports", ["target_type"]
    )
    op.create_index("ix_content_reports_target_id", "content_reports", ["target_id"])
    op.create_index("ix_content_reports_status", "content_reports", ["status"])
    op.create_index(
        "ix_content_reports_handled_by", "content_reports", ["handled_by"]
    )


def downgrade() -> None:
    op.drop_index("ix_content_reports_handled_by", table_name="content_reports")
    op.drop_index("ix_content_reports_status", table_name="content_reports")
    op.drop_index("ix_content_reports_target_id", table_name="content_reports")
    op.drop_index("ix_content_reports_target_type", table_name="content_reports")
    op.drop_index("ix_content_reports_reporter_id", table_name="content_reports")
    op.drop_table("content_reports")
