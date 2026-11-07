"""P0-18 内容种子四层结构测试。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import KnowledgePoint
from scripts.seed import _prune_default_sections, _put_kp, _put_section


def _count(db: Session, **filters) -> int:
    stmt = select(func.count(KnowledgePoint.id))
    for key, value in filters.items():
        stmt = stmt.where(getattr(KnowledgePoint, key) == value)
    return db.scalar(stmt) or 0


def test_section_and_point_are_distinct_rows(db: Session) -> None:
    section = _put_section(
        db, subject="math", grade=1, name="10以内加减法", order_index=1
    )
    point = _put_kp(
        db,
        subject="math",
        grade=1,
        name="10以内加减法",
        explanation="掌握 10 以内口算",
        section=section,
        order_index=1,
    )
    db.commit()

    assert section.id != point.id
    assert section.node_type == "section"
    assert section.parent_id is None
    assert point.node_type == "point"
    assert point.parent_id == section.id
    assert _count(db, subject="math", grade=1) == 2


def test_put_is_idempotent_and_updates_order(db: Session) -> None:
    section = _put_section(db, subject="math", grade=1, name="第一节", order_index=1)
    point = _put_kp(
        db,
        subject="math",
        grade=1,
        name="10以内加法",
        explanation="第一版讲解",
        section=section,
        order_index=1,
    )
    db.commit()

    section2 = _put_section(db, subject="math", grade=1, name="第一节", order_index=5)
    point2 = _put_kp(
        db,
        subject="math",
        grade=1,
        name="10以内加法",
        explanation="第二版讲解",
        section=section2,
        order_index=3,
    )
    db.commit()

    assert section2.id == section.id
    assert section2.order_index == 5
    assert point2.id == point.id
    assert point2.order_index == 3
    assert point2.explanation == "第二版讲解"
    assert _count(db, subject="math", grade=1, node_type="section") == 1
    assert _count(db, subject="math", grade=1, node_type="point") == 1


def test_point_name_avoids_section_collision(db: Session) -> None:
    section = _put_section(
        db, subject="math", grade=1, name="10以内加减法", order_index=1
    )
    point = _put_kp(
        db,
        subject="math",
        grade=1,
        name="10以内加减法",
        explanation="掌握 10 以内口算",
        section=section,
        order_index=1,
    )
    again = _put_kp(
        db,
        subject="math",
        grade=1,
        name="10以内加减法",
        explanation="掌握 10 以内口算",
        section=section,
        order_index=1,
    )
    db.commit()

    assert point.name == "10以内加减法（要点）"
    assert again.id == point.id
    assert _count(db, subject="math", grade=1) == 2


def test_prune_default_sections(db: Session) -> None:
    default = _put_section(db, subject="math", grade=9, name="默认节", order_index=0)
    child = KnowledgePoint(
        subject="math", grade=9, name="有理数", node_type="point", parent_id=default.id
    )
    db.add(child)
    db.commit()

    assert _prune_default_sections(db) == 0

    chapter_section = _put_section(
        db, subject="math", grade=9, name="第一章 有理数", order_index=1
    )
    child.parent_id = chapter_section.id
    db.commit()

    assert _prune_default_sections(db) == 1
    db.commit()
    assert _count(db, name="默认节") == 0
