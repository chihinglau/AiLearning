from datetime import datetime, timedelta

from app.models.practice import StudentQuestionRecord
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

STUDENT_PHONE = "13900000000"


def _student(db: Session) -> User:
    user = db.scalar(select(User).where(User.phone == STUDENT_PHONE))
    assert user is not None
    return user


def _add_record(
    db: Session,
    user_id: int,
    question_id: int,
    minutes: int,
    when=None,
) -> None:
    db.add(
        StudentQuestionRecord(
            user_id=user_id,
            question_id=question_id,
            is_correct=True,
            duration_ms=minutes * 60_000,
            attempted_at=when or datetime.utcnow(),
        )
    )
    db.commit()


def test_usage_endpoint_defaults(
    client: TestClient,
    student_headers: dict[str, str],
) -> None:
    response = client.get("/api/users/me/usage", headers=student_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["used_minutes"] == 0
    assert body["limited"] is False
    assert body["remaining_minutes"] == body["daily_limit_minutes"]


def test_practice_blocked_after_daily_limit(
    client: TestClient,
    student_headers: dict[str, str],
    sample_question: int,
    db: Session,
) -> None:
    user = _student(db)
    user.daily_limit_minutes = 30
    db.commit()
    _add_record(db, user.id, sample_question, 30)

    response = client.post(
        "/api/practice/start", headers=student_headers, json={"count": 1}
    )
    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["code"] == "DAILY_LIMIT_REACHED"
    assert detail["limit_minutes"] == 30
    assert detail["used_minutes"] == 30
    assert int(response.headers["Retry-After"]) > 0

    status = client.get("/api/users/me/usage", headers=student_headers).json()
    assert status["limited"] is True
    assert status["remaining_minutes"] == 0
    assert status["unlocks_at"] is not None


def test_zero_limit_disables_teen_mode(
    client: TestClient,
    student_headers: dict[str, str],
    sample_chapter: int,
    sample_question: int,
    db: Session,
) -> None:
    user = _student(db)
    user.daily_limit_minutes = 0
    db.commit()
    _add_record(db, user.id, sample_question, 120)

    response = client.post(
        "/api/practice/start",
        headers=student_headers,
        json={"chapter_id": sample_chapter, "count": 1},
    )
    assert response.status_code == 200, response.text


def test_yesterday_records_do_not_count_today(
    client: TestClient,
    student_headers: dict[str, str],
    sample_chapter: int,
    sample_question: int,
    db: Session,
) -> None:
    user = _student(db)
    user.daily_limit_minutes = 30
    db.commit()
    _add_record(
        db,
        user.id,
        sample_question,
        30,
        when=datetime.utcnow() - timedelta(days=2),
    )

    status = client.get("/api/users/me/usage", headers=student_headers).json()
    assert status["used_minutes"] == 0
    assert status["limited"] is False

    response = client.post(
        "/api/practice/start",
        headers=student_headers,
        json={"chapter_id": sample_chapter, "count": 1},
    )
    assert response.status_code == 200, response.text
