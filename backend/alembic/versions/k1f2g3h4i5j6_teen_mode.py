"""家长控制：users.teen_mode（P1-05，D-03 §10.2）。"""

import sqlalchemy as sa

from alembic import op

revision = "k1f2g3h4i5j6"
down_revision = "j0e1f2g3h4i5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("teen_mode", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "teen_mode")
