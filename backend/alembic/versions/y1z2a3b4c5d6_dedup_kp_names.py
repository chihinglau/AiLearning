"""消除同学科同年级的同名知识点：重命名与 section 重名的 point。

Revision ID: y1z2a3b4c5d6
Revises: x1y2z3a4b5c6
Create Date: 2026-11-07

背景：小学 1-3 年级语数英生成"章节名同时作为核心知识点名"，
导致同一 subject+grade 下存在 section 与 point 同名，共 54 组。
按名称挂载题目的自动导入无法区分，本迁移统一保留 section 名称，
把 point 改名为「名称（要点）」「名称（要点2）」…。
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "y1z2a3b4c5d6"
down_revision: Union[str, None] = "x1y2z3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SUFFIX = "（要点）"


def _candidate(base: str, index: int) -> str:
    return f"{base}{SUFFIX}" if index == 1 else f"{base}（要点{index}）"


def _names(conn: sa.Connection, subject: str, grade: int) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT name FROM knowledge_points "
                "WHERE subject = :subject AND grade = :grade"
            ),
            {"subject": subject, "grade": grade},
        )
    }


def _dedup(conn: sa.Connection) -> int:
    groups = conn.execute(
        sa.text(
            "SELECT subject, grade, name FROM knowledge_points "
            "GROUP BY subject, grade, name HAVING COUNT(1) > 1 "
            "ORDER BY subject, grade, name"
        )
    ).all()
    renamed = 0
    for subject, grade, name in groups:
        points = conn.execute(
            sa.text(
                "SELECT id FROM knowledge_points "
                "WHERE subject = :subject AND grade = :grade AND name = :name "
                "AND node_type = 'point' ORDER BY id"
            ),
            {"subject": subject, "grade": grade, "name": name},
        ).all()
        sections = conn.execute(
            sa.text(
                "SELECT COUNT(1) FROM knowledge_points "
                "WHERE subject = :subject AND grade = :grade AND name = :name "
                "AND node_type = 'section'"
            ),
            {"subject": subject, "grade": grade, "name": name},
        ).scalar_one()
        # 无 section 时保留最早的一个 point，其余改名
        targets = points if sections else points[1:]
        taken = _names(conn, subject, grade)
        index = 0
        for (point_id,) in targets:
            index += 1
            candidate = _candidate(name, index)
            while candidate in taken:
                index += 1
                candidate = _candidate(name, index)
            conn.execute(
                sa.text("UPDATE knowledge_points SET name = :name WHERE id = :id"),
                {"name": candidate, "id": point_id},
            )
            taken.add(candidate)
            renamed += 1
    return renamed


def _restore(conn: sa.Connection) -> int:
    rows = conn.execute(
        sa.text(
            "SELECT id, name FROM knowledge_points WHERE node_type = 'point' "
            "AND (name LIKE '%（要点）' OR name LIKE '%（要点%')"
        )
    ).all()
    restored = 0
    for point_id, name in rows:
        base = name.split("（要点", 1)[0]
        conn.execute(
            sa.text("UPDATE knowledge_points SET name = :name WHERE id = :id"),
            {"name": base, "id": point_id},
        )
        restored += 1
    return restored


def upgrade() -> None:
    _dedup(op.get_bind())


def downgrade() -> None:
    _restore(op.get_bind())
