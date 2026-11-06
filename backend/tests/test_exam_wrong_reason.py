"""P1-12 考试错题默认错因分类与错题复习优先级。"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Question
from app.models.practice import WrongQuestion
from app.models.user import User
from app.services import wrong_reason as wrong_reason_service


def _question(q_type: str) -> Question:
    return Question(
        chapter_id=1,
        knowledge_point_id=1,
        subject="math",
        q_type=q_type,
        content={"stem": "?"},
        answer={"value": "A"},
    )


def test_classify_exam_wrong_by_question_type() -> None:
    assert wrong_reason_service.classify_exam_wrong(
        _question("choice"), {"value": "B"}
    ) == "concept"
    assert wrong_reason_service.classify_exam_wrong(
        _question("judge"), {"value": False}
    ) == "concept"
    assert wrong_reason_service.classify_exam_wrong(
        _question("fill"), {"value": "41"}
    ) == "calculation"
    assert wrong_reason_service.classify_exam_wrong(
        _question("multiple"), {"value": ["A"]}
    ) == "reading"
    assert wrong_reason_service.classify_exam_wrong(
        _question("answer"), {"value": "作答"}
    ) == "method"


def test_classify_empty_answer_as_careless() -> None:
    assert wrong_reason_service.classify_exam_wrong(
        _question("choice"), None
    ) == "careless"
    assert wrong_reason_service.classify_exam_wrong(
        _question("fill"), {"value": "   "}
    ) == "careless"


def test_wrong_question_list_exposes_review_priority(
    client: TestClient, db: Session
) -> None:
    client.post(
        "/api/auth/register",
        json={"phone": "13622000011", "password": "pass1234", "grade": 3},
    )
    login = client.post(
        "/api/auth/login",
        data={"username": "13622000011", "password": "pass1234"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    user = db.scalar(select(User).where(User.phone == "13622000011"))
    assert user is not None

    high_q = _question("choice")
    low_q = _question("fill")
    db.add_all([high_q, low_q])
    db.flush()
    now = datetime.utcnow()
    db.add_all(
        [
            WrongQuestion(
                user_id=user.id,
                question_id=high_q.id,
                wrong_count=3,
                lapses=2,
                next_review_at=now - timedelta(days=3),
                last_wrong_at=now - timedelta(days=10),
            ),
            WrongQuestion(
                user_id=user.id,
                question_id=low_q.id,
                wrong_count=1,
                lapses=0,
                next_review_at=now + timedelta(days=3),
                last_wrong_at=now,
            ),
        ]
    )
    db.commit()

    rows = client.get("/api/learn/wrong-questions", headers=headers).json()
    assert len(rows) == 2
    assert rows[0]["question_id"] == high_q.id
    assert rows[0]["review_priority"] == "high"
    assert rows[0]["priority_score"] >= 6
    assert rows[1]["review_priority"] == "low"
    assert rows[1]["priority_score"] < 3
