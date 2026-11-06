"""users school id for school scope

Revision ID: e1b2c3d4f5a6
Revises: d7a9c3e5b210
Create Date: 2026-11-06 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e1b2c3d4f5a6'
down_revision: Union[str, None] = 'd7a9c3e5b210'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column(
                'school_id',
                sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
                nullable=True,
            )
        )
        batch_op.create_index(op.f('ix_users_school_id'), ['school_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index(op.f('ix_users_school_id'))
        batch_op.drop_column('school_id')
