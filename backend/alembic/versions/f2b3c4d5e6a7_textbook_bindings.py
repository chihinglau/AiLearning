"""textbook_bindings 学生教材绑定表（D-04 §9.3）。"""

import sqlalchemy as sa
from alembic import op

revision = "f2b3c4d5e6a7"
down_revision = "e1b2c3d4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "textbook_bindings",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer, "sqlite"), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("subject", sa.String(length=20), nullable=False),
        sa.Column("textbook_id", sa.BigInteger(), sa.ForeignKey("textbooks.id"), nullable=False),
        sa.Column("semester", sa.String(length=10), nullable=False, server_default="first"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="auto"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("bound_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "subject", "semester", "textbook_id", name="uq_textbook_binding"
        ),
    )
    op.create_index(
        "ix_binding_user_subject", "textbook_bindings", ["user_id", "subject", "status"]
    )
    op.create_index("ix_textbook_bindings_user_id", "textbook_bindings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_textbook_bindings_user_id", table_name="textbook_bindings")
    op.drop_index("ix_binding_user_subject", table_name="textbook_bindings")
    op.drop_table("textbook_bindings")
