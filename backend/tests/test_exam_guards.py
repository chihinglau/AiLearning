"""P0-39 考试边界：年级/发布状态守卫、列表过滤、超时结算、重复提交与报告权限。"""

from datetime import datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamAttempt


def _student(client: TestClient, phone: str = "13610000001", grade: int = 3) -> dict[str, str]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_exam(
    db: Session,
    *,
    grade: int = 3,
    status: str = "published",
    time_limit_min: int = 90,
    title: str = "三年级数学单元测",
) -> dict[str, Any]:
    book = db.scalar(
        select(Textbook).where(
            Textbook.subject == "math",
            Textbook.grade == grade,
            Textbook.version == "北师大版",
            Textbook.semester == "first",
        )
    )
    if book is None:
        book = Textbook(subject="math", grade=grade, version="北师大版", semester="first")
        db.add(book)
        db.flush()
    chapter = Chapter(textbook_id=book.id, grade=grade, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="分数的认识", grade=grade, node_type="point")
    db.add_all([chapter, kp])
    db.flush()
    question = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="choice",
        difficulty=1,
        content={"stem": "1/2 = ?"},
        options=[{"key": "A", "text": "0.5"}, {"key": "B", "text": "0.2"}],
        answer={"value": "A"},
        analysis="1/2 = 0.5",
    )
    db.add(question)
    db.flush()
    exam = Exam(
        title=title,
        subject="math",
        grade=grade,
        exam_type="unit",
        total_score=100,
        time_limit_min=time_limit_min,
        questions=[
            {
                "question_id": question.id,
                "score": 100,
                "section_index": 0,
                "section_name": "一、选择",
            }
        ],
        chapter_ids=[chapter.id],
        status=status,
    )
    db.add(exam)
    db.commit()
    return {"exam": exam, "question": question}


