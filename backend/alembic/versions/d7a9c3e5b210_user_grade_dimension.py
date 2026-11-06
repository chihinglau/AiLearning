"""users grade dimension and grade histories

Revision ID: d7a9c3e5b210
Revises: b3f1a2c77d8e
Create Date: 2026-11-06 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd7a9c3e5b210'
down_revision: Union[str, None] = 'b3f1a2c77d8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('grade_group', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('enrollment_year', sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column('region', sa.String(length=20), nullable=False, server_default='shenzhen')
        )
        batch_op.add_column(
            sa.Column('semester', sa.String(length=10), nullable=False, server_default='first')
        )
        batch_op.add_column(
            sa.Column(
                'elective_subjects',
                sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column('grade_updated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('graduated_at', sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column('token_version', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column(
                'teacher_subjects',
                sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column('grade_start', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('grade_end', sa.Integer(), nullable=True))

    op.create_table(
        'grade_histories',
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
        sa.Column('from_grade', sa.Integer(), nullable=True),
        sa.Column('to_grade', sa.Integer(), nullable=False),
        sa.Column('school_year', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=True),
        sa.Column(
            'operator_id',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            nullable=True,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['operator_id'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'to_grade', 'school_year', name='uq_grade_history_user_target_year'
        ),
    )
    op.create_index(
        op.f('ix_grade_histories_user_id'), 'grade_histories', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_grade_histories_operator_id'), 'grade_histories', ['operator_id'], unique=False
    )

    # 存量回填：按年级派生 stage / grade_group，不覆盖已有 stage
    op.execute(
        """
        UPDATE users SET stage = CASE
            WHEN grade BETWEEN 1 AND 6 THEN 'primary'
            WHEN grade BETWEEN 7 AND 9 THEN 'junior'
            WHEN grade BETWEEN 10 AND 12 THEN 'senior'
            ELSE NULL END
        WHERE role = 'student' AND grade IS NOT NULL AND stage IS NULL
        """
    )
    op.execute(
        """
        UPDATE users SET grade_group = CASE
            WHEN grade <= 2 THEN 'primary_low'
            WHEN grade <= 4 THEN 'primary_mid'
            WHEN grade <= 6 THEN 'primary_high'
            WHEN grade <= 9 THEN 'junior'
            ELSE 'senior' END
        WHERE grade IS NOT NULL AND grade_group IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_grade_histories_operator_id'), table_name='grade_histories')
    op.drop_index(op.f('ix_grade_histories_user_id'), table_name='grade_histories')
    op.drop_table('grade_histories')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('grade_end')
        batch_op.drop_column('grade_start')
        batch_op.drop_column('teacher_subjects')
        batch_op.drop_column('token_version')
        batch_op.drop_column('graduated_at')
        batch_op.drop_column('grade_updated_at')
        batch_op.drop_column('elective_subjects')
        batch_op.drop_column('semester')
        batch_op.drop_column('region')
        batch_op.drop_column('enrollment_year')
        batch_op.drop_column('grade_group')
