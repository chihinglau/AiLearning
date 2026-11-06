"""P1-09 主观题自评：参考答案、评分点、自评量表与成绩回写。"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam
from app.models.practice import StudentQuestionRecord
from app.models.user import User


def _student(
    client: TestClient, phone: str = "13620000001", grade: int = 3
) -> tuple[dict[str, str], int]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": grade}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    user_id = registered.json()["id"]
    return {"Authorization": f"Bearer {login.json()['access_token']}"}, user_id


def _seed_exam(db: Session) -> dict[str, int]:
    book = Textbook(subject="math", grade=3, version="北师大版-自评", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="分数的应用", grade=3, node_type="point")
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
    subjective = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="answer",
        difficulty=3,
        content={"stem": "小明吃了 1/4 个蛋糕，还剩几分之几？请写出过程。"},
        answer={
            "value": "3/4",
            "scoring_points": ["列式正确（25 分）", "计算结果正确（25 分）"],
        },
        analysis="把整个蛋糕看作 1，1 - 1/4 = 3/4。",
    )
    db.add_all([choice, subjective])
    db.flush()

    exam = Exam(
        title="三年级数学单元测",
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=100,
        time_limit_min=60,
        questions=[
            {"question_id": choice.id, "score": 50, "section_index": 0, "section_name": "一、选择"},
            {"question_id": subjective.id, "score": 50, "section_index": 1, "section_name": "二、解答"},
        ],
        chapter_ids=[chapter.id],
        status="published",
    )
    db.add(exam)
    db.commit()
    return {"exam_id": exam.id, "choice_id": choice.id, "subjective_id": subjective.id}


def _submitted_attempt(client: TestClient, headers: dict[str, str], seeded: dict[str, int]) -> int:
    started = client.post(f"/api/exams/{seeded['exam_id']}/attempts", headers=headers)
    assert started.status_code == 200, started.text
    attempt_id = started.json()["id"]
    submitted = client.post(
        f"/api/exams/attempts/{attempt_id}/submit",
        headers=headers,
        json={
            "submit_token": "token-1",
            "answers": [
                {"question_id": seeded["choice_id"], "user_answer": {"value": "A"}},
                {"question_id": seeded["subjective_id"], "user_answer": {"value": "3/4"}},
            ],
        },
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "grading"
    return attempt_id


def test_report_lists_pending_subjective_with_reference(client: TestClient, db: Session) -> None:
    headers, _ = _student(client)
    seeded = _seed_exam(db)
    attempt_id = _submitted_attempt(client, headers, seeded)

    report = client.get(f"/api/exams/attempts/{attempt_id}/report", headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["status"] == "grading"
    assert body["total_score"] == 50

    pending = body["pending_subjective"]
    assert len(pending) == 1
    item = pending[0]
    assert item["question_id"] == seeded["subjective_id"]
    assert item["q_type"] == "answer"
    assert item["full_score"] == 50
    assert item["reference_answer"]["value"] == "3/4"
    assert item["scoring_points"] == ["列式正确（25 分）", "计算结果正确（25 分）"]
    assert item["user_answer"]["value"] == "3/4"
    assert item["self_score"] is None


def test_self_assess_writes_back_score_and_learning(client: TestClient, db: Session) -> None:
    headers, user_id = _student(client)
    seeded = _seed_exam(db)
    attempt_id = _submitted_attempt(client, headers, seeded)

    assessed = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=headers,
        json={"items": [{"question_id": seeded["subjective_id"], "score": 40}]},
    )
    assert assessed.status_code == 200, assessed.text
    body = assessed.json()
    assert body["status"] == "completed"
    assert body["objective_score"] == 50
    assert body["subjective_score"] == 40
    assert body["total_score"] == 90
    assert body["assessed_count"] == 1
    assert body["pending_count"] == 0

    report = client.get(f"/api/exams/attempts/{attempt_id}/report", headers=headers)
    assert report.status_code == 200, report.text
    report_body = report.json()
    assert report_body["status"] == "completed"
    assert report_body["pending_subjective"] == []
    assert report_body["total_score"] == 90

    records = db.scalar(
        select(func.count(StudentQuestionRecord.id)).where(
            StudentQuestionRecord.user_id == user_id
        )
    )
    assert records == 2

    # 重新自评不会重复回流学习记录
    rescored = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=headers,
        json={"items": [{"question_id": seeded["subjective_id"], "score": 50}]},
    )
    assert rescored.status_code == 200, rescored.text
    assert rescored.json()["total_score"] == 100
    assert (
        db.scalar(
            select(func.count(StudentQuestionRecord.id)).where(
                StudentQuestionRecord.user_id == user_id
            )
        )
        == 2
    )


def test_self_assess_validations(client: TestClient, db: Session) -> None:
    headers, _ = _student(client, "13620000002")
    seeded = _seed_exam(db)
    attempt_id = _submitted_attempt(client, headers, seeded)

    too_high = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=headers,
        json={"items": [{"question_id": seeded["subjective_id"], "score": 60}]},
    )
    assert too_high.status_code == 422
    assert too_high.json()["detail"]["code"] == "SELF_SCORE_OUT_OF_RANGE"

    objective = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=headers,
        json={"items": [{"question_id": seeded["choice_id"], "score": 10}]},
    )
    assert objective.status_code == 422
    assert objective.json()["detail"]["code"] == "SELF_ASSESS_NOT_SUBJECTIVE"

    duplicate = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=headers,
        json={
            "items": [
                {"question_id": seeded["subjective_id"], "score": 10},
                {"question_id": seeded["subjective_id"], "score": 20},
            ]
        },
    )
    assert duplicate.status_code == 422
    assert duplicate.json()["detail"]["code"] == "SELF_ASSESS_DUPLICATE"

    other_headers, _ = _student(client, "13620000003")
    forbidden = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=other_headers,
        json={"items": [{"question_id": seeded["subjective_id"], "score": 10}]},
    )
    assert forbidden.status_code == 404


def test_self_assess_requires_submitted_attempt(client: TestClient, db: Session) -> None:
    headers, _ = _student(client, "13620000004")
    seeded = _seed_exam(db)
    started = client.post(f"/api/exams/{seeded['exam_id']}/attempts", headers=headers)
    assert started.status_code == 200, started.text
    attempt_id = started.json()["id"]

    response = client.post(
        f"/api/exams/attempts/{attempt_id}/self-assess",
        headers=headers,
        json={"items": [{"question_id": seeded["subjective_id"], "score": 10}]},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EXAM_NOT_SUBMITTED"