def _start(client: TestClient, headers: dict[str, str], exam_id: int) -> dict[str, Any]:
    response = client.post(f"/api/exams/{exam_id}/attempts", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_student_cannot_take_other_grade_exam(client: TestClient, db: Session) -> None:
    headers = _student(client, grade=4)
    data = _seed_exam(db, grade=3)

    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []

    detail = client.get(f"/api/exams/{data['exam'].id}", headers=headers)
    assert detail.status_code == 403
    assert detail.json()["detail"]["code"] == "GRADE_MISMATCH"

    started = client.post(f"/api/exams/{data['exam'].id}/attempts", headers=headers)
    assert started.status_code == 403


def test_unpublished_exam_is_hidden(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db, status="draft")

    assert client.get("/api/exams", headers=headers).json() == []
    assert client.get(f"/api/exams/{data['exam'].id}", headers=headers).status_code == 404
    assert client.post(f"/api/exams/{data['exam'].id}/attempts", headers=headers).status_code == 404


def test_list_filters_by_category_and_type(client: TestClient, db: Session) -> None:
    headers = _student(client)
    available = _seed_exam(db, title="待考单元测")
    completed = _seed_exam(db, title="已完成单元测")
    in_progress = _seed_exam(db, title="进行中单元测")

    attempt = _start(client, headers, completed["exam"].id)
    client.post(
        f"/api/exams/attempts/{attempt['id']}/submit",
        headers=headers,
        json={"submit_token": "done"},
    )
    _start(client, headers, in_progress["exam"].id)

    all_exams = client.get("/api/exams", headers=headers).json()
    assert {item["title"] for item in all_exams} == {
        available["exam"].title,
        completed["exam"].title,
        in_progress["exam"].title,
    }

    completed_only = client.get("/api/exams?status=completed", headers=headers).json()
    assert [item["title"] for item in completed_only] == [completed["exam"].title]
    assert completed_only[0]["attempt"]["status"] == "completed"

    doing_only = client.get("/api/exams?status=in_progress", headers=headers).json()
    assert [item["title"] for item in doing_only] == [in_progress["exam"].title]

    available_only = client.get("/api/exams?status=available", headers=headers).json()
    assert [item["title"] for item in available_only] == [available["exam"].title]

    assert len(client.get("/api/exams?type=unit", headers=headers).json()) == 3
    assert client.get("/api/exams?type=midterm", headers=headers).json() == []


def test_expired_attempt_is_finalized_then_new_attempt(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db, time_limit_min=1)
    first = _start(client, headers, data["exam"].id)

    row = db.get(ExamAttempt, first["id"])
    assert row is not None
    row.started_at = datetime.utcnow() - timedelta(minutes=3)
    db.commit()

    second = _start(client, headers, data["exam"].id)
    assert second["id"] != first["id"]
    assert second["seed"] == first["seed"] + 1
    assert second["remaining_seconds"] > 0

    db.refresh(row)
    assert row.status == "completed"
    assert row.submitted_at is not None
    assert row.submit_token == f"auto-expired-{first['id']}"


def test_save_on_expired_attempt_auto_submits(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db, time_limit_min=1)
    attempt = _start(client, headers, data["exam"].id)

    row = db.get(ExamAttempt, attempt["id"])
    assert row is not None
    row.started_at = datetime.utcnow() - timedelta(minutes=3)
    db.commit()

    response = client.patch(
        f"/api/exams/attempts/{attempt['id']}",
        headers=headers,
        json={"answers": [{"question_id": data["question"].id, "user_answer": {"value": "A"}}]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved"] == 1
    assert body["status"] == "completed"
    assert body["remaining_seconds"] == 0
    assert body["answers"][0]["is_correct"] is True


def test_patch_after_submit_is_read_only(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db, title="已交卷单元测")
    attempt = _start(client, headers, data["exam"].id)
    submitted = client.post(
        f"/api/exams/attempts/{attempt['id']}/submit",
        headers=headers,
        json={
            "submit_token": "first",
            "answers": [{"question_id": data["question"].id, "user_answer": {"value": "A"}}],
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "completed"

    patched = client.patch(
        f"/api/exams/attempts/{attempt['id']}",
        headers=headers,
        json={"answers": [{"question_id": data["question"].id, "user_answer": {"value": "B"}}]},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["saved"] == 0
    assert body["status"] == "completed"
    assert body["answers"][0]["user_answer"]["value"] == "A"

    resubmit = client.post(
        f"/api/exams/attempts/{attempt['id']}/submit",
        headers=headers,
        json={"submit_token": "second"},
    )
    assert resubmit.json()["duplicate"] is True
    assert resubmit.json()["objective_score"] == submitted.json()["objective_score"]


def test_seed_conflict_only_after_attempt_consumed(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db)
    first = _start(client, headers, data["exam"].id)
    client.post(
        f"/api/exams/attempts/{first['id']}/submit",
        headers=headers,
        json={"submit_token": "seed-1"},
    )

    conflict = client.post(
        f"/api/exams/{data['exam'].id}/attempts",
        headers=headers,
        json={"seed": first["seed"]},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "SEED_CONFLICT"

    retake = client.post(
        f"/api/exams/{data['exam'].id}/attempts",
        headers=headers,
        json={"seed": first["seed"] + 1},
    )
    assert retake.status_code == 200, retake.text
    assert retake.json()["seed"] == first["seed"] + 1
    assert retake.json()["status"] == "in_progress"


def test_report_requires_submission_and_owner(client: TestClient, db: Session) -> None:
    headers = _student(client, phone="13610000002")
    other = _student(client, phone="13610000003")
    data = _seed_exam(db)
    attempt = _start(client, headers, data["exam"].id)

    early = client.get(f"/api/exams/attempts/{attempt['id']}/report", headers=headers)
    assert early.status_code == 409
    assert early.json()["detail"]["code"] == "EXAM_NOT_SUBMITTED"

    submitted = client.post(
        f"/api/exams/attempts/{attempt['id']}/submit",
        headers=headers,
        json={
            "submit_token": "report-token",
            "duration_ms": 1234,
            "answers": [{"question_id": data["question"].id, "user_answer": {"value": "B"}}],
        },
    )
    assert submitted.status_code == 200, submitted.text

    report = client.get(f"/api/exams/attempts/{attempt['id']}/report", headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["attempt_id"] == attempt["id"]
    assert body["duration_ms"] == 1234
    assert body["status"] == "completed"
    assert body["total_score"] == 0
    assert body["wrong_questions"][0]["correct_answer"]["value"] == "A"
    assert body["wrong_questions"][0]["user_answer"]["value"] == "B"

    assert client.get(
        f"/api/exams/attempts/{attempt['id']}/report", headers=other
    ).status_code == 404


def test_report_kp_and_type_stats_cover_paper(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db)
    attempt = _start(client, headers, data["exam"].id)
    client.post(
        f"/api/exams/attempts/{attempt['id']}/submit",
        headers=headers,
        json={
            "submit_token": "stats-token",
            "answers": [{"question_id": data["question"].id, "user_answer": {"value": "A"}}],
        },
    )

    report = client.get(f"/api/exams/attempts/{attempt['id']}/report", headers=headers).json()
    assert report["accuracy"] == 1.0
    assert report["correct_count"] == 1
    assert report["answered_count"] == 1
    assert report["type_stats"][0]["q_type"] == "choice"
    assert report["type_stats"][0]["score_rate"] == 1.0
    assert report["kp_stats"][0]["name"] == "分数的认识"
    assert report["wrong_questions"] == []


def test_attempt_owner_cannot_be_hijacked(client: TestClient, db: Session) -> None:
    headers = _student(client, phone="13610000004")
    other = _student(client, phone="13610000005")
    data = _seed_exam(db)
    attempt = _start(client, headers, data["exam"].id)

    assert client.patch(
        f"/api/exams/attempts/{attempt['id']}",
        headers=other,
        json={"answers": []},
    ).status_code == 404
    assert client.post(
        f"/api/exams/attempts/{attempt['id']}/submit",
        headers=other,
        json={"submit_token": "hijack"},
    ).status_code == 404
    assert client.get(f"/api/exams/attempts/{attempt['id']}/report", headers=other).status_code == 404

    rows = list(db.scalars(select(ExamAttempt).where(ExamAttempt.id == attempt["id"])))
    assert len(rows) == 1
