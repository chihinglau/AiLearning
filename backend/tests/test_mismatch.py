"""P0-16 教材与年级冲突检测测试。"""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, Question, Textbook
from app.services import textbook as textbook_service
from app.models.user import User


def _student(client: TestClient, db: Session, phone: str, grade: int = 3) -> User:
    response = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert response.status_code == 201, response.text
    user = db.scalar(select(User).where(User.phone == phone))
    assert user is not None
    return user


def _seed_math(db: Session, grade: int = 3) -> int:
    book = Textbook(subject="math", grade=grade, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=grade, name="加减法", order_index=1)
    db.add(chapter)
    db.flush()
    question = Question(
        chapter_id=chapter.id,
        subject="math",
        q_type="choice",
        content={"stem": "12 + 9 = ?"},
        options=[{"key": "A", "text": "20"}, {"key": "B", "text": "21"}],
        answer={"value": "B"},
        difficulty=2,
    )
    db.add(question)
    db.commit()
    return chapter.id


def _login(client: TestClient, phone: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_binding_marks_mismatch_after_grade_change(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13400000001")
    _seed_math(db)
    textbook_service.auto_bind(db, user)
    db.commit()

    user.grade = 4
    db.commit()

    headers = _login(client, "13400000001")
    listed = client.get("/api/me/textbooks", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["mismatch"] is True

    home = client.get("/api/learn/home", headers=headers).json()
    assert home["mismatch_subjects"] == ["math"]
    assert home["textbooks"][0]["mismatch"] is True


def test_start_requires_confirmation_on_mismatch(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13400000002")
    chapter_id = _seed_math(db)
    textbook_service.auto_bind(db, user)
    db.commit()
    user.grade = 4
    db.commit()
    headers = _login(client, "13400000002")

    blocked = client.post(
        "/api/learn/start", headers=headers, json={"chapter_id": chapter_id, "count": 5}
    )
    assert blocked.status_code == 428
    assert blocked.json()["detail"]["code"] == "TEXTBOOK_MISMATCH"

    confirmed = client.post(
        "/api/learn/start",
        headers=headers,
        json={"chapter_id": chapter_id, "count": 5, "confirm_mismatch": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert len(confirmed.json()["questions"]) == 1


def test_start_without_mismatch_is_not_blocked(client: TestClient, db: Session) -> None:
    user = _student(client, db, "13400000003")
    chapter_id = _seed_math(db)
    textbook_service.auto_bind(db, user)
    db.commit()
    headers = _login(client, "13400000003")

    response = client.post(
        "/api/learn/start", headers=headers, json={"chapter_id": chapter_id, "count": 5}
    )
    assert response.status_code == 200, response.text
