"""校正高中地理教材版本：湘教版改为人教版。

Revision ID: x1y2z3a4b5c6
Revises: v1w2x3y4z5a6
Create Date: 2026-11-07
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "x1y2z3a4b5c6"
down_revision: Union[str, None] = "v1w2x3y4z5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SUBJECT = "geography"
SOURCE = "湘教版"
TARGET = "人教版"


def _rename_version(
    conn: sa.Connection, source: str, target: str
) -> None:
    """把高中地理旧版本教材改名为新版本；若新版本已存在则迁移章节后删除旧记录。"""
    rows = conn.execute(
        sa.text(
            "SELECT id, grade, semester FROM textbooks "
            "WHERE subject = :subject AND version = :source AND grade >= 10"
        ),
        {"subject": SUBJECT, "source": source},
    ).mappings().all()
    for row in rows:
        existing = conn.execute(
            sa.text(
                "SELECT id FROM textbooks "
                "WHERE subject = :subject AND grade = :grade "
                "AND version = :target AND semester = :semester"
            ),
            {
                "subject": SUBJECT,
                "grade": row["grade"],
                "target": target,
                "semester": row["semester"],
            },
        ).first()
        if existing:
            conn.execute(
                sa.text("UPDATE chapters SET textbook_id = :target WHERE textbook_id = :old"),
                {"target": existing[0], "old": row["id"]},
            )
            conn.execute(
                sa.text("DELETE FROM textbooks WHERE id = :old"),
                {"old": row["id"]},
            )
        else:
            conn.execute(
                sa.text("UPDATE textbooks SET version = :target WHERE id = :id"),
                {"target": target, "id": row["id"]},
            )


def upgrade() -> None:
    _rename_version(op.get_bind(), SOURCE, TARGET)


def downgrade() -> None:
    _rename_version(op.get_bind(), TARGET, SOURCE)
