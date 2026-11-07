"""内容审核双人复核（P2-09）。

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-11-07
"""

import sqlalchemy as sa

from alembic import op

revision = "p6q7r8s9t0u1"
down_revision = "o5p6q7r8s9t0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_reviews",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("submitted_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("reviewed_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("published_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_content_reviews_content_type", "content_reviews", ["content_type"])
    op.create_index("ix_content_reviews_status", "content_reviews", ["status"])
    op.create_index("ix_content_reviews_submitted_by", "content_reviews", ["submitted_by"])
    op.create_index("ix_content_reviews_reviewed_by", "content_reviews", ["reviewed_by"])
    op.create_index("ix_content_reviews_published_by", "content_reviews", ["published_by"])

    with op.batch_alter_table("questions") as batch:
        batch.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="published",
            )
        )
        batch.create_index("ix_questions_status", ["status"])


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.drop_index("ix_questions_status")
        batch.drop_column("status")

    op.drop_index("ix_content_reviews_published_by", table_name="content_reviews")
    op.drop_index("ix_content_reviews_reviewed_by", table_name="content_reviews")
    op.drop_index("ix_content_reviews_submitted_by", table_name="content_reviews")
    op.drop_index("ix_content_reviews_status", table_name="content_reviews")
    op.drop_index("ix_content_reviews_content_type", table_name="content_reviews")
    op.drop_table("content_reviews")
