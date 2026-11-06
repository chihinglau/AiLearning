"""P0-30 考试数据回流：答题记录、错题本与掌握度按考试权重更新。"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam
from app.models.practice import MasteryScore, StudentQuestionRecord, WrongQuestion

PHONE = "13600000021"


def _student(client: TestClient, phone: str = PHONE) -> tuple[dict[str, str], int]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": 3}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, registered.json()["id"]


def _seed_exam(db: Session, *, exam_type: str = "unit") -> dict[str, Any]:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    kp1 = KnowledgePoint(subject="math", name="分数的认识", grade=3, node_type="point")
    kp2 = KnowledgePoint(subject="math", name="分数比较", grade=3, node_type="point")
    db.add_all([chapter, kp1, kp2])
    db.flush()

    choice = Question(
        chapter_id=chapter.id, knowledge_point_id=kp1.id, subject="math",
        q_type="choice", difficulty=1, content={"stem": "1/2 = ?"},
        options=[{"key": "A", "text": "0.5"}, {"key": "B", "text": "0.2"}],
        answer={"value": "A"},
    )
    judge = Question(
        chapter_id=chapter.id, knowledge_point_id=kp2.id, subject="math",
        q_type="judge", difficulty=2, content={"stem": "1/2 大于 1/3"},
        answer={"value": True},
    )
    calc = Question(
        chapter_id=chapter.id, knowledge_point_id=kp1.id, subject="math",
        q_type="calc", difficulty=3, content={"stem": "3/4 - 1/4 = ?"},
        answer={"value": "1/2"},
    )
    db.add_all([choice, judge, calc])
    db.flush()

    exam = Exam(
        title="三年级数学单元测", subject="math", grade=3, exam_type=exam_type,
        total_score=100, time_limit_min=90, status="published",
        questions=[
            {"question_id": choice.id, "score": 40},
            {"question_id": judge.id, "score": 20},
            {"question_id": calc.id, "score": 40},
        ],
    )
    db.add(exam)
    db.commit()
    return {"exam": exam, "choice": choice, "judge": judge, "calc": calc, "kp1": kp1, "kp2": kp2}


def _submit(
    client: TestClient, headers: dict[str, str], data: dict[str, Any], token: str
) -> dict[str, Any]:
    started = client.post(f"/api/exams/{data['exam'].id}/attempts", headers=headers)
    assert started.status_code == 200, started.text
    submitted = client.post(
        f"/api/exams/attempts/{started.json()['id']}/submit", headers=headers,
        json={
            "submit_token": token,
            "answers": [
                {"question_id": data["choice"].id, "user_answer": {"value": "A"}},
                {"question_id": data["judge"].id, "user_answer": {"value": False}},
                {"question_id": data["calc"].id, "user_answer": {"value": "1/2"}},
            ],
        },
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


def test_unit_exam_backflow_writes_records_wrongbook_and_mastery(
    client: TestClient, db: Session
) -> None:
    headers, user_id = _student(client)
    data = _seed_exam(db, exam_type="unit")
    submitted = _submit(client, headers, data, "t1")

    records = list(
        db.scalars(
            select(StudentQuestionRecord).where(
                StudentQuestionRecord.attempt_id == submitted["attempt_id"]
            )
        )
    )
    assert len(records) == 2  # 主观题不回流
    assert {row.question_id for row in records} == {data["choice"].id, data["judge"].id}
    assert all(row.source == "exam" for row in records)
    assert all(row.kp_weight == 0.8 for row in records)
    assert {row.question_id: row.is_correct for row in records} == {
        data["choice"].id: True,
        data["judge"].id: False,
    }

    wrong = db.scalar(
        select(WrongQuestion).where(
            WrongQuestion.user_id == user_id,
            WrongQuestion.question_id == data["judge"].id,
        )
    )
    assert wrong is not None
    assert wrong.wrong_count == 1
    assert wrong.wrong_reason == "concept"

    correct_kp = db.scalar(
        select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id == data["kp1"].id,
        )
    )
    assert correct_kp is not None
    assert correct_kp.score == pytest.approx(48)  # EMA 0.6 * 0.8 * 100
    assert correct_kp.source_breakdown["exam"] == {"answered": 1, "correct": 1}

    wrong_kp = db.scalar(
        select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id == data["kp2"].id,
        )
    )
    assert wrong_kp is not None
    assert wrong_kp.score == 0
    assert wrong_kp.source_breakdown["exam"] == {"answered": 1, "correct": 0}


def test_backflow_is_not_repeated_on_idempotent_resubmit(
    client: TestClient, db: Session
) -> None:
    headers, _ = _student(client)
    data = _seed_exam(db)
    first = _submit(client, headers, data, "t1")
    second = client.post(
        f"/api/exams/attempts/{first['attempt_id']}/submit", headers=headers,
        json={"submit_token": "t2"},
    )
    assert second.status_code == 200, second.text
    assert second.json()["duplicate"] is True

    records = list(
        db.scalars(
            select(StudentQuestionRecord).where(
                StudentQuestionRecord.attempt_id == first["attempt_id"]
            )
        )
    )
    assert len(records) == 2

    wrong = db.scalar(
        select(WrongQuestion).where(WrongQuestion.question_id == data["judge"].id)
    )
    assert wrong is not None
    assert wrong.wrong_count == 1


def test_midterm_weight_is_lower(client: TestClient, db: Session) -> None:
    headers, user_id = _student(client, "13600000022")
    data = _seed_exam(db, exam_type="midterm")
    _submit(client, headers, data, "t1")

    records = list(
        db.scalars(select(StudentQuestionRecord).where(StudentQuestionRecord.source == "exam"))
    )
    assert all(row.kp_weight == 0.6 for row in records)

    correct_kp = db.scalar(
        select(MasteryScore).where(
            MasteryScore.user_id == user_id,
            MasteryScore.knowledge_point_id == data["kp1"].id,
        )
    )
    assert correct_kp is not None
    assert correct_kp.score == pytest.approx(36)  # EMA 0.6 * 0.6 * 100
