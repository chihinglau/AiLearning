"""前置知识点按教材章节顺序输出，并带讲解可用性。

回归目标：kp_detail 用无 ORDER BY 的 IN 查询 + 字典 values() 输出，
原本既不是教材顺序也不是声明顺序；离线包还把整册前置塞给每个知识点。
"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import KnowledgePoint
from app.models.user import User
from app.services.textbook_bundle import _kp_detail, _ordered_prerequisites


def _login(client: TestClient, db: Session) -> dict[str, str]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13900000012", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    assert db.scalar(select(User).where(User.phone == "13900000012")) is not None
    login = client.post(
        "/api/auth/login",
        data={"username": "13900000012", "password": "pass1234"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_kp_detail_prerequisites_sorted_by_textbook(
    client: TestClient, db: Session
) -> None:
    headers = _login(client, db)
    # 故意先创建 order_index 更大的节，确认排序依据不是数据库物理顺序/id。
    section_b = KnowledgePoint(
        subject="chinese", name="第二节", grade=3,
        node_type="section", order_index=2,
    )
    section_a = KnowledgePoint(
        subject="chinese", name="第一节", grade=3,
        node_type="section", order_index=1,
    )
    db.add_all([section_b, section_a])
    db.flush()

    late = KnowledgePoint(
        subject="chinese", name="第二节知识点", grade=3, node_type="point",
        parent_id=section_b.id, order_index=1, explanation="第二节讲解",
    )
    early = KnowledgePoint(
        subject="chinese", name="第一节第1点", grade=3, node_type="point",
        parent_id=section_a.id, order_index=1, explanation="第一节讲解",
    )
    mid = KnowledgePoint(
        subject="chinese", name="第一节第2点", grade=3, node_type="point",
        parent_id=section_a.id, order_index=2, explanation=None,
    )
    db.add_all([late, early, mid])
    db.flush()  # 先拿到前置知识点 id，再写入 prerequisites 数组
    main = KnowledgePoint(
        subject="chinese", name="当前知识点", grade=3, node_type="point",
        parent_id=section_a.id, order_index=3,
        prerequisites=[late.id, mid.id, early.id],
    )
    db.add(main)
    db.commit()

    response = client.get(f"/api/learn/kp/{main.id}", headers=headers)
    assert response.status_code == 200, response.text
    prerequisites = response.json()["prerequisites"]
    assert [item["name"] for item in prerequisites] == [
        "第一节第1点",
        "第一节第2点",
        "第二节知识点",
    ]
    assert [item["section_order"] for item in prerequisites] == [1, 1, 2]
    assert [item["section_name"] for item in prerequisites] == [
        "第一节",
        "第一节",
        "第二节",
    ]
    assert [item["has_explanation"] for item in prerequisites] == [True, False, True]


def test_bundle_prerequisites_only_own_and_sorted() -> None:
    section_a = KnowledgePoint(
        id=1, subject="chinese", name="第一节", grade=3,
        node_type="section", order_index=1,
    )
    section_b = KnowledgePoint(
        id=2, subject="chinese", name="第二节", grade=3,
        node_type="section", order_index=2,
    )
    early = KnowledgePoint(
        id=10, subject="chinese", name="第一节第1点", grade=3,
        node_type="point", parent_id=1, order_index=1, explanation="有讲解",
    )
    mid = KnowledgePoint(
        id=11, subject="chinese", name="第一节第2点", grade=3,
        node_type="point", parent_id=1, order_index=2, explanation=None,
    )
    late = KnowledgePoint(
        id=12, subject="chinese", name="第二节知识点", grade=3,
        node_type="point", parent_id=2, order_index=1,
    )
    unrelated = KnowledgePoint(
        id=13, subject="chinese", name="别人的前置", grade=3,
        node_type="point", parent_id=2, order_index=2,
    )
    main = KnowledgePoint(
        id=20, subject="chinese", name="当前知识点", grade=3,
        node_type="point", parent_id=1, order_index=3,
        prerequisites=[late.id, mid.id, early.id],
    )
    pool = {item.id: item for item in (early, mid, late, unrelated)}
    sections = {1: section_a, 2: section_b}

    ordered = _ordered_prerequisites(main, pool, sections)
    assert [item.id for item in ordered] == [10, 11, 12]

    detail = _kp_detail(
        main, question_count=0, sections=sections, prerequisites=ordered
    )
    assert [item.id for item in detail.prerequisites] == [10, 11, 12]
    assert detail.prerequisites[0].section_order == 1
    assert detail.prerequisites[2].section_order == 2
    assert detail.prerequisites[0].section_name == "第一节"
    assert detail.prerequisites[0].has_explanation is True
    assert detail.prerequisites[1].has_explanation is False
