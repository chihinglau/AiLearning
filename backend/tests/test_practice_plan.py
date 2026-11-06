"""P0-22 组卷算法：KP 覆盖、题型配比、去重、时长预算、到期错题占比、预览=实际。"""

from datetime import datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Chapter, KnowledgePoint, Question, Textbook
from app.models.practice import StudentQuestionRecord, WrongQuestion
from app.models.user import User


def _setup(
    client: TestClient,
    db: Session,
    *,
    kps: int = 2,
    per_kp: int = 1,
    types: tuple[str, ...] = ("choice",),
    difficulty: int = 1,
) -> dict[str, Any]:
    registered = client.post(
        "/api/auth/register",
        json={"phone": "13700000002", "password": "pass1234", "grade": 3},
    )
    assert registered.status_code == 201, registered.text
    user = db.scalar(select(User).where(User.phone == "13700000002"))
    assert user is not None
    login = client.post(
        "/api/auth/login", data={"username": "13700000002", "password": "pass1234"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    book = Textbook(subject="math", grade=3, version="北师大版", semester="first")
    db.add(book)
    db.flush()
    chapter = Chapter(textbook_id=book.id, grade=3, name="第一单元", order_index=1)
    db.add(chapter)
    db.flush()

    kp_rows: list[KnowledgePoint] = []
    questions: list[Question] = []
    for kp_index in range(kps):
        kp = KnowledgePoint(
            subject="math", name=f"知识点{kp_index + 1}", grade=3,
            node_type="point", order_index=kp_index + 1,
        )
        db.add(kp)
        db.flush()
        kp_rows.append(kp)
        for i in range(per_kp):
            q_type = types[i % len(types)]
            question = Question(
                chapter_id=chapter.id, knowledge_point_id=kp.id, subject="math",
                q_type=q_type, difficulty=difficulty,
                content={"stem": f"{kp.name}-{i}"},
                answer={"value": "A"},
            )
            db.add(question)
            questions.append(question)
    db.commit()
    return {
        "headers": headers,
        "user_id": user.id,
        "book_id": book.id,
        "chapter_id": chapter.id,
        "kp_ids": [kp.id for kp in kp_rows],
        "question_ids": [q.id for q in questions],
    }


def _preview(client: TestClient, ids: dict[str, Any], **payload: Any) -> dict[str, Any]:
    response = client.post(
        "/api/learn/practice/preview", headers=ids["headers"],
        json={"scope_type": "chapter", "scope_ids": [ids["chapter_id"]], **payload},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_kp_coverage_at_least_80_percent(client: TestClient, db: Session) -> None:
    ids = _setup(client, db, kps=10, per_kp=3)
    body = _preview(client, ids, count=12, seed=1)
    assert body["range_kp_count"] == 10
    assert body["covered_kp_count"] >= 8
    assert body["kp_coverage"] >= 0.8


def test_type_ratio_primary_sync(client: TestClient, db: Session) -> None:
    ids = _setup(
        client, db, kps=4, per_kp=5, types=("choice", "judge", "fill", "answer")
    )
    body = _preview(client, ids, count=10, seed=3, mode="sync")
    assert body["count"] == 10
    assert body["q_type_mix"] == {"choice": 4, "judge": 2, "fill": 2, "answer": 2}


def test_due_review_quota_not_over_25_percent(client: TestClient, db: Session) -> None:
    ids = _setup(client, db, kps=6, per_kp=5)
    due_ids = ids["question_ids"][:12]
    for q_id in due_ids:
        db.add(
            WrongQuestion(
                user_id=ids["user_id"], question_id=q_id, status="active",
                next_review_at=datetime.utcnow() - timedelta(hours=1),
            )
        )
    db.commit()

    response = client.post(
        "/api/learn/start", headers=ids["headers"],
        json={
            "scope_type": "chapter", "scope_ids": [ids["chapter_id"]],
            "count": 12, "seed": 9,
        },
    )
    assert response.status_code == 200, response.text
    started = [q["id"] for q in response.json()["questions"]]
    used_due = len(set(started) & set(due_ids))
    assert used_due <= 3  # floor(12 * 25%)


def test_excludes_questions_answered_in_last_7_days(
    client: TestClient, db: Session
) -> None:
    ids = _setup(client, db, kps=4, per_kp=5)
    recent_ids = ids["question_ids"][:5]
    for q_id in recent_ids:
        db.add(
            StudentQuestionRecord(
                user_id=ids["user_id"], question_id=q_id, is_correct=True,
                attempted_at=datetime.utcnow() - timedelta(days=2),
            )
        )
    # 超出 7 天窗口的作答不影响去重
    db.add(
        StudentQuestionRecord(
            user_id=ids["user_id"], question_id=ids["question_ids"][5], is_correct=True,
            attempted_at=datetime.utcnow() - timedelta(days=10),
        )
    )
    db.commit()

    body = _preview(client, ids, count=20, seed=4)
    assert body["available"] == 15


def test_duration_budget_trims_questions(client: TestClient, db: Session) -> None:
    ids = _setup(client, db, kps=5, per_kp=4, types=("answer",))
    body = _preview(client, ids, count=20, seed=5, duration_limit_min=5)
    # 解答题按 120 秒/题，5 分钟最多 2 题
    assert body["count"] == 2
    assert body["estimated_minutes"] <= 5


def test_start_matches_preview_with_same_seed(client: TestClient, db: Session) -> None:
    ids = _setup(client, db, kps=5, per_kp=4, types=("choice", "fill", "judge"))
    payload = {
        "scope_type": "chapter", "scope_ids": [ids["chapter_id"]],
        "count": 8, "seed": 77,
    }
    preview = _preview(client, ids, count=8, seed=77)
    response = client.post("/api/learn/start", headers=ids["headers"], json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["seed"] == preview["seed"] == 77
    assert len(body["questions"]) == preview["count"]
