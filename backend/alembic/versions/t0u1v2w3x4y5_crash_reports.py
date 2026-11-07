"""R-09 崩溃与错误监控表迁移。

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "t0u1v2w3x4y5"
down_revision: Union[str, None] = "s9t0u1v2w3x4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crash_reports",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="app"),
        sa.Column(
            "platform",
            sa.String(length=30),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("app_version", sa.String(length=30), nullable=True),
        sa.Column("os_version", sa.String(length=80), nullable=True),
        sa.Column("device_model", sa.String(length=80), nullable=True),
        sa.Column("route", sa.String(length=120), nullable=True),
        sa.Column("error_type", sa.String(length=80), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=40), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crash_reports_user_id", "crash_reports", ["user_id"])
    op.create_index("ix_crash_reports_fingerprint", "crash_reports", ["fingerprint"])
    op.create_index("ix_crash_reports_created_at", "crash_reports", ["created_at"])
    op.create_index(
        "ix_crash_reports_fingerprint_created",
        "crash_reports",
        ["fingerprint", "created_at"],
    )
    op.create_index(
        "ix_crash_reports_source_created",
        "crash_reports",
        ["source", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_crash_reports_source_created", table_name="crash_reports")
    op.drop_index(
        "ix_crash_reports_fingerprint_created", table_name="crash_reports"
    )
    op.drop_index("ix_crash_reports_created_at", table_name="crash_reports")
    op.drop_index("ix_crash_reports_fingerprint", table_name="crash_reports")
    op.drop_index("ix_crash_reports_user_id", table_name="crash_reports")
    op.drop_table("crash_reports")
