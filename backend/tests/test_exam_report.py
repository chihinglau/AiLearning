"""P0-29 考试报告：总分、题型得分、KP 得分率、错题清单与下一步。"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam

PHONE = "13600000011"


def _headers(client: TestClient, phone: str = PHONE) -> dict[str, str]:
    registered = client.post(
        "/api/auth/register", json={"phone": phone, "password": "pass1234", "grade": 3}
    )
    assert registered.status_code == 201, registered.text
    login = client.post("/api/auth/login", data={"username": phone, "password": "pass1234"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_exam(db: Session, *, with_subjective: bool = True) -> dict[str, Any]:
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
        answer={"value": "A"}, analysis="1/2 = 0.5",
    )
    judge = Question(
        chapter_id=chapter.id, knowledge_point_id=kp2.id, subject="math",
        q_type="judge", difficulty=2, content={"stem": "1/2 大于 1/3"},
        answer={"value": True}, analysis="分母相同看分子",
    )
    db.add_all([choice, judge])
    db.flush()

    entries = [
        {"question_id": choice.id, "score": 40, "section_name": "一、选择"},
        {"question_id": judge.id, "score": 20, "section_name": "二、判断"},
    ]
    if with_subjective:
        calc = Question(
            chapter_id=chapter.id, knowledge_point_id=kp1.id, subject="math",
            q_type="calc", difficulty=3, content={"stem": "3/4 - 1/4 = ?"},
            answer={"value": "1/2"}, analysis="同分母相减",
        )
        db.add(calc)
        db.flush()
        entries.append({"question_id": calc.id, "score": 40, "section_name": "三、计算"})

    exam = Exam(
        title="三年级数学单元测", subject="math", grade=3, exam_type="unit",
        total_score=100, time_limit_min=90, questions=entries, status="published",
    )
    db.add(exam)
    db.commit()
    return {"exam": exam, "choice": choice, "judge": judge}


def _submit(
    client: TestClient,
    headers: dict[str, str],
    exam_id: int,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    started = client.post(f"/api/exams/{exam_id}/attempts", headers=headers)
    assert started.status_code == 200, started.text
    attempt_id = started.json()["id"]
    submitted = client.post(
        f"/api/exams/attempts/{attempt_id}/submit", headers=headers,
        json={"submit_token": f"t-{attempt_id}", "answers": answers},
    )
    assert submitted.status_code == 200, submitted.text
    return submitted.json()


def test_report_requires_submission(client: TestClient, db: Session) -> None:
    headers = _headers(client)
    data = _seed_exam(db)
    started = client.post(f"/api/exams/{data['exam'].id}/attempts", headers=headers)
    assert started.status_code == 200, started.text

    response = client.get(
        f"/api/exams/attempts/{started.json()['id']}/report", headers=headers
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "EXAM_NOT_SUBMITTED"


def test_report_aggregates_scores_and_actions(client: TestClient, db: Session) -> None:
    headers = _headers(client)
    data = _seed_exam(db, with_subjective=True)
    submitted = _submit(
        client, headers, data["exam"].id,
        answers=[
            {"question_id": data["choice"].id, "user_answer": {"value": "A"}},
            {"question_id": data["judge"].id, "user_answer": {"value": False}},
        ],
    )

    response = client.get(
        f"/api/exams/attempts/{submitted['attempt_id']}/report", headers=headers
    )
    assert response.status_code == 200, response.text
    report = response.json()

    assert report["status"] == "grading"
    assert report["total_score"] == 40
    assert report["full_score"] == 100
    assert report["objective_score"] == 40
    assert report["subjective_score"] is None
    assert report["correct_count"] == 1
    assert report["answered_count"] == 2
    assert report["accuracy"] == 0.5
    assert report["question_count"] == 3

    type_stats = {item["q_type"]: item for item in report["type_stats"]}
    assert type_stats["choice"]["score_rate"] == 1.0
    assert type_stats["judge"]["score"] == 0
    assert type_stats["calc"]["score"] == 0
    assert type_stats["calc"]["full_score"] == 40

    kp_stats = {item["knowledge_point_id"]: item for item in report["kp_stats"]}
    assert kp_stats[data["choice"].knowledge_point_id]["name"] == "分数的认识"
    assert kp_stats[data["choice"].knowledge_point_id]["score_rate"] == 0.5
    assert kp_stats[data["judge"].knowledge_point_id]["score_rate"] == 0

    assert [item["question_id"] for item in report["wrong_questions"]] == [data["judge"].id]
    assert report["wrong_questions"][0]["correct_answer"] == {"value": True}

    actions = {item["action"]: item for item in report["next_actions"]}
    assert set(actions) == {"weak_practice", "wrong_review", "retake"}
    assert actions["weak_practice"]["count"] == 2
    assert actions["wrong_review"]["count"] == 1


def test_report_for_objective_only_exam(client: TestClient, db: Session) -> None:
    headers = _headers(client)
    data = _seed_exam(db, with_subjective=False)
    submitted = _submit(
        client, headers, data["exam"].id,
        answers=[
            {"question_id": data["choice"].id, "user_answer": {"value": "A"}},
            {"question_id": data["judge"].id, "user_answer": {"value": True}},
        ],
    )

    report = client.get(
        f"/api/exams/attempts/{submitted['attempt_id']}/report", headers=headers
    ).json()
    assert report["status"] == "completed"
    assert report["full_score"] == 100
    assert report["total_score"] == 60
    assert report["accuracy"] == 1.0
    assert report["wrong_questions"] == []
    actions = {item["action"] for item in report["next_actions"]}
    assert "wrong_review" not in actions
    assert "retake" in actions


def test_report_is_private_to_owner(client: TestClient, db: Session) -> None:
    headers = _headers(client)
    other = _headers(client, "13600000012")
    data = _seed_exam(db)
    submitted = _submit(
        client, headers, data["exam"].id,
        answers=[{"question_id": data["choice"].id, "user_answer": {"value": "A"}}],
    )

    response = client.get(
        f"/api/exams/attempts/{submitted['attempt_id']}/report", headers=other
    )
    assert response.status_code == 404
