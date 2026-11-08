from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import KnowledgePoint
from app.models.practice import MasteryScore, StudentQuestionRecord, WrongQuestion


def _create_question(client: TestClient, headers: dict[str, str], kp_id: int) -> int:
    textbook = client.post(
        "/api/admin/textbooks",
        headers=headers,
        json={"subject": "math", "grade": 1, "version": "人教版", "semester": "first"},
    )
    assert textbook.status_code == 201, textbook.text
    textbook_id = textbook.json()["id"]
    chapter = client.post(
        "/api/admin/chapters",
        headers=headers,
        json={
            "textbook_id": textbook_id,
            "grade": 1,
            "name": "单元一",
            "order_index": 1,
        },
    )
    assert chapter.status_code == 201, chapter.text
    question = client.post(
        "/api/admin/questions",
        headers=headers,
        json={
            "chapter_id": chapter.json()["id"],
            "knowledge_point_id": kp_id,
            "subject": "math",
            "q_type": "choice",
            "content": {"stem": "2 + 2 = ?"},
            "options": [{"key": "A", "text": "3"}, {"key": "B", "text": "4"}],
            "answer": {"value": "B"},
            "analysis": "2 + 2 = 4",
            "difficulty": 1,
        },
    )
    assert question.status_code == 201, question.text
    return int(question.json()["id"])


def _kp(db: Session) -> KnowledgePoint:
    kp = KnowledgePoint(subject="math", name="加法", grade=1, node_type="point")
    db.add(kp)
    db.commit()
    db.refresh(kp)
    return kp


def test_duplicate_client_key_is_skipped(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    kp = _kp(db)
    question_id = _create_question(client, admin_headers, kp.id)
    body = {
        "items": [
            {
                "client_key": "key-1",
                "question_id": question_id,
                "user_answer": {"value": "B"},
                "duration_ms": 500,
                "answered_at": datetime.utcnow().isoformat(),
                "source": "practice",
            }
        ]
    }

    first = client.post(
        "/api/learn/offline/attempts", headers=student_headers, json=body
    )
    assert first.status_code == 200, first.text
    result = first.json()["results"][0]
    assert result["is_correct"] is True
    assert result["skipped"] is False

    second = client.post(
        "/api/learn/offline/attempts", headers=student_headers, json=body
    )
    assert second.status_code == 200
    assert second.json()["results"][0]["skipped"] is True

    count = db.scalar(
        select(func.count(StudentQuestionRecord.id)).where(
            StudentQuestionRecord.question_id == question_id
        )
    )
    assert count == 1


def test_wrong_answer_updates_mastery_and_wrong_book(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    kp = _kp(db)
    question_id = _create_question(client, admin_headers, kp.id)
    response = client.post(
        "/api/learn/offline/attempts",
        headers=student_headers,
        json={
            "items": [
                {
                    "client_key": "key-wrong",
                    "question_id": question_id,
                    "user_answer": {"value": "A"},
                    "duration_ms": 1200,
                    "answered_at": datetime.utcnow().isoformat(),
                    "source": "practice",
                }
            ]
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["is_correct"] is False
    assert result["correct_answer"] == {"value": "B"}
    assert result["analysis"] == "2 + 2 = 4"

    mastery = db.scalar(
        select(MasteryScore).where(MasteryScore.knowledge_point_id == kp.id)
    )
    assert mastery is not None
    assert mastery.score < 60

    wrong = db.scalar(
        select(WrongQuestion).where(WrongQuestion.question_id == question_id)
    )
    assert wrong is not None
    assert wrong.status == "active"


def test_attempts_processed_in_answered_at_order(
    client: TestClient,
    db: Session,
    admin_headers: dict[str, str],
    student_headers: dict[str, str],
) -> None:
    kp = _kp(db)
    question_id = _create_question(client, admin_headers, kp.id)
    now = datetime.utcnow()
    earlier = (now - timedelta(hours=2)).isoformat()
    later = now.isoformat()

    response = client.post(
        "/api/learn/offline/attempts",
        headers=student_headers,
        json={
            "items": [
                {
                    "client_key": "late",
                    "question_id": question_id,
                    "user_answer": {"value": "A"},
                    "answered_at": later,
                },
                {
                    "client_key": "early",
                    "question_id": question_id,
                    "user_answer": {"value": "B"},
                    "answered_at": earlier,
                },
            ]
        },
    )
    assert response.status_code == 200

    records = list(
        db.scalars(
            select(StudentQuestionRecord)
            .where(StudentQuestionRecord.question_id == question_id)
            .order_by(StudentQuestionRecord.attempted_at)
        )
    )
    assert [record.client_key for record in records] == ["early", "late"]


def test_unknown_question_is_skipped(
    client: TestClient, student_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/learn/offline/attempts",
        headers=student_headers,
        json={
            "items": [
                {
                    "client_key": "missing",
                    "question_id": 999999,
                    "user_answer": {"value": "A"},
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["skipped"] is True


def test_offline_attempts_requires_login(client: TestClient) -> None:
    response = client.post(
        "/api/learn/offline/attempts", json={"items": []}
    )
    assert response.status_code == 401
