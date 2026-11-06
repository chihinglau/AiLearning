"""P0-21 练习组卷预览测试。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import WrongQuestion
from app.models.user import User


def _setup(client: TestClient, db: Session) -> dict[str, int | str]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13700000001", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    user = db.scalar(select(User).where(User.phone == "13700000001"))
    assert user is not None
    login = client.post(
        "/api/auth/login", data={"username": "13700000001", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    section = KnowledgePoint(
        subject="math", name="第1节", grade=3, node_type="section", order_index=1
    )
    db.add(section)
    db.flush()
    kp1 = KnowledgePoint(
        subject="math", name="进位加法", grade=3, node_type="point",
        parent_id=section.id, order_index=1,
    )
    kp2 = KnowledgePoint(
        subject="math", name="退位减法", grade=3, node_type="point",
        parent_id=section.id, order_index=2,
    )
    db.add_all([kp1, kp2])
    db.flush()

    questions = [
        Question(
            chapter_id=chapter.id, knowledge_point_id=kp1.id, subject="math",
            q_type="choice", content={"stem": "12 + 9 = ?"}, answer={"value": "B"},
        ),
        Question(
            chapter_id=chapter.id, knowledge_point_id=kp1.id, subject="math",
            q_type="choice", content={"stem": "18 + 7 = ?"}, answer={"value": "A"},
        ),
        Question(
            chapter_id=chapter.id, knowledge_point_id=kp2.id, subject="math",
            q_type="fill", content={"stem": "15 - 8 = ____"}, answer={"value": "7"},
        ),
    ]
    db.add_all(questions)
    db.commit()
    return {
        "headers": headers,
        "user_id": user.id,
        "book_id": book.id,
        "chapter_id": chapter.id,
        "kp1": kp1.id,
        "kp2": kp2.id,
        "q_id": questions[0].id,
    }


def test_preview_reports_insufficient(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json={"scope_type": "kp", "scope_ids": [ids["kp1"], ids["kp2"]], "count": 5},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["available"] == 3
    assert body["count"] == 3
    assert body["insufficient"] is True
    assert body["kp_coverage"] == 1.0
    assert body["range_kp_count"] == 2
    assert body["estimated_minutes"] == 2
    assert body["q_type_mix"] == {"choice": 2, "fill": 1}


def test_preview_chapter_and_textbook_scope(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    chapter = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json={"scope_type": "chapter", "scope_ids": [ids["chapter_id"]], "count": 3},
    )
    assert chapter.status_code == 200
    assert chapter.json()["available"] == 3
    assert chapter.json()["insufficient"] is False

    textbook = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json={"scope_type": "textbook", "scope_ids": [ids["book_id"]], "count": 2},
    )
    assert textbook.status_code == 200
    assert textbook.json()["available"] == 3
    assert textbook.json()["count"] == 2


def test_preview_filters_q_types_and_is_deterministic(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    payload = {
        "scope_type": "chapter",
        "scope_ids": [ids["chapter_id"]],
        "count": 2,
        "q_types": ["choice"],
        "seed": 42,
    }
    first = client.post("/api/learn/practice/preview", headers=ids["headers"], json=payload)
    second = client.post("/api/learn/practice/preview", headers=ids["headers"], json=payload)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["available"] == 2
    assert first.json()["q_type_mix"] == {"choice": 2}
    assert first.json()["seed"] == 42


def test_preview_wrong_scope_counts_due(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    db.add(
        WrongQuestion(
            user_id=ids["user_id"],
            question_id=ids["q_id"],
            status="active",
            next_review_at=datetime.utcnow() - timedelta(hours=2),
        )
    )
    db.commit()

    response = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json={"scope_type": "wrong", "count": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["available"] == 1
    assert body["due_review_count"] == 1
    assert body["seed"] > 0


def test_preview_rejects_unknown_scope(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    response = client.post(
        "/api/learn/practice/preview",
        headers=ids["headers"],
        json={"scope_type": "unknown"},
    )
    assert response.status_code == 422
