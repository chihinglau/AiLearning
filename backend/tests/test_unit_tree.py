"""P0-19 教材→单元→节→知识点目录接口测试。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import MasteryScore, StudentQuestionRecord, WrongQuestion
from app.models.user import User


def _setup(client: TestClient, db: Session) -> dict[str, int | str]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13500000001", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    user = db.scalar(select(User).where(User.phone == "13500000001"))
    assert user is not None
    login = client.post(
        "/api/auth/login", data={"username": "13500000001", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元 加减法", order_index=1)
    db.add(chapter)
    db.flush()
    section = KnowledgePoint(
        subject="math", name="第1节 口算", grade=3, node_type="section", order_index=1
    )
    db.add(section)
    db.flush()
    kp1 = KnowledgePoint(
        subject="math",
        name="两位数进位加法",
        grade=3,
        node_type="point",
        parent_id=section.id,
        order_index=1,
    )
    kp2 = KnowledgePoint(
        subject="math",
        name="退位减法",
        grade=3,
        node_type="point",
        parent_id=section.id,
        order_index=2,
    )
    db.add_all([kp1, kp2])
    db.flush()

    q1 = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp1.id,
        subject="math",
        q_type="choice",
        content={"stem": "12 + 9 = ?"},
        answer={"value": "B"},
    )
    q2 = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp2.id,
        subject="math",
        q_type="choice",
        content={"stem": "15 - 8 = ?"},
        answer={"value": "A"},
    )
    db.add_all([q1, q2])
    db.flush()

    db.add(MasteryScore(user_id=user.id, knowledge_point_id=kp1.id, score=55.0, confidence=2))
    db.add(
        StudentQuestionRecord(
            user_id=user.id,
            question_id=q1.id,
            is_correct=True,
            attempted_at=datetime.utcnow() - timedelta(days=1),
        )
    )
    db.add(
        WrongQuestion(
            user_id=user.id,
            question_id=q2.id,
            status="active",
            next_review_at=datetime.utcnow() - timedelta(hours=1),
        )
    )
    db.commit()
    return {
        "headers": headers,
        "user_id": user.id,
        "book_id": book.id,
        "chapter_id": chapter.id,
        "section_id": section.id,
        "kp1": kp1.id,
        "kp2": kp2.id,
    }


def test_textbook_units_aggregates(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.get(
        f"/api/learn/textbook/{ids['book_id']}/units", headers=ids["headers"]
    )
    assert response.status_code == 200, response.text
    units = response.json()
    assert len(units) == 1
    unit = units[0]
    assert unit["kp_count"] == 2
    assert unit["question_count"] == 2
    assert unit["section_count"] == 1
    assert unit["avg_mastery"] == 27.5
    assert unit["mastery_band"] == "weak"
    assert unit["learned_kp_count"] == 1
    assert unit["progress"] == 0.5


def test_unit_detail_lists_sections_and_states(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.get(f"/api/learn/unit/{ids['chapter_id']}", headers=ids["headers"])
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["unit"]["kp_count"] == 2
    assert len(body["sections"]) == 1
    section = body["sections"][0]
    assert section["id"] == ids["section_id"]
    assert section["kp_count"] == 2
    assert section["avg_mastery"] == 27.5

    nodes = {node["id"]: node for node in body["knowledge_points"]}
    assert nodes[ids["kp1"]]["mastery_score"] == 55.0
    assert nodes[ids["kp1"]]["state"] == "待巩固"
    assert nodes[ids["kp1"]]["last_studied_at"] is not None
    assert nodes[ids["kp2"]]["state"] == "复习中"


def test_kp_detail(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.get(f"/api/learn/kp/{ids['kp1']}", headers=ids["headers"])
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["name"] == "两位数进位加法"
    assert body["section_id"] == ids["section_id"]
    assert body["section_name"] == "第1节 口算"
    assert body["mastery_score"] == 55.0
    assert body["mastery_band"] == "growing"
    assert body["question_count"] == 1
    assert body["state"] == "待巩固"


def test_kp_detail_unknown_returns_404(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.get("/api/learn/kp/999999", headers=ids["headers"])
    assert response.status_code == 404
