"""P1-10 报告增强：能力维度、班级平均与趋势对比。"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.exam import Exam
from app.models.org import ClassMember, School, SchoolClass


def _student(
    client: TestClient, phone: str, grade: int = 3
) -> tuple[dict[str, str], int]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": phone, "password": "pass1234", "grade": grade},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/auth/login", data={"username": phone, "password": "pass1234"}
    )
    assert login.status_code == 200, login.text
    return (
        {"Authorization": f"Bearer {login.json()['access_token']}"},
        registered.json()["id"],
    )


def _seed_exam(db: Session, title: str = "三年级数学单元测") -> dict[str, int]:
    book = Textbook(
        subject="math", grade=3, version=f"北师大版-报告-{title}", semester="first"
    )
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
    fill = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="fill",
        difficulty=2,
        content={"stem": "3 × 14 = ?"},
        answer={"value": "42"},
    )
    multiple = Question(
        chapter_id=chapter.id,
        knowledge_point_id=kp.id,
        subject="math",
        q_type="multiple",
        difficulty=3,
        content={"stem": "下列哪些是偶数？"},
        options=[
            {"key": "A", "text": "2"},
            {"key": "B", "text": "3"},
            {"key": "C", "text": "8"},
        ],
        answer={"value": "A|C"},
    )
    db.add_all([choice, fill, multiple])
    db.flush()

    exam = Exam(
        title=title,
        subject="math",
        grade=3,
        exam_type="unit",
        total_score=100,
        time_limit_min=60,
        questions=[
            {"question_id": choice.id, "score": 40},
            {"question_id": fill.id, "score": 30},
            {"question_id": multiple.id, "score": 30},
        ],
        chapter_ids=[chapter.id],
        status="published",
    )
    db.add(exam)
    db.commit()
    return {
        "exam_id": exam.id,
        "choice_id": choice.id,
        "fill_id": fill.id,
        "multiple_id": multiple.id,
    }


def _submit(
    client: TestClient,
    headers: dict[str, str],
    seeded: dict[str, int],
    *,
    correct: bool,
) -> int:
    started = client.post(f"/api/exams/{seeded['exam_id']}/attempts", headers=headers)
    assert started.status_code == 200, started.text
    attempt_id = started.json()["id"]
    answers = (
        [
            {"question_id": seeded["choice_id"], "user_answer": {"value": "A"}},
            {"question_id": seeded["fill_id"], "user_answer": {"value": "42"}},
            {
                "question_id": seeded["multiple_id"],
                "user_answer": {"value": ["A", "C"]},
            },
        ]
        if correct
        else [
            {"question_id": seeded["choice_id"], "user_answer": {"value": "B"}},
            {"question_id": seeded["fill_id"], "user_answer": {"value": "41"}},
            {"question_id": seeded["multiple_id"], "user_answer": {"value": ["A"]}},
        ]
    )
    submitted = client.post(
        f"/api/exams/attempts/{attempt_id}/submit",
        headers=headers,
        json={"submit_token": "token-1", "answers": answers},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "completed"
    return attempt_id


def test_report_ability_stats_and_class_average(
    client: TestClient, db: Session
) -> None:
    headers_a, user_a = _student(client, "13620000011")
    headers_b, user_b = _student(client, "13620000012")
    seeded = _seed_exam(db)

    school = School(name="报告测试小学")
    db.add(school)
    db.flush()
    room = SchoolClass(
        school_id=school.id, grade=3, name="三年级1班", school_year="2026-2027"
    )
    db.add(room)
    db.flush()
    db.add_all(
        [
            ClassMember(class_id=room.id, student_id=user_a),
            ClassMember(class_id=room.id, student_id=user_b),
        ]
    )
    db.commit()

    attempt_a = _submit(client, headers_a, seeded, correct=True)
    _submit(client, headers_b, seeded, correct=False)

    report = client.get(f"/api/exams/attempts/{attempt_a}/report", headers=headers_a)
    assert report.status_code == 200, report.text
    body = report.json()

    abilities = {item["ability"]: item for item in body["ability_stats"]}
    assert list(abilities) == ["understand", "calculate", "analyze"]
    assert abilities["understand"]["label"] == "理解"
    assert abilities["calculate"]["label"] == "计算"
    assert abilities["analyze"]["label"] == "分析"
    assert abilities["understand"]["score_rate"] == 1.0
    assert abilities["calculate"]["score_rate"] == 1.0
    assert abilities["analyze"]["score_rate"] == 1.0

    average = body["class_average"]
    assert average["available"] is True
    assert average["class_name"] == "三年级1班"
    assert average["student_count"] == 2
    assert average["average_score"] == 50.0
    assert average["average_rate"] == 0.5

    assert body["trend"]["points"] == [] or body["trend"]["delta_rate"] is None


def test_report_trend_compares_recent_attempts(client: TestClient, db: Session) -> None:
    headers, _ = _student(client, "13620000013")
    first = _seed_exam(db, title="第一次单元测")
    second = _seed_exam(db, title="第二次单元测")

    _submit(client, headers, first, correct=False)
    second_attempt = _submit(client, headers, second, correct=True)

    report = client.get(f"/api/exams/attempts/{second_attempt}/report", headers=headers)
    assert report.status_code == 200, report.text
    body = report.json()

    points = body["trend"]["points"]
    assert len(points) == 2
    assert points[0]["exam_title"] == "第一次单元测"
    assert points[0]["score_rate"] == 0.0
    assert points[-1]["exam_title"] == "第二次单元测"
    assert points[-1]["score_rate"] == 1.0
    assert body["trend"]["delta_rate"] == 1.0
