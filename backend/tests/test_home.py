"""P0-14 学习首页聚合接口测试。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import MasteryScore, WrongQuestion
from app.models.user import User


def _student(
    client: TestClient, db: Session, phone: str, grade: int = 3
) -> tuple[dict[str, str], int]:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    user = db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user.id


def _seed_books(db: Session, grade: int = 3) -> dict[tuple[str, str], int]:
    specs = [("chinese", "人教版"), ("math", "北师大版"), ("english", "牛津深圳版")]
    books: dict[tuple[str, str], int] = {}
    for subject, version in specs:
        book = Textbook(
            subject=subject, grade=grade, version=version, semester="first", is_active=True
        )
        db.add(book)
        db.flush()
        books[(subject, version)] = book.id
    db.commit()
    return books


def _seed_kp_with_mastery(db: Session, user_id: int, score: float) -> int:
    kp = KnowledgePoint(subject="math", name="两位数进位加法", grade=3)
    db.add(kp)
    db.flush()
    db.add(
        MasteryScore(user_id=user_id, knowledge_point_id=kp.id, score=score, confidence=2)
    )
    db.commit()
    return kp.id


def test_home_without_binding_recommends_textbooks(client: TestClient, db: Session) -> None:
    _seed_books(db)
    headers, _ = _student(client, db, "13200000001")

    response = client.get("/api/learn/home", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["grade"] == 3
    assert body["stage"] == "primary"
    assert body["grade_group"] == "primary_mid"
    assert body["semester"] == "first"
    assert body["needs_binding"] is True
    assert body["textbooks"] == []
    assert {item["subject"] for item in body["recommended"]} == {"chinese", "math", "english"}
    assert body["today_plan"]["practice_questions"] == 12
    assert body["today_plan"]["practice_minutes"] == 20
    assert body["recommendation"]["action"] == "daily"
    assert body["pending_exams"] == []


def test_home_after_binding_shows_textbooks(client: TestClient, db: Session) -> None:
    _seed_books(db)
    headers, _ = _student(client, db, "13200000002")
    bound = client.post("/api/me/textbooks/auto-bind", headers=headers)
    assert bound.status_code == 201, bound.text

    body = client.get("/api/learn/home", headers=headers).json()
    assert body["needs_binding"] is False
    assert body["recommended"] == []
    assert len(body["textbooks"]) == 3
    assert {item["subject"] for item in body["textbooks"]} == {"chinese", "math", "english"}


def test_home_prioritizes_due_review(client: TestClient, db: Session) -> None:
    headers, user_id = _student(client, db, "13200000003")
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="加减法", order_index=1)
    db.add(chapter)
    db.flush()
    question = Question(
        chapter_id=chapter.id,
        knowledge_point_id=_seed_kp_with_mastery(db, user_id, 30.0),
        subject="math",
        q_type="choice",
        content={"stem": "12 + 9 = ?"},
        answer={"value": "B"},
    )
    db.add(question)
    db.flush()
    db.add(
        WrongQuestion(
            user_id=user_id,
            question_id=question.id,
            status="active",
            next_review_at=datetime.utcnow() - timedelta(minutes=5),
        )
    )
    db.commit()

    body = client.get("/api/learn/home", headers=headers).json()
    assert body["today_plan"]["due_review"] == 1
    assert body["recommendation"]["action"] == "review"
    assert body["recommendation"]["label"] == "去复习"


def test_home_recommends_learn_kp_for_weak_mastery(
    client: TestClient, db: Session
) -> None:
    headers, user_id = _student(client, db, "13200000004")
    kp_id = _seed_kp_with_mastery(db, user_id, 20.0)

    body = client.get("/api/learn/home", headers=headers).json()
    assert body["recommendation"]["action"] == "learn_kp"
    assert body["recommendation"]["knowledge_point_id"] == kp_id


def test_home_recommends_practice_for_mid_mastery(
    client: TestClient, db: Session
) -> None:
    headers, user_id = _student(client, db, "13200000005")
    kp_id = _seed_kp_with_mastery(db, user_id, 55.0)

    body = client.get("/api/learn/home", headers=headers).json()
    assert body["recommendation"]["action"] == "practice"
    assert body["recommendation"]["knowledge_point_id"] == kp_id


def test_home_rejects_non_student(client: TestClient) -> None:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13200000006", "password": "pass1234", "role": "parent"},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/auth/login", data={"username": "13200000006", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get("/api/learn/home", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "NOT_STUDENT"
