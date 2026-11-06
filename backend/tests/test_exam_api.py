"""P0-28 考试接口：开始/续答、防抖保存、幂等交卷与客观自动判。"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam, ExamAnswer, ExamBlueprint

PHONE = "13600000001"


def _student(client: TestClient) -> dict[str, str]:
    registered = client.post(
        "/api/auth/register", json={"phone": PHONE, "password": "pass1234", "grade": 3}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": PHONE, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _other_student(client: TestClient) -> dict[str, str]:
    phone = "13600000002"
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": 3}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_exam(db: Session, *, with_subjective: bool = True, title: str = "三年级数学单元测") -> dict[str, Any]:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="分数的认识", grade=3, node_type="point")
    db.add_all([chapter, kp])
    db.flush()

    choice = Question(
        chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
        q_type="choice", difficulty=1, content={"stem": "1/2 = ?"},
        options=[{"key": "A", "text": "0.5"}, {"key": "B", "text": "0.2"}],
        answer={"value": "A"}, analysis="1/2 = 0.5",
    )
    judge = Question(
        chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
        q_type="judge", difficulty=2, content={"stem": "1/2 大于 1/3"},
        answer={"value": True},
    )
    db.add_all([choice, judge])
    db.flush()

    entries = [
        {"question_id": choice.id, "score": 40, "section_index": 0, "section_name": "一、选择"},
        {"question_id": judge.id, "score": 20, "section_index": 1, "section_name": "二、判断"},
    ]
    if with_subjective:
        calc = Question(
            chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
            q_type="calc", difficulty=3, content={"stem": "3/4 - 1/4 = ?"},
            answer={"value": "1/2"}, analysis="同分母相减",
        )
        db.add(calc)
        db.flush()
        entries.append(
            {"question_id": calc.id, "score": 40, "section_index": 2, "section_name": "三、计算"}
        )

    exam = Exam(
        title=title, subject="math", grade=3, exam_type="unit", total_score=100,
        time_limit_min=90, questions=entries, chapter_ids=[chapter.id], status="published",
    )
    db.add(exam)
    db.commit()
    return {
        "exam": exam,
        "choice": choice,
        "judge": judge,
        "chapter": chapter,
        "entries": entries,
    }


def _start(client: TestClient, headers: dict[str, str], exam_id: int) -> dict[str, Any]:
    response = client.post(f"/api/exams/{exam_id}/attempts", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_list_and_detail_do_not_leak_answers(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db)

    listed = client.get("/api/exams", headers=headers)
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert len(body) == 1
    assert body[0]["category"] == "available"
    assert body[0]["question_count"] == 3
    assert body[0]["attempt"] is None

    detail = client.get(f"/api/exams/{data['exam'].id}", headers=headers)
    assert detail.status_code == 200, detail.text
    questions = detail.json()["questions"]
    assert len(questions) == 3
    assert questions[0]["score"] == 40
    assert questions[0]["section_name"] == "一、选择"
    assert "answer" not in questions[0]
    assert "analysis" not in questions[0]


def test_start_attempt_reuses_in_progress_and_resumes(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db)
    exam_id = data["exam"].id

    first = _start(client, headers, exam_id)
    assert first["status"] == "in_progress"
    assert first["seed"] == 1
    assert first["remaining_seconds"] > 0
    assert first["answers"] == []
    assert first["next_index"] == 0

    second = _start(client, headers, exam_id)
    assert second["id"] == first["id"]
    assert second["answers"] == []

    listed = client.get("/api/exams", headers=headers).json()
    assert listed[0]["category"] == "in_progress"
    assert listed[0]["attempt"]["id"] == first["id"]


def test_save_answers_is_idempotent_upsert(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db)
    attempt = _start(client, headers, data["exam"].id)

    first = client.patch(
        f"/api/exams/attempts/{attempt['id']}", headers=headers,
        json={"answers": [{"question_id": data["choice"].id, "user_answer": {"value": "A"}}]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["saved"] == 1

    second = client.patch(
        f"/api/exams/attempts/{attempt['id']}", headers=headers,
        json={"answers": [{"question_id": data["choice"].id, "user_answer": {"value": "B"}}]},
    )
    assert second.status_code == 200, second.text
    assert second.json()["saved"] == 1
    assert second.json()["answers"][0]["user_answer"]["value"] == "B"

    rows = list(
        db.scalars(
            select(ExamAnswer).where(
                ExamAnswer.attempt_id == attempt["id"],
                ExamAnswer.question_id == data["choice"].id,
            )
        )
    )
    assert len(rows) == 1
    assert rows[0].user_answer == {"value": "B"}


def test_save_answers_rejects_question_not_in_exam(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db)
    attempt = _start(client, headers, data["exam"].id)

    response = client.patch(
        f"/api/exams/attempts/{attempt['id']}", headers=headers,
        json={"answers": [{"question_id": 9999, "user_answer": {"value": "A"}}]},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "QUESTION_NOT_IN_EXAM"


def test_submit_grades_objective_and_is_idempotent(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db, with_subjective=True)
    attempt = _start(client, headers, data["exam"].id)

    client.patch(
        f"/api/exams/attempts/{attempt['id']}", headers=headers,
        json={
            "answers": [
                {"question_id": data["choice"].id, "user_answer": {"value": "A"}},
                {"question_id": data["judge"].id, "user_answer": {"value": False}},
            ]
        },
    )

    first = client.post(
        f"/api/exams/attempts/{attempt['id']}/submit", headers=headers,
        json={"submit_token": "token-1"},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["duplicate"] is False
    assert body["status"] == "grading"
    assert body["pending_grading"] is True
    assert body["objective_score"] == 40
    assert body["total_score"] == 40
    assert body["correct_count"] == 1
    assert body["question_count"] == 3
    assert body["submitted_at"] is not None

    second = client.post(
        f"/api/exams/attempts/{attempt['id']}/submit", headers=headers,
        json={"submit_token": "token-2"},
    )
    assert second.status_code == 200, second.text
    duplicated = second.json()
    assert duplicated["duplicate"] is True
    assert duplicated["objective_score"] == body["objective_score"]
    assert duplicated["submitted_at"] == body["submitted_at"]

    # 客观题 2 行 + 主观题未保存答案 → 不产生重复行
    rows = list(db.scalars(select(ExamAnswer).where(ExamAnswer.attempt_id == attempt["id"])))
    assert len(rows) == 2


def test_submit_objective_only_completes_immediately(client: TestClient, db: Session) -> None:
    headers = _student(client)
    data = _seed_exam(db, with_subjective=False, title="客观题单元测")
    attempt = _start(client, headers, data["exam"].id)

    response = client.post(
        f"/api/exams/attempts/{attempt['id']}/submit", headers=headers,
        json={
            "submit_token": "only-objective",
            "answers": [
                {"question_id": data["choice"].id, "user_answer": {"value": "A"}},
                {"question_id": data["judge"].id, "user_answer": {"value": True}},
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["pending_grading"] is False
    assert body["objective_score"] == 60
    assert body["subjective_score"] == 0.0
    assert body["correct_count"] == 2

    listed = client.get("/api/exams", headers=headers).json()
    assert listed[0]["category"] == "completed"


def test_attempt_is_private_to_owner(client: TestClient, db: Session) -> None:
    headers = _student(client)
    other = _other_student(client)
    data = _seed_exam(db)
    attempt = _start(client, headers, data["exam"].id)

    assert client.patch(
        f"/api/exams/attempts/{attempt['id']}", headers=other,
        json={"answers": []},
    ).status_code == 404
    assert client.post(
        f"/api/exams/attempts/{attempt['id']}/submit", headers=other,
        json={"submit_token": "x"},
    ).status_code == 404


def test_generate_exam_from_blueprint(
    client: TestClient, db: Session, admin_headers: dict[str, str]
) -> None:
    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    kp = KnowledgePoint(subject="math", name="分数的认识", grade=3, node_type="point")
    db.add_all([chapter, kp])
    db.flush()
    for index in range(6):
        db.add(
            Question(
                chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
                q_type="choice", difficulty=1 + index % 2,
                content={"stem": f"题 {index}"}, answer={"value": "A"},
            )
        )
    blueprint = ExamBlueprint(
        code="test_primary_unit", name="三年级数学单元测", subject="math", grade=3,
        exam_type="unit", total_score=100, time_limit_min=45,
        sections=[{"name": "一、选择", "q_type": "choice", "count": 5,
                   "score_each": 20, "difficulty": [1, 2]}],
        kp_coverage_min=0.8, difficulty_mix={"easy": 1},
    )
    db.add(blueprint)
    db.commit()

    response = client.post(
        "/api/exams/generate", headers=admin_headers,
        json={"blueprint_code": "test_primary_unit", "chapter_ids": [chapter.id], "seed": 9},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["question_count"] == 5
    assert body["total_score"] == 100
    assert body["fallback_count"] == 0
    assert body["insufficient"] is False

    exam = db.get(Exam, body["exam_id"])
    assert exam is not None
    assert exam.blueprint_id == blueprint.id
    assert exam.exam_type == "unit"
    assert exam.status == "published"
    assert len(exam.questions) == 5
