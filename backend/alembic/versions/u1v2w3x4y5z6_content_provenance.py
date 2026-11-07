"""CT-02 题库/知识库来源与版权登记字段。

Revision ID: u1v2w3x4y5z6
Revises: t0u1v2w3x4y5
Create Date: 2026-11-07
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "u1v2w3x4y5z6"
down_revision: Union[str, None] = "t0u1v2w3x4y5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.add_column(
            sa.Column(
                "source_type",
                sa.String(length=20),
                nullable=False,
                server_default="original",
            )
        )
        batch.add_column(sa.Column("source_name", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("source_ref", sa.String(length=200), nullable=True))
        batch.add_column(
            sa.Column("copyright_owner", sa.String(length=200), nullable=True)
        )
        batch.add_column(sa.Column("license_note", sa.Text(), nullable=True))
        batch.add_column(sa.Column("adapted_from", sa.String(length=200), nullable=True))

    with op.batch_alter_table("knowledge_points") as batch:
        batch.add_column(
            sa.Column(
                "source_type",
                sa.String(length=20),
                nullable=False,
                server_default="original",
            )
        )
        batch.add_column(sa.Column("source_name", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("source_ref", sa.String(length=200), nullable=True))
        batch.add_column(
            sa.Column("copyright_owner", sa.String(length=200), nullable=True)
        )
        batch.add_column(sa.Column("license_note", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("knowledge_points") as batch:
        batch.drop_column("license_note")
        batch.drop_column("copyright_owner")
        batch.drop_column("source_ref")
        batch.drop_column("source_name")
        batch.drop_column("source_type")

    with op.batch_alter_table("questions") as batch:
        batch.drop_column("adapted_from")
        batch.drop_column("license_note")
        batch.drop_column("copyright_owner")
        batch.drop_column("source_ref")
        batch.drop_column("source_name")
        batch.drop_column("source_type")
