"""wrong book and question kp link

Revision ID: b3f1a2c77d8e
Revises: 75d207fd95d5
Create Date: 2026-11-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b3f1a2c77d8e'
down_revision: Union[str, None] = '75d207fd95d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('questions') as batch_op:
        batch_op.add_column(
            sa.Column(
                'knowledge_point_id',
                sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
                nullable=True,
            )
        )
        batch_op.create_index(
            op.f('ix_questions_knowledge_point_id'),
            ['knowledge_point_id'],
            unique=False,
        )
        batch_op.create_foreign_key(
            'fk_questions_knowledge_point',
            'knowledge_points',
            ['knowledge_point_id'],
            ['id'],
        )

    op.create_table(
        'wrong_questions',
        sa.Column(
            'id',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            nullable=False,
        ),
        sa.Column(
            'question_id',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            nullable=False,
        ),
        sa.Column('wrong_count', sa.Integer(), nullable=False),
        sa.Column('correct_streak', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('ease_factor', sa.Float(), nullable=False),
        sa.Column('interval_days', sa.Integer(), nullable=False),
        sa.Column('reps', sa.Integer(), nullable=False),
        sa.Column('lapses', sa.Integer(), nullable=False),
        sa.Column('next_review_at', sa.DateTime(), nullable=True),
        sa.Column('last_wrong_at', sa.DateTime(), nullable=False),
        sa.Column('wrong_reason', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'question_id', name='uq_wrong_user_question'),
    )
    op.create_index(
        op.f('ix_wrong_questions_user_id'), 'wrong_questions', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_wrong_questions_question_id'),
        'wrong_questions',
        ['question_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_wrong_questions_status'), 'wrong_questions', ['status'], unique=False
    )
    op.create_index(
        op.f('ix_wrong_questions_next_review_at'),
        'wrong_questions',
        ['next_review_at'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_wrong_questions_next_review_at'), table_name='wrong_questions')
    op.drop_index(op.f('ix_wrong_questions_status'), table_name='wrong_questions')
    op.drop_index(op.f('ix_wrong_questions_question_id'), table_name='wrong_questions')
    op.drop_index(op.f('ix_wrong_questions_user_id'), table_name='wrong_questions')
    op.drop_table('wrong_questions')
    with op.batch_alter_table('questions') as batch_op:
        batch_op.drop_constraint('fk_questions_knowledge_point', type_='foreignkey')
        batch_op.drop_index(op.f('ix_questions_knowledge_point_id'))
        batch_op.drop_column('knowledge_point_id')
