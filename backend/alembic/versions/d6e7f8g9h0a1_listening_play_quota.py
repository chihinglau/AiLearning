"""听力材料播放次数记账表（CR-008）。

Revision ID: d6e7f8g9h0a1
Revises: c5d6e7f8g9h0
Create Date: 2026-11-18

背景：听力题恢复后，客户端每次点击喇叭都会请求音频。若不做后端记账，
学生可以无限重播，听力题就退化成「看着原文找答案」。新增
`listening_plays` 按 (attempt_id, question_id) 累计次数，接口侧按
`listening_play_limit_per_attempt`（默认 2）拦截。

只记试卷作答（attempt_id 非空）；练习页不计数，故不加任何 NOT NULL 约束
到业务数据上，存量数据不受影响。

回滚：downgrade() 直接 drop 表，已作答记录在 exam_answers 中，不丢作答结果。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "d6e7f8g9h0a1"
down_revision: Union[str, None] = "c5d6e7f8g9h0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listening_plays",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer, "sqlite"),
            primary_key=True,
        ),
        sa.Column(
            "attempt_id",
            sa.BigInteger(),
            sa.ForeignKey("exam_attempts.id"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.BigInteger(),
            sa.ForeignKey("questions.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("play_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_played_at", sa.DateTime(), nullable=False),
        sa.Column("last_played_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "attempt_id", "question_id", name="uq_listening_play_attempt_question"
        ),
    )
    op.create_index(
        "ix_listening_plays_attempt_id", "listening_plays", ["attempt_id"]
    )
    op.create_index(
        "ix_listening_plays_question_id", "listening_plays", ["question_id"]
    )
    op.create_index("ix_listening_plays_user_id", "listening_plays", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_listening_plays_user_id", table_name="listening_plays")
    op.drop_index("ix_listening_plays_question_id", table_name="listening_plays")
    op.drop_index("ix_listening_plays_attempt_id", table_name="listening_plays")
    op.drop_table("listening_plays")
