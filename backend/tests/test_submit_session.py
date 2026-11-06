"""P0-24 提交兼容扩展：session_id/source 写入与掌握度来源拆分。"""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import MasteryScore, StudentQuestionRecord


def _setup(client: TestClient, db: Session) -> dict[str, Any]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13700000005", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    login = client.post(
        "/api/auth/login", data={"username": "13700000005", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()
    kp = KnowledgePoint(
        subject="math", name="分数的认识", grade=3, node_type="point", order_index=1
    )
    db.add(kp)
    db.flush()
    questions = []
    for i in range(3):
        question = Question(
            chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
            q_type="choice", difficulty=1,
            content={"stem": f"分数的认识-{i}"}, answer={"value": "A"},
        )
        db.add(question)
        questions.append(question)
    db.commit()
    return {
        "headers": headers,
        "chapter_id": chapter.id,
        "kp_id": kp.id,
        "question_ids": [q.id for q in questions],
    }


def test_submit_with_session_links_record(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    started = client.post(
        "/api/learn/start", headers=ids["headers"],
        json={"scope_type": "chapter", "scope_ids": [ids["chapter_id"]], "count": 2, "seed": 21},
    ).json()
    session_id = started["session_id"]
    question_id = started["questions"][0]["id"]

    response = client.post(
        "/api/learn/submit", headers=ids["headers"],
        json={
            "question_id": question_id, "user_answer": {"value": "A"},
            "session_id": session_id,
        },
    )
    assert response.status_code == 200, response.text

    resumed = client.get(f"/api/learn/sessions/{session_id}", headers=ids["headers"])
    assert resumed.json()["answered_count"] == 1

    record = db.scalar(
        select(StudentQuestionRecord).where(
            StudentQuestionRecord.question_id == question_id
        )
    )
    assert record is not None
    assert record.session_id == session_id
    assert record.source == "practice"


def test_mastery_source_breakdown(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    question_id = ids["question_ids"][0]

    for source in ("practice", "review"):
        response = client.post(
            "/api/learn/submit", headers=ids["headers"],
            json={
                "question_id": question_id, "user_answer": {"value": "A"},
                "source": source,
            },
        )
        assert response.status_code == 200, response.text

    mastery = db.scalar(
        select(MasteryScore).where(
            MasteryScore.user_id == 1, MasteryScore.knowledge_point_id == ids["kp_id"]
        )
    )
    assert mastery is not None
    breakdown = mastery.source_breakdown
    assert breakdown["practice"] == {"answered": 1, "correct": 1}
    assert breakdown["review"] == {"answered": 1, "correct": 1}


def test_foreign_session_and_mismatched_question_rejected(
    client: TestClient, db: Session
) -> None:
    ids = _setup(client, db)
    started = client.post(
        "/api/learn/start", headers=ids["headers"],
        json={"scope_type": "chapter", "scope_ids": [ids["chapter_id"]], "count": 2, "seed": 22},
    ).json()
    session_id = started["session_id"]

    other = client.post(
        "/api/auth/register",
        json={"phone": "13700000006", "password": "pass1234", "grade": 3},
    )
    assert other.status_code == 201, other.text
    login = client.post(
        "/api/auth/login", data={"username": "13700000006", "password": "pass1234"}
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    foreign = client.post(
        "/api/learn/submit", headers=other_headers,
        json={
            "question_id": ids["question_ids"][0], "user_answer": {"value": "A"},
            "session_id": session_id,
        },
    )
    assert foreign.status_code == 404

    # 题目不在会话内（会话只取了 2 题，取第 3 题）
    started_ids = {q["id"] for q in started["questions"]}
    outside = next(q for q in ids["question_ids"] if q not in started_ids)
    mismatch = client.post(
        "/api/learn/submit", headers=ids["headers"],
        json={"question_id": outside, "user_answer": {"value": "A"}, "session_id": session_id},
    )
    assert mismatch.status_code == 422


def test_legacy_submit_without_session(client: TestClient, db: Session) -> None:
    ids = _setup(client, db)
    question_id = ids["question_ids"][1]
    response = client.post(
        "/api/learn/submit", headers=ids["headers"],
        json={"question_id": question_id, "user_answer": {"value": "A"}},
    )
    assert response.status_code == 200, response.text
    record = db.scalar(
        select(StudentQuestionRecord).where(
            StudentQuestionRecord.question_id == question_id
        )
    )
    assert record is not None
    assert record.session_id is None
    assert record.source == "practice"
