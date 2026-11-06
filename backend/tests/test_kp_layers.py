"""P0-17 知识点四层结构字段测试。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import KnowledgePoint
from app.schemas.content import KnowledgePointOut


def test_kp_defaults_are_point(db: Session) -> None:
    kp = KnowledgePoint(subject="math", name="10以内加法", grade=1)
    db.add(kp)
    db.commit()
    db.refresh(kp)

    assert kp.node_type == "point"
    assert kp.order_index == 0
    assert kp.weight == 1.0


def test_section_and_point_relation(db: Session) -> None:
    section = KnowledgePoint(
        subject="math", name="第一单元 第一节", grade=1, node_type="section", order_index=1
    )
    db.add(section)
    db.flush()
    point = KnowledgePoint(
        subject="math",
        name="10以内加法",
        grade=1,
        node_type="point",
        parent_id=section.id,
        order_index=2,
        weight=1.5,
    )
    db.add(point)
    db.commit()

    children = list(
        db.scalars(
            select(KnowledgePoint).where(KnowledgePoint.parent_id == section.id)
        )
    )
    assert [child.name for child in children] == ["10以内加法"]
    assert children[0].weight == 1.5

    out = KnowledgePointOut.model_validate(point)
    assert out.node_type == "point"
    assert out.parent_id == section.id
