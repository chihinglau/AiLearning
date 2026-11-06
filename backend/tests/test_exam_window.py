"""P1-08 考试窗口：开放/未开始/已结束与过期自动交卷。"""

from datetime import datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamBlueprint


def _student(client: TestClient, phone: str = "13610000001") -> dict[str, str]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": 3}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_exam(
    db: Session,
    *,
    title: str,
    exam_type: str = "unit",
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> dict[str, Any]:
    book = Textbook(
        subject="math", grade=3, version=f"北师大版-{title}", semester="first"
    )
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="分数的认识", grade=3, node_type="point")
    db.add_all([chapter, kp])
    db.flush()

    choice = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="choice",
        difficulty=1,
        content={"stem": "1/2 = ?"},
        options=[{"key": "A", "text": "0.5"}, {"key": "B", "text": "0.2"}],
        answer={"value": "A"},
    )
    judge = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="judge",
        difficulty=2,
        content={"stem": "1/2 大于 1/3"},
        answer={"value": True},
    )
    db.add_all([choice, judge])
    db.flush()

    exam = Exam(
        title=title,
        subject="math",
        grade=3,
        exam_type=exam_type,
        total_score=100,
        time_limit_min=60,
        questions=[
            {"question_id": choice.id, "score": 50, "section_index": 0, "section_name": "一、选择"},
            {"question_id": judge.id, "score": 50, "section_index": 1, "section_name": "二、判断"},
        ],
        chapter_ids=[chapter.id],
        status="published",
        window_start=window_start,
        window_end=window_end,
    )
    db.add(exam)
    db.commit()
    return {"exam": exam, "choice": choice}


def test_window_states_in_list_and_start_guard(client: TestClient, db: Session) -> None:
    headers = _student(client)
    now = datetime.utcnow()
    scheduled = _seed_exam(
        db,
        title="三年级数学期中",
        exam_type="midterm",
        window_start=now + timedelta(hours=1),
        window_end=now + timedelta(hours=3),
    )
    closed = _seed_exam(
        db,
        title="三年级数学期末",
        exam_type="final",
        window_end=now - timedelta(minutes=10),
    )

    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200, listed.text
    states = {item["title"]: item["window_state"] for item in listed.json()}
    assert states == {"三年级数学期中": "scheduled", "三年级数学期末": "closed"}

    denied_future = client.post(f"/api/exams/{scheduled['exam'].id}/attempts", headers=headers)
    assert denied_future.status_code == 403, denied_future.text
    assert denied_future.json()["detail"]["code"] == "EXAM_WINDOW_NOT_OPEN"

    denied_past = client.post(f"/api/exams/{closed['exam'].id}/attempts", headers=headers)
    assert denied_past.status_code == 403, denied_past.text
    assert denied_past.json()["detail"]["code"] == "EXAM_WINDOW_CLOSED"


def test_open_window_allows_and_expired_window_auto_finalizes(
    client: TestClient, db: Session
) -> None:
    headers = _student(client, "13610000002")
    now = datetime.utcnow()
    seeded = _seed_exam(
        db,
        title="三年级数学单元测",
        window_start=now - timedelta(hours=1),
        window_end=now + timedelta(hours=1),
    )

    started = client.post(f"/api/exams/{seeded['exam'].id}/attempts", headers=headers)
    assert started.status_code == 200, started.text
    attempt_id = started.json()["id"]

    seeded["exam"].window_end = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    saved = client.patch(
        f"/api/exams/attempts/{attempt_id}",
        headers=headers,
        json={
            "answers": [
                {"question_id": seeded["choice"].id, "user_answer": {"value": "A"}},
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["status"] == "completed"
    # 窗口关闭后不再接收新答案，按已保存内容自动交卷
    assert saved.json()["saved"] == 0

    duplicate = client.post(
        f"/api/exams/attempts/{attempt_id}/submit",
        headers=headers,
        json={"submit_token": "late-submit"},
    )
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["attempt_id"] == attempt_id

    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["category"] == "completed"


def test_generate_accepts_exam_window(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="分数的认识", grade=3, node_type="point")
    db.add_all([chapter, kp])
    db.flush()
    for index in range(2):
        db.add(
            Question(
                chapter_id=chapter.id,
                knowledge_point_id=kp.id,
                subject="math",
                q_type="fill",
                difficulty=2,
                content={"stem": f"填空{index}"},
                answer={"value": "1/2"},
            )
        )
    blueprint = ExamBlueprint(
        code="window_math_midterm",
        name="窗口测试卷",
        subject="math",
        grade=3,
        exam_type="midterm",
        total_score=10,
        time_limit_min=60,
        sections=[
            {
                "name": "一、填空",
                "q_type": "fill",
                "count": 2,
                "score_each": 5,
                "band": "medium",
            }
        ],
        kp_coverage_min=0.5,
        difficulty_mix={"medium": 1.0},
        is_active=True,
    )
    db.add(blueprint)
    db.commit()

    window_start = datetime.utcnow() + timedelta(hours=1)
    window_end = window_start + timedelta(hours=2)
    response = client.post(
        "/api/exams/generate",
        headers=admin_headers,
        json={
            "blueprint_code": "window_math_midterm",
            "chapter_ids": [chapter.id],
            "title": "三年级数学期中",
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        },
    )
    assert response.status_code == 200, response.text

    exam = db.get(Exam, response.json()["exam_id"])
    assert exam is not None
    assert exam.window_start is not None
    assert exam.window_end is not None
    assert exam.window_end - exam.window_start == timedelta(hours=2)

    headers = _student(client, "13610000003")
    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()[0]["window_state"] == "scheduled"
