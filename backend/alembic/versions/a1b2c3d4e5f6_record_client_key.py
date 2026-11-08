"""student_question_records.client_key：离线答题幂等同步。

Revision ID: a1b2c3d4e5f6
Revises: z1a2b3c4d5e6
Create Date: 2026-11-08
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "z1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("student_question_records") as batch:
        batch.add_column(
            sa.Column("client_key", sa.String(length=64), nullable=True)
        )
        batch.create_unique_constraint(
            "uq_record_user_client_key", ["user_id", "client_key"]
        )


def downgrade() -> None:
    with op.batch_alter_table("student_question_records") as batch:
        batch.drop_constraint("uq_record_user_client_key", type_="unique")
        batch.drop_column("client_key")
