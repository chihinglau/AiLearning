"""knowledge_points 增加四层结构字段并兼容存量数据（D-04 §6.1）。

- 新增 `node_type`（section/point）、`order_index`、`weight`
- 存量数据：`parent_id` 为空的知识点视为 point，按 (subject, grade) 补建"默认节"并挂接
"""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "f2b3c4d5e6a7"
branch_labels = None
depends_on = None

DEFAULT_SECTION_NAME = "默认节"


def _grade_clause(grade) -> tuple[str, dict]:
    if grade is None:
        return " AND grade IS NULL", {}
    return " AND grade = :grade", {"grade": int(grade)}


def upgrade() -> None:
    with op.batch_alter_table("knowledge_points") as batch:
        batch.add_column(
            sa.Column("node_type", sa.String(length=20), nullable=False, server_default="point")
        )
        batch.add_column(
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0")
        )
    op.create_index(
        "ix_knowledge_points_node_type", "knowledge_points", ["node_type"]
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT DISTINCT subject, grade FROM knowledge_points "
            "WHERE parent_id IS NULL AND node_type = 'point'"
        )
    ).fetchall()
    for subject, grade in rows:
        grade_clause, grade_params = _grade_clause(grade)
        params = {"subject": subject, **grade_params}

        section_id = conn.execute(
            sa.text(
                "SELECT id FROM knowledge_points WHERE node_type = 'section' "
                "AND name = :name AND subject = :subject" + grade_clause
            ),
            {**params, "name": DEFAULT_SECTION_NAME},
        ).scalar()
        if section_id is None:
            insert_sql = (
                "INSERT INTO knowledge_points "
                "(subject, name, parent_id, grade, node_type, order_index, weight, created_at) "
                "VALUES (:subject, :name, NULL, "
                + ("NULL" if grade is None else ":grade")
                + ", 'section', 0, 1.0, :created_at)"
            )
            values = {
                "subject": subject,
                "name": DEFAULT_SECTION_NAME,
                "created_at": datetime.utcnow(),
            }
            if grade is not None:
                values["grade"] = int(grade)
            conn.execute(sa.text(insert_sql), values)
            section_id = conn.execute(
                sa.text(
                    "SELECT id FROM knowledge_points WHERE node_type = 'section' "
                    "AND name = :name AND subject = :subject" + grade_clause
                ),
                {**params, "name": DEFAULT_SECTION_NAME},
            ).scalar()

        conn.execute(
            sa.text(
                "UPDATE knowledge_points SET parent_id = :section_id, node_type = 'point' "
                "WHERE parent_id IS NULL AND node_type = 'point' AND subject = :subject"
                + grade_clause
            ),
            {**params, "section_id": section_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    sections = conn.execute(
        sa.text(
            "SELECT id FROM knowledge_points WHERE node_type = 'section' AND name = :name"
        ),
        {"name": DEFAULT_SECTION_NAME},
    ).fetchall()
    for (section_id,) in sections:
        conn.execute(
            sa.text("UPDATE knowledge_points SET parent_id = NULL WHERE parent_id = :section_id"),
            {"section_id": section_id},
        )
        conn.execute(
            sa.text("DELETE FROM knowledge_points WHERE id = :section_id"),
            {"section_id": section_id},
        )

    op.drop_index("ix_knowledge_points_node_type", table_name="knowledge_points")
    with op.batch_alter_table("knowledge_points") as batch:
        batch.drop_column("weight")
        batch.drop_column("order_index")
        batch.drop_column("node_type")
