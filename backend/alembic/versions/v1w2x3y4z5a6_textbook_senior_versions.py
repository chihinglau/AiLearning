"""校正高中教材版本：数学人教版 A 版、英语外研版。

Revision ID: v1w2x3y4z5a6
Revises: u1v2w3x4y5z6
Create Date: 2026-11-07
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "v1w2x3y4z5a6"
down_revision: Union[str, None] = "u1v2w3x4y5z6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (学科, 旧版本, 新版本)
MAPPINGS = [
    ("math", "北师大版", "人教版A版"),
    ("english", "牛津深圳版", "外研版"),
]


def _rename_version(
    conn: sa.Connection, subject: str, source: str, target: str
) -> None:
    """把高中阶段旧版本教材改名为新版本；若新版本已存在则迁移章节后删除旧记录。"""
    rows = conn.execute(
        sa.text(
            "SELECT id, grade, semester FROM textbooks "
            "WHERE subject = :subject AND version = :source AND grade >= 10"
        ),
        {"subject": subject, "source": source},
    ).mappings().all()
    for row in rows:
        existing = conn.execute(
            sa.text(
                "SELECT id FROM textbooks "
                "WHERE subject = :subject AND grade = :grade "
                "AND version = :target AND semester = :semester"
            ),
            {
                "subject": subject,
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
    conn = op.get_bind()
    for subject, source, target in MAPPINGS:
        _rename_version(conn, subject, source, target)


def downgrade() -> None:
    conn = op.get_bind()
    for subject, source, target in MAPPINGS:
        _rename_version(conn, subject, target, source)
